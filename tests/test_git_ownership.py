from pathlib import Path

from otter_kr.git_ownership import collect_git_ownership
from otter_kr.git_ports import CommitMetadata


class FakeHistory:
    def __init__(self, commits: list[CommitMetadata]) -> None:
        self.commits = commits

    def commit_metadata(self, repository: Path, query):
        return list(self.commits)


def test_groups_bounded_commit_authors_without_claiming_ownership(tmp_path: Path) -> None:
    report = collect_git_ownership(
        tmp_path,
        since_unix_time=1,
        limit=2,
        history=FakeHistory(
            [
                CommitMetadata("b", ("a",), 3, "Zed", "z@example.com", "later"),
                CommitMetadata("a", (), 2, "Ada", "a@example.com", "first"),
                CommitMetadata("x", (), 1, "Ada", "a@example.com", "older"),
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
        "author_count": 2,
        "authors": [
            {
                "author_name": "Ada",
                "author_email": "a@example.com",
                "commit_count": 1,
                "commit_shas": ["a"],
            },
            {
                "author_name": "Zed",
                "author_email": "z@example.com",
                "commit_count": 1,
                "commit_shas": ["b"],
            },
        ],
    }
