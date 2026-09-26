from pathlib import Path

import pytest

from otter_kr.git_cli_history import GitCliHistory, GitHistoryValidationError


def test_parses_porcelain_blame_line_origin() -> None:
    def runner(command: tuple[str, ...]) -> tuple[int, bytes, bytes]:
        return 0, b"abc123 1 1 1\nauthor Test\n\tvalue = 1\n", b""

    origins = GitCliHistory(runner).line_origins(Path("/repo"), "pkg/service.py", "HEAD", (1,))

    assert origins[0].origin_commit == "abc123"
    assert origins[0].text == "value = 1"
    assert origins[0].status == "resolved"


@pytest.mark.parametrize("revision", ["--upload-pack=evil", "HEAD;touch /tmp/pwned"])
def test_rejects_unsafe_blame_revisions(revision: str) -> None:
    with pytest.raises(GitHistoryValidationError, match="revision"):
        GitCliHistory(lambda command: (0, b"", b"")).line_origins(
            Path("/repo"), "pkg/service.py", revision, (1,)
        )


@pytest.mark.parametrize("path", ["../outside.py", "/etc/passwd", "pkg\\service.py"])
def test_rejects_unsafe_blame_paths(path: str) -> None:
    with pytest.raises(GitHistoryValidationError, match="paths must be repository-relative"):
        GitCliHistory(lambda command: (0, b"", b"")).line_origins(Path("/repo"), path, "HEAD", (1,))
