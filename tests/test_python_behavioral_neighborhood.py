from pathlib import Path

from otter_kr.python_behavioral_neighborhood import find_behavioral_neighborhood


class FakeFiles:
    def __init__(self, paths: list[Path]) -> None:
        self.paths = paths

    def python_files(self, repository: Path) -> list[Path]:
        return self.paths


def test_reports_calls_fields_and_comparisons(tmp_path: Path) -> None:
    source = tmp_path / "service.py"
    source.write_text(
        "def payment(amount):\n    amount.validate()\n    return amount == Currency.USD\n",
        encoding="utf-8",
    )
    report = find_behavioral_neighborhood(tmp_path, "amount", FakeFiles([source]))

    assert [edge.to_dict() for edge in report.edges] == [
        {"seed": "amount", "neighbor": "Currency", "reason": "type/enum comparison", "weight": 1},
        {"seed": "amount", "neighbor": "validate", "reason": "field access", "weight": 1},
    ]
