"""Statically visible behavioral evidence around a Python identifier."""

from __future__ import annotations

import ast
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal, TypedDict

from otter_kr.git_files import GitCliFileSource, GitRepository


@dataclass(frozen=True, slots=True)
class BehavioralEdge:
    seed: str
    neighbor: str
    reason: str
    weight: int
    locations: tuple[dict[str, object], ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "neighbor": self.neighbor,
            "reason": self.reason,
            "weight": self.weight,
            "locations": list(self.locations),
        }


@dataclass(frozen=True, slots=True)
class PythonBehavioralNeighborhoodReport:
    seed: str
    files_scanned: int
    edges: tuple[BehavioralEdge, ...]
    parse_failures: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "language": "python",
            "seed": self.seed,
            "files_scanned": self.files_scanned,
            "edges": [edge.to_dict() for edge in self.edges],
            "parse_failures": list(self.parse_failures),
        }


class InvalidBehavioralSeed(ValueError):
    """The seed is outside the supported Python identifier syntax."""


def find_behavioral_neighborhood(
    repository: GitRepository, seed: str
) -> PythonBehavioralNeighborhoodReport:
    if not seed.isidentifier():
        raise InvalidBehavioralSeed("Seed must be a Python identifier")
    root = repository.root
    files = GitCliFileSource().python_files(root)
    sources = [(path.relative_to(root).as_posix(), path) for path in files]
    return _measure_behavioral_neighborhood(seed, sources)


class BehavioralRelationship(StrEnum):
    CALL_ARGUMENT = "call argument"
    PASSED_AS_ARGUMENT = "passed as argument"
    METHOD_CALL = "method call"
    FIELD_ACCESS = "field access"
    COMPARISON = "type/enum comparison"


class PositionalArgument(TypedDict):
    argument_index: int


class KeywordArgument(TypedDict):
    argument: str | None


class FieldAccess(TypedDict):
    access: Literal["read", "write", "delete"]


_ATTRIBUTE_ACCESS_BY_CONTEXT: dict[type[ast.expr_context], Literal["read", "write", "delete"]] = {
    ast.Load: "read",
    ast.Store: "write",
    ast.Del: "delete",
}


class Comparison(TypedDict):
    operator: str


@dataclass(frozen=True, slots=True)
class BehavioralObservation:
    neighbor: str
    relationship: BehavioralRelationship
    site: ast.expr
    detail: PositionalArgument | KeywordArgument | FieldAccess | Comparison | None = None

    def location(self, path: str) -> dict[str, object]:
        return {
            "path": path,
            "line": self.site.lineno,
            "column": self.site.col_offset,
            **(self.detail or {}),
        }


def _measure_behavioral_neighborhood(
    seed: str, sources: Sequence[tuple[str, Path]]
) -> PythonBehavioralNeighborhoodReport:
    locations: dict[tuple[str, BehavioralRelationship], list[dict[str, object]]] = defaultdict(list)
    failures: list[dict[str, object]] = []
    for relative, path in sources:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except (SyntaxError, UnicodeError) as error:
            failures.append({"path": relative, "message": str(error)})
        else:
            for node in ast.walk(tree):
                for observation in _observations(node, seed):
                    key = (observation.neighbor, observation.relationship)
                    locations[key].append(observation.location(relative))
    edges = tuple(
        BehavioralEdge(seed, neighbor, relationship.value, len(sites), tuple(sites))
        for (neighbor, relationship), sites in sorted(locations.items())
        if neighbor != seed
    )
    return PythonBehavioralNeighborhoodReport(seed, len(sources), edges, tuple(failures))


def _observations(node: ast.AST, seed: str) -> tuple[BehavioralObservation, ...]:
    if isinstance(node, ast.Call):
        return _call_observations(node, seed)
    if isinstance(node, ast.Attribute) and _is_seed(node.value, seed):
        return (_field_observation(node),)
    if isinstance(node, ast.Compare) and _is_seed(node.left, seed):
        return _comparison_observations(node)
    return ()


def _is_seed(expression: ast.expr, seed: str) -> bool:
    return isinstance(expression, ast.Name) and expression.id == seed


def _call_observations(call: ast.Call, seed: str) -> tuple[BehavioralObservation, ...]:
    callee = call.func
    if isinstance(callee, ast.Name):
        if callee.id == seed:
            return tuple(
                BehavioralObservation(argument.id, BehavioralRelationship.CALL_ARGUMENT, argument)
                for argument in call.args
                if isinstance(argument, ast.Name)
            )
        return _arguments_passed_to(callee, call, seed)
    if isinstance(callee, ast.Attribute) and _is_seed(callee.value, seed):
        return (BehavioralObservation(callee.attr, BehavioralRelationship.METHOD_CALL, callee),)
    return ()


def _arguments_passed_to(
    callee: ast.Name, call: ast.Call, seed: str
) -> tuple[BehavioralObservation, ...]:
    relationship = BehavioralRelationship.PASSED_AS_ARGUMENT
    positional = tuple(
        BehavioralObservation(callee.id, relationship, callee, {"argument_index": index})
        for index, argument in enumerate(call.args)
        if _is_seed(argument, seed)
    )
    keyword = tuple(
        BehavioralObservation(callee.id, relationship, callee, {"argument": argument.arg})
        for argument in call.keywords
        if _is_seed(argument.value, seed)
    )
    return positional + keyword


def _field_observation(field: ast.Attribute) -> BehavioralObservation:
    access = _ATTRIBUTE_ACCESS_BY_CONTEXT[type(field.ctx)]
    return BehavioralObservation(
        field.attr, BehavioralRelationship.FIELD_ACCESS, field, {"access": access}
    )


def _comparison_observations(comparison: ast.Compare) -> tuple[BehavioralObservation, ...]:
    comparator = comparison.comparators[0]
    if isinstance(comparator, ast.Name):
        neighbor = comparator.id
    elif isinstance(comparator, ast.Attribute) and isinstance(comparator.value, ast.Name):
        neighbor = comparator.value.id
    else:
        return ()
    return (
        BehavioralObservation(
            neighbor,
            BehavioralRelationship.COMPARISON,
            comparator,
            {"operator": _comparison_operator(comparison.ops[0])},
        ),
    )


def _comparison_operator(operator: ast.cmpop) -> str:
    names = {
        ast.Eq: "eq",
        ast.NotEq: "not_eq",
        ast.Lt: "lt",
        ast.LtE: "lt_eq",
        ast.Gt: "gt",
        ast.GtE: "gt_eq",
        ast.In: "in",
        ast.NotIn: "not_in",
        ast.Is: "is",
        ast.IsNot: "is_not",
    }
    return names.get(type(operator), type(operator).__name__)
