from otter_kr.git_hunk_family import FamilyReport, PathTransition, expand_family
from otter_kr.git_hunks import extract_hunks


def test_expands_matching_prior_hunks_and_honors_limit() -> None:
    topic = extract_hunks(b"+++ b/a.py\n@@ -1 +1 @@\n-old\n+new\n")
    prior = extract_hunks(b"+++ b/a.py\n@@ -2 +2 @@\n-old\n+new\n")
    report = expand_family(topic, (("p1", prior), ("p2", prior)), limit=1)

    assert len(report.members) == 1
    assert report.members[0].commit_sha == "p1"
    assert report.termination == "limit"


def test_path_transition_is_citeable_and_serializable() -> None:
    transition = PathTransition("rename-sha", 2, "rename", "pkg/new.py", "pkg/old.py")

    assert transition.to_dict() == {
        "commit_sha": "rename-sha",
        "depth": 2,
        "status": "rename",
        "path": "pkg/new.py",
        "previous_path": "pkg/old.py",
    }


def test_family_report_serializes_unmatched_hunks_and_budget() -> None:
    topic = extract_hunks(b"+++ b/a.py\n@@ -1 +1 @@\n-old\n+new\n")
    report = expand_family(topic, (), limit=3)

    report = FamilyReport(
        report.members,
        report.matches,
        report.termination,
        topic_hunks=topic,
        unmatched_hunks=topic,
        budget_limit=3,
    )

    data = report.to_dict()
    assert data["topic_hunks"][0]["path"] == "a.py"
    assert data["unmatched_hunks"][0]["fingerprint"] == topic[0].fingerprint
    assert data["budget_limit"] == 3
