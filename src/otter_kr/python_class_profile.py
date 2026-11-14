"""Compose declared-field and method evidence for an exact tracked Python class."""

import ast
from dataclasses import dataclass
from pathlib import Path

from otter_kr.python_complexity import _collect_tracked_python_trees, _FunctionCollector
from otter_kr.python_function_profile import FunctionTarget, _profile_matches
from otter_kr.python_primitive_density import _measure_annotations


@dataclass(frozen=True, slots=True)
class ClassProfileQuery:
    target: FunctionTarget
    limit: int


class _ClassCollector(_FunctionCollector):
    def __init__(self, path: str, qualified_name: str) -> None:
        super().__init__(path)
        self.target_name = qualified_name
        self.matches: list[ast.ClassDef] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if self.qualified_name(node.name) == self.target_name:
            self.matches.append(node)
        super().visit_ClassDef(node)


def profile_python_class(repository: Path, query: ClassProfileQuery) -> dict[str, object]:
    """Profile direct annotated fields and direct methods in source order."""
    target = query.target
    warnings: list[dict[str, str]] = []
    collector = _ClassCollector(target.path, target.qualified_name)
    for _, tree in _collect_tracked_python_trees(
        repository, None, warnings, target_paths={target.path}
    ):
        collector.visit(tree)

    if not collector.matches:
        return {"match_status": "unavailable" if warnings else "not_found", "warnings": warnings}
    if len(collector.matches) > 1:
        return {
            "match_status": "ambiguous",
            "match_count": len(collector.matches),
            "warnings": warnings,
        }

    node = collector.matches[0]
    fields = [
        statement.annotation for statement in node.body if isinstance(statement, ast.AnnAssign)
    ]
    density = _measure_annotations(node, target.qualified_name, fields)
    direct_statements = set(node.body)
    methods = [
        definition for definition in collector.definitions if definition.node in direct_statements
    ]
    return {
        "match_status": "found",
        "class": {
            "path": target.path,
            "qualified_name": target.qualified_name,
            "line": node.lineno,
            "column": node.col_offset,
            "end_line": node.end_lineno or node.lineno,
        },
        "field_density": {
            "primitive_count": density.primitive_count,
            "specialized_count": density.specialized_count,
            "total_count": density.total_count,
            "primitive_ratio": density.primitive_ratio,
        },
        "method_count": len(methods),
        "methods_truncated": len(methods) > query.limit,
        "methods": [_profile_matches([method], []) for method in methods[: query.limit]],
        "warnings": warnings,
    }
