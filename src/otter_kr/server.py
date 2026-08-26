"""FastMCP transport for repository evidence tools."""

from dataclasses import asdict
from pathlib import Path

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from otter_kr.git_files import GitFileSourceError
from otter_kr.python_inventory import inventory_python


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
    def research(repository_root: str, operation: str) -> dict:
        """Dispatch admitted research operations and reject the remainder."""
        if operation == "python.inventory":
            try:
                report = asdict(inventory_python(Path(repository_root)))
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
            for file_evidence in report["files"]:
                if file_evidence["syntax_error"] is None:
                    del file_evidence["syntax_error"]
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
