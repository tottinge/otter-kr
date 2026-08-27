"""Capability-shaped ports for bounded Git history evidence."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class CommitHistoryQuery:
    """Describe a bounded backward commit walk."""

    limit: int
    since_unix_time: int
    tip_sha: str | None = None
    paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class CommitMetadata:
    """Evidence describing one commit without exposing Git-library objects."""

    sha: str
    parent_shas: tuple[str, ...]
    committed_unix_time: int
    author_name: str
    author_email: str
    subject: str


@dataclass(frozen=True)
class CommitFileChange:
    """Evidence for one file's line changes in one commit."""

    commit_sha: str
    committed_unix_time: int
    path: str
    additions: int
    deletions: int


class CommitFileChangeSource(Protocol):
    """Read bounded per-file change statistics for one repository."""

    def commit_file_changes(
        self, repository: Path, query: CommitHistoryQuery
    ) -> list[CommitFileChange]:
        """Return per-file changes in deterministic commit order."""


@dataclass(frozen=True)
class CommitPatchRequest:
    """Describe one explicit parent-based patch request."""

    commit_sha: str
    parent_sha: str
    paths: tuple[str, ...] = ()
    max_bytes: int = 1_000_000


@dataclass(frozen=True)
class RawCommitPatch:
    """Raw patch bytes for one commit-parent pair."""

    commit_sha: str
    parent_sha: str
    patch: bytes


class CommitMetadataSource(Protocol):
    """Read bounded commit metadata for one repository."""

    def commit_metadata(self, repository: Path, query: CommitHistoryQuery) -> list[CommitMetadata]:
        """Return commit metadata in deterministic order."""


class CommitPatchSource(Protocol):
    """Read one explicit parent-based patch for one repository."""

    def commit_patch(self, repository: Path, request: CommitPatchRequest) -> RawCommitPatch:
        """Return raw patch bytes for the selected parent/commit pair."""
