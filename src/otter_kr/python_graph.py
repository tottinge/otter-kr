"""Build a deterministic import-backed graph for Python repositories."""

from __future__ import annotations

from pathlib import Path

from otter_kr.evidence_graph import EvidenceEdge, EvidenceGraph, build_evidence_graph
from otter_kr.python_imports import import_python


def build_python_import_graph(repository: Path) -> EvidenceGraph:
    report = import_python(repository)
    tracked = {
        path.relative_to(repository.resolve()).with_suffix("").as_posix().replace("/", ".")
        for path in _tracked_python_files(repository)
    }
    edges = tuple(
        EvidenceEdge(
            source=edge.path,
            target=(
                edge.target_module
                if edge.target_module in tracked
                else f"module:{edge.target_module}"
            ),
            weight=1.0,
            provenance="python.import",
        )
        for edge in report.edges
    )
    return build_evidence_graph(edges)


def _tracked_python_files(repository: Path) -> list[Path]:
    from otter_kr.git_files import GitCliFileSource

    return GitCliFileSource().python_files(repository.resolve())
