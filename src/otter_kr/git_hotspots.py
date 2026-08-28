"""File-level change-frequency and churn evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from otter_kr.git_history_window import collect_bounded_file_changes
from otter_kr.git_ports import CommitFileChange, CommitFileChangeSource
from otter_kr.git_provenance import BoundedHistoryProvenance, python_history_provenance

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
    provenance: BoundedHistoryProvenance
    files: tuple[HotspotFile, ...]

    @property
    def commit_count(self) -> int:
        return self.provenance.commit_count

    @property
    def truncated(self) -> bool:
        return self.provenance.truncated

    def to_dict(self) -> dict[str, object]:
        return self.provenance.to_dict() | {"files": [file.to_dict() for file in self.files]}


def collect_git_hotspots(
    repository: Path,
    *,
    since_unix_time: int,
    limit: int,
    changes: CommitFileChangeSource,
) -> GitHotspotReport:
    """Aggregate bounded Git numstat evidence by tracked Python file."""
    window = collect_bounded_file_changes(
        repository, since_unix_time=since_unix_time, limit=limit, changes=changes
    )
    files = _aggregate(window.visible_records)
    return GitHotspotReport(
        provenance=python_history_provenance(
            str(window.repository),
            since_unix_time=since_unix_time,
            limit=limit,
            commit_count=len(window.visible_commits),
            truncated=len(window.commit_order) > limit,
        ),
        files=files,
    )


def _aggregate(records: tuple[CommitFileChange, ...]) -> tuple[HotspotFile, ...]:
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
