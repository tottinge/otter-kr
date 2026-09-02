"""Deterministic Python import-edge evidence."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path

from otter_kr.git_files import GitCliFileSource, TrackedFileSource


@dataclass(frozen=True, slots=True)
class PythonImportEdge:
    path: str
    source_module: str
    target_module: str
    imported_names: tuple[str, ...]
    relative_level: int
    line: int

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["imported_names"] = list(self.imported_names)
        return data


@dataclass(frozen=True, slots=True)
class PythonImportReport:
    language: str
    edges: tuple[PythonImportEdge, ...]
    warnings: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "language": self.language,
            "edges": [edge.to_dict() for edge in self.edges],
            "warnings": list(self.warnings),
        }


def _module_name(relative_path: Path) -> str:
    parts = list(relative_path.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _resolve_relative_target(
    source_module: str, level: int, module: str | None, *, source_is_package: bool = False
) -> tuple[str, bool]:
    if level == 0:
        return module or "", False

    source_parts = source_module.split(".")
    parent_parts = source_parts if source_is_package else source_parts[:-1]
    if level > len(parent_parts):
        return module or "", True

    anchor_parts = parent_parts[: len(parent_parts) - level + 1]
    if module:
        anchor_parts.extend(module.split("."))
    return ".".join(anchor_parts), False


def import_python(
    repository: Path, file_source: TrackedFileSource | None = None
) -> PythonImportReport:
    """Report statically visible import edges for tracked Python files."""
    repository = repository.resolve()
    if not repository.is_dir():
        raise ValueError(f"Repository is not a directory: {repository}")

    edges: list[PythonImportEdge] = []
    warnings: list[dict[str, str]] = []
    candidates = (file_source or GitCliFileSource()).python_files(repository)
    for path in candidates:
        relative = path.relative_to(repository)
        relative_path = relative.as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError:
            warnings.append(
                {
                    "code": "unreadable_file",
                    "path": relative_path,
                    "message": "File could not be decoded as UTF-8.",
                }
            )
            continue
        source_module = _module_name(relative)
        try:
            tree = ast.parse(text, filename=relative_path)
        except SyntaxError as error:
            warnings.append(
                {
                    "code": "invalid_python",
                    "path": relative_path,
                    "message": (
                        f"Syntax error at line {error.lineno}, column {error.offset}: {error.msg}"
                    ),
                }
            )
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    edges.append(
                        PythonImportEdge(
                            path=relative_path,
                            source_module=source_module,
                            target_module=alias.name,
                            imported_names=(),
                            relative_level=0,
                            line=node.lineno,
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                target_module, unresolved = _resolve_relative_target(
                    source_module,
                    node.level,
                    node.module,
                    source_is_package=relative.name == "__init__.py",
                )
                if unresolved:
                    warnings.append(
                        {
                            "code": "unresolved_relative_import",
                            "path": relative_path,
                            "message": (
                                f"Relative import level {node.level} escapes the tracked package "
                                f"boundary for {source_module}."
                            ),
                        }
                    )
                edges.append(
                    PythonImportEdge(
                        path=relative_path,
                        source_module=source_module,
                        target_module=target_module,
                        imported_names=tuple(alias.name for alias in node.names),
                        relative_level=node.level,
                        line=node.lineno,
                    )
                )

    return PythonImportReport(
        language="python",
        edges=tuple(
            sorted(
                edges,
                key=lambda edge: (
                    edge.path,
                    edge.line,
                    edge.target_module,
                    edge.imported_names,
                    edge.relative_level,
                ),
            )
        ),
        warnings=tuple(
            sorted(
                warnings, key=lambda warning: (warning["path"], warning["code"], warning["message"])
            )
        ),
    )
