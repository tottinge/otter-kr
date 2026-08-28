"""Historical file-neighborhood evidence for a Python identifier seed."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from otter_kr.git_cli_history import GitCliHistory
from otter_kr.git_ports import CommitFileChangeSource
from otter_kr.git_scoped_cochange import collect_scoped_cochange
from otter_kr.python_names import find_names


@dataclass(frozen=True, slots=True)
class HistoricalEdge:
    seed_path: str
    neighbor_path: str
    weight: float
    cochange_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "seed_path": self.seed_path,
            "neighbor_path": self.neighbor_path,
            "weight": self.weight,
            "cochange_count": self.cochange_count,
        }


@dataclass(frozen=True, slots=True)
class PythonHistoricalNeighborhoodReport:
    seed: str
    seed_paths: tuple[str, ...]
    edges: tuple[HistoricalEdge, ...]
    parse_failures: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "language": "python",
            "seed": self.seed,
            "seed_paths": list(self.seed_paths),
            "edges": [edge.to_dict() for edge in self.edges],
            "parse_failures": list(self.parse_failures),
        }


def find_historical_neighborhood(
    repository: Path,
    seed: str,
    *,
    since_unix_time: int,
    limit: int,
    changes: CommitFileChangeSource | None = None,
) -> PythonHistoricalNeighborhoodReport:
    names = find_names(repository, seed)
    seed_paths = tuple(sorted({occurrence.path for occurrence in names.occurrences}))
    edges: list[HistoricalEdge] = []
    source = changes or GitCliHistory()
    for seed_path in seed_paths:
        report = collect_scoped_cochange(
            repository,
            seed_path,
            since_unix_time=since_unix_time,
            limit=limit,
            changes=source,
        )
        for pair in report.pairs:
            neighbor = pair.right_path if pair.left_path == seed_path else pair.left_path
            edges.append(HistoricalEdge(seed_path, neighbor, pair.weight, pair.commit_count))
    return PythonHistoricalNeighborhoodReport(
        seed,
        seed_paths,
        tuple(sorted(edges, key=lambda edge: (edge.seed_path, edge.neighbor_path))),
        tuple(
            {"path": failure.path, "message": failure.message}
            for failure in names.parse_failures
        ),
    )
