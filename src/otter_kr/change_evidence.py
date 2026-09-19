"""Evidence connecting one term's current neighborhood to bounded history."""

from dataclasses import dataclass
from pathlib import Path

from otter_kr.evidence_context import EvidenceContext
from otter_kr.git_history_snapshot import collect_git_history_snapshot
from otter_kr.python_carrier_guards import find_carrier_guards_for_seed
from otter_kr.python_neighborhood import find_python_neighborhood
from otter_kr.python_object_lifecycle import find_object_lifecycle


@dataclass(frozen=True, slots=True)
class TermChangeEvidence:
    term: str
    current: dict[str, object]
    history: dict[str, object]
    carrier_guards: dict[str, object] | None
    object_lifecycle: dict[str, object] | None = None
    dimensions: dict[str, dict[str, object]] | None = None

    def to_dict(self) -> dict[str, object]:
        dimensions = self.dimensions or {
            "ownership": {
                "source": "carrier_guards",
                "available": self.carrier_guards is not None,
            },
            "multiplicity": {
                "source": "current.nodes",
                "node_count": len(self.current.get("nodes", [])),
            },
            "coupling": {
                "source": "current.edges",
                "edge_count": len(self.current.get("edges", [])),
            },
            "history": {
                "source": "history",
                "file_count": len(self.history.get("files", [])),
            },
            "representations": {
                "source": "object_lifecycle",
                "available": self.object_lifecycle is not None,
            },
        }
        return {
            "term": self.term,
            "current": self.current,
            "history": self.history,
            "carrier_guards": self.carrier_guards,
            "object_lifecycle": self.object_lifecycle,
            "dimensions": dimensions,
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
