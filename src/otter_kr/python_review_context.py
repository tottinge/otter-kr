"""Bounded Python names, dependencies, and test mappings for review packets."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from otter_kr.git_files import GitCliFileSource
from otter_kr.python_imports import import_python
from otter_kr.python_tests import find_tests_for_symbol


@dataclass(frozen=True, slots=True)
class PythonReviewContext:
    names: tuple[dict[str, object], ...]
    dependencies: dict[str, object]
    tests: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "names": list(self.names),
            "dependencies": self.dependencies,
            "tests": list(self.tests),
        }


def collect_python_review_context(
    repository: Path, *, limit: int, path: str | None = None
) -> PythonReviewContext:
    resolved = repository.resolve()
    files = GitCliFileSource().python_files(resolved)
    if path is not None:
        files = [
            candidate for candidate in files if candidate.relative_to(resolved).as_posix() == path
        ]
    names: list[dict[str, object]] = []
    for path in files:
        relative = path.relative_to(resolved).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except (OSError, SyntaxError, UnicodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
                names.append(
                    {
                        "path": relative,
                        "line": node.lineno,
                        "column": node.col_offset,
                        "name": node.name,
                        "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                    }
                )
    names.sort(key=lambda item: (str(item["path"]), int(item["line"]), int(item["column"])))
    selected = tuple(names[:limit])
    tests = tuple(find_tests_for_symbol(resolved, str(item["name"])).to_dict() for item in selected)
    dependencies = import_python(resolved).to_dict()
    if path is not None:
        dependencies["edges"] = [edge for edge in dependencies["edges"] if edge["path"] == path]
        dependencies["warnings"] = [
            warning for warning in dependencies["warnings"] if warning["path"] == path
        ]
    edges = dependencies["edges"]
    dependencies["edge_count"] = len(edges)
    dependencies["edges"] = edges[:limit]
    dependencies["edges_truncated"] = len(edges) > limit
    return PythonReviewContext(selected, dependencies, tests)
