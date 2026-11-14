"""Compose existing Python measurements for an exact tracked function."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from otter_kr.python_complexity import _collect_tracked_functions, _function_metrics
from otter_kr.python_primitive_density import _measure_annotations, _parameter_annotations
from otter_kr.python_structural_complexity import (
    UnsupportedStructuralSyntax,
    count_operands,
    count_operations,
    count_paths,
)


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
    warnings: list[dict[str, str]] = []
    matches = [
        definition
        for definition in _collect_tracked_functions(
            repository, None, warnings, target_path=target.path
        )
        if definition.qualified_name == target.qualified_name
    ]
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
        "structural_complexity": {
            "operands": _structural_measure(lambda: count_operands(node)),
            "operations": _structural_measure(lambda: count_operations(node)),
            "paths": _structural_measure(lambda: count_paths(node)),
        },
        "warnings": warnings,
    }
