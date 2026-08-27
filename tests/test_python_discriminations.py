import subprocess
from pathlib import Path

from otter_kr.python_discriminations import find_type_discriminations


class ReversedFileSource:
    def python_files(self, repository: Path) -> list[Path]:
        return [repository / "pkg/b.py", repository / "pkg/a.py", repository / "broken.py"]


def write_python(repository: Path, relative_path: str, source: str) -> None:
    target = repository / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source)


def git_repository(repository: Path, *paths: str) -> None:
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "add", *paths], check=True)


def assert_invalid_python_warning(warning: dict[str, str], path: str) -> None:
    assert warning["code"] == "invalid_python"
    assert warning["path"] == path
    assert isinstance(warning["message"], str)
    assert warning["message"]


def test_reports_enum_members_comparisons_and_lookups_for_selected_type(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "pkg/service.py",
        (
            "from enum import Enum\n\n"
            "class Status(Enum):\n"
            '    OPEN = "open"\n'
            '    CLOSED = "closed"\n\n'
            'LABELS = {Status.OPEN: "Open", Status.CLOSED: "Closed"}\n\n'
            "def describe(status):\n"
            "    if status is Status.OPEN:\n"
            "        return LABELS[Status.OPEN]\n"
            "    if Status.CLOSED == status:\n"
            "        return LABELS[Status.CLOSED]\n"
            "    return LABELS[status]\n"
        ),
    )
    git_repository(tmp_path, "pkg")

    report = find_type_discriminations(tmp_path, "Status")

    assert report.type_name == "Status"
    assert report.declarations[0].to_dict() == {
        "path": "pkg/service.py",
        "line": 3,
        "column": 0,
        "qualified_name": "Status",
        "kind": "enum",
        "members": ["OPEN", "CLOSED"],
    }
    assert [item.to_dict() for item in report.comparisons] == [
        {
            "path": "pkg/service.py",
            "line": 10,
            "column": 7,
            "operator": "is",
            "member": "OPEN",
            "expression": "status is Status.OPEN",
        },
        {
            "path": "pkg/service.py",
            "line": 12,
            "column": 7,
            "operator": "==",
            "member": "CLOSED",
            "expression": "Status.CLOSED == status",
        },
    ]
    assert [item.to_dict() for item in report.lookups] == [
        {
            "path": "pkg/service.py",
            "line": 7,
            "column": 10,
            "kind": "dict_key",
            "member": "OPEN",
            "expression": "Status.OPEN",
        },
        {
            "path": "pkg/service.py",
            "line": 7,
            "column": 31,
            "kind": "dict_key",
            "member": "CLOSED",
            "expression": "Status.CLOSED",
        },
        {
            "path": "pkg/service.py",
            "line": 11,
            "column": 15,
            "kind": "subscript",
            "member": "OPEN",
            "expression": "LABELS[Status.OPEN]",
        },
        {
            "path": "pkg/service.py",
            "line": 13,
            "column": 15,
            "kind": "subscript",
            "member": "CLOSED",
            "expression": "LABELS[Status.CLOSED]",
        },
    ]
    assert report.warnings == ()


def test_sorts_deterministically_and_reports_parse_warnings(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "pkg/a.py",
        (
            "from enum import Enum\n\n"
            "class Status(Enum):\n"
            '    OPEN = "open"\n'
            '    CLOSED = "closed"\n'
        ),
    )
    write_python(
        tmp_path,
        "pkg/b.py",
        (
            "def render(status, labels):\n"
            "    if status == Status.CLOSED:\n"
            "        return labels[Status.CLOSED]\n"
            "    return labels[status]\n"
        ),
    )
    write_python(tmp_path, "broken.py", "def nope(:\n")
    git_repository(tmp_path, "pkg", "broken.py")

    report = find_type_discriminations(tmp_path, "Status", file_source=ReversedFileSource())

    assert [item.path for item in report.declarations] == ["pkg/a.py"]
    assert [item.path for item in report.comparisons] == ["pkg/b.py"]
    assert [item.path for item in report.lookups] == ["pkg/b.py"]
    warnings = list(report.warnings)
    assert len(warnings) == 1
    assert_invalid_python_warning(warnings[0], "broken.py")
