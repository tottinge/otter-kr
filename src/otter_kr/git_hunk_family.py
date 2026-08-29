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
class FamilyReport:
    members: tuple[FamilyMember, ...]
    matches: tuple[HunkMatch, ...]
    termination: str

    def to_dict(self) -> dict[str, object]:
        return {
            "members": [m.to_dict() for m in self.members],
            "matches": [m.to_dict() for m in self.matches],
            "termination": self.termination,
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
    candidates = []
    for item in walk.commits[1:]:
        commit = item["sha"]
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
    return expand_family(topic, tuple(candidates), limit)
