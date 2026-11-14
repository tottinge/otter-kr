from pathlib import Path

from otter_kr.git_files import GitRepository
from otter_kr.python_behavioral_neighborhood import (
    _measure_behavioral_neighborhood,
    find_behavioral_neighborhood,
)
from tests.support import git_repository


def test_finds_behavioral_evidence_from_a_validated_repository(tmp_path: Path) -> None:
    source = tmp_path / "service.py"
    source.write_text("amount.validate()\n", encoding="utf-8")
    git_repository(tmp_path, source.name)

    report = find_behavioral_neighborhood(GitRepository(tmp_path), "amount")

    assert report.files_scanned == 1
    assert [(edge.neighbor, edge.reason) for edge in report.edges] == [
        ("validate", "field access"),
        ("validate", "method call"),
    ]


def test_reports_calls_fields_and_comparisons(tmp_path: Path) -> None:
    source = tmp_path / "service.py"
    source.write_text(
        "def payment(amount):\n    amount.validate()\n    return amount == Currency.USD\n",
        encoding="utf-8",
    )
    report = _measure_behavioral_neighborhood("amount", [(source.name, source)])

    edges = [edge.to_dict() for edge in report.edges]
    assert {
        "seed": "amount",
        "neighbor": "Currency",
        "reason": "type/enum comparison",
        "weight": 1,
        "locations": [{"path": "service.py", "line": 3, "column": 21, "operator": "eq"}],
    } in edges
    assert {
        "seed": "amount",
        "neighbor": "validate",
        "reason": "field access",
        "weight": 1,
        "locations": [{"path": "service.py", "line": 2, "column": 4, "access": "read"}],
    } in edges
    assert {
        "seed": "amount",
        "neighbor": "validate",
        "reason": "method call",
        "weight": 1,
        "locations": [{"path": "service.py", "line": 2, "column": 4}],
    } in edges


def test_reports_field_store_role_separately_from_field_read(tmp_path: Path) -> None:
    source = tmp_path / "service.py"
    source.write_text(
        "def payment(amount):\n"
        "    amount.total = 1\n"
        "    del amount.total\n"
        "    return amount.total\n",
        encoding="utf-8",
    )

    report = _measure_behavioral_neighborhood("amount", [(source.name, source)])

    locations = next(edge for edge in report.edges if edge.neighbor == "total").locations
    assert [location["access"] for location in locations] == ["write", "delete", "read"]


def test_reports_seed_passed_to_named_call(tmp_path: Path) -> None:
    source = tmp_path / "service.py"
    source.write_text(
        "def payment(amount):\n    validate(amount)\n",
        encoding="utf-8",
    )

    report = _measure_behavioral_neighborhood("amount", [(source.name, source)])

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

    report = _measure_behavioral_neighborhood("amount", [(source.name, source)])

    assert any(
        edge.neighbor == "limit" and edge.reason == "type/enum comparison" for edge in report.edges
    )
    assert not any(edge.neighbor == "maximum" for edge in report.edges)


def test_reports_seed_passed_to_named_keyword_argument(tmp_path: Path) -> None:
    source = tmp_path / "service.py"
    source.write_text(
        "def payment(amount):\n    validate(value=amount)\n",
        encoding="utf-8",
    )

    report = _measure_behavioral_neighborhood("amount", [(source.name, source)])

    assert {
        "seed": "amount",
        "neighbor": "validate",
        "reason": "passed as argument",
        "weight": 1,
        "locations": [{"path": "service.py", "line": 2, "column": 4, "argument": "value"}],
    } in report.to_dict()["edges"]


def test_calls_preserve_seed_roles_and_count_argument_occurrences(tmp_path: Path) -> None:
    source = tmp_path / "service.py"
    source.write_text(
        "amount(currency, amount, ignored=other)\n"
        "validate(amount, amount, value=amount, **amount)\n",
        encoding="utf-8",
    )

    report = _measure_behavioral_neighborhood("amount", [(source.name, source)])

    assert report.to_dict()["edges"] == [
        {
            "seed": "amount",
            "neighbor": "currency",
            "reason": "call argument",
            "weight": 1,
            "locations": [{"path": "service.py", "line": 1, "column": 7}],
        },
        {
            "seed": "amount",
            "neighbor": "validate",
            "reason": "passed as argument",
            "weight": 4,
            "locations": [
                {"path": "service.py", "line": 2, "column": 0, "argument_index": 0},
                {"path": "service.py", "line": 2, "column": 0, "argument_index": 1},
                {"path": "service.py", "line": 2, "column": 0, "argument": "value"},
                {"path": "service.py", "line": 2, "column": 0, "argument": None},
            ],
        },
    ]
