"""Evidence connecting one term's current neighborhood to bounded history."""

from dataclasses import dataclass
from pathlib import Path

from otter_kr.evidence_context import EvidenceContext
from otter_kr.git_history_snapshot import collect_git_history_snapshot
from otter_kr.python_carrier_guards import find_carrier_guards_for_seed
from otter_kr.python_neighborhood import find_python_neighborhood


@dataclass(frozen=True, slots=True)
class TermChangeEvidence:
    term: str
    current: dict[str, object]
    history: dict[str, object]
    carrier_guards: dict[str, object] | None

    def to_dict(self) -> dict[str, object]:
        return {
            "term": self.term,
            "current": self.current,
            "history": self.history,
            "carrier_guards": self.carrier_guards,
        }


def collect_term_change_evidence(
    repository: Path, term: str, *, since_unix_time: int, limit: int
) -> TermChangeEvidence:
    context = EvidenceContext.from_git()
    carrier_guards = find_carrier_guards_for_seed(repository, term)
    return TermChangeEvidence(
        term,
        find_python_neighborhood(repository, term).to_dict(),
        collect_git_history_snapshot(
            repository, since_unix_time=since_unix_time, limit=limit, changes=context.changes
        ).to_dict(),
        carrier_guards.to_dict() if carrier_guards is not None else None,
    )
