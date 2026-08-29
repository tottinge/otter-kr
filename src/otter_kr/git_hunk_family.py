"""Bounded recursive expansion of matched topic hunk families."""

from __future__ import annotations

from dataclasses import dataclass

from otter_kr.git_cli_history import GitCliHistory
from otter_kr.git_hunk_matches import HunkMatch, match_hunks
from otter_kr.git_hunks import TopicHunk, collect_topic_hunks
from otter_kr.git_ports import CommitHistoryQuery, CommitPatchRequest
from otter_kr.git_topic_walk import walk_topic_history


@dataclass(frozen=True, slots=True)
class FamilyMember:
    commit_sha: str
    depth: int
    hunk_fingerprint: str

    def to_dict(self) -> dict[str, object]:
        return {
            "commit_sha": self.commit_sha,
            "depth": self.depth,
            "hunk_fingerprint": self.hunk_fingerprint,
        }


@dataclass(frozen=True, slots=True)
class PathTransition:
    """Git-reported path identity evidence encountered in family history."""

    commit_sha: str
    depth: int
    status: str
    path: str
    previous_path: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "commit_sha": self.commit_sha,
            "depth": self.depth,
            "status": self.status,
            "path": self.path,
            "previous_path": self.previous_path,
        }


@dataclass(frozen=True, slots=True)
class FamilyReport:
    members: tuple[FamilyMember, ...]
    matches: tuple[HunkMatch, ...]
    termination: str
    path_transitions: tuple[PathTransition, ...] = ()
    topic_sha: str | None = None
    topic_hunks: tuple[TopicHunk, ...] = ()
    unmatched_hunks: tuple[TopicHunk, ...] = ()
    skipped_commits: tuple[dict[str, object], ...] = ()
    budget_limit: int | None = None
    history_commits: tuple[dict[str, object], ...] = ()
    topic_metadata: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "members": [m.to_dict() for m in self.members],
            "matches": [m.to_dict() for m in self.matches],
            "termination": self.termination,
            "path_transitions": [item.to_dict() for item in self.path_transitions],
            "topic_sha": self.topic_sha,
            "topic_hunks": [item.to_dict() for item in self.topic_hunks],
            "unmatched_hunks": [item.to_dict() for item in self.unmatched_hunks],
            "skipped_commits": list(self.skipped_commits),
            "budget_limit": self.budget_limit,
            "history_commits": list(self.history_commits),
            "topic_metadata": self.topic_metadata,
        }


def expand_family(
    topic: tuple[TopicHunk, ...],
    candidates: tuple[tuple[str, tuple[TopicHunk, ...]], ...],
    limit: int,
) -> FamilyReport:
    active = topic
    members: list[FamilyMember] = []
    matches: list[HunkMatch] = []
    seen: set[tuple[str, str]] = set()
    for depth, (commit_sha, hunks) in enumerate(candidates, 1):
        if len(members) >= limit:
            return FamilyReport(tuple(members), tuple(matches), "limit")
        found = match_hunks(active, hunks)
        for match in found:
            key = (commit_sha, match.prior_fingerprint)
            if key in seen:
                continue
            seen.add(key)
            members.append(FamilyMember(commit_sha, depth, match.prior_fingerprint))
            matches.append(match)
            active = tuple(hunk for hunk in hunks if hunk.fingerprint == match.prior_fingerprint)
    return FamilyReport(tuple(members), tuple(matches), "exhausted")


def collect_topic_family(
    repository, topic_sha: str, *, since_unix_time: int, limit: int
) -> FamilyReport:
    source = GitCliHistory()
    topic = collect_topic_hunks(repository, topic_sha).hunks
    walk = walk_topic_history(repository, topic_sha, since_unix_time=since_unix_time, limit=limit)
    metadata = source.commit_metadata(
        repository, CommitHistoryQuery(1, since_unix_time, tip_sha=topic_sha)
    )
    candidates = []
    path_transitions: list[PathTransition] = []
    for depth, item in enumerate(walk.commits[1:], 1):
        commit = item["sha"]
        for change in source.commit_changes(repository, commit):
            path_transitions.append(
                PathTransition(
                    commit,
                    depth,
                    _path_status(change.status, change.previous_path),
                    change.path,
                    change.previous_path,
                )
            )
        metadata = source.commit_metadata(
            repository, CommitHistoryQuery(1, since_unix_time, tip_sha=commit)
        )
        if not metadata or len(metadata[0].parent_shas) != 1:
            continue
        patch = source.commit_patch(
            repository, CommitPatchRequest(commit, metadata[0].parent_shas[0])
        )
        from otter_kr.git_hunks import extract_hunks

        candidates.append((commit, extract_hunks(patch.patch)))
    report = expand_family(topic, tuple(candidates), limit)
    matched_topics = {match.topic_fingerprint for match in report.matches}
    unmatched = tuple(hunk for hunk in topic if hunk.fingerprint not in matched_topics)
    skipped = tuple(item for item in walk.commits if item.get("skipped") is not None)
    return FamilyReport(
        report.members,
        report.matches,
        report.termination,
        tuple(path_transitions),
        topic_sha,
        topic,
        unmatched,
        skipped,
        limit,
        walk.commits,
        _metadata_dict(metadata[0]) if metadata else None,
    )


def _path_status(status: str, previous_path: str | None) -> str:
    if previous_path is not None:
        return {"R": "rename", "C": "copy"}.get(status, "path_transition")
    return {"A": "added", "D": "deleted", "M": "modified"}.get(status, "discontinuity")


def _metadata_dict(metadata) -> dict[str, object]:
    return {
        "sha": metadata.sha,
        "parent_shas": list(metadata.parent_shas),
        "committed_unix_time": metadata.committed_unix_time,
        "author_name": metadata.author_name,
        "author_email": metadata.author_email,
        "subject": metadata.subject,
    }
