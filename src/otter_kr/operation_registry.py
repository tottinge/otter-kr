"""Admission registry for directly dispatched evidence operations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class OperationSpec:
    analyzer: object
    requires_term: bool = False
    term_message: str | None = None
    catches_value_error: bool = True
    echo_unused_query_fields: bool = True


@dataclass(frozen=True, slots=True)
class BoundedTermOperationSpec:
    analyzer: object
    term_message: str


@dataclass(frozen=True, slots=True)
class BoundedOperationSpec:
    analyzer: object


@dataclass(frozen=True, slots=True)
class BoundedPathOperationSpec:
    analyzer: object
    term_message: str
    path_message: str


@dataclass(frozen=True, slots=True)
class BoundedPairOperationSpec:
    analyzer: object
    pair_message: str
    path_message: str


RegisteredOperation = (
    OperationSpec
    | BoundedTermOperationSpec
    | BoundedOperationSpec
    | BoundedPathOperationSpec
    | BoundedPairOperationSpec
)


class OperationRegistry:
    """Immutable lookup boundary for admitted operations."""

    def __init__(self, specifications: Mapping[str, RegisteredOperation]) -> None:
        self._specifications = MappingProxyType(dict(specifications))

    def find(self, operation: str) -> RegisteredOperation | None:
        """Return the admitted specification, or ``None`` for rejection."""
        return self._specifications.get(operation)
