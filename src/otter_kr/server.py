"""FastMCP transport for repository evidence tools."""

from pathlib import Path

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from otter_kr.git_cli_history import GitCliHistory, GitHistoryValidationError
from otter_kr.git_cochange import collect_global_cochange
from otter_kr.git_files import GitFileSourceError
from otter_kr.git_history_context import collect_git_history
from otter_kr.git_hotspots import collect_git_hotspots
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


def _query(
    repository_root: str,
    term: str | None = None,
    since_unix_time: int | None = None,
    limit: int | None = None,
) -> dict:
    query = {"repository_root": repository_root}
    if term is not None:
        query["term"] = term
    if since_unix_time is not None:
        query["since_unix_time"] = since_unix_time
    if limit is not None:
        query["limit"] = limit
    return query


def _success(
    operation: str,
    repository_root: str,
    data: dict,
    term: str | None = None,
    since_unix_time: int | None = None,
    limit: int | None = None,
) -> dict:
    return {
        "schema_version": "1",
        "status": "ok",
        "operation": operation,
        "query": _query(repository_root, term, since_unix_time, limit),
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
) -> dict:
    return {
        "schema_version": "1",
        "status": "rejected",
        "operation": operation,
        "query": _query(repository_root, term, since_unix_time, limit),
        "error": {
            "code": "invalid_query",
            "message": message,
        },
    }


def _not_a_repository(operation: str, repository_root: str, error: ValueError) -> dict:
    return {
        "schema_version": "1",
        "status": "rejected",
        "operation": operation,
        "query": _query(repository_root),
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
) -> dict:
    return {
        "schema_version": "1",
        "status": "rejected",
        "operation": operation,
        "query": _query(repository_root, term, since_unix_time, limit),
        "error": {
            "code": "repository_access_failed",
            "message": str(error),
            "command": list(error.command),
            "returncode": error.returncode,
            "stderr": error.stderr,
        },
    }


def _run_operation(
    operation: str,
    repository_root: str,
    analyzer,
    *,
    term: str | None = None,
    since_unix_time: int | None = None,
    limit: int | None = None,
    require_term: bool = False,
    term_message: str | None = None,
    catches_value_error: bool = True,
) -> dict:
    if require_term and term is None:
        return _invalid_query(
            operation,
            repository_root,
            term_message or "A term is required.",
            term=term,
            since_unix_time=since_unix_time,
            limit=limit,
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
            since_unix_time=since_unix_time,
            limit=limit,
        )
    except ValueError as error:
        if catches_value_error:
            return _not_a_repository(operation, repository_root, error)
        raise
    except GitFileSourceError as error:
        return _repository_access_failed(
            operation,
            repository_root,
            error,
            term,
            since_unix_time,
            limit,
        )

    data = report.to_dict() if hasattr(report, "to_dict") else report
    return _success(operation, repository_root, data, term, since_unix_time, limit)


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
    ) -> dict:
        """Dispatch admitted research operations and reject the remainder."""
        if operation == "python.inventory":
            return _run_operation(operation, repository_root, inventory_python)
        if operation == "python.names":
            return _run_operation(
                operation,
                repository_root,
                find_names,
                term=term,
                require_term=True,
                term_message="A term is required for python.names.",
            )
        if operation == "python.discriminations":
            return _run_operation(
                operation,
                repository_root,
                find_type_discriminations,
                term=term,
                require_term=True,
                term_message="A term is required for python.discriminations.",
            )
        if operation == "python.tests":
            return _run_operation(
                operation,
                repository_root,
                find_tests_for_symbol,
                term=term,
                require_term=True,
                term_message="A term is required for python.tests.",
            )
        if operation == "python.imports":
            return _run_operation(operation, repository_root, import_python)
        if operation == "python.complexity":
            return _run_operation(
                operation,
                repository_root,
                analyze_python_complexity,
                catches_value_error=False,
            )
        if operation == "python.literals":
            return _run_operation(operation, repository_root, find_repeated_literals)
        if operation == "python.groups":
            return _run_operation(operation, repository_root, find_repeated_groups)
        if operation == "python.duplicates":
            return _run_operation(operation, repository_root, find_duplicate_helpers)
        if operation == "git.history":
            if since_unix_time is None or since_unix_time <= 0:
                return _invalid_query(
                    operation,
                    repository_root,
                    "A positive since_unix_time is required for git.history.",
                    since_unix_time=since_unix_time,
                    limit=limit,
                )
            if limit is None or limit <= 0:
                return _invalid_query(
                    operation,
                    repository_root,
                    "A positive limit is required for git.history.",
                    since_unix_time=since_unix_time,
                    limit=limit,
                )
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
        if operation == "git.hotspots":
            if since_unix_time is None or since_unix_time <= 0:
                return _invalid_query(
                    operation,
                    repository_root,
                    "A positive since_unix_time is required for git.hotspots.",
                    since_unix_time=since_unix_time,
                    limit=limit,
                )
            if limit is None or limit <= 0:
                return _invalid_query(
                    operation,
                    repository_root,
                    "A positive limit is required for git.hotspots.",
                    since_unix_time=since_unix_time,
                    limit=limit,
                )
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
            if since_unix_time is None or since_unix_time <= 0:
                return _invalid_query(
                    operation,
                    repository_root,
                    "A positive since_unix_time is required for git.cochange.",
                    since_unix_time=since_unix_time,
                    limit=limit,
                )
            if limit is None or limit <= 0:
                return _invalid_query(
                    operation,
                    repository_root,
                    "A positive limit is required for git.cochange.",
                    since_unix_time=since_unix_time,
                    limit=limit,
                )
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
