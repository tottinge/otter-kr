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

    def to_dict(self) -> dict[str, str]:
        return {
            "topic_fingerprint": self.topic_fingerprint,
            "prior_fingerprint": self.prior_fingerprint,
            "topic_path": self.topic_path,
            "prior_path": self.prior_path,
            "method": self.method,
        }


def match_hunks(
    topic: tuple[TopicHunk, ...], prior: tuple[TopicHunk, ...]
) -> tuple[HunkMatch, ...]:
    matches: list[HunkMatch] = []
    for topic_hunk in topic:
        for prior_hunk in prior:
            if topic_hunk.fingerprint == prior_hunk.fingerprint:
                matches.append(
                    HunkMatch(
                        topic_hunk.fingerprint,
                        prior_hunk.fingerprint,
                        topic_hunk.path,
                        prior_hunk.path,
                    )
                )
    return tuple(matches)
