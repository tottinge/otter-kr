"""Exact normalized hunk matching evidence."""

from __future__ import annotations

from dataclasses import dataclass

from otter_kr.git_hunks import TopicHunk


@dataclass(frozen=True, slots=True)
class HunkMatch:
    topic_fingerprint: str
    prior_fingerprint: str
    topic_path: str
    prior_path: str
    method: str = "exact_normalized_body"
    overlap_count: int = 0
    topic_hunk_id: str = ""
    prior_hunk_id: str = ""
    topic_range: tuple[int, int, int, int] | None = None
    prior_range: tuple[int, int, int, int] | None = None
    shared_context: tuple[str, ...] = ()
    topic_commit_sha: str | None = None
    prior_commit_sha: str | None = None
    prior_distance: int | None = None
    status: str = "matched"

    def to_dict(self) -> dict[str, object]:
        return {
            "topic_fingerprint": self.topic_fingerprint,
            "prior_fingerprint": self.prior_fingerprint,
            "topic_path": self.topic_path,
            "prior_path": self.prior_path,
            "method": self.method,
            "overlap_count": self.overlap_count,
            "topic_hunk_id": self.topic_hunk_id,
            "prior_hunk_id": self.prior_hunk_id,
            "topic_range": list(self.topic_range) if self.topic_range else None,
            "prior_range": list(self.prior_range) if self.prior_range else None,
            "shared_context": list(self.shared_context),
            "topic_commit_sha": self.topic_commit_sha,
            "prior_commit_sha": self.prior_commit_sha,
            "prior_distance": self.prior_distance,
            "status": self.status,
        }


def match_hunks(
    topic: tuple[TopicHunk, ...],
    prior: tuple[TopicHunk, ...],
    *,
    topic_commit_sha: str | None = None,
    prior_commit_sha: str | None = None,
    prior_distance: int | None = None,
    include_unmatched: bool = False,
) -> tuple[HunkMatch, ...]:
    matches: list[HunkMatch] = []
    for topic_hunk in topic:
        topic_matched = False
        for prior_hunk in prior:
            if topic_hunk.fingerprint == prior_hunk.fingerprint:
                shared_context: tuple[str, ...] = ()
                method = "exact_normalized_body"
                overlap = 0
            else:
                shared_context = tuple(sorted(_shared_context(topic_hunk, prior_hunk)))
                overlap = len(shared_context)
                method = "context_overlap"
                if not overlap:
                    continue
            topic_matched = True
            matches.append(
                _matched_record(
                    topic_hunk,
                    prior_hunk,
                    method=method,
                    overlap=overlap,
                    shared_context=shared_context,
                    topic_commit_sha=topic_commit_sha,
                    prior_commit_sha=prior_commit_sha,
                    prior_distance=prior_distance,
                )
            )
        if include_unmatched and not topic_matched:
            matches.append(
                HunkMatch(
                    topic_hunk.fingerprint,
                    "",
                    topic_hunk.path,
                    "",
                    topic_hunk_id=_hunk_id(topic_hunk),
                    topic_range=_range(topic_hunk),
                    topic_commit_sha=topic_commit_sha,
                    prior_commit_sha=prior_commit_sha,
                    prior_distance=prior_distance,
                    method="no_match",
                    status="unmatched",
                )
            )
    return tuple(matches)


def match_hunk_candidates(
    topic: tuple[TopicHunk, ...],
    prior: tuple[TopicHunk, ...],
    **kwargs: object,
) -> tuple[HunkMatch, ...]:
    """Return matched records plus one explicit unmatched record per topic hunk."""
    return match_hunks(topic, prior, include_unmatched=True, **kwargs)


def _matched_record(
    topic: TopicHunk,
    prior: TopicHunk,
    *,
    method: str,
    overlap: int,
    shared_context: tuple[str, ...],
    topic_commit_sha: str | None,
    prior_commit_sha: str | None,
    prior_distance: int | None,
) -> HunkMatch:
    return HunkMatch(
        topic.fingerprint,
        prior.fingerprint,
        topic.path,
        prior.path,
        method=method,
        overlap_count=overlap,
        topic_hunk_id=_hunk_id(topic),
        prior_hunk_id=_hunk_id(prior),
        topic_range=_range(topic),
        prior_range=_range(prior),
        shared_context=shared_context,
        topic_commit_sha=topic_commit_sha,
        prior_commit_sha=prior_commit_sha,
        prior_distance=prior_distance,
    )


def _hunk_id(hunk: TopicHunk) -> str:
    return f"{hunk.path}:{hunk.new_start}:{hunk.fingerprint[:12]}"


def _range(hunk: TopicHunk) -> tuple[int, int, int, int]:
    return hunk.old_start, hunk.old_count, hunk.new_start, hunk.new_count


def _shared_context(topic: TopicHunk, prior: TopicHunk) -> set[str]:
    topic_context = {line[1:].strip() for line in topic.lines if line.startswith(" ")}
    prior_context = {line[1:].strip() for line in prior.lines if line.startswith(" ")}
    return topic_context & prior_context
