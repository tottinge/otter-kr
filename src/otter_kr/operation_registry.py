"""Admission registry for directly dispatched evidence operations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
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
    ) -> BoundedPathQuery:
        if path is None:
            raise InvalidOperationQuery("A focus file term is required for git.cochange.file.")
        if (
            not path
            or path.startswith("/")
            or "\\" in path
            or any(part == ".." for part in path.split("/"))
        ):
            raise InvalidOperationQuery("focus_path must be repository-relative.")
        if since_unix_time is None or since_unix_time <= 0:
            raise InvalidOperationQuery(
                "A positive since_unix_time is required for git.cochange.file."
            )
        if limit is None or limit <= 0:
            raise InvalidOperationQuery("A positive limit is required for git.cochange.file.")
        return cls(path, since_unix_time, limit)


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


@dataclass(frozen=True, slots=True)
class BoundedPairOperationSpec:
    analyzer: object


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
