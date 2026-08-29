"""Typed boundary representation for successful MCP evidence responses."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EvidenceEnvelope:
    operation: str
    query: dict[str, object]
    data: Any
    schema_version: str = "1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "status": "ok",
            "operation": self.operation,
            "query": self.query,
            "data": self.data,
        }
