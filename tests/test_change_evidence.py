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
            "ownership": {
                "source": "carrier_guards",
                "available": True,
                "occurrence_count": 0,
                "group_count": 0,
            },
            "multiplicity": {"source": "current.nodes", "node_count": 0, "locations": []},
            "coupling": {"source": "current.edges", "edge_count": 0},
            "history": {"source": "history.files", "file_count": 0, "paths": []},
            "representations": {
                "source": "object_lifecycle",
                "available": False,
                "construction_count": 0,
                "operation_count": 0,
            },
        },
    }
