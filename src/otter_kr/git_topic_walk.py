"""Bounded first-parent evidence walk from a topic commit."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from otter_kr.git_cli_history import GitCliHistory
from otter_kr.git_hunks import collect_topic_hunks
from otter_kr.git_ports import (
    CommitChangeSource,
    CommitHistoryQuery,
    CommitMetadataSource,
    CommitPatchSource,
)


@dataclass(frozen=True, slots=True)
class TopicWalkReport:
    topic_sha: str
    commits: tuple[dict[str, object], ...]
    termination: str

    def to_dict(self) -> dict[str, object]:
        return {
            "topic_sha": self.topic_sha,
            "commits": list(self.commits),
            "termination": self.termination,
        }


def walk_topic_history(
    repository: Path,
    topic_sha: str,
    *,
    since_unix_time: int,
    limit: int,
    history: CommitMetadataSource | None = None,
    changes: CommitChangeSource | None = None,
    patches: CommitPatchSource | None = None,
) -> TopicWalkReport:
    if since_unix_time <= 0 or limit <= 0:
        raise ValueError("since_unix_time and limit must be positive.")
    source = history or GitCliHistory()
    metadata = source.commit_metadata(
        repository,
        CommitHistoryQuery(limit=limit + 1, since_unix_time=since_unix_time, tip_sha=topic_sha),
    )
    by_sha = {commit.sha: commit for commit in metadata}
    change_source = changes or GitCliHistory()
    patch_source = patches or GitCliHistory()
    commits: list[dict[str, object]] = []
    current = by_sha.get(topic_sha)
    termination = "missing_topic"
    while current is not None and len(commits) < limit:
        if len(current.parent_shas) > 1:
            evidence = _commit_evidence(
                repository,
                current.sha,
                history=source,
                changes=change_source,
                patches=patch_source,
            )
            commits.append(
                {
                    "sha": current.sha,
                    "parent_shas": list(current.parent_shas),
                    "skipped": "merge",
                    **evidence,
                }
            )
            termination = "merge_encountered"
            break
        commits.append(
            {
                "sha": current.sha,
                "parent_shas": list(current.parent_shas),
                "skipped": None,
                **_commit_evidence(
                    repository,
                    current.sha,
                    history=source,
                    changes=change_source,
                    patches=patch_source,
                ),
            }
        )
        if not current.parent_shas:
            termination = "root"
            break
        current = by_sha.get(current.parent_shas[0])
        termination = "parent_unavailable"
    if len(commits) >= limit and termination == "parent_unavailable":
        termination = "limit"
    return TopicWalkReport(topic_sha, tuple(commits), termination)


def _commit_evidence(
    repository: Path,
    commit_sha: str,
    *,
    history: CommitMetadataSource,
    changes: CommitChangeSource,
    patches: CommitPatchSource,
) -> dict[str, object]:
    path_changes = changes.commit_changes(repository, commit_sha)
    hunk_report = collect_topic_hunks(
        repository,
        commit_sha,
        metadata=history,
        patches=patches,
    )
    return {
        "changes": [
            {
                "status": change.status,
                "path": change.path,
                "previous_path": change.previous_path,
            }
            for change in path_changes
        ],
        "hunks": [hunk.to_dict() for hunk in hunk_report.hunks],
        "hunk_status": hunk_report.status,
    }
