"""Deterministic evidence packet composition for review consumers."""

from dataclasses import dataclass
from pathlib import Path

from otter_kr.evidence_context import EvidenceContext
from otter_kr.git_history_snapshot import collect_git_history_snapshot
from otter_kr.python_review_context import collect_python_review_context
from otter_kr.representation_inventory import collect_representation_inventory


@dataclass(frozen=True, slots=True)
class ReviewEvidencePacket:
    scope: dict[str, object]
    history: dict[str, object]
    inventory: dict[str, object]
    names: list[dict[str, object]]
    dependencies: dict[str, object]
    tests: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return {
            "scope": self.scope,
            "history": self.history,
            "inventory": self.inventory,
            "names": self.names,
            "dependencies": self.dependencies,
            "tests": self.tests,
        }


def compose_review_packet(
    scope: dict[str, object],
    history: dict[str, object],
    inventory: dict[str, object],
    names: list[dict[str, object]] | None = None,
    dependencies: dict[str, object] | None = None,
    tests: list[dict[str, object]] | None = None,
) -> ReviewEvidencePacket:
    """Compose already-collected evidence without performing repository I/O."""
    return ReviewEvidencePacket(
        scope, history, inventory, names or [], dependencies or {}, tests or []
    )


def collect_review_packet(
    repository: Path,
    *,
    since_unix_time: int,
    limit: int,
    path: str | None = None,
    tip_sha: str | None = None,
) -> ReviewEvidencePacket:
    context = EvidenceContext.from_git()
    snapshot = collect_git_history_snapshot(
        repository,
        since_unix_time=since_unix_time,
        limit=limit,
        changes=context.changes,
        tip_sha=tip_sha,
    )
    packet = compose_review_packet(
        scope={
            "repository_root": str(repository.resolve()),
            "since_unix_time": since_unix_time,
            "limit": limit,
            **({"path": path} if path is not None else {}),
            **({"tip_sha": tip_sha} if tip_sha is not None else {}),
        },
        history=snapshot.to_dict(),
        inventory=collect_representation_inventory(
            repository, since_unix_time=since_unix_time, limit=limit
        ).to_dict(),
        **collect_python_review_context(repository, limit=limit, path=path).to_dict(),
    )
    if path is None:
        return packet
    history = dict(packet.history)
    history["files"] = [item for item in history["files"] if item["path"] == path]
    return ReviewEvidencePacket(
        packet.scope, history, packet.inventory, packet.names, packet.dependencies, packet.tests
    )
