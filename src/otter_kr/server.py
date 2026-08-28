"""FastMCP transport for repository evidence tools."""

from dataclasses import dataclass
from pathlib import Path

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from otter_kr.git_cli_history import GitCliHistory, GitHistoryValidationError
from otter_kr.git_cochange import collect_global_cochange
from otter_kr.git_files import GitFileSourceError
from otter_kr.git_history_context import collect_git_history
from otter_kr.git_history_snapshot import collect_git_history_snapshot
from otter_kr.git_hotspots import collect_git_hotspots
from otter_kr.git_pair_cochange import collect_pair_cochange
from otter_kr.git_scoped_cochange import collect_scoped_cochange
from otter_kr.python_complexity import analyze_python_complexity
from otter_kr.python_discriminations import find_type_discriminations
from otter_kr.python_duplicates import find_duplicate_helpers
from otter_kr.python_groups import find_repeated_groups
from otter_kr.python_imports import import_python
from otter_kr.python_inventory import inventory_python
from otter_kr.python_literals import find_repeated_literals
from otter_kr.python_names import find_names
from otter_kr.python_tests import find_tests_for_symbol


@dataclass(frozen=True, slots=True)
class PythonOperationSpec:
    analyzer: object
    requires_term: bool = False
    term_message: str | None = None
    catches_value_error: bool = True


PYTHON_OPERATIONS = {
    "python.inventory": PythonOperationSpec(inventory_python),
    "python.names": PythonOperationSpec(
        find_names, requires_term=True, term_message="A term is required for python.names."
    ),
    "python.discriminations": PythonOperationSpec(
        find_type_discriminations,
        requires_term=True,
        term_message="A term is required for python.discriminations.",
    ),
    "python.tests": PythonOperationSpec(
        find_tests_for_symbol,
        requires_term=True,
        term_message="A term is required for python.tests.",
    ),
    "python.imports": PythonOperationSpec(import_python),
    "python.complexity": PythonOperationSpec(
        analyze_python_complexity, catches_value_error=False
    ),
    "python.literals": PythonOperationSpec(find_repeated_literals),
    "python.groups": PythonOperationSpec(find_repeated_groups),
    "python.duplicates": PythonOperationSpec(find_duplicate_helpers),
}


def _query(
    repository_root: str,
    term: str | None = None,
    since_unix_time: int | None = None,
    limit: int | None = None,
    left_path: str | None = None,
    right_path: str | None = None,
) -> dict:
    query = {"repository_root": repository_root}
    if term is not None:
        query["term"] = term
    if since_unix_time is not None:
        query["since_unix_time"] = since_unix_time
    if limit is not None:
        query["limit"] = limit
    if left_path is not None:
        query["left_path"] = left_path
    if right_path is not None:
        query["right_path"] = right_path
    return query


def _success(
    operation: str,
    repository_root: str,
    data: dict,
    term: str | None = None,
    since_unix_time: int | None = None,
    limit: int | None = None,
    left_path: str | None = None,
    right_path: str | None = None,
) -> dict:
    return {
        "schema_version": "1",
        "status": "ok",
        "operation": operation,
        "query": _query(repository_root, term, since_unix_time, limit, left_path, right_path),
        "data": data,
    }


def _invalid_query(
    operation: str,
    repository_root: str,
    message: str,
    *,
    term: str | None = None,
    since_unix_time: int | None = None,
    limit: int | None = None,
    left_path: str | None = None,
    right_path: str | None = None,
) -> dict:
    return {
        "schema_version": "1",
        "status": "rejected",
        "operation": operation,
        "query": _query(repository_root, term, since_unix_time, limit, left_path, right_path),
        "error": {
            "code": "invalid_query",
            "message": message,
        },
    }


def _not_a_repository(
    operation: str,
    repository_root: str,
    error: ValueError,
    term: str | None = None,
    since_unix_time: int | None = None,
    limit: int | None = None,
    left_path: str | None = None,
    right_path: str | None = None,
) -> dict:
    return {
        "schema_version": "1",
        "status": "rejected",
        "operation": operation,
        "query": _query(repository_root, term, since_unix_time, limit, left_path, right_path),
        "error": {
            "code": "not_a_repository",
            "message": str(error),
        },
    }


def _repository_access_failed(
    operation: str,
    repository_root: str,
    error: GitFileSourceError,
    term: str | None = None,
    since_unix_time: int | None = None,
    limit: int | None = None,
    left_path: str | None = None,
    right_path: str | None = None,
) -> dict:
    return {
        "schema_version": "1",
        "status": "rejected",
        "operation": operation,
        "query": _query(repository_root, term, since_unix_time, limit, left_path, right_path),
        "error": {
            "code": "repository_access_failed",
            "message": str(error),
            "command": list(error.command),
            "returncode": error.returncode,
            "stderr": error.stderr,
        },
    }


