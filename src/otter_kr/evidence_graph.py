"""Typed weighted evidence graphs and deterministic topology projections."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import networkx as nx


@dataclass(frozen=True, slots=True)
class EvidenceEdge:
    source: str
    target: str
    weight: float
    provenance: str


@dataclass(frozen=True, slots=True)
class EvidenceGraph:
    nodes: tuple[str, ...]
    edges: tuple[EvidenceEdge, ...]
    parameters: tuple[tuple[str, object], ...] = field(default_factory=tuple)

    def topology(self) -> dict[str, object]:
        graph = nx.Graph()
        graph.add_nodes_from(self.nodes)
        for edge in self.edges:
            if graph.has_edge(edge.source, edge.target):
                graph[edge.source][edge.target]["weight"] += edge.weight
            else:
                graph.add_edge(edge.source, edge.target, weight=edge.weight)
        degrees = dict(graph.degree())
        components = tuple(
            sorted(
                (tuple(sorted(component)) for component in nx.connected_components(graph)),
                key=lambda component: component[0],
            )
        )
        communities = tuple(
            sorted(
                (node, index) for index, component in enumerate(components) for node in component
            )
        )
        community_by_node = dict(communities)
        cross = sum(
            community_by_node[source] != community_by_node[target] for source, target in graph.edges
        )
        edge_count = graph.number_of_edges()
        node_count = graph.number_of_nodes()
        bridge_edge_count = sum(1 for _ in nx.bridges(graph))
        total_weight = sum(data["weight"] for _, _, data in graph.edges(data=True))
        edge_betweenness = nx.edge_betweenness_centrality(graph, normalized=True)
        bridge_scores = {
            node: round(
                sum(
                    edge_betweenness.get(tuple(sorted((edge.source, edge.target))), 0.0)
                    for source, target in graph.edges
                    if node in (source, target)
                )
                / degrees[node],
                2,
            )
            if degrees[node]
            else 0.0
            for node in sorted(graph)
        }
        return {
            "parameters": dict(self.parameters),
            "node_count": node_count,
            "edge_count": edge_count,
            "average_degree": round(sum(degrees.values()) / node_count, 2) if node_count else 0.0,
            "average_edge_weight": round(total_weight / edge_count, 2) if edge_count else 0.0,
            "community_method": "connected_components",
            "community_ids": dict(sorted(communities)),
            "cross_community_edge_count": cross,
            "cross_community_edge_ratio": round(cross / edge_count, 2) if edge_count else 0.0,
            "component_count": len(components),
            "component_sizes": [len(component) for component in components],
            "total_edge_weight": total_weight,
            "bridge_edge_count": bridge_edge_count,
            "bridge_edge_ratio": round(bridge_edge_count / edge_count, 2) if edge_count else 0.0,
            "formulas": {
                "average_degree": "sum(degrees) / node_count",
                "average_edge_weight": "sum(edge_weights) / edge_count",
                "bridge_score": "sum(edge_betweenness) / node_degree",
                "bridge_edge_ratio": "bridge_edge_count / edge_count",
                "cross_community_edge_ratio": "cross_community_edge_count / edge_count",
            },
            "bridge_scores": bridge_scores,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "nodes": list(self.nodes),
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "weight": edge.weight,
                    "provenance": edge.provenance,
                }
                for edge in self.edges
            ],
            "parameters": dict(self.parameters),
            "topology": self.topology(),
        }


def build_evidence_graph(
    edges: tuple[EvidenceEdge, ...],
    parameters: Mapping[str, object] | None = None,
    nodes: tuple[str, ...] = (),
) -> EvidenceGraph:
    """Build a canonical graph from declared evidence edges and optional isolated nodes."""
    all_nodes = set(nodes)
    all_nodes.update(node for edge in edges for node in (edge.source, edge.target))
    return EvidenceGraph(
        nodes=tuple(sorted(all_nodes)),
        edges=tuple(sorted(edges, key=lambda edge: (edge.source, edge.target, edge.provenance))),
        parameters=tuple(sorted((parameters or {}).items())),
    )
