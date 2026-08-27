from pathlib import Path

from otter_kr.python_imports import import_python
from tests.support import assert_invalid_python_warning, git_repository, write_python


class ReversedFileSource:
    def python_files(self, repository: Path) -> list[Path]:
        return [repository / "pkg/b.py", repository / "pkg/a.py"]


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
    warnings = list(report.warnings)
    assert_invalid_python_warning(warnings[0], "broken.py")
    assert warnings[1] == {
        "code": "unresolved_relative_import",
        "path": "pkg/service.py",
        "message": "Relative import level 2 escapes the tracked package boundary for pkg.service.",
    }


def test_sorts_import_edges_deterministically(tmp_path: Path) -> None:
    write_python(tmp_path, "pkg/a.py", "from pkg.shared import beta\nimport zlib\n")
    write_python(tmp_path, "pkg/b.py", "import sys\nfrom pkg.shared import alpha\n")
    write_python(tmp_path, "pkg/shared.py", "VALUE = 1\n")

    report = import_python(tmp_path, file_source=ReversedFileSource())

    assert [edge.to_dict() for edge in report.edges] == [
        {
            "path": "pkg/a.py",
            "source_module": "pkg.a",
            "target_module": "pkg.shared",
            "imported_names": ["beta"],
            "relative_level": 0,
            "line": 1,
        },
        {
            "path": "pkg/a.py",
            "source_module": "pkg.a",
            "target_module": "zlib",
            "imported_names": [],
            "relative_level": 0,
            "line": 2,
        },
        {
            "path": "pkg/b.py",
            "source_module": "pkg.b",
            "target_module": "sys",
            "imported_names": [],
            "relative_level": 0,
            "line": 1,
        },
        {
            "path": "pkg/b.py",
            "source_module": "pkg.b",
            "target_module": "pkg.shared",
            "imported_names": ["alpha"],
            "relative_level": 0,
            "line": 2,
        },
    ]
