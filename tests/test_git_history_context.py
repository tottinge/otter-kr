from pathlib import Path

from otter_kr.git_history_context import collect_git_history
from otter_kr.git_ports import CommitHistoryQuery, CommitMetadata


class FakeHistorySource:
    def __init__(self, commits: list[CommitMetadata]) -> None:
        self.commits = commits
        self.calls: list[tuple[Path, CommitHistoryQuery]] = []

    def commit_metadata(self, repository: Path, query: CommitHistoryQuery) -> list[CommitMetadata]:
        self.calls.append((repository, query))
        return list(self.commits)


def test_collects_bounded_git_history_context_from_port(tmp_path: Path) -> None:
    commits = [
        CommitMetadata(
            sha="b" * 40,
            parent_shas=("a" * 40,),
            committed_unix_time=1_700_000_002,
            author_name="ignored",
            author_email="ignored@example.com",
            subject="second",
        ),
        CommitMetadata(
            sha="a" * 40,
            parent_shas=(),
            committed_unix_time=1_700_000_001,
            author_name="ignored",
            author_email="ignored@example.com",
            subject="first",
        ),
    ]
    source = FakeHistorySource(commits)

    report = collect_git_history(tmp_path, since_unix_time=1_700_000_000, limit=2, history=source)

    assert source.calls == [
        (
            tmp_path.resolve(),
            CommitHistoryQuery(
                limit=2, since_unix_time=1_700_000_000, tip_sha=None, paths=("*.py",)
            ),
        )
    ]
    assert report.to_dict() == {
        "report_version": "1",
        "repository_root": str(tmp_path.resolve()),
        "tip_revision": "HEAD",
        "since_unix_time": 1_700_000_000,
        "limit": 2,
        "commit_count": 2,
        "truncated": False,
        "source_file_filter": {
            "tracked_by": "git",
            "language": "python",
            "pathspec": "*.py",
            "tip_revision": "HEAD",
        },
        "commits": [
            {
                "sha": "b" * 40,
                "parent_shas": ["a" * 40],
                "committed_unix_time": 1_700_000_002,
                "subject": "second",
            },
            {
                "sha": "a" * 40,
                "parent_shas": [],
                "committed_unix_time": 1_700_000_001,
                "subject": "first",
            },
        ],
    }


def test_collect_git_history_reports_truncation_from_limit_plus_one_fetch(tmp_path: Path) -> None:
    commits = [
        CommitMetadata(
            sha="c" * 40,
            parent_shas=("b" * 40,),
            committed_unix_time=3,
            author_name="ignored",
            author_email="ignored@example.com",
            subject="third",
        ),
        CommitMetadata(
            sha="b" * 40,
            parent_shas=("a" * 40,),
            committed_unix_time=2,
            author_name="ignored",
            author_email="ignored@example.com",
            subject="second",
        ),
        CommitMetadata(
            sha="a" * 40,
            parent_shas=(),
            committed_unix_time=1,
            author_name="ignored",
            author_email="ignored@example.com",
            subject="first",
        ),
    ]

    report = collect_git_history(
        tmp_path,
        since_unix_time=1,
        limit=2,
        history=FakeHistorySource(commits),
    )

    assert report.commit_count == 2
    assert report.truncated is True
    assert [commit.subject for commit in report.commits] == ["third", "second"]
