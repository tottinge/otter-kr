import asyncio

from fastmcp import Client

from otter_kr.server import create_server


def test_research_tool_rejects_every_request_with_stable_shape() -> None:
    server = create_server()

    async def call_research() -> tuple[list[str], dict]:
        async with Client(server) as client:
            tools = await client.list_tools()
            result = await client.call_tool(
                "research",
                {
                    "repository_root": "/definitely/not/a/repository",
                    "operation": "python.names",
                },
            )
            return [tool.name for tool in tools], result.data

    tool_names, rejection = asyncio.run(call_research())

    assert tool_names == ["research"]
    assert rejection == {
        "status": "rejected",
        "repository_root": "/definitely/not/a/repository",
        "operation": "python.names",
        "error": {
            "code": "not_implemented",
            "message": "No repository research capabilities have been admitted yet.",
        },
    }


def test_research_tool_calls_are_independent() -> None:
    server = create_server()

    async def call_research(repository_root: str, operation: str) -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {"repository_root": repository_root, "operation": operation},
            )
            return result.data

    first = asyncio.run(call_research("/repo/one", "python.names"))
    second = asyncio.run(call_research("/repo/two", "git.affinity"))

    assert first == {
        "status": "rejected",
        "repository_root": "/repo/one",
        "operation": "python.names",
        "error": {
            "code": "not_implemented",
            "message": "No repository research capabilities have been admitted yet.",
        },
    }
    assert second == {
        "status": "rejected",
        "repository_root": "/repo/two",
        "operation": "git.affinity",
        "error": {
            "code": "not_implemented",
            "message": "No repository research capabilities have been admitted yet.",
        },
    }
