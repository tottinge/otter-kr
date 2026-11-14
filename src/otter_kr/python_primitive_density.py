"""Deterministic evidence for primitive density in Python nodes."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path

from otter_kr.git_files import GitCliFileSource, TrackedFileSource

_PRIMITIVE_NAMES = {"bool", "bytes", "dict", "float", "int", "list", "set", "str", "tuple"}
_GENERIC_NAMES = {
    "Collection",
    "Dict",
    "Iterable",
    "List",
    "Mapping",
    "MutableMapping",
    "MutableSequence",
    "Sequence",
    "Set",
    "Tuple",
}


@dataclass(frozen=True, slots=True)
class PrimitiveDensityNode:
    name: str
    line: int
    column: int
    primitive_count: int
    specialized_count: int

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["total_count"] = self.total_count
        data["primitive_ratio"] = self.primitive_ratio
        return data

    @property
    def total_count(self) -> int:
        return self.primitive_count + self.specialized_count

    @property
    def primitive_ratio(self) -> float | None:
        if not self.total_count:
            return None
        return self.primitive_count / self.total_count


@dataclass(frozen=True, slots=True)
class PrimitiveDensityFile:
    path: str
    nodes: tuple[PrimitiveDensityNode, ...]

    @property
    def primitive_count(self) -> int:
        return sum(node.primitive_count for node in self.nodes)

    @property
    def specialized_count(self) -> int:
        return sum(node.specialized_count for node in self.nodes)

    @property
    def total_count(self) -> int:
        return self.primitive_count + self.specialized_count

    @property
    def primitive_ratio(self) -> float | None:
        if not self.total_count:
            return None
        return self.primitive_count / self.total_count

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "primitive_count": self.primitive_count,
            "specialized_count": self.specialized_count,
            "total_count": self.total_count,
            "primitive_ratio": self.primitive_ratio,
            "nodes": [node.to_dict() for node in self.nodes],
        }


@dataclass(frozen=True, slots=True)
class PrimitiveDensityReport:
    language: str
    files: tuple[PrimitiveDensityFile, ...]
    warnings: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "language": self.language,
            "files": [item.to_dict() for item in self.files],
            "warnings": list(self.warnings),
        }


def _annotation_kind(annotation: ast.expr) -> str | None:
    if isinstance(annotation, ast.Name):
        name = annotation.id
    elif isinstance(annotation, ast.Attribute):
        name = annotation.attr
    elif isinstance(annotation, ast.Subscript):
        return _annotation_kind(annotation.value)
    else:
        return None
    if name in _PRIMITIVE_NAMES or name in _GENERIC_NAMES:
        return "primitive"
    if name == "Any":
        return None
    return "specialized"


def _parameter_annotations(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.expr]:
    arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    arguments.extend(argument for argument in (node.args.vararg, node.args.kwarg) if argument)
    return [
        argument.annotation
        for argument in arguments
        if argument.arg not in {"self", "cls"} and argument.annotation
    ]


def _measure_annotations(
    node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
    name: str,
    annotations: list[ast.expr],
) -> PrimitiveDensityNode:
    return PrimitiveDensityNode(
        name=name,
        line=node.lineno,
        column=node.col_offset,
        primitive_count=sum(_annotation_kind(item) == "primitive" for item in annotations),
        specialized_count=sum(_annotation_kind(item) == "specialized" for item in annotations),
    )


class _DensityCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.nodes: list[PrimitiveDensityNode] = []
        self._scope: list[str] = []

    def _record(
        self,
        node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
        name: str,
        annotations: list[ast.expr],
    ) -> None:
        density = _measure_annotations(node, name, annotations)
        if density.total_count:
            self.nodes.append(density)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        annotations = [
            statement.annotation for statement in node.body if isinstance(statement, ast.AnnAssign)
        ]
        name = ".".join([*self._scope, node.name])
        self._record(node, name, annotations)
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        name = ".".join([*self._scope, node.name])
        self._record(node, name, _parameter_annotations(node))
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function


def analyze_primitive_density(
    repository: Path, file_source: TrackedFileSource | None = None
) -> PrimitiveDensityReport:
    """Measure annotated primitive versus specialized types in tracked Python files."""
    repository = repository.resolve()
    if not repository.is_dir():
        raise ValueError(f"Repository is not a directory: {repository}")

    files: list[PrimitiveDensityFile] = []
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
        collector = _DensityCollector()
        collector.visit(tree)
        files.append(PrimitiveDensityFile(relative, tuple(collector.nodes)))
    return PrimitiveDensityReport(
        "python",
        tuple(files),
        tuple(sorted(warnings, key=lambda item: (item["path"], item["code"]))),
    )
