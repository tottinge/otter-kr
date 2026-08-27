from pathlib import Path

import pytest

from otter_kr.git_ports import CommitFileChange, CommitHistoryQuery
from otter_kr.git_scoped_cochange import collect_scoped_cochange


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


def test_projects_global_scores_onto_one_focus_file(tmp_path: Path) -> None:
    report = collect_scoped_cochange(
        tmp_path,
        "pkg/a.py",
        since_unix_time=100,
        limit=3,
        changes=FakeChanges(
            [
                change("c1", "pkg/a.py"),
                change("c1", "pkg/b.py"),
                change("c1", "pkg/c.py"),
                change("c2", "pkg/b.py"),
                change("c2", "pkg/c.py"),
            ]
        ),
    )

    assert report.focus_path == "pkg/a.py"
    assert report.pairs[0].to_dict() == {
        "left_path": "pkg/a.py",
        "right_path": "pkg/b.py",
        "score": pytest.approx(1 / 3),
        "commit_count": 1,
        "contributing_commits": ["c1"],
    }
    assert len(report.pairs) == 2
    assert report.pairs[1].right_path == "pkg/c.py"


def test_rejects_non_relative_focus_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="focus_path must be repository-relative"):
        collect_scoped_cochange(
            tmp_path,
            "/pkg/a.py",
            since_unix_time=1,
            limit=1,
            changes=FakeChanges([]),
        )
