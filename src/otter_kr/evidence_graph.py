"""Typed weighted evidence graphs and deterministic topology projections."""

from __future__ import annotations

from dataclasses import dataclass

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

    def topology(self) -> dict[str, object]:
        graph = nx.Graph()
        graph.add_nodes_from(self.nodes)
        for edge in self.edges:
            graph.add_edge(edge.source, edge.target, weight=edge.weight)
        degrees = dict(graph.degree())
        communities = tuple(
            sorted(
                (node, index)
                for index, component in enumerate(
                    sorted(
                        (sorted(component) for component in nx.connected_components(graph)),
                        key=lambda component: component[0],
                    )
                )
                for node in component
            )
        )
        community_by_node = dict(communities)
        cross = sum(
            community_by_node[edge.source] != community_by_node[edge.target]
            for edge in self.edges
        )
        edge_count = graph.number_of_edges()
        node_count = graph.number_of_nodes()
        total_weight = sum(edge.weight for edge in self.edges)
        edge_betweenness = nx.edge_betweenness_centrality(graph, normalized=True)
        bridge_scores = {
            node: round(
                sum(
                    edge_betweenness.get(tuple(sorted((edge.source, edge.target))), 0.0)
                    for edge in self.edges
                    if node in (edge.source, edge.target)
                )
                / degrees[node],
                2,
            )
            if degrees[node]
            else 0.0
            for node in sorted(graph)
        }
        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "average_degree": round(sum(degrees.values()) / node_count, 2) if node_count else 0.0,
            "average_edge_weight": round(total_weight / edge_count, 2) if edge_count else 0.0,
            "community_ids": dict(sorted(communities)),
            "cross_community_edge_count": cross,
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
            "topology": self.topology(),
        }


def build_evidence_graph(edges: tuple[EvidenceEdge, ...]) -> EvidenceGraph:
    """Build a canonical graph from declared evidence edges."""
    nodes = {node for edge in edges for node in (edge.source, edge.target)}
    return EvidenceGraph(
        nodes=tuple(sorted(nodes)),
        edges=tuple(sorted(edges, key=lambda edge: (edge.source, edge.target, edge.provenance))),
    )
