from pathlib import Path

from otter_kr.python_carrier_guards import find_carrier_guards
from tests.support import git_repository, write_python


def test_planted_enclosed_and_early_exit_guards_share_one_rollup(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "pkg/enclosed.py",
        ("def advance(order):\n    if order.status == 'open':\n        order.status = 'closed'\n"),
    )
    write_python(
        tmp_path,
        "pkg/early_exit.py",
        ("def notify(order):\n    if order.status != 'open':\n        return\n    order.touch()\n"),
    )
    git_repository(tmp_path, "pkg")

    report = find_carrier_guards(tmp_path, "order")

    assert [
        (item.path, item.line, item.control_shape, item.predicate_normalized)
        for item in report.occurrences
    ] == [
        (
            "pkg/early_exit.py",
            2,
            "early_exit",
            {
                "carrier": "order",
                "field": "status",
                "value": "'open'",
                "effect_when": "==",
            },
        ),
        (
            "pkg/enclosed.py",
            2,
            "enclosed_branch",
            {
                "carrier": "order",
                "field": "status",
                "value": "'open'",
                "effect_when": "==",
            },
        ),
    ]
    assert [group.to_dict() for group in report.groups] == [
        {
            "predicate_normalized": {
                "carrier": "order",
                "field": "status",
                "value": "'open'",
                "effect_when": "==",
            },
            "occurrence_count": 2,
            "path_count": 2,
            "paths": ["pkg/early_exit.py", "pkg/enclosed.py"],
            "effect_role_counts": {"modification": 2},
            "occurrence_refs": [
                {"path": "pkg/early_exit.py", "line": 2, "column": 4},
                {"path": "pkg/enclosed.py", "line": 2, "column": 4},
            ],
        }
    ]
    assert report.warnings == ()
