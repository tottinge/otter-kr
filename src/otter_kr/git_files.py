"""Git-backed repository file capabilities."""

import subprocess
from pathlib import Path
from typing import Protocol


class GitFileSourceError(RuntimeError):
    """A Git file query failed with reproducible command evidence."""

    def __init__(self, command: tuple[str, ...], returncode: int | None, stderr: str) -> None:
        self.command = command
        self.returncode = returncode
        self.stderr = stderr.strip()
        super().__init__(self.stderr or "Git file query failed")


class TrackedFileSource(Protocol):
    def python_files(self, repository: Path) -> list[Path]:
        """Return tracked Python files in deterministic order."""


class GitCliFileSource:
    """Provide tracked files by asking Git directly."""

    def python_files(self, repository: Path) -> list[Path]:
        command = ("git", "-C", str(repository), "ls-files", "--cached", "-z", "--", "*.py")
        try:
            result = subprocess.run(command, check=False, capture_output=True)
        except OSError as error:
            raise GitFileSourceError(command, None, str(error)) from error
        if result.returncode != 0:
            raise GitFileSourceError(
                command, result.returncode, result.stderr.decode(errors="replace")
            )
        return sorted(
            repository / name.decode("utf-8") for name in result.stdout.split(b"\0") if name
        )
