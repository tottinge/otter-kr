import asyncio

from otter_kr.provider_contract import export_contract


def test_provider_contract_is_generated_from_the_live_server() -> None:
    contract = asyncio.run(export_contract())

    assert contract["schema_version"] == "1"
    assert contract["server"] == "otter-kr"
    tools = {tool["name"]: tool for tool in contract["tools"]}

    assert {
        "research",
        "git_review_packet_file",
        "git_hotspots",
        "python_inventory",
    } <= tools.keys()
    assert tools["git_review_packet_file"]["input_schema"]["required"] == [
        "repository_root",
        "path",
        "since_unix_time",
        "limit",
    ]
    assert "ownership" not in tools
