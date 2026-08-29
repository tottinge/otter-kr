from otter_kr.git_hunk_family import expand_family
from otter_kr.git_hunks import extract_hunks


def test_expands_matching_prior_hunks_and_honors_limit() -> None:
    topic = extract_hunks(b"+++ b/a.py\n@@ -1 +1 @@\n-old\n+new\n")
    prior = extract_hunks(b"+++ b/a.py\n@@ -2 +2 @@\n-old\n+new\n")
    report = expand_family(topic, (("p1", prior), ("p2", prior)), limit=1)

    assert len(report.members) == 1
    assert report.members[0].commit_sha == "p1"
    assert report.termination == "limit"
