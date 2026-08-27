from pathlib import Path

from otter_kr.git_hotspots import collect_git_hotspots
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


def change(sha: str, path: str, additions: int, deletions: int) -> CommitFileChange:
    return CommitFileChange(
        commit_sha=sha,
        committed_unix_time=1,
        path=path,
        additions=additions,
        deletions=deletions,
    )


def test_collects_ranked_file_frequency_and_churn_from_port(tmp_path: Path) -> None:
    source = FakeChanges(
        [
            change("c3", "pkg/alpha.py", 2, 1),
            change("c2", "pkg/beta.py", 10, 0),
            change("c2", "pkg/alpha.py", 1, 1),
            change("c1", "pkg/alpha.py", 3, 2),
        ]
    )

    report = collect_git_hotspots(tmp_path, since_unix_time=100, limit=3, changes=source)

    assert source.calls == [
        (
            tmp_path.resolve(),
            CommitHistoryQuery(limit=3, since_unix_time=100, paths=("*.py",)),
        )
    ]
    assert report.to_dict() == {
        "report_version": "1",
        "repository_root": str(tmp_path.resolve()),
        "tip_revision": "HEAD",
        "since_unix_time": 100,
        "limit": 3,
        "commit_count": 3,
        "truncated": False,
        "source_file_filter": {
            "tracked_by": "git",
            "language": "python",
            "pathspec": "*.py",
            "tip_revision": "HEAD",
        },
        "files": [
            {
                "path": "pkg/alpha.py",
                "commit_count": 3,
                "total_additions": 6,
                "total_deletions": 4,
                "total_changed_lines": 10,
                "average_changed_lines": 10 / 3,
                "recent_commits": ["c3", "c2", "c1"],
            },
            {
                "path": "pkg/beta.py",
                "commit_count": 1,
                "total_additions": 10,
                "total_deletions": 0,
                "total_changed_lines": 10,
                "average_changed_lines": 10.0,
                "recent_commits": ["c2"],
            },
        ],
    }


def test_limits_visible_commits_and_reports_truncation(tmp_path: Path) -> None:
    records = [
        change("c3", "three.py", 1, 0),
        change("c2", "two.py", 2, 0),
        change("c1", "one.py", 3, 0),
    ]

    report = collect_git_hotspots(
        tmp_path, since_unix_time=1, limit=2, changes=FakeChanges(records)
    )

    assert report.commit_count == 2
    assert report.truncated is True
    assert [item.path for item in report.files] == ["two.py", "three.py"]