def _validate_history_bounds(
    operation: str,
    repository_root: str,
    since_unix_time: int | None,
    limit: int | None,
    *,
    term: str | None = None,
    left_path: str | None = None,
    right_path: str | None = None,
) -> dict | None:
    if since_unix_time is None or since_unix_time <= 0:
        return _invalid_query(
            operation,
            repository_root,
            f"A positive since_unix_time is required for {operation}.",
            term=term,
            since_unix_time=since_unix_time,
            limit=limit,
            left_path=left_path,
            right_path=right_path,
        )
    if limit is None or limit <= 0:
        return _invalid_query(
            operation,
            repository_root,
            f"A positive limit is required for {operation}.",
            term=term,
            since_unix_time=since_unix_time,
            limit=limit,
            left_path=left_path,
            right_path=right_path,
        )
    return None


def _run_operation(
    operation: str,
    repository_root: str,
    analyzer,
    *,
    term: str | None = None,
    since_unix_time: int | None = None,
    limit: int | None = None,
    left_path: str | None = None,
    right_path: str | None = None,
    query_term: str | None = None,
    query_since_unix_time: int | None = None,
    query_limit: int | None = None,
    query_left_path: str | None = None,
    query_right_path: str | None = None,
    require_term: bool = False,
    term_message: str | None = None,
    catches_value_error: bool = True,
) -> dict:
    query_term = term if query_term is None else query_term
    query_since_unix_time = (
        since_unix_time if query_since_unix_time is None else query_since_unix_time
    )
    query_limit = limit if query_limit is None else query_limit
    query_left_path = left_path if query_left_path is None else query_left_path
    query_right_path = right_path if query_right_path is None else query_right_path
    if require_term and term is None:
        return _invalid_query(
            operation,
            repository_root,
            term_message or "A term is required.",
            term=term,
            since_unix_time=since_unix_time,
            limit=limit,
            left_path=left_path,
            right_path=right_path,
        )

    repository = Path(repository_root)

    try:
        if term is not None:
            report = analyzer(repository, term)
        elif since_unix_time is not None or limit is not None:
            report = analyzer(repository, since_unix_time=since_unix_time, limit=limit)
        else:
            report = analyzer(repository)
    except GitHistoryValidationError as error:
        return _invalid_query(
            operation,
            repository_root,
            str(error),
            term=query_term,
            since_unix_time=query_since_unix_time,
            limit=query_limit,
            left_path=query_left_path,
            right_path=query_right_path,
        )
    except ValueError as error:
        if catches_value_error:
            return _not_a_repository(
                operation,
                repository_root,
                error,
                query_term,
                query_since_unix_time,
                query_limit,
                query_left_path,
                query_right_path,
            )
        raise
    except GitFileSourceError as error:
        return _repository_access_failed(
            operation,
            repository_root,
            error,
            term,
            since_unix_time,
            limit,
            left_path,
            right_path,
        )

    data = report.to_dict() if hasattr(report, "to_dict") else report
    return _success(
        operation,
        repository_root,
        data,
        term,
        since_unix_time,
        limit,
        left_path,
        right_path,
    )


