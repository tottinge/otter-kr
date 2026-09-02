"""Seed-scoped evidence for carrier field guards and enclosed branches.

Reports mechanical couplings only: a field predicate on a named carrier joined to
access or modification of that same carrier. Does not assert misplaced semantics.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from otter_kr.git_files import GitCliFileSource, TrackedFileSource


@dataclass(frozen=True, slots=True)
class CarrierEffect:
    line: int
    column: int
    role: str
    kind: str
    expression: str

    def to_dict(self) -> dict[str, object]:
        return {
            "line": self.line,
            "column": self.column,
            "role": self.role,
            "kind": self.kind,
            "expression": self.expression,
        }


@dataclass(frozen=True, slots=True)
class CarrierGuardOccurrence:
    path: str
    line: int
    column: int
    control_shape: str
    predicate: dict[str, str]
    predicate_normalized: dict[str, str]
    exit_kind: str | None
    effects: tuple[CarrierEffect, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "control_shape": self.control_shape,
            "predicate": dict(self.predicate),
            "predicate_normalized": dict(self.predicate_normalized),
            "exit_kind": self.exit_kind,
            "effects": [item.to_dict() for item in self.effects],
        }


@dataclass(frozen=True, slots=True)
class CarrierGuardGroup:
    predicate_normalized: dict[str, str]
    occurrence_count: int
    path_count: int
    paths: tuple[str, ...]
    effect_role_counts: dict[str, int]
    occurrence_refs: tuple[dict[str, int | str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "predicate_normalized": dict(self.predicate_normalized),
            "occurrence_count": self.occurrence_count,
            "path_count": self.path_count,
            "paths": list(self.paths),
            "effect_role_counts": dict(self.effect_role_counts),
            "occurrence_refs": [dict(item) for item in self.occurrence_refs],
        }


@dataclass(frozen=True, slots=True)
class CarrierGuardReport:
    language: str
    carrier: str
    path_bound: tuple[str, ...] | None
    occurrences: tuple[CarrierGuardOccurrence, ...]
    groups: tuple[CarrierGuardGroup, ...]
    warnings: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "language": self.language,
            "carrier": self.carrier,
            "path_bound": list(self.path_bound) if self.path_bound is not None else None,
            "occurrences": [item.to_dict() for item in self.occurrences],
            "groups": [item.to_dict() for item in self.groups],
            "warnings": list(self.warnings),
        }


def _operator_name(operator: ast.cmpop) -> str | None:
    mapping: dict[type[ast.cmpop], str] = {
        ast.Eq: "==",
        ast.NotEq: "!=",
        ast.Is: "is",
        ast.IsNot: "is not",
    }
    return mapping.get(type(operator))


def _value_text(node: ast.AST) -> str:
    return ast.unparse(node)


def _carrier_field_compare(node: ast.AST, carrier: str) -> tuple[str, str, str, str, bool] | None:
    """Return expression, field, operator, value, unary_not for a carrier predicate."""
    compare = node
    unary_not = False
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        compare = node.operand
        unary_not = True
    if (
        isinstance(compare, ast.Call)
        and isinstance(compare.func, ast.Name)
        and compare.func.id == "isinstance"
        and len(compare.args) == 2
        and isinstance(compare.args[0], ast.Name)
        and compare.args[0].id == carrier
    ):
        return (
            ast.unparse(node),
            "",
            "isinstance",
            _value_text(compare.args[1]),
            unary_not,
        )
    if not isinstance(compare, ast.Compare) or len(compare.ops) != 1:
        return None
    operator = _operator_name(compare.ops[0])
    if operator is None:
        return None
    left, right = compare.left, compare.comparators[0]
    if (
        isinstance(left, ast.Attribute)
        and isinstance(left.value, ast.Name)
        and left.value.id == carrier
    ):
        return ast.unparse(node), left.attr, operator, _value_text(right), unary_not
    if (
        isinstance(right, ast.Attribute)
        and isinstance(right.value, ast.Name)
        and right.value.id == carrier
    ):
        return ast.unparse(node), right.attr, operator, _value_text(left), unary_not
    return None


_FLIPPED_OPERATORS = {
    "==": "!=",
    "!=": "==",
    "is": "is not",
    "is not": "is",
    "isinstance": "not_isinstance",
    "not_isinstance": "isinstance",
}


def _normalized_key(predicate_normalized: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        predicate_normalized["carrier"],
        predicate_normalized["field"],
        predicate_normalized["value"],
        predicate_normalized["effect_when"],
    )


def _build_groups(occurrences: tuple[CarrierGuardOccurrence, ...]) -> tuple[CarrierGuardGroup, ...]:
    buckets: dict[tuple[str, str, str, str], list[CarrierGuardOccurrence]] = {}
    for occurrence in occurrences:
        buckets.setdefault(_normalized_key(occurrence.predicate_normalized), []).append(occurrence)

    groups: list[CarrierGuardGroup] = []
    for key in sorted(buckets):
        members = buckets[key]
        paths = tuple(sorted({item.path for item in members}))
        role_counts: dict[str, int] = {}
        for member in members:
            for effect in member.effects:
                role_counts[effect.role] = role_counts.get(effect.role, 0) + 1
        groups.append(
            CarrierGuardGroup(
                predicate_normalized=dict(members[0].predicate_normalized),
                occurrence_count=len(members),
                path_count=len(paths),
                paths=paths,
                effect_role_counts=dict(sorted(role_counts.items())),
                occurrence_refs=tuple(
                    {"path": item.path, "line": item.line, "column": item.column}
                    for item in members
                ),
            )
        )
    return tuple(groups)


def _normalize_predicate(
    *,
    carrier: str,
    field: str,
    operator: str,
    value: str,
    control_shape: str,
    unary_not: bool,
) -> dict[str, str]:
    """Map raw predicate onto the relation that holds on the effect path."""
    effect_when = operator
    if unary_not:
        effect_when = _FLIPPED_OPERATORS[effect_when]
    if control_shape == "early_exit":
        # Effects run on the fall-through path (condition false).
        effect_when = _FLIPPED_OPERATORS[effect_when]
    return {
        "carrier": carrier,
        "field": field,
        "value": value,
        "effect_when": effect_when,
    }


def _exit_kind(statement: ast.stmt) -> str | None:
    if isinstance(statement, ast.Return):
        return "return"
    if isinstance(statement, ast.Raise):
        return "raise"
    if isinstance(statement, ast.Continue):
        return "continue"
    if isinstance(statement, ast.Break):
        return "break"
    return None


def _is_pure_early_exit(body: list[ast.stmt]) -> str | None:
    """Return the first exit kind when every statement is a pure exit."""
    if not body:
        return None
    kinds = [_exit_kind(statement) for statement in body]
    if any(kind is None for kind in kinds):
        return None
    return kinds[0]


def _carrier_name(node: ast.AST, carrier: str) -> bool:
    return isinstance(node, ast.Name) and node.id == carrier


def _collect_effects(nodes: list[ast.AST], carrier: str) -> list[CarrierEffect]:
    effects: list[CarrierEffect] = []
    seen: set[tuple[int, int, str, str]] = set()

    def add(node: ast.AST, role: str, kind: str, expression: str) -> None:
        key = (node.lineno, node.col_offset, role, kind)
        if key in seen:
            return
        seen.add(key)
        effects.append(
            CarrierEffect(
                line=node.lineno,
                column=node.col_offset,
                role=role,
                kind=kind,
                expression=expression,
            )
        )

    for root in nodes:
        for node in ast.walk(root):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and _carrier_name(target.value, carrier):
                        add(node, "modification", "attribute_store", ast.unparse(node))
            elif isinstance(node, ast.AugAssign):
                target = node.target
                if isinstance(target, ast.Attribute) and _carrier_name(target.value, carrier):
                    add(node, "modification", "attribute_store", ast.unparse(node))
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and _carrier_name(func.value, carrier):
                    add(node, "modification", "mutative_call", ast.unparse(node))
            elif (
                isinstance(node, ast.Attribute)
                and _carrier_name(node.value, carrier)
                and isinstance(node.ctx, ast.Load)
            ):
                add(node, "access", "attribute_load", ast.unparse(node))

    # Drop attribute_load effects that are only the base of a recorded modification.
    modification_exprs = {effect.expression for effect in effects if effect.role == "modification"}
    filtered: list[CarrierEffect] = []
    for effect in effects:
        if (
            effect.role == "access"
            and effect.kind == "attribute_load"
            and any(effect.expression in expression for expression in modification_exprs)
        ):
            continue
        filtered.append(effect)
    filtered.sort(key=lambda item: (item.line, item.column, item.role, item.kind, item.expression))
    return filtered


class _CarrierGuardCollector(ast.NodeVisitor):
    def __init__(self, path: str, carrier: str) -> None:
        self.path = path
        self.carrier = carrier
        self.occurrences: list[CarrierGuardOccurrence] = []
        self._block_stack: list[list[ast.stmt]] = []

    def _visit_block(self, statements: list[ast.stmt]) -> None:
        self._block_stack.append(statements)
        for statement in statements:
            self.visit(statement)
        self._block_stack.pop()

    def visit_Module(self, node: ast.Module) -> None:
        self._visit_block(list(node.body))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_block(list(node.body))

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit_block(list(node.body))

    def visit_For(self, node: ast.For) -> None:
        self.visit(node.target)
        self.visit(node.iter)
        self._visit_block(list(node.body))
        self._visit_block(list(node.orelse))

    visit_AsyncFor = visit_For

    def visit_While(self, node: ast.While) -> None:
        self.visit(node.test)
        self._visit_block(list(node.body))
        self._visit_block(list(node.orelse))

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars is not None:
                self.visit(item.optional_vars)
        self._visit_block(list(node.body))

    visit_AsyncWith = visit_With

    def _record(
        self,
        *,
        node: ast.If,
        expression: str,
        field: str,
        operator: str,
        value: str,
        unary_not: bool,
        control_shape: str,
        exit_kind: str | None,
        effects: list[CarrierEffect],
    ) -> None:
        if not effects:
            return
        self.occurrences.append(
            CarrierGuardOccurrence(
                path=self.path,
                line=node.lineno,
                column=node.col_offset,
                control_shape=control_shape,
                predicate={
                    "expression": expression,
                    "field": field,
                    "operator": operator,
                    "value": value,
                },
                predicate_normalized=_normalize_predicate(
                    carrier=self.carrier,
                    field=field,
                    operator=operator,
                    value=value,
                    control_shape=control_shape,
                    unary_not=unary_not,
                ),
                exit_kind=exit_kind,
                effects=tuple(effects),
            )
        )

    def visit_If(self, node: ast.If) -> None:
        predicate = _carrier_field_compare(node.test, self.carrier)
        if predicate is not None:
            expression, field, operator, value, unary_not = predicate
            body_exit = _is_pure_early_exit(node.body)
            else_exit = _is_pure_early_exit(node.orelse)
            if body_exit is not None and not node.orelse:
                parent = self._block_stack[-1]
                index = parent.index(node)
                follow = parent[index + 1 :]
                self._record(
                    node=node,
                    expression=expression,
                    field=field,
                    operator=operator,
                    value=value,
                    unary_not=unary_not,
                    control_shape="early_exit",
                    exit_kind=body_exit,
                    effects=_collect_effects(list(follow), self.carrier),
                )
            elif else_exit is not None and body_exit is None:
                self._record(
                    node=node,
                    expression=expression,
                    field=field,
                    operator=operator,
                    value=value,
                    unary_not=unary_not,
                    control_shape="else_exit",
                    exit_kind=else_exit,
                    effects=_collect_effects(list(node.body), self.carrier),
                )
            else:
                self._record(
                    node=node,
                    expression=expression,
                    field=field,
                    operator=operator,
                    value=value,
                    unary_not=unary_not,
                    control_shape="enclosed_branch",
                    exit_kind=None,
                    effects=_collect_effects(list(node.body), self.carrier),
                )
        self.visit(node.test)
        self._visit_block(list(node.body))
        self._visit_block(list(node.orelse))


def _normalize_path_bound(paths: tuple[str, ...] | None) -> tuple[str, ...] | None:
    if paths is None:
        return None
    normalized: list[str] = []
    for raw in paths:
        text = raw.strip()
        if not text:
            raise ValueError("path_bound entries must be non-empty repository-relative paths.")
        candidate = Path(text)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError("path_bound entries must be repository-relative paths without '..'.")
        normalized.append(candidate.as_posix())
    return tuple(sorted(set(normalized)))


def find_carrier_guards(
    repository: Path,
    carrier: str,
    file_source: TrackedFileSource | None = None,
    paths: tuple[str, ...] | None = None,
) -> CarrierGuardReport:
    repository = repository.resolve()
    if not repository.is_dir():
        raise ValueError(f"Repository is not a directory: {repository}")
    if not carrier or not carrier.isidentifier():
        raise ValueError("A non-empty carrier identifier is required.")
    path_bound = _normalize_path_bound(paths)

    occurrences: list[CarrierGuardOccurrence] = []
    warnings: list[dict[str, str]] = []
    for path in (file_source or GitCliFileSource()).python_files(repository):
        relative = path.relative_to(repository).as_posix()
        if path_bound is not None and relative not in path_bound:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except UnicodeError:
            warnings.append(
                {
                    "code": "unreadable_file",
                    "path": relative,
                    "message": "File could not be decoded as UTF-8.",
                }
            )
            continue
        except SyntaxError as error:
            warnings.append(
                {
                    "code": "invalid_python",
                    "path": relative,
                    "message": (
                        f"Syntax error at line {error.lineno}, column {error.offset}: {error.msg}"
                    ),
                }
            )
            continue
        collector = _CarrierGuardCollector(relative, carrier)
        collector.visit(tree)
        occurrences.extend(collector.occurrences)

    occurrences.sort(
        key=lambda item: (
            item.path,
            item.line,
            item.column,
            item.control_shape,
            item.predicate.get("expression", ""),
        )
    )
    warnings.sort(key=lambda item: (item["path"], item["code"]))
    ordered = tuple(occurrences)
    return CarrierGuardReport(
        language="python",
        carrier=carrier,
        path_bound=path_bound,
        occurrences=ordered,
        groups=_build_groups(ordered),
        warnings=tuple(warnings),
    )
