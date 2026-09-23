"""Structural evidence about external functions using one carrier's fields."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from otter_kr.git_files import GitCliFileSource, TrackedFileSource


@dataclass(frozen=True, slots=True)
class CarrierField:
    name: str
    line: int
    column: int

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "line": self.line, "column": self.column}


@dataclass(frozen=True, slots=True)
class CarrierDeclaration:
    path: str
    line: int
    column: int
    kind: str
    fields: tuple[CarrierField, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "kind": self.kind,
            "fields": [field.to_dict() for field in self.fields],
        }


@dataclass(frozen=True, slots=True)
class FieldAccess:
    path: str
    line: int
    column: int
    function: str
    field: str
    role: str

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "function": self.function,
            "field": self.field,
            "role": self.role,
        }


@dataclass(frozen=True, slots=True)
class FieldAffinity:
    fields: tuple[str, ...]
    function_count: int
    functions: tuple[str, ...]
    occurrence_count: int
    role_counts: dict[str, int]
    occurrence_refs: tuple[FieldAccess, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "fields": list(self.fields),
            "function_count": self.function_count,
            "functions": list(self.functions),
            "occurrence_count": self.occurrence_count,
            "role_counts": dict(self.role_counts),
            "occurrence_refs": [item.to_dict() for item in self.occurrence_refs],
        }


@dataclass(frozen=True, slots=True)
class RuleOccurrence:
    path: str
    line: int
    column: int
    function: str
    expression: str
    field: str
    operator: str
    value: str

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "function": self.function,
            "expression": self.expression,
        }


@dataclass(frozen=True, slots=True)
class RepeatedRule:
    field: str
    operator: str
    value: str
    occurrences: tuple[RuleOccurrence, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "comparison",
            "normalized": {
                "field": self.field,
                "operator": self.operator,
                "value": self.value,
            },
            "occurrence_count": len(self.occurrences),
            "functions": sorted({item.function for item in self.occurrences}),
            "occurrence_refs": [item.to_dict() for item in self.occurrences],
        }


@dataclass(frozen=True, slots=True)
class ExternalFieldRulesReport:
    language: str
    carrier: str
    declarations: tuple[CarrierDeclaration, ...]
    affinities: tuple[FieldAffinity, ...]
    warnings: tuple[dict[str, str], ...]
    rules: tuple[RepeatedRule, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "language": self.language,
            "carrier": self.carrier,
            "declarations": [item.to_dict() for item in self.declarations],
            "affinities": [item.to_dict() for item in self.affinities],
            "warnings": list(self.warnings),
            "rules": [item.to_dict() for item in self.rules],
        }


def _is_dataclass_decorator(node: ast.expr) -> bool:
    return (isinstance(node, ast.Name) and node.id == "dataclass") or (
        isinstance(node, ast.Attribute) and node.attr == "dataclass"
    )


def _class_declarations(tree: ast.AST, path: str, carrier: str) -> tuple[CarrierDeclaration, ...]:
    declarations: list[CarrierDeclaration] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != carrier:
            continue
        fields = tuple(
            CarrierField(statement.target.id, statement.lineno, statement.col_offset)
            for statement in node.body
            if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
        )
        declarations.append(
            CarrierDeclaration(
                path,
                node.lineno,
                node.col_offset,
                "dataclass"
                if any(_is_dataclass_decorator(item) for item in node.decorator_list)
                else "class",
                fields,
            )
        )
    return tuple(declarations)


class _ExternalAccessCollector(ast.NodeVisitor):
    def __init__(self, path: str, carrier: str) -> None:
        self.path = path
        self.carrier = carrier
        self.class_stack: list[str] = []
        self.function_stack: list[str] = []
        self.carrier_bindings: list[set[str]] = []
        self.accesses: list[FieldAccess] = []
        self.rule_occurrences: list[RuleOccurrence] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if self.carrier in self.class_stack:
            return
        owner = ".".join([*self.class_stack, node.name])
        self.function_stack.append(owner)
        arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        bindings = {
            argument.arg
            for argument in arguments
            if argument.arg == self.carrier
            or (
                isinstance(argument.annotation, ast.Name) and argument.annotation.id == self.carrier
            )
        }
        self.carrier_bindings.append(bindings)
        for statement in node.body:
            self.visit(statement)
        self.carrier_bindings.pop()
        self.function_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Compare(self, node: ast.Compare) -> None:
        if self.function_stack and len(node.ops) == 1 and len(node.comparators) == 1:
            left, right = node.left, node.comparators[0]
            carrier_attribute = None
            value = None
            if (
                isinstance(left, ast.Attribute)
                and isinstance(left.value, ast.Name)
                and left.value.id in self.carrier_bindings[-1]
            ):
                carrier_attribute, value = left, right
            elif (
                isinstance(right, ast.Attribute)
                and isinstance(right.value, ast.Name)
                and right.value.id in self.carrier_bindings[-1]
            ):
                carrier_attribute, value = right, left
            operator = {
                ast.Eq: "==",
                ast.NotEq: "!=",
                ast.Is: "is",
                ast.IsNot: "is not",
                ast.Lt: "<",
                ast.LtE: "<=",
                ast.Gt: ">",
                ast.GtE: ">=",
                ast.In: "in",
                ast.NotIn: "not in",
            }.get(type(node.ops[0]))
            if carrier_attribute is not None and value is not None and operator is not None:
                self.rule_occurrences.append(
                    RuleOccurrence(
                        self.path,
                        node.lineno,
                        node.col_offset,
                        self.function_stack[-1],
                        ast.unparse(node),
                        carrier_attribute.attr,
                        operator,
                        ast.unparse(value),
                    )
                )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if (
            self.function_stack
            and isinstance(node.value, ast.Name)
            and node.value.id in self.carrier_bindings[-1]
        ):
            role = (
                "read"
                if isinstance(node.ctx, ast.Load)
                else "write"
                if isinstance(node.ctx, ast.Store)
                else "delete"
            )
            self.accesses.append(
                FieldAccess(
                    self.path,
                    node.lineno,
                    node.col_offset,
                    self.function_stack[-1],
                    node.attr,
                    role,
                )
            )
        self.generic_visit(node)


def _affinities(accesses: tuple[FieldAccess, ...]) -> tuple[FieldAffinity, ...]:
    by_function: dict[str, list[FieldAccess]] = {}
    for access in accesses:
        by_function.setdefault(access.function, []).append(access)

    grouped: dict[tuple[str, ...], list[str]] = {}
    for function, items in by_function.items():
        fields = tuple(sorted({item.field for item in items}))
        for pair in combinations(fields, 2):
            grouped.setdefault(pair, []).append(function)

    result: list[FieldAffinity] = []
    for fields, functions in sorted(grouped.items()):
        if len(functions) < 2:
            continue
        members = tuple(
            access for access in accesses if access.function in functions and access.field in fields
        )
        role_counts: dict[str, int] = {}
        for member in members:
            role_counts[member.role] = role_counts.get(member.role, 0) + 1
        result.append(
            FieldAffinity(
                fields,
                len(functions),
                tuple(sorted(functions)),
                len(members),
                dict(sorted(role_counts.items())),
                members,
            )
        )
    return tuple(result)


def _repeated_rules(occurrences: tuple[RuleOccurrence, ...]) -> tuple[RepeatedRule, ...]:
    grouped: dict[tuple[str, str, str], list[RuleOccurrence]] = {}
    for occurrence in occurrences:
        key = (occurrence.field, occurrence.operator, occurrence.value)
        grouped.setdefault(key, []).append(occurrence)
    return tuple(
        RepeatedRule(
            field,
            operator,
            value,
            tuple(
                sorted(items, key=lambda item: (item.path, item.line, item.column, item.function))
            ),
        )
        for (field, operator, value), items in sorted(grouped.items())
        if len(items) > 1
    )


def find_external_field_rules(
    repository: Path,
    carrier: str,
    file_source: TrackedFileSource | None = None,
) -> ExternalFieldRulesReport:
    repository = repository.resolve()
    if not repository.is_dir():
        raise ValueError(f"Repository is not a directory: {repository}")

    declarations: list[CarrierDeclaration] = []
    accesses: list[FieldAccess] = []
    rule_occurrences: list[RuleOccurrence] = []
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
        declarations.extend(_class_declarations(tree, relative, carrier))
        collector = _ExternalAccessCollector(relative, carrier)
        collector.visit(tree)
        accesses.extend(collector.accesses)
        rule_occurrences.extend(collector.rule_occurrences)

    ordered_accesses = tuple(
        sorted(
            accesses,
            key=lambda item: (
                item.path,
                item.line,
                item.column,
                item.function,
                item.field,
                item.role,
            ),
        )
    )
    return ExternalFieldRulesReport(
        "python",
        carrier,
        tuple(sorted(declarations, key=lambda item: (item.path, item.line, item.column))),
        _affinities(ordered_accesses),
        tuple(sorted(warnings, key=lambda item: (item["path"], item["code"]))),
        _repeated_rules(tuple(rule_occurrences)),
    )
