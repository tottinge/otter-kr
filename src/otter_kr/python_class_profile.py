"""Compose declared-field and method evidence for an exact tracked Python class."""

import ast
from dataclasses import dataclass
from pathlib import Path

from otter_kr.python_complexity import _collect_tracked_python_trees, _FunctionCollector
from otter_kr.python_function_profile import (
    FunctionTarget,
    _attribute_operations,
    _body_nodes,
    _profile_matches,
)
from otter_kr.python_primitive_density import _measure_annotations

_FIELD_SITE_LIMIT = 16


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


def _method_field_accesses(
    node: ast.FunctionDef | ast.AsyncFunctionDef, fields: set[str]
) -> dict[str, object]:
    """Find syntactic accesses through the first positional parameter's name."""
    positional = [*node.args.posonlyargs, *node.args.args]
    static = any(
        ast.unparse(decorator) in {"staticmethod", "builtins.staticmethod"}
        for decorator in node.decorator_list
    )
    sites = []
    if positional and fields and not static:
        receiver = positional[0].arg
        for statement in node.body:
            for access, parent in _body_nodes(statement, node):
                if not (
                    isinstance(access, ast.Attribute)
                    and isinstance(access.value, ast.Name)
                    and access.value.id == receiver
                    and access.attr in fields
                ):
                    continue
                operations = _attribute_operations(access, parent)
                if operations:
                    sites.append((access.lineno, access.col_offset, access.attr, operations))
    sites.sort()
    return {
        "site_count": len(sites),
        "truncated": len(sites) > _FIELD_SITE_LIMIT,
        "sites": [
            {"field": field, "line": line, "column": column, "operations": operations}
            for line, column, field, operations in sites[:_FIELD_SITE_LIMIT]
        ],
    }


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
    declarations = [statement for statement in node.body if isinstance(statement, ast.AnnAssign)]
    fields = {
        statement.target.id for statement in declarations if isinstance(statement.target, ast.Name)
    }
    density = _measure_annotations(
        node, target.qualified_name, [statement.annotation for statement in declarations]
    )
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
        "methods": [
            {
                **_profile_matches([method], []),
                "field_accesses": _method_field_accesses(method.node, fields),
            }
            for method in methods[: query.limit]
        ],
        "warnings": warnings,
    }
