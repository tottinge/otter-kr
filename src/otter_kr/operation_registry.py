"""Admission registry for directly dispatched evidence operations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType


class InvalidOperationQuery(ValueError):
    """A query failed the admitted operation's shape or bounds contract."""


@dataclass(frozen=True, slots=True)
class BoundedPairQuery:
    left_path: str
    right_path: str
    since_unix_time: int
    limit: int

    @classmethod
    def create(
        cls,
        left_path: str | None,
        right_path: str | None,
        since_unix_time: int | None,
        limit: int | None,
    ) -> BoundedPairQuery:
        if left_path is None or right_path is None:
            raise InvalidOperationQuery(
                "left_path and right_path are required for git.cochange.pair."
            )
        if left_path == right_path:
            raise InvalidOperationQuery("left_path and right_path must be different files.")
        if any(
            not value
            or value.startswith("/")
            or "\\" in value
            or any(part == ".." for part in value.split("/"))
            for value in (left_path, right_path)
        ):
            raise InvalidOperationQuery("file paths must be repository-relative.")
        if since_unix_time is None or since_unix_time <= 0:
            raise InvalidOperationQuery(
                "A positive since_unix_time is required for git.cochange.pair."
            )
        if limit is None or limit <= 0:
            raise InvalidOperationQuery("A positive limit is required for git.cochange.pair.")
        return cls(left_path, right_path, since_unix_time, limit)


@dataclass(frozen=True, slots=True)
class BoundedPathQuery:
    path: str
    since_unix_time: int
    limit: int

    @classmethod
    def create(
        cls,
        path: str | None,
        since_unix_time: int | None,
        limit: int | None,
        *,
        operation: str,
        term_message: str,
        path_message: str,
    ) -> BoundedPathQuery:
        if path is None:
            raise InvalidOperationQuery(term_message)
        if (
            not path
            or path.startswith("/")
            or "\\" in path
            or any(part == ".." for part in path.split("/"))
        ):
            raise InvalidOperationQuery(path_message)
        if since_unix_time is None or since_unix_time <= 0:
            raise InvalidOperationQuery(f"A positive since_unix_time is required for {operation}.")
        if limit is None or limit <= 0:
            raise InvalidOperationQuery(f"A positive limit is required for {operation}.")
        return cls(path, since_unix_time, limit)


@dataclass(frozen=True, slots=True)
class LineOriginsQuery:
    revision: str
    path: str
    lines: tuple[int, ...]

    @classmethod
    def create(
        cls, revision: str | None, path: str | None, lines: list[int] | None
    ) -> LineOriginsQuery:
        if revision is None or path is None or not lines:
            raise InvalidOperationQuery(
                "term, path, and at least one line are required for git.line_origins."
            )
        return cls(revision, path, tuple(lines))


@dataclass(frozen=True, slots=True)
class VariableClusterQuery:
    terms: tuple[str, ...]
    since_unix_time: int | None
    limit: int | None

    @classmethod
    def create(
        cls,
        terms: list[str] | tuple[str, ...] | None,
        since_unix_time: int | None,
        limit: int | None,
    ) -> VariableClusterQuery:
        if (
            not isinstance(terms, list | tuple)
            or not 2 <= len(terms) <= 5
            or any(not isinstance(name, str) or not name.isidentifier() for name in terms)
            or len(set(terms)) != len(terms)
        ):
            raise InvalidOperationQuery("terms must contain 2 to 5 distinct Python identifiers.")
        return cls(tuple(terms), since_unix_time, limit)


@dataclass(frozen=True, slots=True)
class VariableOccurrenceQuery:
    term: str

    @classmethod
    def create(cls, term: str | None) -> VariableOccurrenceQuery:
        if term is None:
            raise InvalidOperationQuery("A term is required for python.variable_cluster.")
        return cls(term)


@dataclass(frozen=True, slots=True)
class LifecycleQuery:
    carrier: str
    since_unix_time: int | None
    limit: int | None

    @classmethod
    def create(
        cls, carrier: str | None, since_unix_time: int | None, limit: int | None
    ) -> LifecycleQuery:
        if carrier is None:
            raise InvalidOperationQuery("A carrier name is required for python.object_lifecycle.")
        return cls(carrier, since_unix_time, limit)


@dataclass(frozen=True, slots=True)
class CarrierGuardsQuery:
    carrier: str
    paths: tuple[str, ...] | None

    @classmethod
    def create(cls, carrier: str | None, path: str | None) -> CarrierGuardsQuery:
        if carrier is None:
            raise InvalidOperationQuery("A carrier name is required for python.carrier_guards.")
        if path is None:
            return cls(carrier, None)
        text = path.strip()
        candidate = Path(text)
        if not text or candidate.is_absolute() or ".." in candidate.parts:
            raise InvalidOperationQuery("path must be a repository-relative path without '..'.")
        return cls(carrier, (candidate.as_posix(),))


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


@dataclass(frozen=True, slots=True)
class LineOriginsOperationSpec:
    analyzer: object


@dataclass(frozen=True, slots=True)
class VariableClusterOperationSpec:
    cluster_analyzer: object
    occurrence_analyzer: object


@dataclass(frozen=True, slots=True)
class LifecycleOperationSpec:
    analyzer: object


@dataclass(frozen=True, slots=True)
class CarrierGuardsOperationSpec:
    analyzer: object


RegisteredOperation = (
    OperationSpec
    | BoundedTermOperationSpec
    | BoundedOperationSpec
    | BoundedPathOperationSpec
    | BoundedPairOperationSpec
    | LineOriginsOperationSpec
    | VariableClusterOperationSpec
    | LifecycleOperationSpec
    | CarrierGuardsOperationSpec
)


class OperationRegistry:
    """Immutable lookup boundary for admitted operations."""

    def __init__(self, specifications: Mapping[str, RegisteredOperation]) -> None:
        self._specifications = MappingProxyType(dict(specifications))

    def find(self, operation: str) -> RegisteredOperation | None:
        """Return the admitted specification, or ``None`` for rejection."""
        return self._specifications.get(operation)
