"""Compose existing Python measurements for an exact tracked function."""

import ast
from collections import defaultdict
from collections.abc import Callable, Iterator, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

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

_IF_GUARD_LIMIT = 16


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


def _if_guards(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, object]:
    predicates = sorted(
        (
            candidate.test
            for statement in node.body
            for candidate, _ in _body_nodes(statement, node)
            if isinstance(candidate, ast.If)
        ),
        key=lambda test: (test.lineno, test.col_offset),
    )
    return {
        "site_count": len(predicates),
        "truncated": len(predicates) > _IF_GUARD_LIMIT,
        "sites": [
            {
                "line": test.lineno,
                "column": test.col_offset,
                "end_line": test.end_lineno,
                "end_column": test.end_col_offset,
            }
            for test in predicates[:_IF_GUARD_LIMIT]
        ],
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
        "if_guards": _if_guards(node),
        "structural_complexity": {
            "operands": _structural_measure(lambda: count_operands(node)),
            "operations": _structural_measure(lambda: count_operations(node)),
            "paths": _structural_measure(lambda: count_paths(node)),
        },
        "warnings": warnings,
    }
