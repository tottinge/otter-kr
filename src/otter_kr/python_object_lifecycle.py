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
    guards: tuple[GuardContext, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "guards": [guard.to_dict() for guard in self.guards],
        }


@dataclass(frozen=True, slots=True)
class GuardContext:
    path: str
    kind: str
    line: int
    column: int
    expression: str
    branch: str
    depth: int

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
class OperationGroup:
    field: str
    kind: str
    occurrence_count: int
    occurrence_refs: tuple[tuple[str, int, int], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "field": self.field,
            "kind": self.kind,
            "occurrence_count": self.occurrence_count,
            "occurrence_refs": [
                {"path": path, "line": line, "column": column}
                for path, line, column in self.occurrence_refs
            ],
        }


@dataclass(frozen=True, slots=True)
class TransitionObservation:
    path: str
    scope: str
    field: str
    from_kind: str
    to_kind: str
    from_line: int
    to_line: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AliasLink:
    source: str
    target: str
    path: str
    line: int
    column: int
    scope: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BoundaryLink:
    kind: str
    path: str
    line: int
    column: int
    scope: str
    detail: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ObjectLifecycleReport:
    carrier: str
    files_scanned: int
    constructions: tuple[ConstructionSite, ...]
    operations: tuple[FieldOperation, ...]
    operation_groups: tuple[OperationGroup, ...]
    transitions: tuple[TransitionObservation, ...]
    aliases: tuple[AliasLink, ...]
    boundaries: tuple[BoundaryLink, ...]
    parse_failures: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "language": "python",
            "carrier": self.carrier,
            "files_scanned": self.files_scanned,
            "constructions": [item.to_dict() for item in self.constructions],
            "operations": [item.to_dict() for item in self.operations],
            "operation_groups": [item.to_dict() for item in self.operation_groups],
            "transitions": [item.to_dict() for item in self.transitions],
            "aliases": [item.to_dict() for item in self.aliases],
            "boundaries": [item.to_dict() for item in self.boundaries],
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
        self.guards: list[GuardContext] = []
        self.constructions: list[ConstructionSite] = []
        self.operations: list[FieldOperation] = []
        self.aliases: list[AliasLink] = []
        self.boundaries: list[BoundaryLink] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scopes.append(node.name)
        self.generic_visit(node)
        self.scopes.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        if any(
            isinstance(target, ast.Name) and target.id == self.carrier for target in node.targets
        ):
            self._construction(node, "assignment")
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target = node.targets[0].id
            if (
                isinstance(node.value, ast.Name)
                and node.value.id == self.carrier
                and target != self.carrier
            ):
                self.aliases.append(
                    AliasLink(
                        self.carrier,
                        target,
                        self.path,
                        node.lineno,
                        node.col_offset,
                        ".".join(self.scopes),
                    )
                )
            elif (
                target == self.carrier
                and isinstance(node.value, ast.Name)
                and node.value.id != self.carrier
            ):
                self.aliases.append(
                    AliasLink(
                        node.value.id,
                        self.carrier,
                        self.path,
                        node.lineno,
                        node.col_offset,
                        ".".join(self.scopes),
                    )
                )
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if (
            isinstance(node.target, ast.Name)
            and node.target.id == self.carrier
            and node.value is not None
        ):
            self._construction(node, "annotated_assignment")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        arguments = (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
        if any(argument.arg == self.carrier for argument in arguments):
            self.boundaries.append(
                BoundaryLink(
                    "parameter",
                    self.path,
                    node.lineno,
                    node.col_offset,
                    ".".join(self.scopes),
                    self.carrier,
                )
            )
        self.scopes.append(node.name)
        self.generic_visit(node)
        self.scopes.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Return(self, node: ast.Return) -> None:
        if isinstance(node.value, ast.Name) and node.value.id == self.carrier:
            self.boundaries.append(
                BoundaryLink(
                    "return",
                    self.path,
                    node.lineno,
                    node.col_offset,
                    ".".join(self.scopes),
                    self.carrier,
                )
            )
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        self.visit(node.test)
        self._visit_guarded(node.test, node.body, "body", "if")
        self._visit_guarded(node.test, node.orelse, "else", "if")

    def visit_While(self, node: ast.While) -> None:
        self.visit(node.test)
        self._visit_guarded(node.test, node.body, "body", "while")
        self._visit_statements(node.orelse)

    def _visit_guarded(
        self, test: ast.AST, statements: list[ast.stmt], branch: str, kind: str
    ) -> None:
        guard = GuardContext(
            self.path,
            kind,
            test.lineno,
            test.col_offset,
            ast.get_source_segment(self.source, test) or "",
            branch,
            len(self.guards) + 1,
        )
        self.guards.append(guard)
        self._visit_statements(statements)
        self.guards.pop()

    def _visit_statements(self, statements: list[ast.stmt]) -> None:
        for statement in statements:
            self.visit(statement)

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
        if any(
            isinstance(argument, ast.Name) and argument.id == self.carrier for argument in node.args
        ):
            self.boundaries.append(
                BoundaryLink(
                    "argument",
                    self.path,
                    node.lineno,
                    node.col_offset,
                    ".".join(self.scopes),
                    self.carrier,
                )
            )
        if any(
            isinstance(keyword.value, ast.Name) and keyword.value.id == self.carrier
            for keyword in node.keywords
        ):
            self.boundaries.append(
                BoundaryLink(
                    "keyword_argument",
                    self.path,
                    node.lineno,
                    node.col_offset,
                    ".".join(self.scopes),
                    self.carrier,
                )
            )
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
            tuple(self.guards),
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
    aliases: list[AliasLink] = []
    boundaries: list[BoundaryLink] = []
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
        aliases.extend(collector.aliases)
        boundaries.extend(collector.boundaries)
    constructions.sort(key=lambda item: (item.path, item.line, item.column, item.kind))
    operations.sort(key=lambda item: (item.path, item.line, item.column, item.kind, item.field))
    groups = _group_operations(operations)
    transitions = _observe_transitions(operations)
    aliases.sort(key=lambda item: (item.path, item.line, item.column, item.source, item.target))
    boundaries.sort(key=lambda item: (item.path, item.line, item.column, item.kind))
    return ObjectLifecycleReport(
        carrier,
        len(files),
        tuple(constructions),
        tuple(operations),
        groups,
        transitions,
        tuple(aliases),
        tuple(boundaries),
        tuple(failures),
    )


def _group_operations(operations: list[FieldOperation]) -> tuple[OperationGroup, ...]:
    grouped: dict[tuple[str, str], list[FieldOperation]] = {}
    for operation in operations:
        grouped.setdefault((operation.field, operation.kind), []).append(operation)
    return tuple(
        OperationGroup(
            field,
            kind,
            len(items),
            tuple((item.path, item.line, item.column) for item in items),
        )
        for (field, kind), items in sorted(grouped.items())
    )


def _observe_transitions(
    operations: list[FieldOperation],
) -> tuple[TransitionObservation, ...]:
    transitions: list[TransitionObservation] = []
    for previous, current in zip(operations, operations[1:], strict=False):
        if (previous.path, previous.scope, previous.field) != (
            current.path,
            current.scope,
            current.field,
        ):
            continue
        transitions.append(
            TransitionObservation(
                current.path,
                current.scope,
                current.field,
                previous.kind,
                current.kind,
                previous.line,
                current.line,
            )
        )
    return tuple(transitions)
