"""Compose existing Python measurements for an exact tracked function."""

import ast
from collections import defaultdict
from collections.abc import Callable, Iterator, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from otter_kr.python_behavioral_neighborhood import _comparison_operator
from otter_kr.python_complexity import (
    _collect_tracked_functions,
    _CollectedFunction,
    _function_metrics,
)
from otter_kr.python_primitive_density import _measure_annotations, _parameter_annotations
from otter_kr.python_structural_complexity import (
    UnsupportedStructuralSyntax,
    count_operands,
    count_operations,
    count_paths,
)

_DECISION_SITE_LIMIT = 16


@dataclass(frozen=True, slots=True)
class FunctionTarget:
    path: str
    qualified_name: str

    def __post_init__(self) -> None:
        path = Path(self.path)
        if (
            path.is_absolute()
            or path.suffix != ".py"
            or path.as_posix() != self.path
            or ".." in path.parts
            or "\\" in self.path
        ):
            raise ValueError("path must be a repository-relative Python file.")
        if not all(part.isidentifier() for part in self.qualified_name.split(".")):
            raise ValueError("qualified_name must be a dot-separated Python identifier.")


def _structural_measure(counter: Callable[[], int]) -> dict[str, object]:
    try:
        return {"count": counter()}
    except UnsupportedStructuralSyntax as error:
        return {"diagnostic": str(error)}


def profile_python_function(repository: Path, target: FunctionTarget) -> dict[str, object]:
    """Return metrics for the one definition matching the file and qualified name."""
    return _profiles_for_targets(repository, (target,))[0]


def profile_python_functions(
    repository: Path, targets: Sequence[FunctionTarget]
) -> dict[str, object]:
    """Return one profile per requested target in request order."""
    return {
        "profiles": [
            {"target": asdict(target), **profile}
            for target, profile in zip(
                targets, _profiles_for_targets(repository, targets), strict=True
            )
        ]
    }


def _profiles_for_targets(
    repository: Path, targets: Sequence[FunctionTarget]
) -> list[dict[str, object]]:
    selected = {(target.path, target.qualified_name): target for target in targets}
    definitions: dict[FunctionTarget, list[_CollectedFunction]] = defaultdict(list)
    warnings: list[dict[str, str]] = []
    for definition in _collect_tracked_functions(
        repository, None, warnings, target_paths={target.path for target in targets}
    ):
        target = selected.get((definition.path, definition.qualified_name))
        if target is not None:
            definitions[target].append(definition)

    warnings_by_path: dict[str, list[dict[str, str]]] = defaultdict(list)
    for warning in warnings:
        warnings_by_path[warning["path"]].append(warning)
    profiles = {
        target: _profile_matches(definitions[target], warnings_by_path[target.path])
        for target in selected.values()
    }
    return [profiles[target] for target in targets]


def _body_nodes(
    node: ast.AST,
    parent: ast.AST,
) -> Iterator[tuple[ast.AST, ast.AST]]:
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Lambda):
        return
    yield node, parent
    for child in ast.iter_child_nodes(node):
        yield from _body_nodes(child, node)


def _bounded_decision_sites(
    expressions: list[ast.expr], *, include_operators: bool = False
) -> dict[str, object]:
    expressions.sort(key=lambda expression: (expression.lineno, expression.col_offset))
    sites = []
    for expression in expressions[:_DECISION_SITE_LIMIT]:
        site: dict[str, object] = {
            "line": expression.lineno,
            "column": expression.col_offset,
            "end_line": expression.end_lineno,
            "end_column": expression.end_col_offset,
        }
        if include_operators and isinstance(expression, ast.Compare):
            site["operators"] = [_comparison_operator(operator) for operator in expression.ops]
        sites.append(site)
    return {
        "site_count": len(expressions),
        "truncated": len(expressions) > _DECISION_SITE_LIMIT,
        "sites": sites,
    }


def _decision_evidence(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, object]:
    guards: list[ast.expr] = []
    comparisons: list[ast.expr] = []
    for statement in node.body:
        for candidate, _ in _body_nodes(statement, node):
            if isinstance(candidate, ast.If):
                guards.append(candidate.test)
            elif isinstance(candidate, ast.Compare):
                comparisons.append(candidate)
    return {
        "if_guards": _bounded_decision_sites(guards),
        "comparisons": _bounded_decision_sites(comparisons, include_operators=True),
    }


def _profile_matches(
    matches: list[_CollectedFunction], warnings: list[dict[str, str]]
) -> dict[str, object]:
    if not matches:
        return {"match_status": "unavailable" if warnings else "not_found", "warnings": warnings}
    if len(matches) > 1:
        return {
            "match_status": "ambiguous",
            "match_count": len(matches),
            "warnings": warnings,
        }

    definition = matches[0]
    node = definition.node
    branches, cyclomatic, nesting = _function_metrics(node)
    density = _measure_annotations(node, definition.qualified_name, _parameter_annotations(node))
    return {
        "match_status": "found",
        "function": {
            "path": definition.path,
            "qualified_name": definition.qualified_name,
            "kind": definition.kind,
            "line": definition.line,
            "column": definition.column,
            "end_line": definition.end_line,
        },
        "complexity": {
            "branch_count": branches,
            "cyclomatic_count": cyclomatic,
            "max_nesting_depth": nesting,
            "line_count": definition.end_line - definition.line + 1,
        },
        "primitive_density": {
            "primitive_count": density.primitive_count,
            "specialized_count": density.specialized_count,
            "total_count": density.total_count,
            "primitive_ratio": density.primitive_ratio,
        },
        **_decision_evidence(node),
        "structural_complexity": {
            "operands": _structural_measure(lambda: count_operands(node)),
            "operations": _structural_measure(lambda: count_operations(node)),
            "paths": _structural_measure(lambda: count_paths(node)),
        },
        "warnings": warnings,
    }
