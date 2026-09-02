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


def test_reports_direct_from_import_target_for_seed(tmp_path: Path) -> None:
    source = tmp_path / "service.py"
    source.write_text(
        "from app.models import Payment\n\ndef quote():\n    return Payment()\n",
        encoding="utf-8",
    )

    report = find_structural_neighborhood(tmp_path, "Payment", FakeFiles([source]))

    assert {
        "seed": "Payment",
        "neighbor": "app.models",
        "weight": 1,
        "reason": "import target",
    } in report.to_dict()["edges"]


def test_aggregates_repeated_direct_import_targets(tmp_path: Path) -> None:
    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    first.write_text("from app.models import Payment\nPayment()\n", encoding="utf-8")
    second.write_text("from app.models import Payment\nPayment()\n", encoding="utf-8")

    report = find_structural_neighborhood(tmp_path, "Payment", FakeFiles([first, second]))

    assert {
        "seed": "Payment",
        "neighbor": "app.models",
        "weight": 2,
        "reason": "import target",
    } in report.to_dict()["edges"]
    assert {"name": "app.models", "occurrence_count": 2} in report.to_dict()["nodes"]


def test_reports_plain_import_alias_target_for_seed(tmp_path: Path) -> None:
    source = tmp_path / "service.py"
    source.write_text("import app.models as Payment\nPayment.quote()\n", encoding="utf-8")

    report = find_structural_neighborhood(tmp_path, "Payment", FakeFiles([source]))

    assert {
        "seed": "Payment",
        "neighbor": "app.models",
        "weight": 1,
        "reason": "import target",
    } in report.to_dict()["edges"]


def test_rejects_unaliased_plain_import_as_seed_target(tmp_path: Path) -> None:
    source = tmp_path / "service.py"
    source.write_text("import app.models\nPayment()\n", encoding="utf-8")

    report = find_structural_neighborhood(tmp_path, "Payment", FakeFiles([source]))

    assert not any(edge["reason"] == "import target" for edge in report.to_dict()["edges"])
