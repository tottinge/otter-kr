"""Admission registry for directly dispatched evidence operations."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType


class InvalidOperationQuery(ValueError):
    """A query failed the admitted operation's shape or bounds contract."""


@dataclass(frozen=True, slots=True)
class ResearchRequest:
    """The complete, transport-independent input to one research operation."""

    repository_root: str
    operation: str
    term: str | None = None
    terms: tuple[str, ...] | None = None
    since_unix_time: int | None = None
    limit: int | None = None
    left_path: str | None = None
    right_path: str | None = None
    path: str | None = None
    lines: tuple[int, ...] | None = None

    @classmethod
    def create(
        cls,
        repository_root: str,
        operation: str,
        *,
        term: str | None = None,
        terms: list[str] | tuple[str, ...] | None = None,
        since_unix_time: int | None = None,
        limit: int | None = None,
        left_path: str | None = None,
        right_path: str | None = None,
        path: str | None = None,
        lines: list[int] | tuple[int, ...] | None = None,
    ) -> ResearchRequest:
        """Normalize MCP tool arguments before operation-specific admission."""
        return cls(
            repository_root=repository_root,
            operation=operation,
            term=term,
            terms=tuple(terms) if terms is not None else None,
            since_unix_time=since_unix_time,
            limit=limit,
            left_path=left_path,
            right_path=right_path,
            path=path,
            lines=tuple(lines) if lines is not None else None,
        )


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

    def execute(
        self,
        request: ResearchRequest,
        runner: Callable[..., object],
        reject: Callable[..., object],
    ) -> object:
        """Run this bounded term operation through shared query handling."""
        if request.term is None:
            return reject(request.operation, request.repository_root, self.term_message)
        return runner(
            request.operation,
            request.repository_root,
            self.analyzer,
            term=request.term,
            since_unix_time=request.since_unix_time,
            limit=request.limit,
            pass_bounds_with_term=True,
        )


@dataclass(frozen=True, slots=True)
class BoundedOperationSpec:
    analyzer: object

    def execute(self, request: ResearchRequest, runner: Callable[..., object]) -> object:
        """Run this bounded operation through the shared envelope boundary."""
        return runner(
            request.operation,
            request.repository_root,
            self.analyzer,
            since_unix_time=request.since_unix_time,
            limit=request.limit,
        )


@dataclass(frozen=True, slots=True)
class BoundedPathOperationSpec:
    analyzer: object
    term_message: str
    path_message: str

    def execute(
        self,
        request: ResearchRequest,
        runner: Callable[..., object],
        reject: Callable[..., object],
    ) -> object:
        """Admit and run a bounded repository-relative path query."""
        try:
            query = BoundedPathQuery.create(
                request.term,
                request.since_unix_time,
                request.limit,
                operation=request.operation,
                term_message=self.term_message,
                path_message=self.path_message,
            )
        except ValueError as error:
            return reject(
                request.operation,
                request.repository_root,
                str(error),
                term=request.term,
                since_unix_time=request.since_unix_time,
                limit=request.limit,
            )
        return runner(
            request.operation,
            request.repository_root,
            self.analyzer,
            term=query.path,
            since_unix_time=query.since_unix_time,
            limit=query.limit,
            pass_bounds_with_term=True,
        )


@dataclass(frozen=True, slots=True)
class BoundedPairOperationSpec:
    analyzer: object

    def execute(
        self,
        request: ResearchRequest,
        runner: Callable[..., object],
        reject: Callable[..., object],
    ) -> object:
        """Admit and run a bounded pair-of-paths query."""
        try:
            query = BoundedPairQuery.create(
                request.left_path,
                request.right_path,
                request.since_unix_time,
                request.limit,
            )
        except ValueError as error:
            return reject(
                request.operation,
                request.repository_root,
                str(error),
                since_unix_time=request.since_unix_time,
                limit=request.limit,
                left_path=request.left_path,
                right_path=request.right_path,
            )
        return runner(
            request.operation,
            request.repository_root,
            self.analyzer,
            since_unix_time=query.since_unix_time,
            limit=query.limit,
            left_path=query.left_path,
            right_path=query.right_path,
            pass_pair_paths=True,
        )


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
