from otter_kr.review_packet import ReviewEvidencePacket


def test_review_packet_keeps_sources_separate() -> None:
    packet = ReviewEvidencePacket({"repository_root": "/repo"}, {"files": []}, {"hotspots": {}})

    assert packet.to_dict() == {
        "scope": {"repository_root": "/repo"},
        "history": {"files": []},
        "inventory": {"hotspots": {}},
    }
