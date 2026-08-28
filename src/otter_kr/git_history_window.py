"""Shared bounded file-change acquisition for Git-derived reports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from otter_kr.git_identity import canonicalize_file_changes
from otter_kr.git_ports import CommitFileChange, CommitFileChangeSource, CommitHistoryQuery


@dataclass(frozen=True, slots=True)
class BoundedFileChangeWindow:
    repository: Path
    records: tuple[CommitFileChange, ...]
    commit_order: tuple[str, ...]
    visible_commits: tuple[str, ...]

    @property
    def visible_records(self) -> tuple[CommitFileChange, ...]:
        visible = set(self.visible_commits)
        return tuple(record for record in self.records if record.commit_sha in visible)


def collect_bounded_file_changes(
    repository: Path,
    *,
    since_unix_time: int,
    limit: int,
    changes: CommitFileChangeSource,
) -> BoundedFileChangeWindow:
    resolved_repository = repository.resolve()
    if not resolved_repository.is_dir():
        raise ValueError(f"Repository is not a directory: {resolved_repository}")
    if since_unix_time <= 0:
        raise ValueError("since_unix_time must be positive.")
    if limit <= 0:
        raise ValueError("limit must be positive.")
    records = tuple(
        canonicalize_file_changes(
            changes.commit_file_changes(
                resolved_repository,
                CommitHistoryQuery(
                    limit=limit,
                    since_unix_time=since_unix_time,
                    paths=("*.py",),
                ),
            )
        )
    )
    commit_order = tuple(dict.fromkeys(record.commit_sha for record in records))
    return BoundedFileChangeWindow(
        repository=resolved_repository,
        records=records,
        commit_order=commit_order,
        visible_commits=commit_order[:limit],
    )
