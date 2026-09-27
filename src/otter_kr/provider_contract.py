"""Generate the provider contract from the live MCP tool schemas."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Sequence
from pathlib import Path

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


def validate_examples(
    contract: dict[str, object], examples: Sequence[dict[str, object]]
) -> list[str]:
    """Return contract violations for structured provider examples."""
    tools = {tool["name"]: tool for tool in contract["tools"]}
    errors: list[str] = []
    for number, example in enumerate(examples, start=1):
        tool_name = example.get("tool")
        prefix = f"example {number}"
        if tool_name not in tools:
            errors.append(f"{prefix}: unknown tool {tool_name!r}")
            continue
        arguments = example.get("arguments", {})
        schema = tools[tool_name]["input_schema"]
        properties = set(schema.get("properties", {}))
        unknown = sorted(set(arguments) - properties)
        if unknown:
            errors.append(f"{prefix}: unknown arguments: {', '.join(unknown)}")
        missing = sorted(set(schema.get("required", [])) - set(arguments))
        if missing:
            errors.append(f"{prefix}: missing required arguments: {', '.join(missing)}")
    return errors


def main() -> None:
    """Print or validate the generated provider contract."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--validate-examples",
        type=Path,
        help="validate a JSON array of structured provider examples",
    )
    args = parser.parse_args()
    contract = asyncio.run(export_contract())
    if args.validate_examples is not None:
        examples = json.loads(args.validate_examples.read_text())
        errors = validate_examples(contract, examples)
        if errors:
            raise SystemExit("\n".join(errors))
        return
    print(json.dumps(contract, indent=2, sort_keys=True))
