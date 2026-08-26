"""Deterministic function-level complexity evidence for tracked Python files."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path

from otter_kr.git_files import GitCliFileSource, TrackedFileSource


@dataclass(frozen=True, slots=True)
class FunctionComplexity:
    path: str
    qualified_name: str
    kind: str
    line: int
    column: int
    end_line: int
    max_nesting_depth: int
    branch_count: int
    line_count: int
    cyclomatic_count: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ComplexityReport:
    language: str
    functions: tuple[FunctionComplexity, ...]
    warnings: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "language": self.language,
            "functions": [function.to_dict() for function in self.functions],
            "warnings": list(self.warnings),
        }


def _module_name(relative_path: Path) -> str:
    parts = list(relative_path.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _function_metrics(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[int, int, int]:
    branches = 0
    cyclomatic = 1
    max_nesting = 0

    def visit(current: ast.AST, nesting: int) -> None:
        nonlocal branches, cyclomatic, max_nesting
        if isinstance(current, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            return
        if isinstance(current, ast.If | ast.For | ast.AsyncFor | ast.While | ast.Try | ast.IfExp):
            branches += 1
            cyclomatic += 1
            nesting += 1
            max_nesting = max(max_nesting, nesting)
        elif isinstance(current, ast.BoolOp):
            cyclomatic += len(current.values) - 1
        elif isinstance(current, ast.comprehension):
            branches += 1
            cyclomatic += 1
        for child in ast.iter_child_nodes(current):
            visit(child, nesting)

    for child in ast.iter_child_nodes(node):
        visit(child, 0)
    return branches, cyclomatic, max_nesting


class _FunctionCollector(ast.NodeVisitor):
    def __init__(self, relative_path: str, module: str) -> None:
        self.relative_path = relative_path
        self.module = module
        self.stack: list[str] = []
        self.functions: list[FunctionComplexity] = []

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, kind: str) -> None:
        components = [
            component[7:-1] if component.startswith("<class:") else component
            for component in self.stack
        ]
        qualname = ".".join([*components, node.name])
        branches, cyclomatic, max_nesting = _function_metrics(node)
        self.functions.append(
            FunctionComplexity(
                path=self.relative_path,
                qualified_name=qualname,
                kind=kind,
                line=node.lineno,
                column=node.col_offset,
                end_line=node.end_lineno or node.lineno,
                max_nesting_depth=max_nesting,
                branch_count=branches,
                line_count=(node.end_lineno or node.lineno) - node.lineno + 1,
                cyclomatic_count=cyclomatic,
            )
        )
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(
            node, "method" if self.stack and self.stack[-1].startswith("<class:") else "function"
        )

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(
            node, "method" if self.stack and self.stack[-1].startswith("<class:") else "function"
        )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.stack.append(f"<class:{node.name}>")
        self.generic_visit(node)
        self.stack.pop()


def analyze_python_complexity(
    repository: Path, file_source: TrackedFileSource | None = None
) -> ComplexityReport:
    """Report deterministic AST complexity measurements for tracked Python files."""
    repository = repository.resolve()
    if not repository.is_dir():
        raise ValueError(f"Repository is not a directory: {repository}")

    functions: list[FunctionComplexity] = []
    warnings: list[dict[str, str]] = []
    for path in (file_source or GitCliFileSource()).python_files(repository):
        relative = path.relative_to(repository)
        relative_path = relative.as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError:
            warnings.append(
                {
                    "code": "unreadable_file",
                    "path": relative_path,
                    "message": "File could not be decoded as UTF-8.",
                }
            )
            continue
        try:
            tree = ast.parse(text, filename=relative_path)
        except SyntaxError as error:
            warnings.append(
                {
                    "code": "invalid_python",
                    "path": relative_path,
                    "message": (
                        f"Syntax error at line {error.lineno}, column {error.offset}: {error.msg}"
                    ),
                }
            )
            continue
        collector = _FunctionCollector(relative_path, _module_name(relative))
        collector.visit(tree)
        functions.extend(collector.functions)

    return ComplexityReport(
        language="python",
        functions=tuple(
            sorted(
                functions, key=lambda item: (item.path, item.line, item.column, item.qualified_name)
            )
        ),
        warnings=tuple(sorted(warnings, key=lambda item: (item["path"], item["code"]))),
    )
