import subprocess
from pathlib import Path

from otter_kr.python_imports import import_python


def write_python(repository: Path, relative_path: str, source: str) -> None:
    target = repository / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source)


def git_repository(repository: Path, *paths: str) -> None:
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "add", *paths], check=True)


def test_reports_direct_import_edges_for_tracked_python_files(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "pkg/service.py",
        "import os\nfrom pkg.helpers import helper, other\nfrom . import local_name\n",
    )
    write_python(tmp_path, "pkg/helpers.py", "def helper():\n    return 1\n")
    write_python(tmp_path, "pkg/__init__.py", "\n")
    git_repository(tmp_path, "pkg")

    report = import_python(tmp_path)

    assert [edge.to_dict() for edge in report.edges] == [
        {
            "path": "pkg/service.py",
            "source_module": "pkg.service",
            "target_module": "os",
            "imported_names": [],
            "relative_level": 0,
            "line": 1,
        },
        {
            "path": "pkg/service.py",
            "source_module": "pkg.service",
            "target_module": "pkg.helpers",
            "imported_names": ["helper", "other"],
            "relative_level": 0,
            "line": 2,
        },
        {
            "path": "pkg/service.py",
            "source_module": "pkg.service",
            "target_module": "pkg",
            "imported_names": ["local_name"],
            "relative_level": 1,
            "line": 3,
        },
    ]
    assert report.warnings == ()


def test_ignores_present_but_untracked_python_files(tmp_path: Path) -> None:
    write_python(tmp_path, "tracked.py", "import os\n")
    write_python(tmp_path, "generated.py", "import sys\n")
    git_repository(tmp_path, "tracked.py")

    report = import_python(tmp_path)

    assert [edge.path for edge in report.edges] == ["tracked.py"]


def test_reports_parse_failures_and_unresolved_relative_imports(tmp_path: Path) -> None:
    write_python(tmp_path, "pkg/service.py", "from ..missing import thing\n")
    write_python(tmp_path, "broken.py", "from nope import (\n")
    write_python(tmp_path, "pkg/__init__.py", "\n")
    git_repository(tmp_path, "pkg", "broken.py")

    report = import_python(tmp_path)

    assert [edge.to_dict() for edge in report.edges] == [
        {
            "path": "pkg/service.py",
            "source_module": "pkg.service",
            "target_module": "missing",
            "imported_names": ["thing"],
            "relative_level": 2,
            "line": 1,
        }
    ]
    assert list(report.warnings) == [
        {
            "code": "invalid_python",
            "path": "broken.py",
            "message": "Syntax error at line 1, column 18: '(' was never closed",
        },
        {
            "code": "unresolved_relative_import",
            "path": "pkg/service.py",
            "message": (
                "Relative import level 2 escapes the tracked package boundary for pkg.service."
            ),
        },
    ]
