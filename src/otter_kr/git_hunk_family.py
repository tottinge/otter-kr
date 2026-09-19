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
class FamilyAncestryEdge:
    parent_commit_sha: str
    child_commit_sha: str
    parent_hunk_id: str
    child_hunk_id: str
    depth: int
    method: str

    def to_dict(self) -> dict[str, object]:
        return {
            "parent_commit_sha": self.parent_commit_sha,
            "child_commit_sha": self.child_commit_sha,
            "parent_hunk_id": self.parent_hunk_id,
            "child_hunk_id": self.child_hunk_id,
            "depth": self.depth,
            "method": self.method,
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
    ancestry_edges: tuple[FamilyAncestryEdge, ...] = ()
    report_version: str = "1"

    @classmethod
    def with_history_evidence(
        cls,
        report: FamilyReport,
        *,
        topic_sha: str,
        topic_hunks: tuple[TopicHunk, ...],
        unmatched_hunks: tuple[TopicHunk, ...],
        skipped_commits: tuple[dict[str, object], ...],
        budget_limit: int,
        history_commits: tuple[dict[str, object], ...],
        topic_metadata: dict[str, object] | None,
        path_transitions: tuple[PathTransition, ...],
    ) -> FamilyReport:
        return cls(
            report.members,
            report.matches,
            report.termination,
            path_transitions,
            topic_sha,
            topic_hunks,
            unmatched_hunks,
            skipped_commits,
            budget_limit,
            history_commits,
            topic_metadata,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "report_version": self.report_version,
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
            "ancestry_edges": [edge.to_dict() for edge in self.ancestry_edges],
            "counts": {
                "members": len(self.members),
                "matches": len(self.matches),
                "unmatched_hunks": len(self.unmatched_hunks),
                "skipped_commits": len(self.skipped_commits),
                "path_transitions": len(self.path_transitions),
                "ancestry_edges": len(self.ancestry_edges),
            },
        }


def expand_family(
    topic: tuple[TopicHunk, ...],
    candidates: tuple[tuple[str, tuple[TopicHunk, ...]], ...],
    limit: int,
    topic_sha: str = "topic",
) -> FamilyReport:
    active_sources = {_hunk_id(hunk): topic_sha for hunk in topic}
    active = topic
    members: list[FamilyMember] = []
    matches: list[HunkMatch] = []
    ancestry_edges: list[FamilyAncestryEdge] = []
    seen: set[tuple[str, str]] = set()
    for depth, (commit_sha, hunks) in enumerate(candidates, 1):
        if len(members) >= limit:
            return FamilyReport(
                tuple(members), tuple(matches), "limit", ancestry_edges=tuple(ancestry_edges)
            )
        found = match_hunks(
            active,
            hunks,
            prior_commit_sha=commit_sha,
            prior_distance=depth,
        )
        next_active: dict[str, TopicHunk] = {}
        for match in found:
            key = (commit_sha, match.prior_fingerprint)
            if key in seen:
                continue
            seen.add(key)
            members.append(FamilyMember(commit_sha, depth, match.prior_fingerprint))
            matches.append(match)
            parent_hunk_id = _hunk_id_for_fingerprint(active, match.topic_fingerprint)
            ancestry_edges.append(
                FamilyAncestryEdge(
                    active_sources.get(match.topic_hunk_id, topic_sha),
                    commit_sha,
                    parent_hunk_id,
                    match.prior_hunk_id,
                    depth,
                    match.method,
                )
            )
            next_active[match.prior_fingerprint] = next(
                hunk for hunk in hunks if hunk.fingerprint == match.prior_fingerprint
            )
        if next_active:
            active = tuple(next_active.values())
            active_sources = {_hunk_id(hunk): commit_sha for hunk in next_active.values()}
    return FamilyReport(
        tuple(members), tuple(matches), "exhausted", ancestry_edges=tuple(ancestry_edges)
    )


def _hunk_id(hunk: TopicHunk) -> str:
    return f"{hunk.path}:{hunk.new_start}:{hunk.fingerprint[:12]}"


def _hunk_id_for_fingerprint(hunks: tuple[TopicHunk, ...], fingerprint: str) -> str:
    return next((_hunk_id(hunk) for hunk in hunks if hunk.fingerprint == fingerprint), fingerprint)


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
    report = expand_family(topic, tuple(candidates), limit, topic_sha=topic_sha)
    member_commits = {member.commit_sha for member in report.members}
    path_transitions = _family_path_transitions(path_transitions, member_commits)
    matched_topics = {match.topic_fingerprint for match in report.matches}
    unmatched = tuple(hunk for hunk in topic if hunk.fingerprint not in matched_topics)
    skipped = tuple(item for item in walk.commits if item.get("skipped") is not None)
    return FamilyReport.with_history_evidence(
        report,
        topic_sha=topic_sha,
        topic_hunks=topic,
        unmatched_hunks=unmatched,
        skipped_commits=skipped,
        budget_limit=limit,
        history_commits=walk.commits,
        topic_metadata=_metadata_dict(metadata[0]) if metadata else None,
        path_transitions=tuple(path_transitions),
    )


def _path_status(status: str, previous_path: str | None) -> str:
    if previous_path is not None:
        return {"R": "rename", "C": "copy"}.get(status, "path_transition")
    return {"A": "added", "D": "deleted", "M": "modified"}.get(status, "discontinuity")


def _family_path_transitions(
    transitions: list[PathTransition], member_commits: set[str]
) -> list[PathTransition]:
    return [transition for transition in transitions if transition.commit_sha in member_commits]


def _metadata_dict(metadata) -> dict[str, object]:
    return {
        "sha": metadata.sha,
        "parent_shas": list(metadata.parent_shas),
        "committed_unix_time": metadata.committed_unix_time,
        "author_name": metadata.author_name,
        "author_email": metadata.author_email,
        "subject": metadata.subject,
    }
