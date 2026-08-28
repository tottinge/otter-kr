import subprocess
from pathlib import Path
from typing import Any

from fastmcp import Client


async def call_research(server: Any, request: dict[str, Any]) -> dict[str, Any]:
    """Invoke the research tool while keeping transport plumbing out of tests."""
    async with Client(server) as client:
        result = await client.call_tool("research", request)
        return result.data


async def list_tools(server: Any) -> list[str]:
    async with Client(server) as client:
        return [tool.name for tool in await client.list_tools()]


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


def git_commit(repository: Path, message: str, *paths: str) -> str:
    if paths:
        subprocess.run(["git", "-C", str(repository), "add", *paths], check=True)
    env = {
        "GIT_AUTHOR_NAME": "Test User",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test User",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }
    subprocess.run(
        ["git", "-C", str(repository), "commit", "-q", "-m", message],
        check=True,
        env=env,
    )
    result = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


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


def assert_unreadable_file_warning(warning: dict[str, str], path: str) -> None:
    assert warning == {
        "code": "unreadable_file",
        "path": path,
        "message": "File could not be decoded as UTF-8.",
    }
