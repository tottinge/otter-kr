"""Deterministic evidence for selected Python enum/type discriminations."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path

from otter_kr.git_files import GitCliFileSource, TrackedFileSource


@dataclass(frozen=True, slots=True)
class TypeDeclaration:
    path: str
    line: int
    column: int
    qualified_name: str
    kind: str
    members: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "qualified_name": self.qualified_name,
            "kind": self.kind,
            "members": list(self.members),
        }


@dataclass(frozen=True, slots=True)
class ComparisonEvidence:
    path: str
    line: int
    column: int
    operator: str
    member: str
    expression: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LookupEvidence:
    path: str
    line: int
    column: int
    kind: str
    member: str
    expression: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TypeDiscriminationReport:
    language: str
    type_name: str
    declarations: tuple[TypeDeclaration, ...]
    comparisons: tuple[ComparisonEvidence, ...]
    lookups: tuple[LookupEvidence, ...]
    warnings: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "language": self.language,
            "type_name": self.type_name,
            "declarations": [item.to_dict() for item in self.declarations],
            "comparisons": [item.to_dict() for item in self.comparisons],
            "lookups": [item.to_dict() for item in self.lookups],
            "warnings": list(self.warnings),
        }


def _member_reference(node: ast.AST, type_name: str) -> str | None:
    if (
        isinstance(node, ast.Attribute)
        and node.attr.isidentifier()
        and isinstance(node.value, ast.Name)
        and node.value.id == type_name
    ):
        return node.attr
    return None


def _enum_members(node: ast.ClassDef) -> tuple[str, ...]:
    members: list[str] = []
    for statement in node.body:
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name):
                    members.append(target.id)
        elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            members.append(statement.target.id)
    return tuple(members)


def _is_enum_declaration(node: ast.ClassDef) -> bool:
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id.endswith("Enum"):
            return True
        if isinstance(base, ast.Attribute) and base.attr.endswith("Enum"):
            return True
    return False


class _DiscriminationCollector(ast.NodeVisitor):
    def __init__(self, relative_path: str, type_name: str) -> None:
        self.relative_path = relative_path
        self.type_name = type_name
        self.class_stack: list[str] = []
        self.declarations: list[TypeDeclaration] = []
        self.comparisons: list[ComparisonEvidence] = []
        self.lookups: list[LookupEvidence] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if node.name == self.type_name:
            self.declarations.append(
                TypeDeclaration(
                    path=self.relative_path,
                    line=node.lineno,
                    column=node.col_offset,
                    qualified_name=".".join([*self.class_stack, node.name]),
                    kind="enum" if _is_enum_declaration(node) else "type",
                    members=_enum_members(node),
                )
            )
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_Compare(self, node: ast.Compare) -> None:
        left_member = _member_reference(node.left, self.type_name)
        for operator, comparator in zip(node.ops, node.comparators, strict=False):
            right_member = _member_reference(comparator, self.type_name)
            member = left_member or right_member
            operator_name = _compare_operator(operator)
            if member is not None and operator_name is not None:
                self.comparisons.append(
                    ComparisonEvidence(
                        path=self.relative_path,
                        line=node.lineno,
                        column=node.col_offset,
                        operator=operator_name,
                        member=member,
                        expression=ast.unparse(node),
                    )
                )
            left_member = right_member
        self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict) -> None:
        for key in node.keys:
            if key is None:
                continue
            member = _member_reference(key, self.type_name)
            if member is None:
                continue
            self.lookups.append(
                LookupEvidence(
                    path=self.relative_path,
                    line=key.lineno,
                    column=key.col_offset,
                    kind="dict_key",
                    member=member,
                    expression=ast.unparse(key),
                )
            )
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        member = _member_reference(node.slice, self.type_name)
        if member is not None:
            self.lookups.append(
                LookupEvidence(
                    path=self.relative_path,
                    line=node.lineno,
                    column=node.col_offset,
                    kind="subscript",
                    member=member,
                    expression=ast.unparse(node),
                )
            )
        self.generic_visit(node)


def _compare_operator(operator: ast.cmpop) -> str | None:
    if isinstance(operator, ast.Eq):
        return "=="
    if isinstance(operator, ast.Is):
        return "is"
    return None


def find_type_discriminations(
    repository: Path, type_name: str, file_source: TrackedFileSource | None = None
) -> TypeDiscriminationReport:
    repository = repository.resolve()
    if not repository.is_dir():
        raise ValueError(f"Repository is not a directory: {repository}")
    if not type_name.isidentifier():
        raise ValueError("Type name must be a valid Python identifier")

    declarations: list[TypeDeclaration] = []
    comparisons: list[ComparisonEvidence] = []
    lookups: list[LookupEvidence] = []
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
        collector = _DiscriminationCollector(relative, type_name)
        collector.visit(tree)
        declarations.extend(collector.declarations)
        comparisons.extend(collector.comparisons)
        lookups.extend(collector.lookups)

    return TypeDiscriminationReport(
        language="python",
        type_name=type_name,
        declarations=tuple(
            sorted(declarations, key=lambda item: (item.path, item.line, item.column))
        ),
        comparisons=tuple(
            sorted(comparisons, key=lambda item: (item.path, item.line, item.column))
        ),
        lookups=tuple(sorted(lookups, key=lambda item: (item.path, item.line, item.column))),
        warnings=tuple(sorted(warnings, key=lambda item: (item["path"], item["code"]))),
    )
