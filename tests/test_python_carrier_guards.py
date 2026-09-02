from pathlib import Path

from otter_kr.python_carrier_guards import find_carrier_guards
from tests.support import assert_invalid_python_warning, git_repository, write_python


class SingleFileSource:
    def __init__(self, relative: str) -> None:
        self.relative = relative

    def python_files(self, repository: Path) -> list[Path]:
        return [repository / self.relative]


def test_reports_enclosed_branch_when_predicate_and_body_modify_carrier(tmp_path: Path) -> None:
    source = (
        "def advance(order):\n"
        "    if order.status == 'open':\n"
        "        order.status = 'closed'\n"
        "        order.touch()\n"
    )
    write_python(tmp_path, "pkg/service.py", source)
    git_repository(tmp_path, "pkg")

    report = find_carrier_guards(tmp_path, "order")

    assert report.carrier == "order"
    assert [item.to_dict() for item in report.occurrences] == [
        {
            "path": "pkg/service.py",
            "line": 2,
            "column": 4,
            "control_shape": "enclosed_branch",
            "predicate": {
                "expression": "order.status == 'open'",
                "field": "status",
                "operator": "==",
                "value": "'open'",
            },
            "predicate_normalized": {
                "carrier": "order",
                "field": "status",
                "value": "'open'",
                "effect_when": "==",
            },
            "exit_kind": None,
            "effects": [
                {
                    "line": 3,
                    "column": 8,
                    "role": "modification",
                    "kind": "attribute_store",
                    "expression": "order.status = 'closed'",
                },
                {
                    "line": 4,
                    "column": 8,
                    "role": "modification",
                    "kind": "mutative_call",
                    "expression": "order.touch()",
                },
            ],
        }
    ]
    assert report.warnings == ()


def test_reports_guard_clause_with_fallthrough_access_and_modification(tmp_path: Path) -> None:
    source = (
        "def advance(order):\n"
        "    if order.status != 'open':\n"
        "        return\n"
        "    label = order.status\n"
        "    order.closed = True\n"
    )
    write_python(tmp_path, "pkg/service.py", source)
    git_repository(tmp_path, "pkg")

    report = find_carrier_guards(tmp_path, "order")

    assert [item.to_dict() for item in report.occurrences] == [
        {
            "path": "pkg/service.py",
            "line": 2,
            "column": 4,
            "control_shape": "early_exit",
            "predicate": {
                "expression": "order.status != 'open'",
                "field": "status",
                "operator": "!=",
                "value": "'open'",
            },
            "predicate_normalized": {
                "carrier": "order",
                "field": "status",
                "value": "'open'",
                "effect_when": "==",
            },
            "exit_kind": "return",
            "effects": [
                {
                    "line": 4,
                    "column": 12,
                    "role": "access",
                    "kind": "attribute_load",
                    "expression": "order.status",
                },
                {
                    "line": 5,
                    "column": 4,
                    "role": "modification",
                    "kind": "attribute_store",
                    "expression": "order.closed = True",
                },
            ],
        }
    ]


def test_ignores_unrelated_branches_and_sorts_occurrences(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "pkg/a.py",
        ("def one(order):\n    if order.kind == 'a':\n        order.mark()\n"),
    )
    write_python(
        tmp_path,
        "pkg/b.py",
        (
            "def two(order):\n"
            "    if other.kind == 'a':\n"
            "        other.mark()\n"
            "    if order.kind != 'b':\n"
            "        return\n"
            "    order.note = 1\n"
        ),
    )
    git_repository(tmp_path, "pkg")

    report = find_carrier_guards(tmp_path, "order", file_source=SingleFileSource("pkg/b.py"))

    assert [item.path for item in report.occurrences] == ["pkg/b.py"]
    assert [item.control_shape for item in report.occurrences] == ["early_exit"]
    assert report.occurrences[0].predicate["field"] == "kind"


def test_normalized_keys_align_enclosed_equality_with_early_exit_inequality(
    tmp_path: Path,
) -> None:
    write_python(
        tmp_path,
        "pkg/a.py",
        ("def enclosed(order):\n    if order.status == 'open':\n        order.mark()\n"),
    )
    write_python(
        tmp_path,
        "pkg/b.py",
        (
            "def guarded(order):\n"
            "    if order.status != 'open':\n"
            "        return\n"
            "    order.mark()\n"
            "def identity(order):\n"
            "    if order.status is Status.OPEN:\n"
            "        order.mark()\n"
            "def identity_guard(order):\n"
            "    if order.status is not Status.OPEN:\n"
            "        return\n"
            "    order.mark()\n"
        ),
    )
    git_repository(tmp_path, "pkg")

    report = find_carrier_guards(tmp_path, "order")
    keys = [item.predicate_normalized for item in report.occurrences]

    assert (
        keys[0]
        == keys[1]
        == {
            "carrier": "order",
            "field": "status",
            "value": "'open'",
            "effect_when": "==",
        }
    )
    assert (
        keys[2]
        == keys[3]
        == {
            "carrier": "order",
            "field": "status",
            "value": "Status.OPEN",
            "effect_when": "is",
        }
    )


def test_reports_parse_warnings_and_rejects_empty_carrier(tmp_path: Path) -> None:
    write_python(tmp_path, "broken.py", "def nope(:\n")
    git_repository(tmp_path, "broken.py")

    report = find_carrier_guards(tmp_path, "order")
    assert report.occurrences == ()
    assert len(report.warnings) == 1
    assert_invalid_python_warning(report.warnings[0], "broken.py")

    try:
        find_carrier_guards(tmp_path, "")
    except ValueError as error:
        assert "carrier" in str(error).lower()
    else:
        raise AssertionError("expected empty carrier to raise ValueError")
