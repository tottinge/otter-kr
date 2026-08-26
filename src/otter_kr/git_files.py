"""Git-backed repository file capabilities."""

import subprocess
from pathlib import Path
from typing import Protocol


class TrackedFileSource(Protocol):
    def python_files(self, repository: Path) -> list[Path]:
        """Return tracked Python files in deterministic order."""


class GitCliFileSource:
    """Provide tracked files by asking Git directly."""

    def python_files(self, repository: Path) -> list[Path]:
        result = subprocess.run(
            ["git", "-C", str(repository), "ls-files", "--cached", "-z", "--", "*.py"],
            check=False,
            capture_output=True,
        )
        if result.returncode != 0:
            raise ValueError(f"Not a Git repository: {repository}")
        return sorted(
            repository / name.decode("utf-8") for name in result.stdout.split(b"\0") if name
        )
