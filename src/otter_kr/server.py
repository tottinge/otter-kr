"""FastMCP transport for repository evidence tools."""

from dataclasses import asdict
from pathlib import Path

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from otter_kr.python_names import find_names


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
        name="names",
        title="Find Python identifiers",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    def names(repository: str, term: str) -> dict:
        """Find exact and lexical-family identifier evidence in a local Python repository."""
        return asdict(find_names(Path(repository), term))

    return server


mcp = create_server()


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
