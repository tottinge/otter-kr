"""Deterministic cache identity and comparison evidence for topic reports."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
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


@dataclass(frozen=True, slots=True)
class TopicHistoryCacheResult:
    status: str
    key: TopicHistoryCacheKey
    report: Mapping[str, object] | None = None
    invalidation: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "cache_status": self.status,
            "cache_key": self.key.to_dict(),
            "report": dict(self.report) if self.report is not None else None,
            "invalidation": self.invalidation,
        }


class TopicHistoryCache:
    """Caller-owned cache; the MCP does not create or retain one implicitly."""

    def __init__(self) -> None:
        self._entries: dict[
            tuple[str, str, int, int], tuple[TopicHistoryCacheKey, Mapping[str, object]]
        ] = {}

    def store(self, key: TopicHistoryCacheKey, report: Mapping[str, object]) -> None:
        self._entries[_cache_identity(key)] = (key, dict(report))

    def lookup(self, key: TopicHistoryCacheKey) -> TopicHistoryCacheResult:
        cached = self._entries.get(_cache_identity(key))
        if cached is None:
            return TopicHistoryCacheResult("miss", key)
        cached_key, report = cached
        comparison = compare_topic_cache_keys(key, cached_key)
        if comparison["cache_status"] == "hit":
            return TopicHistoryCacheResult("hit", key, report)
        return TopicHistoryCacheResult("invalidated", key, invalidation=comparison)


def _cache_identity(key: TopicHistoryCacheKey) -> tuple[str, str, int, int]:
    return key.topic_sha, key.matching_policy, key.since_unix_time, key.limit
