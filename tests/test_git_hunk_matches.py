from otter_kr.git_hunk_matches import match_hunk_candidates, match_hunks
from otter_kr.git_hunks import extract_hunks


def test_matches_identical_hunks_at_different_line_numbers() -> None:
    topic = extract_hunks(b"+++ b/a.py\n@@ -1 +4 @@\n-old\n+new\n")
    prior = extract_hunks(b"+++ b/a.py\n@@ -20 +40 @@\n-old\n+new\n")
    matches = match_hunks(topic, prior)
    assert len(matches) == 1
    assert matches[0].method == "exact_normalized_body"


def test_preserves_context_overlap_as_a_separate_match_method() -> None:
    topic = extract_hunks(b"+++ b/a.py\n@@ -1 +4 @@\n-old\n+new\n context\n")
    prior = extract_hunks(b"+++ b/a.py\n@@ -20 +40 @@\n-old\n+changed\n context\n")
    matches = match_hunks(topic, prior)
    assert matches[0].method == "context_overlap"
    assert matches[0].overlap_count == 1


def test_match_carries_ranges_context_and_commit_distance() -> None:
    topic = extract_hunks(b"+++ b/a.py\n@@ -1 +4 @@\n-old\n+new\n context\n")
    prior = extract_hunks(b"+++ b/a.py\n@@ -20 +40 @@\n-old\n+changed\n context\n")

    match = match_hunks(
        topic,
        prior,
        topic_commit_sha="topic",
        prior_commit_sha="prior",
        prior_distance=3,
    )[0]

    assert match.topic_hunk_id.startswith("a.py:4:")
    assert match.topic_range == (1, 1, 4, 1)
    assert match.prior_range == (20, 1, 40, 1)
    assert match.shared_context == ("context",)
    assert match.prior_commit_sha == "prior"
    assert match.prior_distance == 3


def test_match_candidates_preserves_an_explicit_no_match() -> None:
    topic = extract_hunks(b"+++ b/a.py\n@@ -1 +1 @@\n-old\n+new\n")

    candidate = match_hunk_candidates(topic, (), topic_commit_sha="topic")[0]

    assert candidate.status == "unmatched"
    assert candidate.method == "no_match"
    assert candidate.prior_fingerprint == ""


def test_preserves_range_overlap_as_a_distinct_match_method() -> None:
    topic = extract_hunks(b"+++ b/a.py\n@@ -10,3 +10,3 @@\n-a\n+b\n context\n")
    prior = extract_hunks(b"+++ b/a.py\n@@ -11,3 +11,3 @@\n-x\n+y\n context\n")

    match = match_hunks(topic, prior)[0]

    assert match.method == "range_overlap"
    assert match.overlap_count == 2
