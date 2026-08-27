from pathlib import Path

from otter_kr.python_complexity import analyze_python_complexity
from tests.support import assert_invalid_python_warning, git_repository, write_python


class ReversedFileSource:
    def python_files(self, repository: Path) -> list[Path]:
        return [repository / "pkg/b.py", repository / "pkg/a.py"]


def test_reports_function_level_complexity_evidence_for_functions_and_methods(
    tmp_path: Path,
) -> None:
    write_python(
        tmp_path,
        "pkg/service.py",
        (
            "def top(flag: bool) -> int:\n"
            "    if flag:\n"
            "        return 1\n"
            "    return 0\n\n"
            "class Worker:\n"
            "    def run(self, items: list[int]) -> int:\n"
            "        total = 0\n"
            "        for item in items:\n"
            "            if item % 2:\n"
            "                total += item\n"
            "        return total\n\n"
            "def outer(values: list[int]) -> list[int]:\n"
            "    def inner(value: int) -> int:\n"
            "        return value * 2 if value > 0 else value\n"
            "    return [inner(value) for value in values if value]\n"
        ),
    )
    git_repository(tmp_path, "pkg")

    report = analyze_python_complexity(tmp_path)

    assert [function.to_dict() for function in report.functions] == [
        {
            "path": "pkg/service.py",
            "qualified_name": "top",
            "kind": "function",
            "line": 1,
            "column": 0,
            "end_line": 4,
            "line_count": 4,
            "branch_count": 1,
            "max_nesting_depth": 1,
            "cyclomatic_count": 2,
        },
        {
            "path": "pkg/service.py",
            "qualified_name": "Worker.run",
            "kind": "method",
            "line": 7,
            "column": 4,
            "end_line": 12,
            "line_count": 6,
            "branch_count": 2,
            "max_nesting_depth": 2,
            "cyclomatic_count": 3,
        },
        {
            "path": "pkg/service.py",
            "qualified_name": "outer",
            "kind": "function",
            "line": 14,
            "column": 0,
            "end_line": 17,
            "line_count": 4,
            "branch_count": 1,
            "max_nesting_depth": 0,
            "cyclomatic_count": 2,
        },
        {
            "path": "pkg/service.py",
            "qualified_name": "outer.inner",
            "kind": "function",
            "line": 15,
            "column": 4,
            "end_line": 16,
            "line_count": 2,
            "branch_count": 1,
            "max_nesting_depth": 1,
            "cyclomatic_count": 2,
        },
    ]
    assert report.warnings == ()


def test_reports_parse_warnings_and_ignores_untracked_python_files(tmp_path: Path) -> None:
    write_python(tmp_path, "tracked.py", "def ready():\n    return True\n")
    write_python(tmp_path, "broken.py", "def nope(:\n")
    write_python(tmp_path, "generated.py", "def hidden():\n    return 0\n")
    git_repository(tmp_path, "tracked.py", "broken.py")

    report = analyze_python_complexity(tmp_path)

    assert [function.qualified_name for function in report.functions] == ["ready"]
    warnings = list(report.warnings)
    assert len(warnings) == 1
    assert_invalid_python_warning(warnings[0], "broken.py")


def test_sorts_complexity_evidence_deterministically(tmp_path: Path) -> None:
    write_python(tmp_path, "pkg/a.py", "def beta():\n    return 2\n")
    write_python(tmp_path, "pkg/b.py", "def alpha():\n    return 1\n")

    report = analyze_python_complexity(tmp_path, file_source=ReversedFileSource())

    assert [function.qualified_name for function in report.functions] == [
        "beta",
        "alpha",
    ]
