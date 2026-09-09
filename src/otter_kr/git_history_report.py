"""Shared envelope for bounded per-file Git-history evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from otter_kr.git_provenance import BoundedHistoryProvenance


class HistoryFileEvidence(Protocol):
    """A file-level evidence item that can be serialized in a history report."""

    def to_dict(self) -> dict[str, object]: ...


@dataclass(frozen=True, slots=True)
class BoundedFileHistoryReport[FileEvidence: HistoryFileEvidence]:
    """The common provenance-and-files envelope for bounded history reports."""

    provenance: BoundedHistoryProvenance
    files: tuple[FileEvidence, ...]

    @property
    def commit_count(self) -> int:
        return self.provenance.commit_count

    @property
    def truncated(self) -> bool:
        return self.provenance.truncated

    def to_dict(self) -> dict[str, object]:
        return self.provenance.to_dict() | {"files": [file.to_dict() for file in self.files]}
