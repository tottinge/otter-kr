"""FastMCP transport for repository evidence tools."""

from pathlib import Path

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from otter_kr.git_files import GitFileSourceError
from otter_kr.python_complexity import analyze_python_complexity
from otter_kr.python_discriminations import find_type_discriminations
from otter_kr.python_duplicates import find_duplicate_helpers
from otter_kr.python_groups import find_repeated_groups
from otter_kr.python_imports import import_python
from otter_kr.python_inventory import inventory_python
from otter_kr.python_literals import find_repeated_literals
from otter_kr.python_names import find_names
from otter_kr.python_tests import find_tests_for_symbol


def _query(repository_root: str, term: str | None = None) -> dict:
    query = {"repository_root": repository_root}
    if term is not None:
        query["term"] = term
    return query


def _success(operation: str, repository_root: str, data: dict, term: str | None = None) -> dict:
    return {
        "schema_version": "1",
        "status": "ok",
        "operation": operation,
        "query": _query(repository_root, term),
        "data": data,
    }


def _invalid_query(operation: str, repository_root: str, message: str) -> dict:
    return {
        "schema_version": "1",
        "status": "rejected",
        "operation": operation,
        "query": _query(repository_root),
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
) -> dict:
    return {
        "schema_version": "1",
        "status": "rejected",
        "operation": operation,
        "query": _query(repository_root, term),
        "error": {
            "code": "repository_access_failed",
            "message": str(error),
            "command": list(error.command),
            "returncode": error.returncode,
            "stderr": error.stderr,
        },
    }


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
    def research(repository_root: str, operation: str, term: str | None = None) -> dict:
        """Dispatch admitted research operations and reject the remainder."""
        if operation == "python.inventory":
            try:
                report = inventory_python(Path(repository_root)).to_dict()
            except ValueError as error:
                return _not_a_repository(operation, repository_root, error)
            except GitFileSourceError as error:
                return _repository_access_failed(operation, repository_root, error)
            return _success(operation, repository_root, report)
        if operation == "python.names":
            if term is None:
                return _invalid_query(
                    operation, repository_root, "A term is required for python.names."
                )
            try:
                report = find_names(Path(repository_root), term)
            except ValueError as error:
                return _not_a_repository(operation, repository_root, error)
            except GitFileSourceError as error:
                return _repository_access_failed(operation, repository_root, error, term)
            return _success(operation, repository_root, report.to_dict(), term)
        if operation == "python.discriminations":
            if term is None:
                return _invalid_query(
                    operation,
                    repository_root,
                    "A term is required for python.discriminations.",
                )
            try:
                report = find_type_discriminations(Path(repository_root), term)
            except ValueError as error:
                return _not_a_repository(operation, repository_root, error)
            except GitFileSourceError as error:
                return _repository_access_failed(operation, repository_root, error, term)
            return _success(operation, repository_root, report.to_dict(), term)
        if operation == "python.tests":
            if term is None:
                return _invalid_query(
                    operation,
                    repository_root,
                    "A term is required for python.tests.",
                )
            try:
                report = find_tests_for_symbol(Path(repository_root), term)
            except ValueError as error:
                return _not_a_repository(operation, repository_root, error)
            except GitFileSourceError as error:
                return _repository_access_failed(operation, repository_root, error, term)
            return _success(operation, repository_root, report.to_dict(), term)
        if operation == "python.imports":
            try:
                report = import_python(Path(repository_root)).to_dict()
            except ValueError as error:
                return _not_a_repository(operation, repository_root, error)
            except GitFileSourceError as error:
                return _repository_access_failed(operation, repository_root, error)
            return _success(operation, repository_root, report)
        if operation == "python.complexity":
            try:
                report = analyze_python_complexity(Path(repository_root)).to_dict()
            except GitFileSourceError as error:
                return _repository_access_failed(operation, repository_root, error)
            return _success(operation, repository_root, report)
        if operation == "python.literals":
            try:
                report = find_repeated_literals(Path(repository_root)).to_dict()
            except ValueError as error:
                return _not_a_repository(operation, repository_root, error)
            except GitFileSourceError as error:
                return _repository_access_failed(operation, repository_root, error)
            return _success(operation, repository_root, report)
        if operation == "python.groups":
            try:
                report = find_repeated_groups(Path(repository_root)).to_dict()
            except ValueError as error:
                return _not_a_repository(operation, repository_root, error)
            except GitFileSourceError as error:
                return _repository_access_failed(operation, repository_root, error)
            return _success(operation, repository_root, report)
        if operation == "python.duplicates":
            try:
                report = find_duplicate_helpers(Path(repository_root)).to_dict()
            except ValueError as error:
                return _not_a_repository(operation, repository_root, error)
            except GitFileSourceError as error:
                return _repository_access_failed(operation, repository_root, error)
            return _success(operation, repository_root, report)
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
