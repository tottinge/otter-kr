"""Projection of existing evidence under a caller-supplied seed."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from otter_kr.python_carrier_guards import CarrierGuardReport, find_carrier_guards_for_seed
from otter_kr.python_neighborhood import PythonNeighborhoodReport, find_python_neighborhood


@dataclass(frozen=True, slots=True)
class SeedEvidenceReport:
    seed: str
    source: str
    nodes: tuple[dict[str, object], ...]
    edges: tuple[dict[str, object], ...]
    locations: tuple[dict[str, object], ...]
    counts: dict[str, int]
    provenance: dict[str, object]
    carrier_guards: dict[str, object] | None

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "source": self.source,
            "nodes": list(self.nodes),
            "edges": list(self.edges),
            "locations": list(self.locations),
            "counts": self.counts,
            "provenance": self.provenance,
            "carrier_guards": self.carrier_guards,
        }


def project_python_neighborhood(
    repository: Path,
    seed: str,
    neighborhood: PythonNeighborhoodReport | None = None,
    carrier_guards: CarrierGuardReport | None = None,
) -> SeedEvidenceReport:
    evidence = neighborhood or find_python_neighborhood(repository, seed)
    guard_evidence = carrier_guards
    if guard_evidence is None and repository is not None:
        guard_evidence = find_carrier_guards_for_seed(repository, seed)
    nodes = tuple(node.to_dict() for node in evidence.nodes)
    edges = tuple(edge.to_dict() for edge in evidence.edges)
    return SeedEvidenceReport(
        seed=seed,
        source="python.neighborhood",
        nodes=nodes,
        edges=edges,
        locations=(),
        counts={"files_scanned": evidence.files_scanned, "nodes": len(nodes), "edges": len(edges)},
        provenance={
            "operation": "python.neighborhood",
            "parse_failures": list(evidence.parse_failures),
        },
        carrier_guards=guard_evidence.to_dict() if guard_evidence is not None else None,
    )
