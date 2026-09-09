"""Bounded evidence about one Python carrier's construction and field operations."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path

from otter_kr.git_files import GitCliFileSource, TrackedFileSource


@dataclass(frozen=True, slots=True)
class FieldOperation:
    carrier: str
    field: str
    path: str
    line: int
    column: int
    scope: str
    kind: str
    expression: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ConstructionSite:
    carrier: str
    path: str
    line: int
    column: int
    scope: str
    kind: str
    expression: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ObjectLifecycleReport:
    carrier: str
    files_scanned: int
    constructions: tuple[ConstructionSite, ...]
    operations: tuple[FieldOperation, ...]
    parse_failures: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "language": "python",
            "carrier": self.carrier,
            "files_scanned": self.files_scanned,
            "constructions": [item.to_dict() for item in self.constructions],
            "operations": [item.to_dict() for item in self.operations],
            "parse_failures": list(self.parse_failures),
        }


class _LifecycleCollector(ast.NodeVisitor):
    _MUTATORS = {
        "append",
        "clear",
        "extend",
        "insert",
        "pop",
        "remove",
        "reverse",
        "sort",
        "update",
    }

    def __init__(self, carrier: str, path: str, source: str) -> None:
        self.carrier = carrier
        self.path = path
        self.source = source
        self.scopes: list[str] = []
        self.constructions: list[ConstructionSite] = []
        self.operations: list[FieldOperation] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.scopes.append(node.name)
        self.generic_visit(node)
        self.scopes.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scopes.append(node.name)
        self.generic_visit(node)
        self.scopes.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        if any(
            isinstance(target, ast.Name) and target.id == self.carrier for target in node.targets
        ):
            self._construction(node, "assignment")
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if (
            isinstance(node.target, ast.Name)
            and node.target.id == self.carrier
            and node.value is not None
        ):
            self._construction(node, "annotated_assignment")
        self.generic_visit(node)

    def _construction(self, node: ast.Assign | ast.AnnAssign, kind: str) -> None:
        value = node.value
        self.constructions.append(
            ConstructionSite(
                self.carrier,
                self.path,
                node.lineno,
                node.col_offset,
                ".".join(self.scopes),
                kind,
                ast.get_source_segment(self.source, value) or "",
            )
        )

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.value, ast.Name) and node.value.id == self.carrier:
            kind = {
                ast.Load: "field_read",
                ast.Store: "field_write",
                ast.Del: "field_delete",
            }.get(type(node.ctx))
            if kind is not None:
                self.operations.append(self._operation(node, kind))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        is_mutator = (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Attribute)
            and isinstance(node.func.value.value, ast.Name)
            and node.func.value.value.id == self.carrier
            and node.func.attr in self._MUTATORS
        )
        if is_mutator:
            self.operations.append(self._operation(node.func.value, "mutative_call"))
            for argument in node.args:
                self.visit(argument)
            for keyword in node.keywords:
                self.visit(keyword.value)
            return
        self.generic_visit(node)

    def _operation(self, node: ast.Attribute, kind: str) -> FieldOperation:
        return FieldOperation(
            self.carrier,
            node.attr,
            self.path,
            node.lineno,
            node.col_offset,
            ".".join(self.scopes),
            kind,
            ast.get_source_segment(self.source, node) or "",
        )


def find_object_lifecycle(
    repository: Path, carrier: str, file_source: TrackedFileSource | None = None
) -> ObjectLifecycleReport:
    repository = repository.resolve()
    if not repository.is_dir():
        raise ValueError(f"Repository is not a directory: {repository}")
    if not carrier or not carrier.isidentifier():
        raise ValueError("Carrier must be a Python identifier")
    files = (file_source or GitCliFileSource()).python_files(repository)
    constructions: list[ConstructionSite] = []
    operations: list[FieldOperation] = []
    failures: list[dict[str, object]] = []
    for path in files:
        relative = path.relative_to(repository).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=relative)
        except (SyntaxError, UnicodeError) as error:
            failures.append({"path": relative, "message": str(error)})
            continue
        collector = _LifecycleCollector(carrier, relative, source)
        collector.visit(tree)
        constructions.extend(collector.constructions)
        operations.extend(collector.operations)
    constructions.sort(key=lambda item: (item.path, item.line, item.column, item.kind))
    operations.sort(key=lambda item: (item.path, item.line, item.column, item.kind, item.field))
    return ObjectLifecycleReport(
        carrier,
        len(files),
        tuple(constructions),
        tuple(operations),
        tuple(failures),
    )
