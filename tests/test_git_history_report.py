from otter_kr.git_history_report import BoundedFileHistoryReport
from otter_kr.git_provenance import python_history_provenance


class FileEvidence:
    def __init__(self, path: str) -> None:
        self.path = path

    def to_dict(self) -> dict[str, object]:
        return {"path": self.path}


def test_bounded_file_history_report_owns_common_envelope() -> None:
    report = BoundedFileHistoryReport(
        provenance=python_history_provenance(
            "/repo",
            since_unix_time=10,
            limit=2,
            commit_count=2,
            truncated=True,
        ),
        files=(FileEvidence("pkg/a.py"),),
    )

    assert report.commit_count == 2
    assert report.truncated is True
    assert report.to_dict()["files"] == [{"path": "pkg/a.py"}]
