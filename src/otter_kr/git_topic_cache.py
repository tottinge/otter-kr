"""Deterministic cache identity and comparison evidence for topic reports."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TopicHistoryCacheKey:
    repository_revision: str
    topic_sha: str
    matching_policy: str
    since_unix_time: int
    limit: int

    def digest(self) -> str:
        payload = json.dumps(
            {
                "repository_revision": self.repository_revision,
                "topic_sha": self.topic_sha,
                "matching_policy": self.matching_policy,
                "since_unix_time": self.since_unix_time,
                "limit": self.limit,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "repository_revision": self.repository_revision,
            "topic_sha": self.topic_sha,
            "matching_policy": self.matching_policy,
            "since_unix_time": self.since_unix_time,
            "limit": self.limit,
            "digest": self.digest(),
        }


def compare_topic_cache_keys(
    requested: TopicHistoryCacheKey, cached: TopicHistoryCacheKey
) -> dict[str, object]:
    """Report whether cached evidence is reusable, without judging its contents."""
    differences = {
        field: (getattr(cached, field), getattr(requested, field))
        for field in (
            "repository_revision",
            "topic_sha",
            "matching_policy",
            "since_unix_time",
            "limit",
        )
        if getattr(cached, field) != getattr(requested, field)
    }
    return {
        "cache_status": "hit" if not differences else "miss",
        "requested": requested.to_dict(),
        "cached": cached.to_dict(),
        "differences": differences,
    }
