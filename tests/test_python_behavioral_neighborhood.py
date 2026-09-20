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
        {
            "seed": "amount",
            "neighbor": "Currency",
            "reason": "type/enum comparison",
            "weight": 1,
            "locations": [{"path": "service.py", "line": 3, "column": 21, "operator": "eq"}],
        },
        {
            "seed": "amount",
            "neighbor": "validate",
            "reason": "field access",
            "weight": 1,
            "locations": [{"path": "service.py", "line": 2, "column": 4, "access": "read"}],
        },
    ]


def test_reports_field_store_role_separately_from_field_read(tmp_path: Path) -> None:
    source = tmp_path / "service.py"
    source.write_text(
        "def payment(amount):\n    amount.total = 1\n    return amount.total\n",
        encoding="utf-8",
    )

    report = find_behavioral_neighborhood(tmp_path, "amount", FakeFiles([source]))

    locations = next(edge for edge in report.edges if edge.neighbor == "total").locations
    assert [location["access"] for location in locations] == ["write", "read"]


def test_reports_seed_passed_to_named_call(tmp_path: Path) -> None:
    source = tmp_path / "service.py"
    source.write_text(
        "def payment(amount):\n    validate(amount)\n",
        encoding="utf-8",
    )

    report = find_behavioral_neighborhood(tmp_path, "amount", FakeFiles([source]))

    assert {
        "seed": "amount",
        "neighbor": "validate",
        "reason": "passed as argument",
        "weight": 1,
        "locations": [{"path": "service.py", "line": 2, "column": 4, "argument_index": 0}],
    } in report.to_dict()["edges"]


def test_chained_comparison_reports_only_seed_direct_comparator(tmp_path: Path) -> None:
    source = tmp_path / "service.py"
    source.write_text(
        "def payment(amount, limit, maximum):\n    return amount < limit < maximum\n",
        encoding="utf-8",
    )

    report = find_behavioral_neighborhood(tmp_path, "amount", FakeFiles([source]))

    assert [(edge.neighbor, edge.reason) for edge in report.edges] == [
        ("limit", "type/enum comparison")
    ]


def test_reports_seed_passed_to_named_keyword_argument(tmp_path: Path) -> None:
    source = tmp_path / "service.py"
    source.write_text(
        "def payment(amount):\n    validate(value=amount)\n",
        encoding="utf-8",
    )

    report = find_behavioral_neighborhood(tmp_path, "amount", FakeFiles([source]))

    assert {
        "seed": "amount",
        "neighbor": "validate",
        "reason": "passed as argument",
        "weight": 1,
        "locations": [{"path": "service.py", "line": 2, "column": 4, "argument": "value"}],
    } in report.to_dict()["edges"]
