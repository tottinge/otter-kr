"""FastMCP transport for repository evidence tools."""

from pathlib import Path

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from otter_kr.git_files import GitFileSourceError
from otter_kr.python_imports import import_python
from otter_kr.python_inventory import inventory_python
from otter_kr.python_names import find_names


def _not_a_repository(operation: str, repository_root: str, error: ValueError) -> dict:
    return {
        "schema_version": "1",
        "status": "rejected",
        "operation": operation,
        "query": {"repository_root": repository_root},
        "error": {
            "code": "not_a_repository",
            "message": str(error),
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
                return {
                    "schema_version": "1",
                    "status": "rejected",
                    "operation": operation,
                    "query": {"repository_root": repository_root},
                    "error": {
                        "code": "repository_access_failed",
                        "message": str(error),
                        "command": list(error.command),
                        "returncode": error.returncode,
                        "stderr": error.stderr,
                    },
                }
            return {
                "schema_version": "1",
                "status": "ok",
                "operation": operation,
                "query": {"repository_root": repository_root},
                "data": report,
            }
        if operation == "python.names":
            if term is None:
                return {
                    "schema_version": "1",
                    "status": "rejected",
                    "operation": operation,
                    "query": {"repository_root": repository_root},
                    "error": {
                        "code": "invalid_query",
                        "message": "A term is required for python.names.",
                    },
                }
            try:
                report = find_names(Path(repository_root), term)
            except ValueError as error:
                return _not_a_repository(operation, repository_root, error)
            except GitFileSourceError as error:
                return {
                    "schema_version": "1",
                    "status": "rejected",
                    "operation": operation,
                    "query": {"repository_root": repository_root, "term": term},
                    "error": {
                        "code": "repository_access_failed",
                        "message": str(error),
                        "command": list(error.command),
                        "returncode": error.returncode,
                        "stderr": error.stderr,
                    },
                }
            return {
                "schema_version": "1",
                "status": "ok",
                "operation": operation,
                "query": {"repository_root": repository_root, "term": term},
                "data": report.to_dict(),
            }
        if operation == "python.imports":
            try:
                report = import_python(Path(repository_root)).to_dict()
            except ValueError as error:
                return _not_a_repository(operation, repository_root, error)
            except GitFileSourceError as error:
                return {
                    "schema_version": "1",
                    "status": "rejected",
                    "operation": operation,
                    "query": {"repository_root": repository_root},
                    "error": {
                        "code": "repository_access_failed",
                        "message": str(error),
                        "command": list(error.command),
                        "returncode": error.returncode,
                        "stderr": error.stderr,
                    },
                }
            return {
                "schema_version": "1",
                "status": "ok",
                "operation": operation,
                "query": {"repository_root": repository_root},
                "data": report,
            }
        return {
            "schema_version": "1",
            "status": "rejected",
            "operation": operation,
            "query": {"repository_root": repository_root},
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
