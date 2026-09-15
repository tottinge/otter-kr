"""Admission registry for directly dispatched Python evidence operations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class PythonOperationSpec:
    analyzer: object
    requires_term: bool = False
    term_message: str | None = None
    catches_value_error: bool = True


class OperationRegistry:
    """Immutable lookup boundary for admitted Python operations."""

    def __init__(self, specifications: Mapping[str, PythonOperationSpec]) -> None:
        self._specifications = MappingProxyType(dict(specifications))

    def find(self, operation: str) -> PythonOperationSpec | None:
        """Return the admitted specification, or ``None`` for rejection."""
        return self._specifications.get(operation)
