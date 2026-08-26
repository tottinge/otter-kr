"""Deterministic evidence for repeated Python parameter and field groups."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path

from otter_kr.git_files import GitCliFileSource, TrackedFileSource


@dataclass(frozen=True, slots=True)
class GroupOccurrence:
    path: str
    line: int
    column: int
    owner: str


@dataclass(frozen=True, slots=True)
class RepeatedGroup:
    kind: str
    members: tuple[str, ...]
    count: int
    occurrences: tuple[GroupOccurrence, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "members": list(self.members),
            "count": self.count,
            "occurrences": [asdict(item) for item in self.occurrences],
        }


@dataclass(frozen=True, slots=True)
class GroupReport:
    language: str
    groups: tuple[RepeatedGroup, ...]
    warnings: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "language": self.language,
            "groups": [item.to_dict() for item in self.groups],
            "warnings": list(self.warnings),
        }


class _GroupCollector(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.groups: dict[tuple[str, tuple[str, ...]], list[GroupOccurrence]] = {}
        self.class_stack: list[str] = []

    def _add(self, kind: str, members: tuple[str, ...], node: ast.AST, owner: str) -> None:
        if len(members) < 2:
            return
        key = (kind, members)
        self.groups.setdefault(key, []).append(
            GroupOccurrence(self.path, node.lineno, node.col_offset, owner)
        )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        members = tuple(arg.arg for arg in args if arg.arg not in {"self", "cls"})
        owner = ".".join([*self.class_stack, node.name])
        self._add("parameters", members, node, owner)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        fields = tuple(
            target.id
            for statement in node.body
            if isinstance(statement, ast.AnnAssign)
            for target in [statement.target]
            if isinstance(target, ast.Name)
        )
        self._add("fields", fields, node, ".".join([*self.class_stack, node.name]))
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()


def find_repeated_groups(
    repository: Path, file_source: TrackedFileSource | None = None
) -> GroupReport:
    repository = repository.resolve()
    if not repository.is_dir():
        raise ValueError(f"Repository is not a directory: {repository}")
    grouped: dict[tuple[str, tuple[str, ...]], list[GroupOccurrence]] = {}
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
        collector = _GroupCollector(relative)
        collector.visit(tree)
        for key, occurrences in collector.groups.items():
            grouped.setdefault(key, []).extend(occurrences)
    groups = tuple(
        RepeatedGroup(
            kind,
            members,
            len(items),
            tuple(sorted(items, key=lambda x: (x.path, x.line, x.column, x.owner))),
        )
        for (kind, members), items in sorted(grouped.items())
        if len(items) > 1
    )
    return GroupReport(
        "python", groups, tuple(sorted(warnings, key=lambda x: (x["path"], x["code"])))
    )
