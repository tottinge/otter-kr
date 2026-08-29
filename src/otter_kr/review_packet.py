"""Deterministic evidence packet composition for review consumers."""

from dataclasses import dataclass
from pathlib import Path

from otter_kr.evidence_context import EvidenceContext
from otter_kr.git_history_snapshot import collect_git_history_snapshot
from otter_kr.representation_inventory import collect_representation_inventory


@dataclass(frozen=True, slots=True)
class ReviewEvidencePacket:
    scope: dict[str, object]
    history: dict[str, object]
    inventory: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {"scope": self.scope, "history": self.history, "inventory": self.inventory}


def collect_review_packet(
    repository: Path, *, since_unix_time: int, limit: int
) -> ReviewEvidencePacket:
    context = EvidenceContext.from_git()
    snapshot = collect_git_history_snapshot(
        repository, since_unix_time=since_unix_time, limit=limit, changes=context.changes
    )
    return ReviewEvidencePacket(
        scope={
            "repository_root": str(repository.resolve()),
            "since_unix_time": since_unix_time,
            "limit": limit,
        },
        history=snapshot.to_dict(),
        inventory=collect_representation_inventory(
            repository, since_unix_time=since_unix_time, limit=limit
        ).to_dict(),
    )
