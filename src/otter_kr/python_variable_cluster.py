"""Exact-name occurrence evidence for the variable-cluster admission sequence."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path

from otter_kr.git_files import GitCliFileSource


@dataclass(frozen=True, slots=True)
class VariableOccurrence:
    path: str
    line: int
    column: int
    scope: str
    role: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class VariableClusterReport:
    names: tuple[str, ...]
    occurrences: tuple[VariableOccurrence, ...]
    warnings: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "names": list(self.names),
            "occurrences": [item.to_dict() for item in self.occurrences],
            "warnings": list(self.warnings),
        }


class _OccurrenceCollector(ast.NodeVisitor):
    def __init__(self, path: str, name: str) -> None:
        self.path = path
        self.name = name
        self.scopes: list[str] = []
        self.occurrences: list[VariableOccurrence] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.scopes.append(node.name)
        self.generic_visit(node)
        self.scopes.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scopes.append(node.name)
        self.generic_visit(node)
        self.scopes.pop()

    def visit_Name(self, node: ast.Name) -> None:
        if node.id == self.name:
            role = (
                "read"
                if isinstance(node.ctx, ast.Load)
                else "delete"
                if isinstance(node.ctx, ast.Del)
                else "write"
            )
            self.occurrences.append(
                VariableOccurrence(
                    self.path, node.lineno, node.col_offset, ".".join(self.scopes), role
                )
            )

    def visit_arg(self, node: ast.arg) -> None:
        if node.arg == self.name:
            self.occurrences.append(
                VariableOccurrence(
                    self.path, node.lineno, node.col_offset, ".".join(self.scopes), "parameter"
                )
            )


def find_variable_occurrences(repository: Path, name: str) -> VariableClusterReport:
    if not name.isidentifier():
        raise ValueError("name must be a Python identifier")
    occurrences: list[VariableOccurrence] = []
    warnings: list[dict[str, str]] = []
    for path in GitCliFileSource().python_files(repository.resolve()):
        relative = path.relative_to(repository.resolve()).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except (OSError, UnicodeError, SyntaxError) as error:
            warnings.append({"path": relative, "message": str(error)})
            continue
        collector = _OccurrenceCollector(relative, name)
        collector.visit(tree)
        occurrences.extend(collector.occurrences)
    return VariableClusterReport((name,), tuple(occurrences), tuple(warnings))
