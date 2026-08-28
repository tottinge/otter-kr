"""Citeable evidence describing one Git topic commit."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from otter_kr.git_cli_history import GitCliHistory
from otter_kr.git_ports import CommitChangeSource, CommitHistoryQuery, CommitMetadataSource


@dataclass(frozen=True, slots=True)
class TopicCommitReport:
    commit_sha: str
    parent_shas: tuple[str, ...]
    committed_unix_time: int
    subject: str
    changes: tuple[dict[str, object], ...]
    status: str

    def to_dict(self) -> dict[str, object]:
        return {
            "commit_sha": self.commit_sha,
            "parent_shas": list(self.parent_shas),
            "committed_unix_time": self.committed_unix_time,
            "subject": self.subject,
            "changes": list(self.changes),
            "status": self.status,
        }


def describe_topic_commit(
    repository: Path,
    commit_sha: str,
    *,
    metadata: CommitMetadataSource | None = None,
    changes: CommitChangeSource | None = None,
) -> TopicCommitReport:
    history = metadata or GitCliHistory()
    commit = next(
        (
            item
            for item in history.commit_metadata(
                repository, CommitHistoryQuery(1, 1, tip_sha=commit_sha)
            )
        ),
        None,
    )
    if commit is None:
        raise ValueError(f"Commit was not found: {commit_sha}")
    source = changes or GitCliHistory()
    path_changes = source.commit_changes(repository, commit.sha)
    status = (
        "merge"
        if len(commit.parent_shas) > 1
        else "initial"
        if not commit.parent_shas
        else "normal"
    )
    return TopicCommitReport(
        commit.sha,
        commit.parent_shas,
        commit.committed_unix_time,
        commit.subject,
        tuple(
            {
                "status": change.status,
                "path": change.path,
                "previous_path": change.previous_path,
            }
            for change in path_changes
        ),
        status,
    )
