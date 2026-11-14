from pathlib import Path
from unittest.mock import patch

from otter_kr import python_tests
from otter_kr.python_review_context import collect_python_review_context
from otter_kr.review_packet import compose_review_packet
from tests.support import git_repository, write_bytes, write_python


def test_review_packet_keeps_sources_separate() -> None:
    packet = compose_review_packet({"repository_root": "/repo"}, {"files": []}, {"hotspots": {}})

    assert packet.to_dict() == {
        "scope": {"repository_root": "/repo"},
        "history": {"files": []},
        "inventory": {"hotspots": {}},
        "names": [],
        "dependencies": {},
        "tests": [],
    }


def test_review_context_reuses_test_sources_and_preserves_per_symbol_evidence(
    tmp_path: Path,
) -> None:
    write_python(tmp_path, "app.py", "def alpha(): pass\ndef beta(): pass\ndef alpha(): pass\n")
    write_python(
        tmp_path,
        "test_app.py",
        "from app import alpha as first, beta\n"
        "def test_first(): first()\n"
        "def test_second(): beta()\n",
    )
    write_python(tmp_path, "broken.py", "def broken(\n")
    write_bytes(tmp_path, "encoding.py", b"\xff")
    git_repository(tmp_path, "app.py", "test_app.py", "broken.py", "encoding.py")
    expected = tuple(
        python_tests.find_tests_for_symbol(tmp_path, symbol).to_dict()
        for symbol in ("alpha", "beta", "alpha")
    )

    with patch.object(python_tests, "_parent_map", wraps=python_tests._parent_map) as parent_map:
        packet = collect_python_review_context(tmp_path, path="app.py", limit=3)

    assert packet.tests == expected
    assert parent_map.call_count == 2
