"""Git-backed repository file capabilities."""

import subprocess
from dataclasses import dataclass
from os import fsdecode
from pathlib import Path
from typing import Protocol


class GitFileSourceError(RuntimeError):
    """A Git file query failed with reproducible command evidence."""

    def __init__(self, command: tuple[str, ...], returncode: int | None, stderr: str) -> None:
        self.command = command
        self.returncode = returncode
        self.stderr = stderr.strip()
        super().__init__(self.stderr or "Git file query failed")


class InvalidGitRepository(ValueError):
    """Git could not discover a working-tree root at the requested path."""


@dataclass(frozen=True, slots=True, init=False)
class GitRepository:
    """The canonical root of a Git working tree discovered from a path."""

    root: Path

    def __init__(self, path: Path) -> None:
        command = ("git", "-C", str(path), "rev-parse", "--show-toplevel")
        try:
            result = subprocess.run(command, check=True, capture_output=True)
        except subprocess.CalledProcessError as error:
            raise InvalidGitRepository(fsdecode(error.stderr).strip()) from error
        except OSError as error:
            raise GitFileSourceError(command, None, str(error)) from error
        object.__setattr__(self, "root", Path(fsdecode(result.stdout).removesuffix("\n")).resolve())


class TrackedFileSource(Protocol):
    def python_files(self, repository: Path) -> list[Path]:
        """Return tracked Python files in deterministic order."""


class GitCliFileSource:
    """Provide tracked files by asking Git directly."""

    def python_files(self, repository: Path) -> list[Path]:
        command = ("git", "-C", str(repository), "ls-files", "--cached", "-z", "--", "*.py")
        try:
            result = subprocess.run(command, check=False, capture_output=True, shell=False)
        except OSError as error:
            raise GitFileSourceError(command, None, str(error)) from error
        if result.returncode != 0:
            raise GitFileSourceError(
                command, result.returncode, result.stderr.decode(errors="replace")
            )
        return sorted(
            repository / name.decode("utf-8") for name in result.stdout.split(b"\0") if name
        )
