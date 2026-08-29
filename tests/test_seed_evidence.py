from otter_kr.python_neighborhood import (
    NeighborhoodEdge,
    NeighborhoodNode,
    PythonNeighborhoodReport,
)
from otter_kr.seed_evidence import project_python_neighborhood


def test_seed_projection_preserves_neighborhood_evidence_and_provenance() -> None:
    neighborhood = PythonNeighborhoodReport(
        "Widget",
        2,
        (NeighborhoodNode("Widget", 3),),
        (NeighborhoodEdge("Widget", "Widget", 3, "exact", "exact identifier match"),),
        ({"path": "bad.py", "message": "syntax"},),
    )

    report = project_python_neighborhood(None, "Widget", neighborhood)

    assert report.to_dict() == {
        "seed": "Widget",
        "source": "python.neighborhood",
        "nodes": [{"name": "Widget", "occurrence_count": 3}],
        "edges": [
            {
                "seed": "Widget",
                "neighbor": "Widget",
                "weight": 3,
                "discovery_pass": "exact",
                "reason": "exact identifier match",
            }
        ],
        "locations": [],
        "counts": {"files_scanned": 2, "nodes": 1, "edges": 1},
        "provenance": {
            "operation": "python.neighborhood",
            "parse_failures": [{"path": "bad.py", "message": "syntax"}],
        },
    }
