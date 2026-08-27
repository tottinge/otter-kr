from pathlib import Path

from otter_kr.python_duplicates import find_duplicate_helpers
from tests.support import assert_invalid_python_warning, git_repository, write_python


class ReversedFileSource:
    def python_files(self, repository: Path) -> list[Path]:
        return [repository / "pkg/b.py", repository / "pkg/a.py", repository / "broken.py"]


def test_reports_duplicate_helper_groups_and_pairs(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "pkg/helpers.py",
        (
            "def first(item, limit):\n"
            "    if item > limit:\n"
            "        return item - limit\n"
            "    return limit - item\n\n"
            "def second(value, cap):\n"
            "    if value > cap:\n"
            "        return value - cap\n"
            "    return cap - value\n\n"
            "class Worker:\n"
            "    def third(self, current, maximum):\n"
            "        if current > maximum:\n"
            "            return current - maximum\n"
            "        return maximum - current\n\n"
            "def different(item, limit):\n"
            "    if item >= limit:\n"
            "        return item\n"
            "    return limit\n"
        ),
    )
    git_repository(tmp_path, "pkg")

    report = find_duplicate_helpers(tmp_path)

    assert len(report.groups) == 1
    assert report.groups[0].count == 3
    assert report.groups[0].fingerprint == report.pairs[0].fingerprint
    assert [item.qualified_name for item in report.groups[0].occurrences] == [
        "first",
        "second",
        "Worker.third",
    ]
    assert [(item.left.qualified_name, item.right.qualified_name) for item in report.pairs] == [
        ("first", "second"),
        ("first", "Worker.third"),
        ("second", "Worker.third"),
    ]


def test_reports_parse_warnings_and_sorts_deterministically(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "pkg/a.py",
        (
            "def alpha(value, limit):\n"
            "    if value > limit:\n"
            "        return value - limit\n"
            "    return limit - value\n"
        ),
    )
    write_python(
        tmp_path,
        "pkg/b.py",
        (
            "def beta(item, cap):\n"
            "    if item > cap:\n"
            "        return item - cap\n"
            "    return cap - item\n"
        ),
    )
    write_python(tmp_path, "broken.py", "def nope(:\n")
    write_python(tmp_path, "ignored.py", "def gamma(a, b):\n    return a + b\n")
    git_repository(tmp_path, "pkg", "broken.py")

    report = find_duplicate_helpers(tmp_path, file_source=ReversedFileSource())

    assert [item.qualified_name for item in report.groups[0].occurrences] == ["alpha", "beta"]
    warnings = list(report.warnings)
    assert len(warnings) == 1
    assert_invalid_python_warning(warnings[0], "broken.py")
