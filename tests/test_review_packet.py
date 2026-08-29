from otter_kr.review_packet import compose_review_packet


def test_review_packet_keeps_sources_separate() -> None:
    packet = compose_review_packet({"repository_root": "/repo"}, {"files": []}, {"hotspots": {}})

    assert packet.to_dict() == {
        "scope": {"repository_root": "/repo"},
        "history": {"files": []},
        "inventory": {"hotspots": {}},
    }
