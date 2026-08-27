"""File-level change-frequency and churn evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from otter_kr.git_identity import canonicalize_file_changes
from otter_kr.git_ports import CommitFileChange, CommitFileChangeSource, CommitHistoryQuery

_REPORT_VERSION = "1"
_TIP_REVISION = "HEAD"
_PYTHON_PATHSPEC = "*.py"


@dataclass(frozen=True, slots=True)
class HotspotFile:
    path: str
    commit_count: int
    total_additions: int
    total_deletions: int
    total_changed_lines: int
    average_changed_lines: float
    recent_commits: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self) | {"recent_commits": list(self.recent_commits)}


@dataclass(frozen=True, slots=True)
class GitHotspotReport:
    report_version: str
    repository_root: str
    tip_revision: str
    since_unix_time: int
    limit: int
    commit_count: int
    truncated: bool
    source_file_filter: dict[str, str]
    files: tuple[HotspotFile, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "report_version": self.report_version,
            "repository_root": self.repository_root,
            "tip_revision": self.tip_revision,
            "since_unix_time": self.since_unix_time,
            "limit": self.limit,
            "commit_count": self.commit_count,
            "truncated": self.truncated,
            "source_file_filter": self.source_file_filter,
            "files": [file.to_dict() for file in self.files],
        }


def collect_git_hotspots(
    repository: Path,
    *,
    since_unix_time: int,
    limit: int,
    changes: CommitFileChangeSource,
) -> GitHotspotReport:
    """Aggregate bounded Git numstat evidence by tracked Python file."""
    resolved_repository = repository.resolve()
    if not resolved_repository.is_dir():
        raise ValueError(f"Repository is not a directory: {resolved_repository}")
    if since_unix_time <= 0:
        raise ValueError("since_unix_time must be positive.")
    if limit <= 0:
        raise ValueError("limit must be positive.")

    records = canonicalize_file_changes(
        changes.commit_file_changes(
            resolved_repository,
            CommitHistoryQuery(
                limit=limit, since_unix_time=since_unix_time, paths=(_PYTHON_PATHSPEC,)
            ),
        )
    )
    commit_order = _commit_order(records)
    visible_commits = set(commit_order[:limit])
    visible_records = [record for record in records if record.commit_sha in visible_commits]
    files = _aggregate(visible_records)
    return GitHotspotReport(
        report_version=_REPORT_VERSION,
        repository_root=str(resolved_repository),
        tip_revision=_TIP_REVISION,
        since_unix_time=since_unix_time,
        limit=limit,
        commit_count=len(commit_order[:limit]),
        truncated=len(commit_order) > limit,
        source_file_filter={
            "tracked_by": "git",
            "language": "python",
            "pathspec": _PYTHON_PATHSPEC,
            "tip_revision": _TIP_REVISION,
        },
        files=files,
    )


def _commit_order(records: list[CommitFileChange]) -> list[str]:
    return list(dict.fromkeys(record.commit_sha for record in records))


def _aggregate(records: list[CommitFileChange]) -> tuple[HotspotFile, ...]:
    grouped: dict[str, list[CommitFileChange]] = {}
    for record in records:
        grouped.setdefault(record.path, []).append(record)
    hotspots = []
    for path, file_records in grouped.items():
        additions = sum(record.additions for record in file_records)
        deletions = sum(record.deletions for record in file_records)
        changed_lines = additions + deletions
        commit_count = len({record.commit_sha for record in file_records})
        hotspots.append(
            HotspotFile(
                path=path,
                commit_count=commit_count,
                total_additions=additions,
                total_deletions=deletions,
                total_changed_lines=changed_lines,
                average_changed_lines=changed_lines / commit_count,
                recent_commits=tuple(record.commit_sha for record in file_records),
            )
        )
    return tuple(
        sorted(
            hotspots,
            key=lambda file: (-file.commit_count, -file.total_changed_lines, file.path),
        )
    )
