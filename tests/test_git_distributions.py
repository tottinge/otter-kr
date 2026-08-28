from pathlib import Path

from otter_kr.git_distributions import collect_git_distributions
from otter_kr.git_ports import CommitMetadata


class FakeHistory:
    def __init__(self, commits: list[CommitMetadata]) -> None:
        self.commits = commits

    def commit_metadata(self, repository: Path, query):
        return self.commits


def commit(sha: str, timestamp: int, subject: str) -> CommitMetadata:
    return CommitMetadata(sha, (), timestamp, "Test", "test@example.com", subject)


def test_reports_complete_week_rows_and_message_categories(tmp_path: Path) -> None:
    report = collect_git_distributions(
        tmp_path,
        since_unix_time=1_704_067_200,  # 2024-01-01, Monday
        limit=5,
        history=FakeHistory(
            [
                commit("c2", 1_704_153_600, "fix(api): correct result"),  # Jan 2
                commit("c1", 1_705_968_000, "ordinary maintenance"),  # Jan 23
            ]
        ),
    )

    assert report.to_dict()["weeks"] == [
        {
            "week_start": "2024-01-01",
            "commit_count": 1,
            "categories": [
                {
                    "commit_sha": "c2",
                    "subject": "fix(api): correct result",
                    "raw_category": "fix",
                    "normalized_category": "fix",
                }
            ],
        },
        {
            "week_start": "2024-01-08",
            "commit_count": 0,
            "categories": [],
        },
        {
            "week_start": "2024-01-15",
            "commit_count": 0,
            "categories": [],
        },
        {
            "week_start": "2024-01-22",
            "commit_count": 1,
            "categories": [
                {
                    "commit_sha": "c1",
                    "subject": "ordinary maintenance",
                    "raw_category": None,
                    "normalized_category": None,
                }
            ],
        },
    ]
    assert report.minimum_weekly_count == 0
    assert report.maximum_weekly_count == 1
    assert report.average_weekly_count == 0.5
    assert report.unknown_category_count == 1
