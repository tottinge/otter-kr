import asyncio
from pathlib import Path

from fastmcp import Client

from otter_kr.server import create_server


def test_names_tool_returns_structured_repository_evidence(tmp_path: Path) -> None:
    (tmp_path / "orders.py").write_text("class OrderBook:\n    pass\n")
    server = create_server()

    async def call_names() -> dict:
        async with Client(server) as client:
            tools = await client.list_tools()
            assert [tool.name for tool in tools] == ["names"]
            result = await client.call_tool("names", {"repository": str(tmp_path), "term": "order"})
            return result.data

    evidence = asyncio.run(call_names())

    assert evidence["language"] == "python"
    assert evidence["occurrences"][0] == {
        "path": "orders.py",
        "line": 1,
        "column": 0,
        "name": "OrderBook",
        "kind": "class",
    }
