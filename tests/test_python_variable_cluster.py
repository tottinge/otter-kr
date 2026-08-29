from pathlib import Path

from otter_kr.python_variable_cluster import find_variable_occurrences
from tests.support import git_repository, write_python


def test_exact_variable_occurrences_include_scope_and_role(tmp_path: Path) -> None:
    write_python(tmp_path, "sample.py", "value = 1\ndef read():\n    return value\n")
    git_repository(tmp_path, "sample.py")

    report = find_variable_occurrences(tmp_path, "value")

    assert [(item.scope, item.role) for item in report.occurrences] == [
        ("", "write"),
        ("read", "read"),
    ]
