"""Exact and lexical identifier-neighborhood evidence for Python repositories."""

from __future__ import annotations

import ast
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from otter_kr.git_files import GitCliFileSource, TrackedFileSource

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_SEPARATORS = re.compile(r"[^A-Za-z0-9]+")


@dataclass(frozen=True, slots=True)
class NeighborhoodNode:
    name: str
    occurrence_count: int

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "occurrence_count": self.occurrence_count}


@dataclass(frozen=True, slots=True)
class NeighborhoodEdge:
    seed: str
    neighbor: str
    weight: int
    discovery_pass: str
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "neighbor": self.neighbor,
            "weight": self.weight,
            "discovery_pass": self.discovery_pass,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class PythonNeighborhoodReport:
    seed: str
    files_scanned: int
    nodes: tuple[NeighborhoodNode, ...]
    edges: tuple[NeighborhoodEdge, ...]
    parse_failures: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "language": "python",
            "seed": self.seed,
            "files_scanned": self.files_scanned,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "parse_failures": list(self.parse_failures),
        }


def find_python_neighborhood(
    repository: Path, seed: str, file_source: TrackedFileSource | None = None
) -> PythonNeighborhoodReport:
    repository = repository.resolve()
    if not repository.is_dir():
        raise ValueError(f"Repository is not a directory: {repository}")
    seed_words = _identifier_words(seed)
    if not seed_words:
        raise ValueError("Seed must contain at least one letter or number")

    files = (file_source or GitCliFileSource()).python_files(repository)
    counts: Counter[str] = Counter()
    failures: list[dict[str, object]] = []
    for path in files:
        relative = path.relative_to(repository).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except (SyntaxError, UnicodeError) as error:
            failures.append({"path": relative, "message": str(error)})
            continue
        for node in ast.walk(tree):
            name = _node_name(node)
            if name is not None:
                counts[name] += 1

    exact = sorted(name for name in counts if name == seed)
    lexical = sorted(
        name
        for name in counts
        if name != seed and _shares_words(seed_words, _identifier_words(name))
    )
    names = exact + lexical
    nodes = tuple(NeighborhoodNode(name, counts[name]) for name in names)
    edges = tuple(
        NeighborhoodEdge(
            seed=seed,
            neighbor=name,
            weight=counts[name],
            discovery_pass="exact" if name == seed else "lexical",
            reason="exact identifier match" if name == seed else "shared identifier word",
        )
        for name in names
    )
    return PythonNeighborhoodReport(seed, len(files), nodes, edges, tuple(failures))


def _node_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return node.name
    if isinstance(node, ast.arg):
        return node.arg
    if isinstance(node, ast.Name):
        return node.id
    return None


def _identifier_words(identifier: str) -> tuple[str, ...]:
    separated = _CAMEL_BOUNDARY.sub("_", identifier)
    return tuple(word.casefold() for word in _SEPARATORS.split(separated) if word)


def _shares_words(seed_words: tuple[str, ...], candidate_words: tuple[str, ...]) -> bool:
    return bool(seed_words) and bool(set(seed_words) & set(candidate_words))
