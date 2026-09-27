import asyncio

from otter_kr.provider_contract import export_contract, validate_examples


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


def test_provider_examples_are_checked_against_the_generated_contract() -> None:
    contract = asyncio.run(export_contract())

    assert (
        validate_examples(
            contract,
            [
                {
                    "tool": "git_review_packet_file",
                    "arguments": {
                        "repository_root": "/repo",
                        "path": "service.py",
                        "since_unix_time": 1,
                        "limit": 10,
                    },
                }
            ],
        )
        == []
    )

    errors = validate_examples(
        contract,
        [
            {
                "tool": "ownership",
                "arguments": {"repository_root": "/repo"},
            },
            {
                "tool": "git_review_packet_file",
                "arguments": {"repository_root": "/repo", "path": "service.py"},
            },
        ],
    )

    assert errors == [
        "example 1: unknown tool 'ownership'",
        "example 2: missing required arguments: limit, since_unix_time",
    ]
