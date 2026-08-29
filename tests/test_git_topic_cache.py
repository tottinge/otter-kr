from otter_kr.git_topic_cache import TopicHistoryCacheKey, compare_topic_cache_keys


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
