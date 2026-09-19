from otter_kr.change_evidence import TermChangeEvidence


def test_term_change_evidence_keeps_current_and_history_distinct() -> None:
    report = TermChangeEvidence(
        "Widget", {"nodes": []}, {"files": []}, {"carrier": "Widget", "occurrences": []}
    )

    assert report.to_dict() == {
        "term": "Widget",
        "current": {"nodes": []},
        "history": {"files": []},
        "carrier_guards": {"carrier": "Widget", "occurrences": []},
        "object_lifecycle": None,
        "dimensions": {
            "ownership": {"source": "carrier_guards", "available": True},
            "multiplicity": {"source": "current.nodes", "node_count": 0},
            "coupling": {"source": "current.edges", "edge_count": 0},
            "history": {"source": "history", "file_count": 0},
            "representations": {"source": "object_lifecycle", "available": False},
        },
    }
