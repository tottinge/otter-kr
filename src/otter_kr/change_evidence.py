"""Evidence connecting one term's current neighborhood to bounded history."""

from dataclasses import dataclass
from pathlib import Path

from otter_kr.evidence_context import EvidenceContext
from otter_kr.git_history_snapshot import collect_git_history_snapshot
from otter_kr.python_carrier_guards import find_carrier_guards_for_seed
from otter_kr.python_neighborhood import find_python_neighborhood
from otter_kr.python_object_lifecycle import find_object_lifecycle

_MAX_DIMENSION_LOCATIONS = 32


@dataclass(frozen=True, slots=True)
class TermChangeEvidence:
    term: str
    current: dict[str, object]
    history: dict[str, object]
    carrier_guards: dict[str, object] | None
    object_lifecycle: dict[str, object] | None = None
    dimensions: dict[str, dict[str, object]] | None = None

    def to_dict(self) -> dict[str, object]:
        dimensions = self.dimensions or _dimension_index(
            self.current, self.history, self.carrier_guards, self.object_lifecycle
        )
        return {
            "term": self.term,
            "current": self.current,
            "history": self.history,
            "carrier_guards": self.carrier_guards,
            "object_lifecycle": self.object_lifecycle,
            "dimensions": dimensions,
        }


def _dimension_index(
    current: dict[str, object],
    history: dict[str, object],
    carrier_guards: dict[str, object] | None,
    object_lifecycle: dict[str, object] | None,
) -> dict[str, dict[str, object]]:
    nodes = current.get("nodes", [])
    edges = current.get("edges", [])
    files = history.get("files", [])
    locations = [location for node in nodes for location in node.get("locations", [])]
    return {
        "ownership": {
            "source": "carrier_guards",
            "available": carrier_guards is not None,
            "occurrence_count": len(carrier_guards.get("occurrences", [])) if carrier_guards else 0,
            "group_count": len(carrier_guards.get("groups", [])) if carrier_guards else 0,
        },
        "multiplicity": {
            "source": "current.nodes",
            "node_count": len(nodes),
            "location_count": len(locations),
            "locations": locations[:_MAX_DIMENSION_LOCATIONS],
            "locations_truncated": len(locations) > _MAX_DIMENSION_LOCATIONS,
        },
        "coupling": {
            "source": "current.edges",
            "edge_count": len(edges),
        },
        "history": {
            "source": "history.files",
            "file_count": len(files),
            "paths": [item["path"] for item in files],
        },
        "representations": {
            "source": "object_lifecycle",
            "available": object_lifecycle is not None,
            "construction_count": len(object_lifecycle.get("constructions", []))
            if object_lifecycle
            else 0,
            "operation_count": len(object_lifecycle.get("operations", []))
            if object_lifecycle
            else 0,
        },
    }


def collect_term_change_evidence(
    repository: Path, term: str, *, since_unix_time: int, limit: int
) -> TermChangeEvidence:
    context = EvidenceContext.from_git()
    carrier_guards = find_carrier_guards_for_seed(repository, term)
    lifecycle = find_object_lifecycle(repository, term).to_dict() if term.isidentifier() else None
    return TermChangeEvidence(
        term,
        find_python_neighborhood(repository, term).to_dict(),
        collect_git_history_snapshot(
            repository, since_unix_time=since_unix_time, limit=limit, changes=context.changes
        ).to_dict(),
        carrier_guards.to_dict() if carrier_guards is not None else None,
        lifecycle,
    )
