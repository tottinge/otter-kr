"""Exact-name occurrence evidence for the variable-cluster admission sequence."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path

from otter_kr.git_cli_history import GitCliHistory
from otter_kr.git_files import GitCliFileSource
from otter_kr.git_history_snapshot import collect_git_history_snapshot
from otter_kr.python_tests import find_tests_for_symbol


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
class SharedScope:
    path: str
    scope: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ConstructionSite:
    name: str
    path: str
    line: int
    column: int
    scope: str
    target: str
    kind: str
    value: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AliasEvidence:
    name: str
    path: str
    line: int
    column: int
    scope: str
    source: str
    target: str
    kind: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BoundaryEvidence:
    name: str
    path: str
    line: int
    column: int
    scope: str
    kind: str
    detail: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class VariableOccurrence:
    name: str
    path: str
    line: int
    column: int
    scope: str
    role: str
    guards: tuple[GuardContext, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
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
    shared_scopes: tuple[SharedScope, ...] = ()
    shared_guards: tuple[GuardContext, ...] = ()
    construction_sites: tuple[ConstructionSite, ...] = ()
    aliases: tuple[AliasEvidence, ...] = ()
    boundaries: tuple[BoundaryEvidence, ...] = ()
    test_evidence: tuple[dict[str, object], ...] = ()
    history_evidence: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "names": list(self.names),
            "occurrences": [item.to_dict() for item in self.occurrences],
            "warnings": list(self.warnings),
            "shared_scopes": [scope.to_dict() for scope in self.shared_scopes],
            "shared_guards": [guard.to_dict() for guard in self.shared_guards],
            "construction_sites": [site.to_dict() for site in self.construction_sites],
            "aliases": [alias.to_dict() for alias in self.aliases],
            "boundaries": [boundary.to_dict() for boundary in self.boundaries],
            "test_evidence": list(self.test_evidence),
            "history_evidence": self.history_evidence,
        }


class _OccurrenceCollector(ast.NodeVisitor):
    def __init__(self, path: str, name: str, source: str) -> None:
        self.path = path
        self.name = name
        self.source = source
        self.scopes: list[str] = []
        self.guards: list[GuardContext] = []
        self.occurrences: list[VariableOccurrence] = []
        self.construction_sites: list[ConstructionSite] = []
        self.aliases: list[AliasEvidence] = []
        self.boundaries: list[BoundaryEvidence] = []

    def _record_assignment(self, target: ast.AST, value: ast.AST, kind: str) -> None:
        target_name = None
        if isinstance(target, ast.Name) and target.id == self.name:
            target_name = target.id
        elif isinstance(target, ast.Attribute) and target.attr == self.name:
            target_name = ast.get_source_segment(self.source, target)
        if target_name is None:
            return
        if isinstance(target, ast.Attribute):
            kind = "attribute_assignment"
        self.construction_sites.append(
            ConstructionSite(
                self.name,
                self.path,
                target.lineno,
                target.col_offset,
                ".".join(self.scopes),
                target_name,
                kind,
                ast.get_source_segment(self.source, value) or "",
            )
        )

    def visit_Assign(self, node: ast.Assign) -> None:
        if (
            len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Name)
        ):
            target, source = node.targets[0].id, node.value.id
            if self.name in (source, target) and source != target:
                self._record_alias(source, target, node)
        for target in node.targets:
            self._record_assignment(target, node.value, "assignment")
        self.generic_visit(node)

    def _record_alias(self, source: str, target: str, node: ast.Assign) -> None:
        self.aliases.append(
            AliasEvidence(
                self.name,
                self.path,
                node.lineno,
                node.col_offset,
                ".".join(self.scopes),
                source,
                target,
                "assignment",
            )
        )

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            self._record_assignment(node.target, node.value, "annotated_assignment")
        self.generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self._record_assignment(node.target, node.value, "named_assignment")
        self.generic_visit(node)

    def _guard(self, node: ast.AST, branch: str, kind: str) -> GuardContext:
        expression = ast.get_source_segment(self.source, node) or ""
        return GuardContext(
            self.path,
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
                    self.name,
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
            self.boundaries.append(
                BoundaryEvidence(
                    self.name,
                    self.path,
                    node.lineno,
                    node.col_offset,
                    ".".join(self.scopes),
                    "parameter",
                    node.arg,
                )
            )
            self.occurrences.append(
                VariableOccurrence(
                    self.name,
                    self.path,
                    node.lineno,
                    node.col_offset,
                    ".".join(self.scopes),
                    "parameter",
                    tuple(self.guards),
                )
            )

    def visit_Return(self, node: ast.Return) -> None:
        if isinstance(node.value, ast.Name) and node.value.id == self.name:
            self.boundaries.append(
                BoundaryEvidence(
                    self.name,
                    self.path,
                    node.value.lineno,
                    node.value.col_offset,
                    ".".join(self.scopes),
                    "return",
                    node.value.id,
                )
            )
        self.generic_visit(node)


def _validate_names(
    names: tuple[str, ...], *, minimum: int = 1, maximum: int | None = None
) -> None:
    if len(names) < minimum:
        raise ValueError(f"at least {minimum} names are required")
    if maximum is not None and len(names) > maximum:
        raise ValueError(f"at most {maximum} names are supported")
    if not names or any(not name.isidentifier() for name in names):
        raise ValueError("names must be Python identifiers")
    if len(set(names)) != len(names):
        raise ValueError("names must be distinct")


def _find_variable_cluster(
    repository: Path,
    names: tuple[str, ...],
    *,
    since_unix_time: int | None = None,
    limit: int | None = None,
) -> VariableClusterReport:
    occurrences: list[VariableOccurrence] = []
    construction_sites: list[ConstructionSite] = []
    aliases: list[AliasEvidence] = []
    boundaries: list[BoundaryEvidence] = []
    warnings: list[dict[str, str]] = []
    for path in GitCliFileSource().python_files(repository.resolve()):
        relative = path.relative_to(repository.resolve()).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=relative)
        except (OSError, UnicodeError, SyntaxError) as error:
            warnings.append({"path": relative, "message": str(error)})
            continue
        for name in names:
            collector = _OccurrenceCollector(relative, name, source)
            collector.visit(tree)
            occurrences.extend(collector.occurrences)
            construction_sites.extend(collector.construction_sites)
            aliases.extend(collector.aliases)
            boundaries.extend(collector.boundaries)
    occurrences.sort(key=lambda item: (item.path, item.line, item.column, item.name, item.role))
    construction_sites.sort(
        key=lambda item: (item.path, item.line, item.column, item.name, item.kind)
    )
    aliases.sort(key=lambda item: (item.path, item.line, item.column, item.source, item.target))
    boundaries.sort(key=lambda item: (item.path, item.line, item.column, item.kind))
    by_name = {name: tuple(item for item in occurrences if item.name == name) for name in names}
    if len(names) > 1:
        shared_scope_keys = set.intersection(
            *(set((item.path, item.scope) for item in by_name[name]) for name in names)
        )
        shared_scopes = tuple(SharedScope(path, scope) for path, scope in sorted(shared_scope_keys))
        context_sets = [
            {(item.path, item.scope, item.guards) for item in by_name[name]} for name in names
        ]
        shared_contexts = set.intersection(*context_sets)
        shared_guards = tuple(
            sorted(
                {guard for _, _, guards in shared_contexts for guard in guards},
                key=lambda guard: (
                    guard.path,
                    guard.line,
                    guard.column,
                    guard.kind,
                    guard.expression,
                    guard.branch,
                ),
            )
        )
    else:
        shared_scopes = ()
        shared_guards = ()
    test_evidence = tuple(
        {"name": name, "report": find_tests_for_symbol(repository, name).to_dict()}
        for name in names
    )
    history_evidence = None
    if since_unix_time is not None and limit is not None:
        snapshot = collect_git_history_snapshot(
            repository,
            since_unix_time=since_unix_time,
            limit=limit,
            changes=GitCliHistory(),
        ).to_dict()
        paths = {item.path for item in occurrences}
        history_evidence = snapshot | {
            "files": [item for item in snapshot["files"] if item["path"] in paths]
        }
    return VariableClusterReport(
        names,
        tuple(occurrences),
        tuple(warnings),
        shared_scopes,
        shared_guards,
        tuple(construction_sites),
        tuple(aliases),
        tuple(boundaries),
        test_evidence,
        history_evidence,
    )


def find_variable_occurrences(
    repository: Path,
    name: str,
    *,
    since_unix_time: int | None = None,
    limit: int | None = None,
) -> VariableClusterReport:
    _validate_names((name,))
    return _find_variable_cluster(repository, (name,), since_unix_time=since_unix_time, limit=limit)


def find_variable_cluster(
    repository: Path,
    names: tuple[str, ...],
    *,
    since_unix_time: int | None = None,
    limit: int | None = None,
) -> VariableClusterReport:
    _validate_names(names, minimum=2, maximum=5)
    return _find_variable_cluster(repository, names, since_unix_time=since_unix_time, limit=limit)
