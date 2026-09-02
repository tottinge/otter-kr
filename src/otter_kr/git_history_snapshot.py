"""Bounded, citeable per-file Git-history snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from otter_kr.git_hotspots import collect_git_hotspots
from otter_kr.git_ports import CommitFileChangeSource
from otter_kr.git_provenance import BoundedHistoryProvenance


@dataclass(frozen=True, slots=True)
class SnapshotFile:
    path: str
    commit_count: int
    recent_commits: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "commit_count": self.commit_count,
            "recent_commits": list(self.recent_commits),
        }


@dataclass(frozen=True, slots=True)
class GitHistorySnapshotReport:
    provenance: BoundedHistoryProvenance
    files: tuple[SnapshotFile, ...]

    def to_dict(self) -> dict[str, object]:
        return self.provenance.to_dict() | {"files": [file.to_dict() for file in self.files]}


def collect_git_history_snapshot(
    repository: Path,
    *,
    since_unix_time: int,
    limit: int,
    changes: CommitFileChangeSource,
) -> GitHistorySnapshotReport:
    """Project one bounded Git window into compact per-file evidence."""
    hotspots = collect_git_hotspots(
        repository,
        since_unix_time=since_unix_time,
        limit=limit,
        changes=changes,
    )
    return GitHistorySnapshotReport(
        provenance=hotspots.provenance,
        files=tuple(
            sorted(
                (
                    SnapshotFile(
                        path=file.path,
                        commit_count=file.commit_count,
                        recent_commits=file.recent_commits,
                    )
                    for file in hotspots.files
                ),
                key=lambda file: file.path,
            )
        ),
    )
