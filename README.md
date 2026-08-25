# otter-kr

Deterministic source-repository evidence for coding agents, exposed through FastMCP.
The evidence layer answers what exists in a repository; the calling agent remains responsible
for interpretation and engineering judgment.

## Current capability

`names` scans Python source with the standard-library AST without importing or executing target
code. It finds exact names and lexical relatives across snake case, camel case, and Pascal case.
Every occurrence includes its repository-relative path, line, column, and syntactic role. Files
that cannot be parsed are reported as evidence rather than silently discarded.

This is the first vertical slice. Historical co-change, dependencies, repeated parameters,
literals, duplication, and weighted neighborhoods remain on the research roadmap described in
`potential_specifications.yaml`.

## Develop with uv

Install the pinned environment and run all checks:

```shell
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Run the stdio server:

```shell
uv run otter-kr
```

An MCP client can launch it from any directory with an entry like this (replace the path):

```json
{
  "mcpServers": {
    "otter-kr": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/otter-kr",
        "run",
        "otter-kr"
      ]
    }
  }
}
```

Call `names` with `repository` set to an absolute or runtime-relative repository directory and
`term` set to an identifier or identifier fragment, such as `payment` or `payment_processor`.

## Design boundary

Repository analysis lives in framework-independent modules under `src/otter_kr`. The MCP server
only validates transport inputs and presents structured results. Language is explicit in each
report, leaving room for analyzers for other languages without changing the evidence contract.
