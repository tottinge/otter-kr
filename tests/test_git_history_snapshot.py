from pathlib import Path

from otter_kr.git_history_snapshot import collect_git_history_snapshot
from otter_kr.git_ports import CommitFileChange


class FakeChanges:
    def __init__(self, records: list[CommitFileChange]) -> None:
        self.records = records

    def commit_file_changes(self, repository: Path, query):
        return self.records


def change(commit_sha: str, path: str) -> CommitFileChange:
    return CommitFileChange(
        commit_sha=commit_sha,
        committed_unix_time=1,
        path=path,
        additions=1,
        deletions=0,
    )


def test_emits_compact_versioned_per_file_snapshot(tmp_path: Path) -> None:
    report = collect_git_history_snapshot(
        tmp_path,
        since_unix_time=1,
        limit=2,
        changes=FakeChanges(
            [
                change("c2", "pkg/b.py"),
                change("c2", "pkg/a.py"),
                change("c1", "pkg/a.py"),
                change("c0", "pkg/a.py"),
            ]
        ),
    )

    assert report.to_dict() == {
        "report_version": "1",
        "repository_root": str(tmp_path.resolve()),
        "tip_revision": "HEAD",
        "since_unix_time": 1,
        "limit": 2,
        "commit_count": 2,
        "truncated": True,
        "source_file_filter": {
            "tracked_by": "git",
            "language": "python",
            "pathspec": "*.py",
            "tip_revision": "HEAD",
        },
        "files": [
            {"path": "pkg/a.py", "commit_count": 2, "recent_commits": ["c2", "c1"]},
            {"path": "pkg/b.py", "commit_count": 1, "recent_commits": ["c2"]},
        ],
    }
