"""Citeable evidence describing one Git topic commit."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from otter_kr.git_cli_history import GitCliHistory
from otter_kr.git_hunks import TopicHunk, extract_hunks
from otter_kr.git_ports import (
    CommitChangeSource,
    CommitHistoryQuery,
    CommitMetadataSource,
    CommitPatchRequest,
    CommitPatchSource,
)


@dataclass(frozen=True, slots=True)
class TopicCommitReport:
    commit_sha: str
    parent_shas: tuple[str, ...]
    committed_unix_time: int
    subject: str
    changes: tuple[TopicChangeEvidence, ...]
    status: str

    def to_dict(self) -> dict[str, object]:
        return {
            "commit_sha": self.commit_sha,
            "parent_shas": list(self.parent_shas),
            "committed_unix_time": self.committed_unix_time,
            "subject": self.subject,
            "changes": [change.to_dict() for change in self.changes],
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class TopicChangeEvidence:
    status: str
    path: str
    previous_path: str | None
    hunk_status: str
    hunks: tuple[TopicHunk, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "path": self.path,
            "previous_path": self.previous_path,
            "hunk_status": self.hunk_status,
            "hunks": [hunk.to_dict() for hunk in self.hunks],
        }


def describe_topic_commit(
    repository: Path,
    commit_sha: str,
    *,
    metadata: CommitMetadataSource | None = None,
    changes: CommitChangeSource | None = None,
    patches: CommitPatchSource | None = None,
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
    hunks: tuple[TopicHunk, ...] = ()
    if status == "normal":
        patch_source = patches or GitCliHistory()
        patch = patch_source.commit_patch(
            repository,
            CommitPatchRequest(commit.sha, commit.parent_shas[0]),
        )
        hunks = extract_hunks(patch.patch)
        binary_patch = b"GIT binary patch" in patch.patch or b"Binary files" in patch.patch
    else:
        binary_patch = False

    return TopicCommitReport(
        commit.sha,
        commit.parent_shas,
        commit.committed_unix_time,
        commit.subject,
        tuple(
            TopicChangeEvidence(
                status=change.status,
                path=change.path,
                previous_path=change.previous_path,
                hunk_status=_hunk_status(
                    status,
                    change.status,
                    change.path,
                    change.previous_path,
                    hunks,
                    binary_patch,
                ),
                hunks=tuple(
                    hunk for hunk in hunks if hunk.path in {change.path, change.previous_path}
                ),
            )
            for change in path_changes
        ),
        status,
    )


def _hunk_status(
    commit_status: str,
    change_status: str,
    path: str,
    previous_path: str | None,
    hunks: tuple[TopicHunk, ...],
    binary_patch: bool,
) -> str:
    if commit_status == "initial":
        return "initial"
    if commit_status == "merge":
        return "merge"
    if binary_patch:
        return "binary"
    if change_status.startswith("R") and not any(
        hunk.path in {path, previous_path} for hunk in hunks
    ):
        return "rename_only"
    if any(hunk.path in {path, previous_path} for hunk in hunks):
        return "available"
    return "no_hunks"
