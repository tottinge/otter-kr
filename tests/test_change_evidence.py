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
            "multiplicity": {
                "source": "current.nodes",
                "node_count": 0,
                "location_count": 0,
                "locations": [],
                "locations_truncated": False,
            },
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


def test_term_change_evidence_bounds_dimensional_locations() -> None:
    locations = [{"path": "service.py", "line": line, "column": 0} for line in range(40)]
    report = TermChangeEvidence(
        "Widget",
        {"nodes": [{"name": "Widget", "locations": locations}], "edges": []},
        {"files": []},
        None,
    ).to_dict()

    multiplicity = report["dimensions"]["multiplicity"]
    assert multiplicity["location_count"] == 40
    assert len(multiplicity["locations"]) == 32
    assert multiplicity["locations_truncated"] is True
