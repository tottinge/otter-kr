from otter_kr.evidence_graph import EvidenceEdge, EvidenceGraph, build_evidence_graph


def test_topology_is_deterministic_and_exposes_formulas() -> None:
    topology = EvidenceGraph(
        nodes=("b", "a", "c"),
        edges=(
            EvidenceEdge("a", "b", 2.0, "structural"),
            EvidenceEdge("b", "c", 1.0, "historical"),
        ),
        parameters=(("seed", "Payment"), ("edge_filter", "weight >= 1")),
    ).topology()

    assert topology["node_count"] == 3
    assert topology["edge_count"] == 2
    assert topology["average_degree"] == 1.33
    assert topology["average_edge_weight"] == 1.5
    assert topology["community_ids"] == {"a": 0, "b": 0, "c": 0}
    assert topology["cross_community_edge_count"] == 0
    assert topology["component_count"] == 1
    assert topology["component_sizes"] == [3]
    assert topology["cross_community_edge_ratio"] == 0.0
    assert topology["total_edge_weight"] == 3.0
    assert topology["parameters"] == {"edge_filter": "weight >= 1", "seed": "Payment"}
    assert topology["bridge_edge_count"] == 2
    assert topology["bridge_edge_ratio"] == 1.0
    assert topology["formulas"]["average_degree"] == "sum(degrees) / node_count"
    assert topology["formulas"]["bridge_score"] == "sum(edge_betweenness) / node_degree"
    assert topology["formulas"]["bridge_edge_ratio"] == "bridge_edge_count / edge_count"
    assert (
        topology["formulas"]["cross_community_edge_ratio"]
        == "cross_community_edge_count / edge_count"
    )


def test_builder_canonicalizes_nodes_and_edges() -> None:
    graph = build_evidence_graph(
        (
            EvidenceEdge("b", "c", 1.0, "historical"),
            EvidenceEdge("a", "b", 2.0, "structural"),
        )
    )
    assert graph.nodes == ("a", "b", "c")
    assert graph.edges[0].source == "a"
