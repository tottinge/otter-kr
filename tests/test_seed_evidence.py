from otter_kr.python_carrier_guards import CarrierGuardReport
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
        (NeighborhoodNode("Widget", 3, ({"path": "pkg/widget.py", "line": 4, "column": 6},)),),
        (NeighborhoodEdge("Widget", "Widget", 3, "exact", "exact identifier match"),),
        ({"path": "bad.py", "message": "syntax"},),
    )

    report = project_python_neighborhood(None, "Widget", neighborhood)

    assert report.to_dict() == {
        "seed": "Widget",
        "source": "python.neighborhood",
        "nodes": [
            {
                "name": "Widget",
                "occurrence_count": 3,
                "locations": [{"path": "pkg/widget.py", "line": 4, "column": 6}],
            }
        ],
        "edges": [
            {
                "seed": "Widget",
                "neighbor": "Widget",
                "weight": 3,
                "discovery_pass": "exact",
                "reason": "exact identifier match",
            }
        ],
        "locations": [{"name": "Widget", "path": "pkg/widget.py", "line": 4, "column": 6}],
        "counts": {"files_scanned": 2, "nodes": 1, "edges": 1},
        "provenance": {
            "operation": "python.neighborhood",
            "parse_failures": [{"path": "bad.py", "message": "syntax"}],
        },
        "carrier_guards": None,
        "object_lifecycle": None,
    }


def test_identifier_seed_projection_includes_carrier_guard_evidence() -> None:
    neighborhood = PythonNeighborhoodReport("order", 1, (), (), ())
    carrier_guards = CarrierGuardReport("python", "order", None, (), (), ())

    report = project_python_neighborhood(None, "order", neighborhood, carrier_guards)

    assert report.to_dict()["carrier_guards"] == {
        "language": "python",
        "carrier": "order",
        "path_bound": None,
        "occurrences": [],
        "groups": [],
        "warnings": [],
    }


def test_non_identifier_seed_projection_omits_carrier_guard_evidence() -> None:
    neighborhood = PythonNeighborhoodReport("order-status", 1, (), (), ())

    report = project_python_neighborhood(None, "order-status", neighborhood)

    assert report.to_dict()["carrier_guards"] is None
    assert report.to_dict()["object_lifecycle"] is None
