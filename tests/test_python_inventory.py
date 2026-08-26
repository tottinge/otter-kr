import subprocess
from pathlib import Path

from otter_kr.python_inventory import inventory_python


def write_python(repository: Path, relative_path: str, source: str) -> None:
    target = repository / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source)


def git_repository(repository: Path, *paths: str) -> None:
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "add", *paths], check=True)


def test_inventories_tracked_python_files_with_parse_health(tmp_path: Path) -> None:
    write_python(tmp_path, "pkg/__init__.py", "\n")
    write_python(tmp_path, "pkg/service.py", "answer = 42\n")
    write_python(tmp_path, "broken.py", "def nope(:\n")
    write_python(tmp_path, "notes.txt", "not Python\n")
    git_repository(tmp_path, "pkg", "broken.py", "notes.txt")

    report = inventory_python(tmp_path)

    assert [item.path for item in report.files] == [
        "broken.py",
        "pkg/__init__.py",
        "pkg/service.py",
    ]
    assert report.files[0].parse_status == "syntax_error"
    assert report.files[0].syntax_error == {
        "line": 1,
        "column": 10,
        "message": "invalid syntax",
    }
    assert report.files[1].module_kind == "package"
    assert report.files[2].module == "pkg.service"
    assert report.files[2].bytes == len(b"answer = 42\n")
    assert report.files[2].lines == 1
    assert report.files[2].parse_status == "ok"


def test_inventory_ignores_present_but_untracked_python_files(tmp_path: Path) -> None:
    write_python(tmp_path, "app.py", "visible = 1\n")
    write_python(tmp_path, ".hidden/secret.py", "visible = 2\n")
    write_python(tmp_path, ".venv/library.py", "visible = 3\n")
    write_python(tmp_path, "build/generated.py", "visible = 4\n")
    git_repository(tmp_path, "app.py")

    report = inventory_python(tmp_path)

    assert [item.path for item in report.files] == ["app.py"]
