"""Source-level structural measures for functions in tracked Python files."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path

from otter_kr.git_files import TrackedFileSource
from otter_kr.python_complexity import _collect_tracked_functions


class UnsupportedStructuralSyntax(Exception):
    """The function contains syntax outside the requested measure’s counting rules."""


def supports_structural_measure(measure: str) -> bool:
    return measure in _MEASURE_COUNTERS


@dataclass(frozen=True, slots=True)
class StructuralFunction:
    path: str
    qualified_name: str
    kind: str
    line: int
    column: int
    end_line: int
    count: int | None
    diagnostic: str | None = None

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        if self.diagnostic is None:
            result.pop("diagnostic")
        else:
            result.pop("count")
        return result


@dataclass(frozen=True, slots=True)
class StructuralComplexityReport:
    language: str
    measure: str
    functions: tuple[StructuralFunction, ...]
    warnings: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "language": self.language,
            "measure": self.measure,
            "functions": [function.to_dict() for function in self.functions],
            "warnings": list(self.warnings),
        }


def _dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else None
    return None


class _OperandCounter(ast.NodeVisitor):
    def __init__(self) -> None:
        self.names: set[str] = set()
        self.literals: set[tuple[type, object]] = set()

    def visit_Name(self, node: ast.Name) -> None:
        self.names.add(node.id)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        return

    def visit_Attribute(self, node: ast.Attribute) -> None:
        dotted = _dotted_name(node)
        if dotted is None:
            raise UnsupportedStructuralSyntax("Dynamic attribute chains are unsupported.")
        # Only a maximal attribute chain contributes; its prefixes are implicit.
        self.names.add(dotted)

    def visit_Constant(self, node: ast.Constant) -> None:
        self.literals.add((type(node.value), node.value))

    def visit_Lambda(self, node: ast.Lambda) -> None:
        raise UnsupportedStructuralSyntax(
            "Lambda expressions are unsupported in operand measurements."
        )

    def visit_Import(self, node: ast.Import) -> None:
        self.names.update(alias.asname or alias.name.split(".")[0] for alias in node.names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.names.update(alias.asname or alias.name for alias in node.names if alias.name != "*")

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name:
            self.names.add(node.name)
        super().generic_visit(node)

    def visit_MatchAs(self, node: ast.MatchAs) -> None:
        if node.name:
            self.names.add(node.name)
        super().generic_visit(node)

    def visit_MatchStar(self, node: ast.MatchStar) -> None:
        if node.name:
            self.names.add(node.name)

    def visit_MatchMapping(self, node: ast.MatchMapping) -> None:
        if node.rest:
            self.names.add(node.rest)
        super().generic_visit(node)


def _measured_body(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.stmt]:
    if ast.get_docstring(node, clean=False) is not None:
        return node.body[1:]
    return node.body


def count_operands(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Count distinct parameter names, body names/chains, and typed literal values."""
    counter = _OperandCounter()
    arguments = node.args
    counter.names.update(argument.arg for argument in arguments.posonlyargs)
    counter.names.update(argument.arg for argument in arguments.args)
    counter.names.update(argument.arg for argument in arguments.kwonlyargs)
    if arguments.vararg:
        counter.names.add(arguments.vararg.arg)
    if arguments.kwarg:
        counter.names.add(arguments.kwarg.arg)

    for statement in _measured_body(node):
        counter.visit(statement)
    return len(counter.names) + len(counter.literals)


_SUPPORTED_OPERATION_SYNTAX = {
    ast.Expr,
    ast.Return,
    ast.AnnAssign,
    ast.AugAssign,
    ast.If,
    ast.IfExp,
    ast.Pass,
    ast.Name,
    ast.Constant,
    ast.BoolOp,
    ast.Compare,
    ast.Tuple,
    ast.List,
    ast.keyword,
    ast.Slice,
}

_COUNTED_OPERATION_NODES = {
    ast.Assign,
    ast.NamedExpr,
    ast.BinOp,
    ast.UnaryOp,
    ast.Call,
    ast.Attribute,
    ast.Subscript,
    ast.Set,
    ast.Dict,
}
_SUPPORTED_OPERATION_SYNTAX |= _COUNTED_OPERATION_NODES


class _OperationCounter(ast.NodeVisitor):
    def __init__(self) -> None:
        self.count = 0

    def visit(self, node: ast.AST) -> None:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            return
        if isinstance(
            node,
            ast.operator | ast.unaryop | ast.boolop | ast.cmpop | ast.expr_context,
        ):
            return
        if type(node) not in _SUPPORTED_OPERATION_SYNTAX:
            raise UnsupportedStructuralSyntax(
                f"{type(node).__name__} syntax is unsupported in operation measurements."
            )
        if type(node) in _COUNTED_OPERATION_NODES or (
            isinstance(node, ast.AnnAssign) and node.value is not None
        ):
            self.count += 1
        elif isinstance(node, ast.AugAssign):
            self.count += 2
        elif isinstance(node, ast.BoolOp):
            self.count += len(node.values) - 1
        elif isinstance(node, ast.Compare):
            self.count += len(node.ops)
        elif isinstance(node, ast.Tuple | ast.List) and isinstance(node.ctx, ast.Load):
            self.count += 1
        super().visit(node)

    def generic_visit(self, node: ast.AST) -> None:
        if isinstance(node, ast.Call) and any(keyword.arg is None for keyword in node.keywords):
            raise UnsupportedStructuralSyntax(
                "Keyword unpacking is unsupported in operation measurements."
            )
        if isinstance(node, ast.Dict) and any(key is None for key in node.keys):
            raise UnsupportedStructuralSyntax(
                "Dictionary unpacking is unsupported in operation measurements."
            )
        super().generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self.visit(node.target)
        if node.value is not None:
            self.visit(node.value)


def count_operations(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Count admitted syntactic operation occurrences in a function body."""
    counter = _OperationCounter()
    for statement in _measured_body(node):
        counter.visit(statement)
    return counter.count


_MEASURE_COUNTERS = {
    "operands": count_operands,
    "operations": count_operations,
}


def analyze_python_structural_complexity(
    repository: Path,
    measure: str,
    file_source: TrackedFileSource | None = None,
) -> StructuralComplexityReport:
    """Measure source-level structural complexity in tracked Python functions."""
    counter = _MEASURE_COUNTERS.get(measure)
    if counter is None:
        raise ValueError(f"Unsupported Python structural measure: {measure}")
    functions: list[StructuralFunction] = []
    warnings: list[dict[str, str]] = []
    for discovered in _collect_tracked_functions(repository, file_source, warnings):
        try:
            count = counter(discovered.node)
            diagnostic = None
        except UnsupportedStructuralSyntax as error:
            count = None
            diagnostic = str(error)
        functions.append(
            StructuralFunction(
                path=discovered.path,
                qualified_name=discovered.qualified_name,
                kind=discovered.kind,
                line=discovered.line,
                column=discovered.column,
                end_line=discovered.end_line,
                count=count,
                diagnostic=diagnostic,
            )
        )
    return StructuralComplexityReport(
        "python",
        measure,
        tuple(
            sorted(
                functions, key=lambda item: (item.path, item.line, item.column, item.qualified_name)
            )
        ),
        tuple(sorted(warnings, key=lambda item: (item["path"], item["code"]))),
    )
