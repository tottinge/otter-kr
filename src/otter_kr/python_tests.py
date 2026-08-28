"""Deterministic evidence mapping Python symbols to tracked test functions."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path

from otter_kr.git_files import GitCliFileSource, TrackedFileSource


@dataclass(frozen=True, slots=True)
class TestEvidence:
    kind: str
    line: int
    column: int
    name: str
    expression: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TestCandidate:
    path: str
    line: int
    column: int
    qualified_name: str
    kind: str
    evidence: tuple[TestEvidence, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "qualified_name": self.qualified_name,
            "kind": self.kind,
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(frozen=True, slots=True)
class MatchingImport:
    path: str
    line: int
    column: int
    module: str | None
    relative_level: int
    imported_name: str
    local_name: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TestMappingReport:
    language: str
    symbol: str
    mapping_status: str
    candidates: tuple[TestCandidate, ...]
    matching_imports: tuple[MatchingImport, ...]
    warnings: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "language": self.language,
            "symbol": self.symbol,
            "mapping_status": self.mapping_status,
            "candidates": [item.to_dict() for item in self.candidates],
            "matching_imports": [item.to_dict() for item in self.matching_imports],
            "warnings": list(self.warnings),
        }


def _binding_kind(local_name: str, imported_name: str) -> str:
    if local_name == imported_name:
        return "imported_name"
    return "imported_alias"


def _expression_for(node: ast.Name, parents: dict[ast.AST, ast.AST]) -> str:
    parent = parents.get(node)
    if isinstance(parent, ast.Call) and parent.func is node:
        return ast.unparse(parent)
    return ast.unparse(node)


def _module_bindings(module: ast.Module, symbol: str) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for statement in module.body:
        if not isinstance(statement, ast.ImportFrom):
            continue
        for alias in statement.names:
            if alias.name != symbol:
                continue
            local_name = alias.asname or alias.name
            bindings[local_name] = _binding_kind(local_name, alias.name)
    return bindings


def _module_import_bindings(module: ast.Module) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for statement in module.body:
        if not isinstance(statement, ast.Import):
            continue
        for alias in statement.names:
            local_name = alias.asname or alias.name.split(".", 1)[0]
            bindings[local_name] = alias.name
    return bindings


def _attribute_chain(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _attribute_chain(node.value)
        return f"{prefix}.{node.attr}" if prefix else None
    return None


def _matching_imports_in_tree(
    path: str,
    tree: ast.AST,
    symbol: str,
) -> list[MatchingImport]:
    matching_imports: list[MatchingImport] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != symbol:
                    continue
                matching_imports.append(
                    MatchingImport(
                        path=path,
                        line=getattr(alias, "lineno", node.lineno),
                        column=getattr(alias, "col_offset", node.col_offset),
                        module=node.module,
                        relative_level=node.level,
                        imported_name=alias.name,
                        local_name=alias.asname or alias.name,
                    )
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                local_name = alias.asname or alias.name.split(".", 1)[0]
                expected_chains = {f"{alias.name}.{symbol}"}
                if alias.asname:
                    expected_chains.add(f"{local_name}.{symbol}")
                if any(
                    isinstance(candidate, ast.Attribute)
                    and _attribute_chain(candidate) in expected_chains
                    for candidate in ast.walk(tree)
                ):
                    matching_imports.append(
                        MatchingImport(
                            path=path,
                            line=getattr(alias, "lineno", node.lineno),
                            column=getattr(alias, "col_offset", node.col_offset),
                            module=alias.name,
                            relative_level=0,
                            imported_name=symbol,
                            local_name=local_name,
                        )
                    )
    return matching_imports


def _binding_names(target: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(target):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
    return names


class _FunctionLocalBindingCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.names: set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return None

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        return None

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return None

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self.names.update(_binding_names(target))
        self.generic_visit(node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self.names.update(_binding_names(node.target))
        if node.annotation is not None:
            self.generic_visit(node.annotation)
        if node.value is not None:
            self.generic_visit(node.value)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.names.update(_binding_names(node.target))
        self.generic_visit(node.value)

    def visit_For(self, node: ast.For) -> None:
        self.names.update(_binding_names(node.target))
        self.generic_visit(node.iter)
        for statement in [*node.body, *node.orelse]:
            self.visit(statement)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.names.update(_binding_names(node.target))
        self.generic_visit(node.iter)
        for statement in [*node.body, *node.orelse]:
            self.visit(statement)

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            if item.optional_vars is not None:
                self.names.update(_binding_names(item.optional_vars))
            self.visit(item.context_expr)
        for statement in node.body:
            self.visit(statement)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        for item in node.items:
            if item.optional_vars is not None:
                self.names.update(_binding_names(item.optional_vars))
            self.visit(item.context_expr)
        for statement in node.body:
            self.visit(statement)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name is not None:
            self.names.add(node.name)
        if node.type is not None:
            self.visit(node.type)
        for statement in node.body:
            self.visit(statement)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self.names.update(_binding_names(node.target))
        self.visit(node.value)


def _function_local_bindings(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    collector = _FunctionLocalBindingCollector()
    for argument in [
        *node.args.posonlyargs,
        *node.args.args,
        *node.args.kwonlyargs,
    ]:
        collector.names.add(argument.arg)
    if node.args.vararg is not None:
        collector.names.add(node.args.vararg.arg)
    if node.args.kwarg is not None:
        collector.names.add(node.args.kwarg.arg)
    for statement in node.body:
        collector.visit(statement)
    return collector.names


class _FunctionEvidenceCollector(ast.NodeVisitor):
    def __init__(
        self,
        symbol: str,
        parents: dict[ast.AST, ast.AST],
        bindings: dict[str, str],
        module_imports: dict[str, str],
        local_bindings: set[str],
    ) -> None:
        self.symbol = symbol
        self.parents = parents
        self.bindings = dict(bindings)
        self.module_imports = dict(module_imports)
        self.local_bindings = set(local_bindings)
        self.evidence: list[TestEvidence] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return None

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        return None

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name != self.symbol:
                continue
            local_name = alias.asname or alias.name
            self.bindings[local_name] = _binding_kind(local_name, alias.name)

    def visit_Name(self, node: ast.Name) -> None:
        if not isinstance(node.ctx, ast.Load):
            return
        if node.id in self.bindings and node.id in self.local_bindings:
            kind = "shadowed_name"
        elif node.id in self.bindings:
            kind = self.bindings[node.id]
        elif node.id == self.symbol:
            kind = "exact_name"
        else:
            return
        self.evidence.append(
            TestEvidence(
                kind=kind,
                line=node.lineno,
                column=node.col_offset,
                name=node.id,
                expression=_expression_for(node, self.parents),
            )
        )

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if not isinstance(node.ctx, ast.Load):
            return
        chain = _attribute_chain(node)
        if chain is None or node.attr != self.symbol:
            self.generic_visit(node)
            return
        for local_name, module in self.module_imports.items():
            if chain in {f"{local_name}.{self.symbol}", f"{module}.{self.symbol}"}:
                self.evidence.append(
                    TestEvidence(
                        kind="imported_module_attribute",
                        line=node.lineno,
                        column=node.col_offset,
                        name=node.attr,
                        expression=_expression_for(node, self.parents),
                    )
                )
                break
        self.generic_visit(node)


class _TestCollector(ast.NodeVisitor):
    def __init__(self, relative_path: str, symbol: str, parents: dict[ast.AST, ast.AST]) -> None:
        self.relative_path = relative_path
        self.symbol = symbol
        self.parents = parents
        self.class_stack: list[str] = []
        self.module_bindings: dict[str, str] = {}
        self.module_imports: dict[str, str] = {}
        self.candidates: list[TestCandidate] = []

    def visit_Module(self, node: ast.Module) -> None:
        self.module_bindings = _module_bindings(node, self.symbol)
        self.module_imports = _module_import_bindings(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._collect_candidate(node, kind="method" if self.class_stack else "function")

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._collect_candidate(node, kind="method" if self.class_stack else "function")

    def _collect_candidate(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        *,
        kind: str,
    ) -> None:
        if not node.name.startswith("test_"):
            return
        collector = _FunctionEvidenceCollector(
            self.symbol,
            self.parents,
            self.module_bindings,
            self.module_imports,
            _function_local_bindings(node),
        )
        for statement in node.body:
            collector.visit(statement)
        if not collector.evidence:
            return
        self.candidates.append(
            TestCandidate(
                path=self.relative_path,
                line=node.lineno,
                column=node.col_offset,
                qualified_name=".".join([*self.class_stack, node.name]),
                kind=kind,
                evidence=tuple(
                    sorted(
                        collector.evidence,
                        key=lambda item: (item.line, item.column, item.kind, item.name),
                    )
                ),
            )
        )


def _parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


def find_tests_for_symbol(
    repository: Path, symbol: str, file_source: TrackedFileSource | None = None
) -> TestMappingReport:
    repository = repository.resolve()
    if not repository.is_dir():
        raise ValueError(f"Repository is not a directory: {repository}")
    if not symbol.isidentifier():
        raise ValueError("Symbol must be a valid Python identifier")

    candidates: list[TestCandidate] = []
    matching_imports: list[MatchingImport] = []
    warnings: list[dict[str, str]] = []
    for path in (file_source or GitCliFileSource()).python_files(repository):
        relative = path.relative_to(repository).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except UnicodeError:
            warnings.append(
                {
                    "code": "unreadable_file",
                    "path": relative,
                    "message": "File could not be decoded as UTF-8.",
                }
            )
            continue
        except SyntaxError as error:
            warnings.append(
                {
                    "code": "invalid_python",
                    "path": relative,
                    "message": (
                        f"Syntax error at line {error.lineno}, column {error.offset}: {error.msg}"
                    ),
                }
            )
            continue
        matching_imports.extend(_matching_imports_in_tree(relative, tree, symbol))
        collector = _TestCollector(relative, symbol, _parent_map(tree))
        collector.visit(tree)
        candidates.extend(collector.candidates)

    return TestMappingReport(
        language="python",
        symbol=symbol,
        mapping_status="matched" if candidates else "no_mapping_found",
        candidates=tuple(
            sorted(candidates, key=lambda item: (item.path, item.line, item.column, item.kind))
        ),
        matching_imports=tuple(
            sorted(
                matching_imports,
                key=lambda item: (
                    item.path,
                    item.line,
                    item.column,
                    item.module or "",
                    item.relative_level,
                    item.imported_name,
                    item.local_name,
                ),
            )
        ),
        warnings=tuple(sorted(warnings, key=lambda item: (item["path"], item["code"]))),
    )
