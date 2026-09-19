from otter_kr.git_topic_cache import (
    TopicHistoryCache,
    TopicHistoryCacheKey,
    compare_topic_cache_keys,
)


def test_cache_key_is_deterministic_and_exposes_policy_inputs() -> None:
    key = TopicHistoryCacheKey("repo-rev", "topic-sha", "normalized-v1", 1, 10)

    assert (
        key.digest()
        == TopicHistoryCacheKey("repo-rev", "topic-sha", "normalized-v1", 1, 10).digest()
    )
    assert key.to_dict()["matching_policy"] == "normalized-v1"


def test_cache_comparison_reports_revision_miss_without_inference() -> None:
    requested = TopicHistoryCacheKey("new-rev", "topic", "policy", 1, 5)
    cached = TopicHistoryCacheKey("old-rev", "topic", "policy", 1, 5)

    result = compare_topic_cache_keys(requested, cached)

    assert result["cache_status"] == "miss"
    assert result["differences"] == {"repository_revision": ("old-rev", "new-rev")}


def test_caller_owned_cache_reports_hit_and_preserves_report() -> None:
    key = TopicHistoryCacheKey("repo", "topic", "policy", 1, 5)
    cache = TopicHistoryCache()
    cache.store(key, {"members": [{"commit_sha": "prior"}]})

    result = cache.lookup(key)

    assert result.status == "hit"
    assert result.report == {"members": [{"commit_sha": "prior"}]}


def test_caller_owned_cache_reports_invalidation_without_reusing_stale_report() -> None:
    cached = TopicHistoryCacheKey("old-rev", "topic", "policy", 1, 5)
    requested = TopicHistoryCacheKey("new-rev", "topic", "policy", 1, 5)
    cache = TopicHistoryCache()
    cache.store(cached, {"members": ["stale"]})

    result = cache.lookup(requested)

    assert result.status == "invalidated"
    assert result.report is None
    assert result.invalidation["differences"] == {"repository_revision": ("old-rev", "new-rev")}
