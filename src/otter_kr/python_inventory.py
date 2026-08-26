"""Deterministic Python file inventory and parse-health evidence."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path

from otter_kr.git_files import GitCliFileSource, TrackedFileSource


@dataclass(frozen=True, slots=True)
class PythonFileEvidence:
    path: str
    module: str
    module_kind: str
    bytes: int
    lines: int
    parse_status: str
    syntax_error: dict[str, int | str] | None = None

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        if self.syntax_error is None:
            del data["syntax_error"]
        return data


@dataclass(frozen=True, slots=True)
class PythonInventoryReport:
    language: str
    files: tuple[PythonFileEvidence, ...]
    warnings: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "language": self.language,
            "files": [file_evidence.to_dict() for file_evidence in self.files],
            "warnings": list(self.warnings),
        }


def _module_kind(relative_path: Path) -> str:
    if relative_path.name == "__init__.py":
        return "package"
    if relative_path.name.startswith("test_") or "tests" in relative_path.parts:
        return "test"
    return "module"


def _module_name(relative_path: Path) -> str:
    parts = list(relative_path.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _line_count(content: bytes) -> int:
    if not content:
        return 0
    return content.count(b"\n") + int(not content.endswith(b"\n"))


def inventory_python(
    repository: Path, file_source: TrackedFileSource | None = None
) -> PythonInventoryReport:
    """Inventory Python files without importing or executing repository code."""
    repository = repository.resolve()
    if not repository.is_dir():
        raise ValueError(f"Repository is not a directory: {repository}")

    files: list[PythonFileEvidence] = []
    warnings: list[dict[str, str]] = []
    candidates = (file_source or GitCliFileSource()).python_files(repository)
    for path in candidates:
        relative = path.relative_to(repository)
        relative_path = relative.as_posix()
        try:
            content = path.read_bytes()
        except OSError as error:
            files.append(
                PythonFileEvidence(
                    path=relative_path,
                    module=_module_name(relative),
                    module_kind=_module_kind(relative),
                    bytes=0,
                    lines=0,
                    parse_status="unreadable",
                )
            )
            warnings.append(
                {"code": "unreadable_file", "path": relative_path, "message": str(error)}
            )
            continue

        try:
            text = content.decode("utf-8")
        except UnicodeError:
            files.append(
                PythonFileEvidence(
                    path=relative_path,
                    module=_module_name(relative),
                    module_kind=_module_kind(relative),
                    bytes=len(content),
                    lines=_line_count(content),
                    parse_status="unreadable",
                )
            )
            warnings.append(
                {
                    "code": "unreadable_file",
                    "path": relative_path,
                    "message": "File could not be decoded as UTF-8.",
                }
            )
            continue

        try:
            ast.parse(text, filename=relative_path)
        except SyntaxError as error:
            syntax_error = {
                "line": error.lineno or 0,
                "column": error.offset or 0,
                "message": error.msg,
            }
            files.append(
                PythonFileEvidence(
                    path=relative_path,
                    module=_module_name(relative),
                    module_kind=_module_kind(relative),
                    bytes=len(content),
                    lines=_line_count(content),
                    parse_status="syntax_error",
                    syntax_error=syntax_error,
                )
            )
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

        files.append(
            PythonFileEvidence(
                path=relative_path,
                module=_module_name(relative),
                module_kind=_module_kind(relative),
                bytes=len(content),
                lines=_line_count(content),
                parse_status="ok",
            )
        )

    return PythonInventoryReport(language="python", files=tuple(files), warnings=tuple(warnings))
