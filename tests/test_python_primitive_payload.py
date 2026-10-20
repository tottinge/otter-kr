from pathlib import Path

from otter_kr.python_primitive_payload import analyze_primitive_payload
from tests.support import git_repository, write_python


def test_reports_primitive_payload_ratio_for_files_and_nodes(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "orders.py",
        "class Customer:\n    pass\n\n"
        "class Order:\n"
        "    total: int\n"
        "    currency: str\n"
        "    owner: Customer\n"
        "    metadata: dict\n\n"
        "    def approve(self, status: str, reviewer: Customer, count: int):\n"
        "        pass\n",
    )
    git_repository(tmp_path, "orders.py")

    report = analyze_primitive_payload(tmp_path)

    file_evidence = report.files[0]
    assert file_evidence.path == "orders.py"
    assert file_evidence.primitive_count == 5
    assert file_evidence.specialized_count == 2
    assert file_evidence.primitive_ratio == 5 / 7
    assert [
        (item.name, item.primitive_count, item.specialized_count) for item in file_evidence.nodes
    ] == [
        ("Order", 3, 1),
        ("Order.approve", 2, 1),
    ]


def test_ignores_unannotated_payload_values(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "plain.py",
        "class Plain:\n    value = 1\n\n    def update(self, value):\n        pass\n",
    )
    git_repository(tmp_path, "plain.py")

    report = analyze_primitive_payload(tmp_path)

    assert report.files[0].nodes == ()
    assert report.files[0].primitive_count == 0
    assert report.files[0].specialized_count == 0
    assert report.files[0].primitive_ratio is None
