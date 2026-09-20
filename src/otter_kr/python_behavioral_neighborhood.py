"""Statically visible behavioral evidence around a Python identifier."""

from __future__ import annotations

import ast
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from otter_kr.git_files import GitCliFileSource, TrackedFileSource


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


def find_behavioral_neighborhood(
    repository: Path, seed: str, file_source: TrackedFileSource | None = None
) -> PythonBehavioralNeighborhoodReport:
    repository = repository.resolve()
    if not repository.is_dir():
        raise ValueError(f"Repository is not a directory: {repository}")
    if not seed or not seed.isidentifier():
        raise ValueError("Seed must be a Python identifier")
    files = (file_source or GitCliFileSource()).python_files(repository)
    evidence: Counter[tuple[str, str]] = Counter()
    locations: dict[tuple[str, str], list[dict[str, object]]] = {}
    failures: list[dict[str, object]] = []
    for path in files:
        relative = path.relative_to(repository).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except (SyntaxError, UnicodeError) as error:
            failures.append({"path": relative, "message": str(error)})
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == seed
            ):
                for argument in node.args:
                    if isinstance(argument, ast.Name):
                        _record(
                            evidence,
                            locations,
                            (argument.id, "call argument"),
                            relative,
                            argument,
                        )
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id != seed
            ):
                for argument_index, argument in enumerate(node.args):
                    if isinstance(argument, ast.Name) and argument.id == seed:
                        _record(
                            evidence,
                            locations,
                            (node.func.id, "passed as argument"),
                            relative,
                            node.func,
                            {"argument_index": argument_index},
                        )
                for keyword in node.keywords:
                    if isinstance(keyword.value, ast.Name) and keyword.value.id == seed:
                        _record(
                            evidence,
                            locations,
                            (node.func.id, "passed as argument"),
                            relative,
                            node.func,
                            {"argument": keyword.arg},
                        )
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == seed
            ):
                _record(
                    evidence,
                    locations,
                    (node.func.attr, "method call"),
                    relative,
                    node.func,
                )
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == seed
            ):
                access = (
                    "write"
                    if isinstance(node.ctx, ast.Store)
                    else "delete"
                    if isinstance(node.ctx, ast.Del)
                    else "read"
                )
                _record(
                    evidence,
                    locations,
                    (node.attr, "field access"),
                    relative,
                    node,
                    {"access": access},
                )
            if (
                isinstance(node, ast.Compare)
                and isinstance(node.left, ast.Name)
                and node.left.id == seed
            ):
                for operator, comparator in zip(node.ops[:1], node.comparators[:1], strict=True):
                    details = {"operator": _comparison_operator(operator)}
                    if isinstance(comparator, ast.Name):
                        _record(
                            evidence,
                            locations,
                            (comparator.id, "type/enum comparison"),
                            relative,
                            comparator,
                            details,
                        )
                    elif isinstance(comparator, ast.Attribute) and isinstance(
                        comparator.value, ast.Name
                    ):
                        _record(
                            evidence,
                            locations,
                            (comparator.value.id, "type/enum comparison"),
                            relative,
                            comparator,
                            details,
                        )
    edges = tuple(
        BehavioralEdge(seed, neighbor, reason, weight, tuple(locations[(neighbor, reason)]))
        for (neighbor, reason), weight in sorted(evidence.items())
        if neighbor != seed
    )
    return PythonBehavioralNeighborhoodReport(seed, len(files), edges, tuple(failures))


def _record(
    evidence: Counter[tuple[str, str]],
    locations: dict[tuple[str, str], list[dict[str, object]]],
    key: tuple[str, str],
    path: str,
    node: ast.AST,
    details: dict[str, object] | None = None,
) -> None:
    evidence[key] += 1
    locations.setdefault(key, []).append(
        {"path": path, "line": node.lineno, "column": node.col_offset, **(details or {})}
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
