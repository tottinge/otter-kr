"""Generate the provider contract from the live MCP tool schemas."""

from __future__ import annotations

import asyncio
import json

from fastmcp import Client

from otter_kr.server import create_server


async def export_contract() -> dict[str, object]:
    """Return the machine-readable contract exposed by the in-process MCP server."""
    async with Client(create_server()) as client:
        tools = await client.list_tools()

    return {
        "schema_version": "1",
        "server": "otter-kr",
        "tools": [
            {
                "name": tool.name,
                "title": tool.title,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in sorted(tools, key=lambda candidate: candidate.name)
        ],
    }


def main() -> None:
    """Print the generated provider contract as stable JSON."""
    print(json.dumps(asyncio.run(export_contract()), indent=2, sort_keys=True))
