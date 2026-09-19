"""Deterministic evidence packet composition for review consumers."""

from dataclasses import dataclass
from pathlib import Path

from otter_kr.evidence_context import EvidenceContext
from otter_kr.git_history_snapshot import collect_git_history_snapshot
from otter_kr.python_review_context import PythonReviewContext, collect_python_review_context
from otter_kr.representation_inventory import collect_representation_inventory


@dataclass(frozen=True, slots=True)
class ReviewEvidencePacket:
    scope: dict[str, object]
    history: dict[str, object]
    inventory: dict[str, object]
    python: PythonReviewContext

    @property
    def names(self) -> list[dict[str, object]]:
        return list(self.python.names)

    @property
    def dependencies(self) -> dict[str, object]:
        return self.python.dependencies

    @property
    def tests(self) -> list[dict[str, object]]:
        return list(self.python.tests)

    def to_dict(self) -> dict[str, object]:
        return {
            "scope": self.scope,
            "history": self.history,
            "inventory": self.inventory,
            **self.python.to_dict(),
        }


def compose_review_packet(
    scope: dict[str, object],
    history: dict[str, object],
    inventory: dict[str, object],
    python: PythonReviewContext | None = None,
) -> ReviewEvidencePacket:
    """Compose already-collected evidence without performing repository I/O."""
    return ReviewEvidencePacket(
        scope, history, inventory, python or PythonReviewContext((), {}, ())
    )


def collect_review_packet(
    repository: Path,
    *,
    since_unix_time: int,
    limit: int,
    path: str | None = None,
    paths: tuple[str, ...] | None = None,
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
    revision_source = (
        {
            "status": "unavailable_at_revision",
            "tip_sha": tip_sha,
            "message": "Current-tree Python evidence is omitted for an explicit Git revision.",
        }
        if tip_sha is not None
        else None
    )
    selected_paths = paths or ((path,) if path is not None else None)
    file_scope_inventory = None
    packet = compose_review_packet(
        scope={
            "repository_root": str(repository.resolve()),
            "since_unix_time": since_unix_time,
            "limit": limit,
            **({"path": path} if path is not None else {}),
            **({"paths": list(paths)} if paths is not None else {}),
            **({"tip_sha": tip_sha} if tip_sha is not None else {}),
            **({"source_evidence": "unavailable_at_revision"} if tip_sha is not None else {}),
        },
        history=snapshot.to_dict(),
        inventory=(
            revision_source or file_scope_inventory
            if revision_source is not None or file_scope_inventory is not None
            else collect_representation_inventory(
                repository,
                since_unix_time=since_unix_time,
                limit=limit,
                paths=selected_paths,
            ).to_dict()
        ),
        python=(
            PythonReviewContext((), revision_source or {}, ())
            if revision_source is not None
            else collect_python_review_context(repository, limit=limit, path=path, paths=paths)
        ),
    )
    if selected_paths is None:
        return packet
    history = dict(packet.history)
    history["files"] = [item for item in history["files"] if item["path"] in selected_paths]
    return ReviewEvidencePacket(packet.scope, history, packet.inventory, packet.python)
