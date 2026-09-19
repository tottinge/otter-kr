"""Bounded commit-author observations without ownership judgments."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from otter_kr.git_ports import CommitHistoryQuery, CommitMetadataSource
from otter_kr.git_provenance import BoundedHistoryProvenance, python_history_provenance


@dataclass(frozen=True, slots=True)
class AuthorObservation:
    author_name: str
    author_email: str
    commit_count: int
    commit_shas: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "author_name": self.author_name,
            "author_email": self.author_email,
            "commit_count": self.commit_count,
            "commit_shas": list(self.commit_shas),
        }


@dataclass(frozen=True, slots=True)
class GitOwnershipReport:
    provenance: BoundedHistoryProvenance
    authors: tuple[AuthorObservation, ...]

    def to_dict(self) -> dict[str, object]:
        return self.provenance.to_dict() | {
            "author_count": len(self.authors),
            "authors": [author.to_dict() for author in self.authors],
        }


def collect_git_ownership(
    repository: Path,
    *,
    since_unix_time: int,
    limit: int,
    history: CommitMetadataSource,
) -> GitOwnershipReport:
    """Report bounded commit authorship observations, not semantic ownership."""
    resolved = repository.resolve()
    if not resolved.is_dir():
        raise ValueError(f"Repository is not a directory: {resolved}")
    if since_unix_time <= 0:
        raise ValueError("since_unix_time must be positive.")
    if limit <= 0:
        raise ValueError("limit must be positive.")

    commits = history.commit_metadata(
        resolved,
        CommitHistoryQuery(limit=limit, since_unix_time=since_unix_time),
    )
    grouped: dict[tuple[str, str], list[str]] = {}
    for commit in commits[:limit]:
        grouped.setdefault((commit.author_name, commit.author_email), []).append(commit.sha)
    authors = tuple(
        AuthorObservation(name, email, len(shas), tuple(shas))
        for (name, email), shas in sorted(grouped.items())
    )
    return GitOwnershipReport(
        provenance=python_history_provenance(
            str(resolved),
            since_unix_time=since_unix_time,
            limit=limit,
            commit_count=len(commits[:limit]),
            truncated=len(commits) > limit,
        ),
        authors=authors,
    )
