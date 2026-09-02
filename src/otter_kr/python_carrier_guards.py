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
class CarrierGuardReport:
    language: str
    carrier: str
    occurrences: tuple[CarrierGuardOccurrence, ...]
    warnings: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "language": self.language,
            "carrier": self.carrier,
            "occurrences": [item.to_dict() for item in self.occurrences],
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
    """Return expression, field, operator, value, unary_not when testing carrier.field."""
    compare = node
    unary_not = False
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        compare = node.operand
        unary_not = True
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
}


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
        effect_when = _FLIPPED_OPERATORS[effect_when]
    return {
        "carrier": carrier,
        "field": field,
        "value": value,
        "effect_when": effect_when,
    }


def _is_pure_early_exit(body: list[ast.stmt]) -> str | None:
    if len(body) != 1:
        return None
    statement = body[0]
    if isinstance(statement, ast.Return):
        return "return"
    if isinstance(statement, ast.Raise):
        return "raise"
    if isinstance(statement, ast.Continue):
        return "continue"
    if isinstance(statement, ast.Break):
        return "break"
    return None


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

    def visit_If(self, node: ast.If) -> None:
        predicate = _carrier_field_compare(node.test, self.carrier)
        if predicate is not None:
            expression, field, operator, value, unary_not = predicate
            exit_kind = _is_pure_early_exit(node.body)
            if exit_kind is not None and not node.orelse:
                control_shape = "early_exit"
                parent = self._block_stack[-1]
                index = parent.index(node)
                follow = parent[index + 1 :]
                effects = _collect_effects(list(follow), self.carrier)
                if effects:
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
            else:
                control_shape = "enclosed_branch"
                effects = _collect_effects(list(node.body), self.carrier)
                if effects:
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
                            exit_kind=None,
                            effects=tuple(effects),
                        )
                    )
        self.visit(node.test)
        self._visit_block(list(node.body))
        self._visit_block(list(node.orelse))


def find_carrier_guards(
    repository: Path,
    carrier: str,
    file_source: TrackedFileSource | None = None,
) -> CarrierGuardReport:
    repository = repository.resolve()
    if not repository.is_dir():
        raise ValueError(f"Repository is not a directory: {repository}")
    if not carrier or not carrier.isidentifier():
        raise ValueError("A non-empty carrier identifier is required.")

    occurrences: list[CarrierGuardOccurrence] = []
    warnings: list[dict[str, str]] = []
    for path in (file_source or GitCliFileSource()).python_files(repository):
        relative = path.relative_to(repository).as_posix()
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
    return CarrierGuardReport(
        language="python",
        carrier=carrier,
        occurrences=tuple(occurrences),
        warnings=tuple(warnings),
    )
