from pathlib import Path

from otter_kr.python_neighborhood import find_python_neighborhood


class FakeFiles:
    def __init__(self, paths: list[Path]) -> None:
        self.paths = paths

    def python_files(self, repository: Path) -> list[Path]:
        return self.paths


def test_reports_exact_and_lexical_neighbors_without_structural_edges(tmp_path: Path) -> None:
    service = tmp_path / "service.py"
    service.write_text(
        "def collect_payment(amount):\n"
        "    payment_total = amount\n"
        "    return payment_total\n",
        encoding="utf-8",
    )
    report = find_python_neighborhood(tmp_path, "payment", FakeFiles([service]))

    assert report.to_dict()["nodes"] == [
        {"name": "collect_payment", "occurrence_count": 1},
        {"name": "payment_total", "occurrence_count": 2},
    ]
    assert report.to_dict()["edges"] == [
        {
            "seed": "payment",
            "neighbor": "collect_payment",
            "weight": 1,
            "discovery_pass": "lexical",
            "reason": "shared identifier word",
        },
        {
            "seed": "payment",
            "neighbor": "payment_total",
            "weight": 2,
            "discovery_pass": "lexical",
            "reason": "shared identifier word",
        }
    ]
