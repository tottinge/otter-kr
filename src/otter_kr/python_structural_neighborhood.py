"""Structural Python neighborhood evidence around a seed identifier."""

from __future__ import annotations

import ast
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from otter_kr.git_files import GitCliFileSource, TrackedFileSource
from otter_kr.python_neighborhood import _identifier_words, _node_name


@dataclass(frozen=True, slots=True)
class StructuralEdge:
    seed: str
    neighbor: str
    weight: int
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "neighbor": self.neighbor,
            "weight": self.weight,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class PythonStructuralNeighborhoodReport:
    seed: str
    files_scanned: int
    nodes: tuple[dict[str, object], ...]
    edges: tuple[StructuralEdge, ...]
    parse_failures: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "language": "python",
            "seed": self.seed,
            "files_scanned": self.files_scanned,
            "nodes": list(self.nodes),
            "edges": [edge.to_dict() for edge in self.edges],
            "parse_failures": list(self.parse_failures),
        }


def find_structural_neighborhood(
    repository: Path, seed: str, file_source: TrackedFileSource | None = None
) -> PythonStructuralNeighborhoodReport:
    repository = repository.resolve()
    if not repository.is_dir():
        raise ValueError(f"Repository is not a directory: {repository}")
    if not _identifier_words(seed):
        raise ValueError("Seed must contain at least one letter or number")
    files = (file_source or GitCliFileSource()).python_files(repository)
    counts: Counter[str] = Counter()
    evidence: Counter[tuple[str, str]] = Counter()
    failures: list[dict[str, object]] = []
    for path in files:
        relative = path.relative_to(repository).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except (SyntaxError, UnicodeError) as error:
            failures.append({"path": relative, "message": str(error)})
            continue
        names = [name for node in ast.walk(tree) if (name := _node_name(node))]
        counts.update(names)
        if seed not in names:
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.level == 0
                and node.module
                and any(alias.name == seed for alias in node.names)
            ):
                evidence[(node.module, "import target")] += 1
                counts[node.module] += 1
        for name in set(names):
            if name != seed:
                evidence[(name, "shared file")] += 1
        for parent in ast.walk(tree):
            child_names = [
                name for node in ast.iter_child_nodes(parent) if (name := _node_name(node))
            ]
            if seed in child_names:
                for name in child_names:
                    if name != seed:
                        evidence[(name, "AST adjacency")] += 1
    names = sorted(name for name, _ in evidence)
    edges = tuple(
        StructuralEdge(seed, name, weight, reason)
        for (name, reason), weight in sorted(evidence.items())
    )
    nodes = tuple({"name": name, "occurrence_count": counts[name]} for name in names)
    return PythonStructuralNeighborhoodReport(seed, len(files), nodes, edges, tuple(failures))
