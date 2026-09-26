import ast
import subprocess
from pathlib import Path

from otter_kr import git_files
from otter_kr.git_files import GitCliFileSource
from otter_kr.python_inventory import inventory_python
from otter_kr.python_names import find_names
from tests.support import git_commit, git_repository, write_python


def test_git_file_source_disables_shell_execution(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def run(command: tuple[str, ...], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        captured["command"] = command
        captured.update(kwargs)
        return subprocess.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(git_files.subprocess, "run", run)

    GitCliFileSource().python_files(tmp_path)

    assert captured["shell"] is False


def test_inventory_matches_independent_ast_and_git_file_oracle(tmp_path: Path) -> None:
    source = "class Widget:\n    def collect(self, amount):\n        return amount\n"
    write_python(tmp_path, "pkg/widget.py", source)
    write_python(tmp_path, "broken.py", "def nope(:\n")
    write_python(tmp_path, "ignored.py", "not_tracked = True\n")
    git_repository(tmp_path, "pkg", "broken.py")
    git_commit(tmp_path, "fixture")

    tracked = GitCliFileSource().python_files(tmp_path)
    report = inventory_python(tmp_path)
    parsed = ast.parse(source)
    independent_names = {
        node.name for node in ast.walk(parsed) if isinstance(node, ast.ClassDef | ast.FunctionDef)
    }
    names = find_names(tmp_path, "collect")

    assert [path.relative_to(tmp_path).as_posix() for path in tracked] == [
        "broken.py",
        "pkg/widget.py",
    ]
    assert {item.path for item in report.files} == {"broken.py", "pkg/widget.py"}
    assert len(report.warnings) == 1
    assert independent_names == {"Widget", "collect"}
    assert {item.name for item in names.occurrences} == {"collect"}
