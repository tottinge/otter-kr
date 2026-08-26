"""Deterministic evidence for repeated non-trivial Python literals."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path

from otter_kr.git_files import GitCliFileSource, TrackedFileSource


@dataclass(frozen=True, slots=True)
class LiteralOccurrence:
    path: str
    line: int
    column: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RepeatedLiteral:
    kind: str
    value: str
    count: int
    occurrences: tuple[LiteralOccurrence, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "value": self.value,
            "count": self.count,
            "occurrences": [occurrence.to_dict() for occurrence in self.occurrences],
        }


@dataclass(frozen=True, slots=True)
class LiteralReport:
    language: str
    literals: tuple[RepeatedLiteral, ...]
    warnings: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "language": self.language,
            "literals": [literal.to_dict() for literal in self.literals],
            "warnings": list(self.warnings),
        }


def _literal_info(node: ast.Constant) -> tuple[str, str] | None:
    value = node.value
    if value is None or isinstance(value, bool | type(Ellipsis)):
        return None
    if isinstance(value, int | float | complex) and value in {-1, 0, 1}:
        return None
    if isinstance(value, str | bytes) and not value:
        return None
    if isinstance(value, str):
        return "string", value
    if isinstance(value, bytes):
        return "bytes", value.hex()
    if isinstance(value, int):
        return "integer", str(value)
    if isinstance(value, float):
        return "float", repr(value)
    if isinstance(value, complex):
        return "complex", repr(value)
    return None


class _LiteralCollector(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.values: dict[tuple[str, str], list[LiteralOccurrence]] = {}

    def visit_Constant(self, node: ast.Constant) -> None:
        info = _literal_info(node)
        if info is not None:
            kind, value = info
            self.values.setdefault((kind, value), []).append(
                LiteralOccurrence(self.path, node.lineno, node.col_offset)
            )
        self.generic_visit(node)


def find_repeated_literals(
    repository: Path, file_source: TrackedFileSource | None = None
) -> LiteralReport:
    """Report repeated non-trivial constants in tracked Python files."""
    repository = repository.resolve()
    if not repository.is_dir():
        raise ValueError(f"Repository is not a directory: {repository}")

    grouped: dict[tuple[str, str], list[LiteralOccurrence]] = {}
    warnings: list[dict[str, str]] = []
    for path in (file_source or GitCliFileSource()).python_files(repository):
        relative_path = path.relative_to(repository).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=relative_path)
        except UnicodeError:
            warnings.append(
                {
                    "code": "unreadable_file",
                    "path": relative_path,
                    "message": "File could not be decoded as UTF-8.",
                }
            )
            continue
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
        collector = _LiteralCollector(relative_path)
        collector.visit(tree)
        for key, occurrences in collector.values.items():
            grouped.setdefault(key, []).extend(occurrences)

    literals = tuple(
        RepeatedLiteral(
            kind,
            value,
            len(occurrences),
            tuple(sorted(occurrences, key=lambda item: (item.path, item.line, item.column))),
        )
        for (kind, value), occurrences in sorted(grouped.items())
        if len(occurrences) > 1
    )
    return LiteralReport(
        "python", literals, tuple(sorted(warnings, key=lambda item: (item["path"], item["code"])))
    )
