"""Shared provenance for bounded Git-history evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class SourceFileFilterPolicy:
    tracked_by: str = "git"
    language: str = "python"
    pathspec: str = "*.py"
    tip_revision: str = "HEAD"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BoundedHistoryProvenance:
    report_version: str
    repository_root: str
    tip_revision: str
    since_unix_time: int
    limit: int
    commit_count: int
    truncated: bool
    source_file_filter: SourceFileFilterPolicy

    def to_dict(self) -> dict[str, object]:
        return asdict(self) | {"source_file_filter": self.source_file_filter.to_dict()}


def python_history_provenance(
    repository_root: str,
    *,
    since_unix_time: int,
    limit: int,
    commit_count: int,
    truncated: bool,
) -> BoundedHistoryProvenance:
    return BoundedHistoryProvenance(
        report_version="1",
        repository_root=repository_root,
        tip_revision="HEAD",
        since_unix_time=since_unix_time,
        limit=limit,
        commit_count=commit_count,
        truncated=truncated,
        source_file_filter=SourceFileFilterPolicy(),
    )
