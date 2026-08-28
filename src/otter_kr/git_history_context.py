"""Bounded Git-history context evidence for one repository."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from otter_kr.git_ports import CommitHistoryQuery, CommitMetadata, CommitMetadataSource
from otter_kr.git_provenance import (
    BoundedHistoryProvenance,
    python_history_provenance,
)

_REPORT_VERSION = "1"
_TIP_REVISION = "HEAD"
_PYTHON_PATHSPEC = "*.py"


@dataclass(frozen=True, slots=True)
class GitHistoryCommitEvidence:
    sha: str
    parent_shas: tuple[str, ...]
    committed_unix_time: int
    subject: str

    def to_dict(self) -> dict[str, object]:
        return {
            "sha": self.sha,
            "parent_shas": list(self.parent_shas),
            "committed_unix_time": self.committed_unix_time,
            "subject": self.subject,
        }


@dataclass(frozen=True, slots=True)
class GitHistoryContextReport:
    provenance: BoundedHistoryProvenance
    commits: tuple[GitHistoryCommitEvidence, ...]

    @property
    def commit_count(self) -> int:
        return self.provenance.commit_count

    @property
    def truncated(self) -> bool:
        return self.provenance.truncated

    def to_dict(self) -> dict[str, object]:
        return self.provenance.to_dict() | {
            "commits": [commit.to_dict() for commit in self.commits]
        }


def collect_git_history(
    repository: Path,
    *,
    since_unix_time: int,
    limit: int,
    history: CommitMetadataSource,
) -> GitHistoryContextReport:
    """Collect one bounded, citeable Git-history window for tracked Python files."""
    resolved_repository = repository.resolve()
    if not resolved_repository.is_dir():
        raise ValueError(f"Repository is not a directory: {resolved_repository}")
    if since_unix_time <= 0:
        raise ValueError("since_unix_time must be positive.")
    if limit <= 0:
        raise ValueError("limit must be positive.")

    metadata = history.commit_metadata(
        resolved_repository,
        CommitHistoryQuery(
            limit=limit,
            since_unix_time=since_unix_time,
            tip_sha=None,
            paths=(_PYTHON_PATHSPEC,),
        ),
    )
    truncated = len(metadata) > limit
    visible_commits = tuple(_commit_evidence(commit) for commit in metadata[:limit])
    return GitHistoryContextReport(
        provenance=python_history_provenance(
            str(resolved_repository),
            since_unix_time=since_unix_time,
            limit=limit,
            commit_count=len(visible_commits),
            truncated=truncated,
        ),
        commits=visible_commits,
    )


def _commit_evidence(commit: CommitMetadata) -> GitHistoryCommitEvidence:
    return GitHistoryCommitEvidence(
        sha=commit.sha,
        parent_shas=commit.parent_shas,
        committed_unix_time=commit.committed_unix_time,
        subject=commit.subject,
    )
