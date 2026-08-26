"""Deterministic evidence for structurally duplicate Python helpers."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path

from otter_kr.git_files import GitCliFileSource, TrackedFileSource


@dataclass(frozen=True, slots=True)
class HelperOccurrence:
    path: str
    qualified_name: str
    kind: str
    line: int
    column: int
    end_line: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DuplicateGroup:
    fingerprint: str
    count: int
    occurrences: tuple[HelperOccurrence, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "fingerprint": self.fingerprint,
            "count": self.count,
            "occurrences": [item.to_dict() for item in self.occurrences],
        }


@dataclass(frozen=True, slots=True)
class DuplicatePair:
    fingerprint: str
    left: HelperOccurrence
    right: HelperOccurrence

    def to_dict(self) -> dict[str, object]:
        return {
            "fingerprint": self.fingerprint,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class DuplicateReport:
    language: str
    groups: tuple[DuplicateGroup, ...]
    pairs: tuple[DuplicatePair, ...]
    warnings: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "language": self.language,
            "groups": [item.to_dict() for item in self.groups],
            "pairs": [item.to_dict() for item in self.pairs],
            "warnings": list(self.warnings),
        }


def _ordered_unique(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            ordered.append(value)
            seen.add(value)
    return ordered


class _BoundNameCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.names: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        return

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store | ast.Del):
            self.names.append(node.id)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name is not None:
            self.names.append(node.name)
        self.generic_visit(node)

    def visit_alias(self, node: ast.alias) -> None:
        if node.asname is not None:
            self.names.append(node.asname)


def _local_name_mapping(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, str]:
    names = [arg.arg for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]]
    if node.args.vararg is not None:
        names.append(node.args.vararg.arg)
    if node.args.kwarg is not None:
        names.append(node.args.kwarg.arg)
    collector = _BoundNameCollector()
    for statement in node.body:
        collector.visit(statement)
    names.extend(collector.names)
    ordered = [name for name in _ordered_unique(names) if name not in {"self", "cls"}]
    return {name: f"local_{index}" for index, name in enumerate(ordered)}


class _StructureNormalizer(ast.NodeTransformer):
    def __init__(self, mapping: dict[str, str], root_name: str) -> None:
        self.mapping = mapping
        self.root_name = root_name

    def visit_Name(self, node: ast.Name) -> ast.AST:
        normalized = self.mapping.get(node.id)
        if normalized is None:
            return node
        return ast.copy_location(ast.Name(id=normalized, ctx=node.ctx), node)

    def visit_arg(self, node: ast.arg) -> ast.arg:
        normalized = self.mapping.get(node.arg, node.arg)
        return ast.arg(
            arg=normalized,
            annotation=self.visit(node.annotation) if node.annotation is not None else None,
            type_comment=node.type_comment,
        )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        if node.name == self.root_name:
            node = ast.FunctionDef(
                name="__function__",
                args=_normalized_arguments(self.visit(node.args)),
                body=[self.visit(statement) for statement in _body_without_docstring(node.body)],
                decorator_list=[self.visit(item) for item in node.decorator_list],
                returns=self.visit(node.returns) if node.returns is not None else None,
                type_comment=node.type_comment,
                type_params=node.type_params,
            )
            return ast.fix_missing_locations(node)
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        if node.name == self.root_name:
            node = ast.AsyncFunctionDef(
                name="__function__",
                args=_normalized_arguments(self.visit(node.args)),
                body=[self.visit(statement) for statement in _body_without_docstring(node.body)],
                decorator_list=[self.visit(item) for item in node.decorator_list],
                returns=self.visit(node.returns) if node.returns is not None else None,
                type_comment=node.type_comment,
                type_params=node.type_params,
            )
            return ast.fix_missing_locations(node)
        return self.generic_visit(node)


def _body_without_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    if not body:
        return body
    first = body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return body[1:]
    return body


def _normalized_arguments(arguments: ast.arguments) -> ast.arguments:
    return ast.arguments(
        posonlyargs=[item for item in arguments.posonlyargs if item.arg not in {"self", "cls"}],
        args=[item for item in arguments.args if item.arg not in {"self", "cls"}],
        vararg=arguments.vararg,
        kwonlyargs=[item for item in arguments.kwonlyargs if item.arg not in {"self", "cls"}],
        kw_defaults=arguments.kw_defaults,
        kwarg=arguments.kwarg,
        defaults=arguments.defaults,
    )


def _fingerprint(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    mapping = _local_name_mapping(node)
    normalized = _StructureNormalizer(mapping, node.name).visit(node)
    return ast.dump(normalized, include_attributes=False)


class _DuplicateCollector(ast.NodeVisitor):
    def __init__(self, relative_path: str) -> None:
        self.relative_path = relative_path
        self.class_stack: list[str] = []
        self.duplicates: dict[str, list[HelperOccurrence]] = {}

    def _record(self, node: ast.FunctionDef | ast.AsyncFunctionDef, kind: str) -> None:
        occurrence = HelperOccurrence(
            path=self.relative_path,
            qualified_name=".".join([*self.class_stack, node.name]),
            kind=kind,
            line=node.lineno,
            column=node.col_offset,
            end_line=node.end_lineno or node.lineno,
        )
        self.duplicates.setdefault(_fingerprint(node), []).append(occurrence)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        kind = "method" if self.class_stack else "function"
        self._record(node, kind)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        kind = "method" if self.class_stack else "function"
        self._record(node, kind)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()


def find_duplicate_helpers(
    repository: Path, file_source: TrackedFileSource | None = None
) -> DuplicateReport:
    """Report exact duplicate helper structure in tracked Python files."""
    repository = repository.resolve()
    if not repository.is_dir():
        raise ValueError(f"Repository is not a directory: {repository}")

    grouped: dict[str, list[HelperOccurrence]] = {}
    warnings: list[dict[str, str]] = []
    for path in (file_source or GitCliFileSource()).python_files(repository):
        relative_path = path.relative_to(repository).as_posix()
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
        collector = _DuplicateCollector(relative_path)
        collector.visit(tree)
        for fingerprint, occurrences in collector.duplicates.items():
            grouped.setdefault(fingerprint, []).extend(occurrences)

    groups = tuple(
        DuplicateGroup(
            fingerprint=fingerprint,
            count=len(sorted_occurrences),
            occurrences=sorted_occurrences,
        )
        for fingerprint, sorted_occurrences in (
            (
                fingerprint,
                tuple(
                    sorted(
                        occurrences,
                        key=lambda item: (
                            item.path,
                            item.line,
                            item.column,
                            item.qualified_name,
                        ),
                    )
                ),
            )
            for fingerprint, occurrences in sorted(grouped.items())
            if len(occurrences) > 1
        )
    )
    pairs = tuple(
        DuplicatePair(group.fingerprint, left, right)
        for group in groups
        for left, right in combinations(group.occurrences, 2)
    )
    return DuplicateReport(
        language="python",
        groups=groups,
        pairs=pairs,
        warnings=tuple(sorted(warnings, key=lambda item: (item["path"], item["code"]))),
    )