def create_server() -> FastMCP:
    server = FastMCP(
        name="otter-kr",
        instructions=(
            "Research source repositories using deterministic evidence. "
            "Use the returned locations and counts as evidence; reserve semantic conclusions "
            "for your own reasoning."
        ),
    )

    @server.tool(
        name="research",
        title="Research a repository",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    def research(
        repository_root: str,
        operation: str,
        term: str | None = None,
        since_unix_time: int | None = None,
        limit: int | None = None,
        left_path: str | None = None,
        right_path: str | None = None,
    ) -> dict:
        """Dispatch admitted research operations and reject the remainder."""
        def run(analyzer, **kwargs):
            return _run_operation(
                operation,
                repository_root,
                analyzer,
                query_term=term,
                query_since_unix_time=since_unix_time,
                query_limit=limit,
                query_left_path=left_path,
                query_right_path=right_path,
                **kwargs,
            )

        python_spec = PYTHON_OPERATIONS.get(operation)
        if python_spec is not None:
            return run(
                python_spec.analyzer,
                term=term if python_spec.requires_term else None,
                require_term=python_spec.requires_term,
                term_message=python_spec.term_message,
                catches_value_error=python_spec.catches_value_error,
            )

        if operation == "git.history":
            rejection = _validate_history_bounds(operation, repository_root, since_unix_time, limit)
            if rejection is not None:
                return rejection
            return _run_operation(
                operation,
                repository_root,
                lambda repository, *, since_unix_time, limit: collect_git_history(
                    repository,
                    since_unix_time=since_unix_time,
                    limit=limit,
                    history=GitCliHistory(),
                ),
                since_unix_time=since_unix_time,
                limit=limit,
            )
        if operation == "git.snapshot":
            rejection = _validate_history_bounds(operation, repository_root, since_unix_time, limit)
            if rejection is not None:
                return rejection
            return _run_operation(
                operation,
                repository_root,
                lambda repository, *, since_unix_time, limit: collect_git_history_snapshot(
                    repository,
                    since_unix_time=since_unix_time,
                    limit=limit,
                    changes=GitCliHistory(),
                ),
                since_unix_time=since_unix_time,
                limit=limit,
            )
        if operation == "git.hotspots":
            rejection = _validate_history_bounds(operation, repository_root, since_unix_time, limit)
            if rejection is not None:
                return rejection
            return _run_operation(
                operation,
                repository_root,
                lambda repository, *, since_unix_time, limit: collect_git_hotspots(
                    repository,
                    since_unix_time=since_unix_time,
                    limit=limit,
                    changes=GitCliHistory(),
                ),
                since_unix_time=since_unix_time,
                limit=limit,
            )
        if operation == "git.cochange":
            rejection = _validate_history_bounds(operation, repository_root, since_unix_time, limit)
            if rejection is not None:
                return rejection
            return _run_operation(
                operation,
                repository_root,
                lambda repository, *, since_unix_time, limit: collect_global_cochange(
                    repository,
                    since_unix_time=since_unix_time,
                    limit=limit,
                    changes=GitCliHistory(),
                ),
                since_unix_time=since_unix_time,
                limit=limit,
            )
        if operation == "git.cochange.file":
            if term is None:
                return _invalid_query(
                    operation,
                    repository_root,
                    "A focus file term is required for git.cochange.file.",
                    term=term,
                    since_unix_time=since_unix_time,
                    limit=limit,
                )
            if (
                not term
                or term.startswith("/")
                or "\\" in term
                or any(part == ".." for part in term.split("/"))
            ):
                return _invalid_query(
                    operation,
                    repository_root,
                    "focus_path must be repository-relative.",
                    term=term,
                    since_unix_time=since_unix_time,
                    limit=limit,
                )
            if since_unix_time is None or since_unix_time <= 0:
                return _invalid_query(
                    operation,
                    repository_root,
                    "A positive since_unix_time is required for git.cochange.file.",
                    term=term,
                    since_unix_time=since_unix_time,
                    limit=limit,
                )
            if limit is None or limit <= 0:
                return _invalid_query(
                    operation,
                    repository_root,
                    "A positive limit is required for git.cochange.file.",
                    term=term,
                    since_unix_time=since_unix_time,
                    limit=limit,
                )
            return _run_operation(
                operation,
                repository_root,
                lambda repository, focus_path: collect_scoped_cochange(
                    repository,
                    focus_path,
                    since_unix_time=since_unix_time,
                    limit=limit,
                    changes=GitCliHistory(),
                ),
                term=term,
                since_unix_time=since_unix_time,
                limit=limit,
            )
        if operation == "git.cochange.pair":
            if left_path is None or right_path is None:
                return _invalid_query(
                    operation,
                    repository_root,
                    "left_path and right_path are required for git.cochange.pair.",
                    since_unix_time=since_unix_time,
                    limit=limit,
                    left_path=left_path,
                    right_path=right_path,
                )
            if since_unix_time is None or since_unix_time <= 0:
                return _invalid_query(
                    operation,
                    repository_root,
                    "A positive since_unix_time is required for git.cochange.pair.",
                    since_unix_time=since_unix_time,
                    limit=limit,
                    left_path=left_path,
                    right_path=right_path,
                )
            if limit is None or limit <= 0:
                return _invalid_query(
                    operation,
                    repository_root,
                    "A positive limit is required for git.cochange.pair.",
                    since_unix_time=since_unix_time,
                    limit=limit,
                    left_path=left_path,
                    right_path=right_path,
                )
            if left_path == right_path:
                return _invalid_query(
                    operation,
                    repository_root,
                    "left_path and right_path must be different files.",
                    since_unix_time=since_unix_time,
                    limit=limit,
                    left_path=left_path,
                    right_path=right_path,
                )
            if (
                left_path.startswith("/")
                or right_path.startswith("/")
                or "\\" in left_path
                or "\\" in right_path
                or any(part == ".." for part in left_path.split("/"))
                or any(part == ".." for part in right_path.split("/"))
            ):
                return _invalid_query(
                    operation,
                    repository_root,
                    "file paths must be repository-relative.",
                    since_unix_time=since_unix_time,
                    limit=limit,
                    left_path=left_path,
                    right_path=right_path,
                )
            return _run_operation(
                operation,
                repository_root,
                lambda repository, **_: collect_pair_cochange(
                    repository,
                    left_path,
                    right_path,
                    since_unix_time=since_unix_time,
                    limit=limit,
                    changes=GitCliHistory(),
                ),
                since_unix_time=since_unix_time,
                limit=limit,
                left_path=left_path,
                right_path=right_path,
            )
        return {
            "schema_version": "1",
            "status": "rejected",
            "operation": operation,
            "query": _query(repository_root),
            "error": {
                "code": "not_implemented",
                "message": "No repository research capabilities have been admitted yet.",
            },
        }

    return server


mcp = create_server()


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
