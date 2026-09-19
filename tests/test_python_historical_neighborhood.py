from pathlib import Path
from types import SimpleNamespace

from otter_kr.git_ports import CommitFileChange
from otter_kr.python_historical_neighborhood import find_historical_neighborhood


class FakeChanges:
    def commit_file_changes(self, repository: Path, query: object) -> list[CommitFileChange]:
        return [
            CommitFileChange("c2", 200, "src/a.py", 1, 0),
            CommitFileChange("c2", 200, "src/b.py", 1, 0),
        ]


def test_reports_bounded_history_provenance(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "otter_kr.python_historical_neighborhood.find_names",
        lambda repository, seed: SimpleNamespace(
            occurrences=(SimpleNamespace(path="src/a.py"),),
            parse_failures=(),
        ),
    )

    report = find_historical_neighborhood(
        tmp_path,
        "Payment",
        since_unix_time=100,
        limit=4,
        changes=FakeChanges(),
    )

    data = report.to_dict()
    assert data["report_version"] == "1"
    assert data["since_unix_time"] == 100
    assert data["limit"] == 4
    assert data["source_file_filter"]["tracked_by"] == "git"
    assert data["edges"][0]["neighbor_path"] == "src/b.py"
