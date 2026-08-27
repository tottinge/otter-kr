import subprocess
from pathlib import Path


def write_python(repository: Path, relative_path: str, source: str) -> None:
    target = repository / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")


def write_bytes(repository: Path, relative_path: str, source: bytes) -> None:
    target = repository / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source)


def git_repository(repository: Path, *paths: str) -> None:
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "add", *paths], check=True)


def assert_valid_source_location(source: str, line: int, column: int) -> None:
    lines = source.splitlines()
    assert 1 <= line <= len(lines)
    assert 1 <= column <= len(lines[line - 1]) + 1


def assert_syntax_error_details(syntax_error: dict[str, int | str], source: str) -> None:
    assert isinstance(syntax_error["line"], int)
    assert isinstance(syntax_error["column"], int)
    assert isinstance(syntax_error["message"], str)
    assert syntax_error["message"]
    assert_valid_source_location(source, syntax_error["line"], syntax_error["column"])


def assert_invalid_python_warning(warning: dict[str, str], path: str) -> None:
    assert warning["code"] == "invalid_python"
    assert warning["path"] == path
    assert isinstance(warning["message"], str)
    assert warning["message"]
