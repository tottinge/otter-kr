from pathlib import Path

import pytest

from otter_kr.git_pair_cochange import collect_pair_cochange
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
    return CommitFileChange(sha, 1, path, 1, 0)


def test_reports_one_explicit_pair_with_global_score_and_context(tmp_path: Path) -> None:
    report = collect_pair_cochange(
        tmp_path,
        "pkg/b.py",
        "pkg/a.py",
        since_unix_time=100,
        limit=2,
        changes=FakeChanges(
            [
                change("c1", "pkg/a.py"),
                change("c1", "pkg/b.py"),
                change("c1", "pkg/c.py"),
            ]
        ),
    )

    assert report.pair is not None
    assert report.pair.score == pytest.approx(1 / 3)
    assert report.pair.commit_count == 1
    assert report.pair.contributing_commits == ("c1",)
    assert report.to_dict()["left_path"] == "pkg/b.py"
    assert report.to_dict()["right_path"] == "pkg/a.py"


def test_reports_absent_pair_without_inference(tmp_path: Path) -> None:
    report = collect_pair_cochange(
        tmp_path,
        "pkg/a.py",
        "pkg/b.py",
        since_unix_time=1,
        limit=1,
        changes=FakeChanges([change("c1", "pkg/a.py")]),
    )

    assert report.pair is None


def test_rejects_same_or_non_relative_paths(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="different files"):
        collect_pair_cochange(
            tmp_path,
            "pkg/a.py",
            "pkg/a.py",
            since_unix_time=1,
            limit=1,
            changes=FakeChanges([]),
        )
    with pytest.raises(ValueError, match="repository-relative"):
        collect_pair_cochange(
            tmp_path,
            "../a.py",
            "pkg/b.py",
            since_unix_time=1,
            limit=1,
            changes=FakeChanges([]),
        )
