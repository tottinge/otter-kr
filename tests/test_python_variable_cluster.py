from pathlib import Path

from otter_kr.python_variable_cluster import find_variable_occurrences
from tests.support import git_repository, write_python


def test_exact_variable_occurrences_include_scope_and_role(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "sample.py",
        "def read(value):\n    value += 1\n    del value\n    return value\n",
    )
    git_repository(tmp_path, "sample.py")

    report = find_variable_occurrences(tmp_path, "value")

    assert [(item.scope, item.role) for item in report.occurrences] == [
        ("read", "parameter"),
        ("read", "write"),
        ("read", "delete"),
        ("read", "read"),
    ]


def test_occurrences_report_enclosing_conditional_evidence(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "sample.py",
        "def read(value):\n"
        "    if value > 0:\n"
        "        value += 1\n"
        "    else:\n"
        "        value = 0\n"
        "    return value\n",
    )
    git_repository(tmp_path, "sample.py")

    report = find_variable_occurrences(tmp_path, "value")

    guarded = [item for item in report.occurrences if item.role == "write"]
    assert [item.guards[0].expression for item in guarded] == ["value > 0", "value > 0"]
    assert [item.guards[0].branch for item in guarded] == ["body", "else"]
    assert all(item.guards[0].depth == 1 for item in guarded)
    assert any(item.role == "read" and item.guards == () for item in report.occurrences)
