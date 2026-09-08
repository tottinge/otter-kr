"""Exact-name occurrence evidence for the variable-cluster admission sequence."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path

from otter_kr.git_files import GitCliFileSource


@dataclass(frozen=True, slots=True)
class GuardContext:
    kind: str
    line: int
    column: int
    expression: str
    branch: str
    depth: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class VariableOccurrence:
    path: str
    line: int
    column: int
    scope: str
    role: str
    guards: tuple[GuardContext, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "scope": self.scope,
            "role": self.role,
            "guards": [guard.to_dict() for guard in self.guards],
        }


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
    def __init__(self, path: str, name: str, source: str) -> None:
        self.path = path
        self.name = name
        self.source = source
        self.scopes: list[str] = []
        self.guards: list[GuardContext] = []
        self.occurrences: list[VariableOccurrence] = []

    def _guard(self, node: ast.AST, branch: str, kind: str) -> GuardContext:
        expression = ast.get_source_segment(self.source, node) or ""
        return GuardContext(
            kind,
            node.lineno,
            node.col_offset,
            expression,
            branch,
            len(self.guards) or 1,
        )

    def _visit_guarded(
        self, test: ast.AST, body: list[ast.stmt], orelse: list[ast.stmt], kind: str
    ) -> None:
        self.visit(test)
        guard = self._guard(test, "body", kind)
        self.guards.append(guard)
        for statement in body:
            self.visit(statement)
        self.guards[-1] = guard = self._guard(test, "else", kind)
        for statement in orelse:
            self.visit(statement)
        self.guards.pop()

    def visit_If(self, node: ast.If) -> None:
        self._visit_guarded(node.test, node.body, node.orelse, "if")

    def visit_While(self, node: ast.While) -> None:
        self.visit(node.test)
        self.guards.append(self._guard(node.test, "body", "while"))
        for statement in node.body:
            self.visit(statement)
        self.guards.pop()
        for statement in node.orelse:
            self.visit(statement)

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
                    self.path,
                    node.lineno,
                    node.col_offset,
                    ".".join(self.scopes),
                    role,
                    tuple(self.guards),
                )
            )

    def visit_arg(self, node: ast.arg) -> None:
        if node.arg == self.name:
            self.occurrences.append(
                VariableOccurrence(
                    self.path,
                    node.lineno,
                    node.col_offset,
                    ".".join(self.scopes),
                    "parameter",
                    tuple(self.guards),
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
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=relative)
        except (OSError, UnicodeError, SyntaxError) as error:
            warnings.append({"path": relative, "message": str(error)})
            continue
        collector = _OccurrenceCollector(relative, name, source)
        collector.visit(tree)
        occurrences.extend(collector.occurrences)
    return VariableClusterReport((name,), tuple(occurrences), tuple(warnings))
