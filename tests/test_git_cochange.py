from pathlib import Path

import pytest

from otter_kr.git_cochange import collect_global_cochange
from otter_kr.git_ports import CommitFileChange, CommitHistoryQuery


class FakeChanges:
    def __init__(self, records: list[CommitFileChange]) -> None:
        self.records = records
        self.calls: list[tuple[Path, CommitHistoryQuery]] = []

    def commit_file_changes(
        self, repository: Path, query: CommitHistoryQuery
    ) -> list[CommitFileChange]:
        self.calls.append((repository, query))
        return list(self.records)


def change(sha: str, path: str) -> CommitFileChange:
    return CommitFileChange(
        commit_sha=sha,
        committed_unix_time=1,
        path=path,
        additions=1,
        deletions=0,
    )


def test_collects_normalized_pair_scores_and_commit_evidence(tmp_path: Path) -> None:
    source = FakeChanges(
        [
            change("c1", "pkg/a.py"),
            change("c1", "pkg/b.py"),
            change("c2", "pkg/a.py"),
            change("c2", "pkg/b.py"),
            change("c2", "pkg/c.py"),
            change("c3", "pkg/solo.py"),
        ]
    )

    report = collect_global_cochange(tmp_path, since_unix_time=100, limit=3, changes=source)

    assert report.commit_count == 3
    assert report.truncated is False
    assert report.excluded_single_file_commits == 1
    assert report.eligible_commit_count == 2
    assert report.pairs[0].to_dict() == {
        "left_path": "pkg/a.py",
        "right_path": "pkg/b.py",
        "score": pytest.approx(1 + 1 / 3),
        "commit_count": 2,
        "contributing_commits": ["c1", "c2"],
    }
    assert report.to_dict()["source_file_filter"] == {
        "tracked_by": "git",
        "language": "python",
        "pathspec": "*.py",
        "tip_revision": "HEAD",
    }


def test_limits_history_before_calculating_scores(tmp_path: Path) -> None:
    records = [
        change("c3", "pkg/a.py"),
        change("c3", "pkg/b.py"),
        change("c2", "pkg/a.py"),
        change("c1", "pkg/a.py"),
        change("c1", "pkg/b.py"),
    ]

    report = collect_global_cochange(
        tmp_path, since_unix_time=1, limit=2, changes=FakeChanges(records)
    )

    assert report.commit_count == 2
    assert report.truncated is True
    assert report.pairs[0].contributing_commits == ("c3",)
    assert report.pairs[0].score == pytest.approx(1.0)
