from pathlib import Path

from otter_kr.python_structural_neighborhood import find_structural_neighborhood


class FakeFiles:
    def __init__(self, paths: list[Path]) -> None:
        self.paths = paths

    def python_files(self, repository: Path) -> list[Path]:
        return self.paths


def test_reports_shared_file_and_ast_adjacency_as_separate_evidence(tmp_path: Path) -> None:
    source = tmp_path / "service.py"
    source.write_text(
        "def payment(amount):\n    total = amount\n    return total\n",
        encoding="utf-8",
    )
    report = find_structural_neighborhood(tmp_path, "payment", FakeFiles([source]))

    assert report.to_dict()["edges"] == [
        {
            "seed": "payment",
            "neighbor": "amount",
            "weight": 1,
            "reason": "shared file",
        },
        {
            "seed": "payment",
            "neighbor": "total",
            "weight": 1,
            "reason": "shared file",
        },
    ]
