from pathlib import Path

from otter_kr.git_cli_history import GitCliHistory


def test_parses_porcelain_blame_line_origin() -> None:
    def runner(command: tuple[str, ...]) -> tuple[int, bytes, bytes]:
        return 0, b"abc123 1 1 1\nauthor Test\n\tvalue = 1\n", b""

    origins = GitCliHistory(runner).line_origins(Path("/repo"), "pkg/service.py", "HEAD", (1,))

    assert origins[0].origin_commit == "abc123"
    assert origins[0].text == "value = 1"
    assert origins[0].status == "resolved"
