"""FastMCP transport for repository evidence tools."""

from fastmcp import FastMCP
from mcp.types import ToolAnnotations


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
        """Reject research requests until an evidence capability is explicitly admitted."""
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
