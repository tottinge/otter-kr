from otter_kr.git_hunk_matches import match_hunks
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
