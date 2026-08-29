"""Bounded first-parent evidence walk from a topic commit."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from otter_kr.git_cli_history import GitCliHistory
from otter_kr.git_ports import CommitHistoryQuery, CommitMetadataSource


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
) -> TopicWalkReport:
    if since_unix_time <= 0 or limit <= 0:
        raise ValueError("since_unix_time and limit must be positive.")
    source = history or GitCliHistory()
    metadata = source.commit_metadata(
        repository,
        CommitHistoryQuery(limit=limit + 1, since_unix_time=since_unix_time, tip_sha=topic_sha),
    )
    by_sha = {commit.sha: commit for commit in metadata}
    commits: list[dict[str, object]] = []
    current = by_sha.get(topic_sha)
    termination = "missing_topic"
    while current is not None and len(commits) < limit:
        if len(current.parent_shas) > 1:
            commits.append(
                {"sha": current.sha, "parent_shas": list(current.parent_shas), "skipped": "merge"}
            )
            termination = "merge_encountered"
            break
        commits.append(
            {"sha": current.sha, "parent_shas": list(current.parent_shas), "skipped": None}
        )
        if not current.parent_shas:
            termination = "root"
            break
        current = by_sha.get(current.parent_shas[0])
        termination = "parent_unavailable"
    if len(commits) >= limit and termination == "parent_unavailable":
        termination = "limit"
    return TopicWalkReport(topic_sha, tuple(commits), termination)
