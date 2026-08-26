"""Python identifier evidence extracted without executing repository code."""

from __future__ import annotations

import ast
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from otter_kr.git_files import GitCliFileSource, TrackedFileSource

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_SEPARATORS = re.compile(r"[^A-Za-z0-9]+")


@dataclass(frozen=True, slots=True)
class NameOccurrence:
    path: str
    line: int
    column: int
    name: str
    kind: str


@dataclass(frozen=True, slots=True)
class ParseFailure:
    path: str
    line: int | None
    message: str


@dataclass(frozen=True, slots=True)
class NameReport:
    repository: str
    query: str
    language: str
    files_scanned: int
    occurrences: tuple[NameOccurrence, ...]
    parse_failures: tuple[ParseFailure, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "language": self.language,
            "files_scanned": self.files_scanned,
            "occurrences": [asdict(occurrence) for occurrence in self.occurrences],
            "parse_failures": [asdict(failure) for failure in self.parse_failures],
        }


def _identifier_words(identifier: str) -> tuple[str, ...]:
    separated = _CAMEL_BOUNDARY.sub("_", identifier)
    return tuple(word.casefold() for word in _SEPARATORS.split(separated) if word)


def _matches(identifier: str, query: str) -> bool:
    query_words = _identifier_words(query)
    identifier_words = _identifier_words(identifier)
    return bool(query_words) and all(word in identifier_words for word in query_words)


class _NameCollector(ast.NodeVisitor):
    def __init__(self, relative_path: str, query: str) -> None:
        self.relative_path = relative_path
        self.query = query
        self.occurrences: list[NameOccurrence] = []

    def _record(self, name: str, node: ast.AST, kind: str) -> None:
        if _matches(name, self.query):
            self.occurrences.append(
                NameOccurrence(
                    path=self.relative_path,
                    line=node.lineno,
                    column=node.col_offset,
                    name=name,
                    kind=kind,
                )
            )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._record(node.name, node, "class")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._record(node.name, node, "function")
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._record(node.name, node, "function")
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:
        self._record(node.arg, node, "parameter")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        kind = "reference" if isinstance(node.ctx, ast.Load) else "assignment"
        self._record(node.id, node, kind)


def find_names(
    repository: Path, query: str, file_source: TrackedFileSource | None = None
) -> NameReport:
    """Find exact or lexical-family identifier occurrences in a Python repository."""
    repository = repository.resolve()
    if not repository.is_dir():
        raise ValueError(f"Repository is not a directory: {repository}")
    if not _identifier_words(query):
        raise ValueError("Query must contain at least one letter or number")

    occurrences: list[NameOccurrence] = []
    failures: list[ParseFailure] = []
    python_files = (file_source or GitCliFileSource()).python_files(repository)
    for path in python_files:
        relative_path = path.relative_to(repository).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative_path)
        except (SyntaxError, UnicodeError) as error:
            failures.append(
                ParseFailure(
                    path=relative_path,
                    line=getattr(error, "lineno", None),
                    message=str(error),
                )
            )
            continue
        collector = _NameCollector(relative_path, query)
        collector.visit(tree)
        occurrences.extend(collector.occurrences)

    return NameReport(
        repository=str(repository),
        query=query,
        language="python",
        files_scanned=len(python_files),
        occurrences=tuple(
            sorted(occurrences, key=lambda item: (item.path, item.line, item.column, item.kind))
        ),
        parse_failures=tuple(failures),
    )
