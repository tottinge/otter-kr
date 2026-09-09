from pathlib import Path

from otter_kr.python_variable_cluster import find_variable_cluster, find_variable_occurrences
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


def test_two_name_cluster_reports_shared_context_and_named_locations(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "sample.py",
        "def adjust(count, limit):\n"
        "    if count < limit:\n"
        "        count += 1\n"
        "        limit -= 1\n",
    )
    git_repository(tmp_path, "sample.py")

    report = find_variable_cluster(tmp_path, ("count", "limit"))

    assert report.names == ("count", "limit")
    assert {(item.name, item.role) for item in report.occurrences} == {
        ("count", "parameter"),
        ("count", "read"),
        ("count", "write"),
        ("limit", "parameter"),
        ("limit", "read"),
        ("limit", "write"),
    }
    assert [(scope.path, scope.scope) for scope in report.shared_scopes] == [
        ("sample.py", "adjust")
    ]
    assert [guard.expression for guard in report.shared_guards] == ["count < limit"]


def test_two_name_cluster_does_not_merge_guards_from_different_contexts(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "sample.py",
        "def adjust(count, limit):\n"
        "    if count > 0:\n"
        "        limit += 1\n"
        "    if limit > 0:\n"
        "        count += 1\n",
    )
    git_repository(tmp_path, "sample.py")

    report = find_variable_cluster(tmp_path, ("count", "limit"))

    assert report.shared_guards == ()


def test_two_name_cluster_does_not_merge_opposite_guard_branches(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "sample.py",
        "def adjust(count, limit):\n"
        "    if count > 0:\n"
        "        limit += 1\n"
        "    else:\n"
        "        count += 1\n",
    )
    git_repository(tmp_path, "sample.py")

    report = find_variable_cluster(tmp_path, ("count", "limit"))

    assert report.shared_guards == ()


def test_occurrences_report_initialization_and_attribute_assignments(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "sample.py",
        "class Counter:\n"
        "    def __init__(self, value):\n"
        "        self.value = value\n"
        "        value = 0\n",
    )
    git_repository(tmp_path, "sample.py")

    report = find_variable_occurrences(tmp_path, "value")

    assert [
        (site.target, site.kind, site.scope, site.value) for site in report.construction_sites
    ] == [
        ("self.value", "attribute_assignment", "Counter.__init__", "value"),
        ("value", "assignment", "Counter.__init__", "0"),
    ]
