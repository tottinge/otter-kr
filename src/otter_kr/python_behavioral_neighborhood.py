"""Statically visible behavioral evidence around a Python identifier."""

from __future__ import annotations

import ast
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from otter_kr.git_files import GitCliFileSource, TrackedFileSource


@dataclass(frozen=True, slots=True)
class BehavioralEdge:
    seed: str
    neighbor: str
    reason: str
    weight: int

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "neighbor": self.neighbor,
            "reason": self.reason,
            "weight": self.weight,
        }


@dataclass(frozen=True, slots=True)
class PythonBehavioralNeighborhoodReport:
    seed: str
    files_scanned: int
    edges: tuple[BehavioralEdge, ...]
    parse_failures: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "language": "python",
            "seed": self.seed,
            "files_scanned": self.files_scanned,
            "edges": [edge.to_dict() for edge in self.edges],
            "parse_failures": list(self.parse_failures),
        }


def find_behavioral_neighborhood(
    repository: Path, seed: str, file_source: TrackedFileSource | None = None
) -> PythonBehavioralNeighborhoodReport:
    repository = repository.resolve()
    if not repository.is_dir():
        raise ValueError(f"Repository is not a directory: {repository}")
    if not seed or not seed.isidentifier():
        raise ValueError("Seed must be a Python identifier")
    files = (file_source or GitCliFileSource()).python_files(repository)
    evidence: Counter[tuple[str, str]] = Counter()
    failures: list[dict[str, object]] = []
    for path in files:
        relative = path.relative_to(repository).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except (SyntaxError, UnicodeError) as error:
            failures.append({"path": relative, "message": str(error)})
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == seed
            ):
                for argument in node.args:
                    if isinstance(argument, ast.Name):
                        evidence[(argument.id, "call argument")] += 1
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == seed
            ):
                evidence[(node.attr, "field access")] += 1
            if (
                isinstance(node, ast.Compare)
                and isinstance(node.left, ast.Name)
                and node.left.id == seed
            ):
                for comparator in node.comparators:
                    if isinstance(comparator, ast.Name):
                        evidence[(comparator.id, "type/enum comparison")] += 1
                    elif isinstance(comparator, ast.Attribute) and isinstance(
                        comparator.value, ast.Name
                    ):
                        evidence[(comparator.value.id, "type/enum comparison")] += 1
    edges = tuple(
        BehavioralEdge(seed, neighbor, reason, weight)
        for (neighbor, reason), weight in sorted(evidence.items())
        if neighbor != seed
    )
    return PythonBehavioralNeighborhoodReport(seed, len(files), edges, tuple(failures))
