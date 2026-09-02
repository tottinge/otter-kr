# otter-kr

Deterministic source-repository evidence for coding agents, exposed through FastMCP.
The evidence layer answers what exists in a repository; the calling agent remains responsible
for interpretation and engineering judgment.

## Current capability

One stateless `research` tool dispatches deterministic Python and Git evidence operations. Current
Python evidence covers tracked-file inventory and parse health, names, imports, tests, complexity,
repeated literals and groups, structural duplicates, type discriminations, exact/structural/
historical/behavioral neighborhoods, graph topology, and seed-scoped carrier guards. Composite
operations project seed evidence, term-change evidence, representation inventories, and review
packets without adding design judgments.

Git evidence covers bounded history, snapshots, hotspots, normalized co-change at global/file/pair
scope, branch additions, temporal and commit-message distributions, topic commits and hunks,
first-parent topic walks and families, rename identity, and line origins. Reports retain explicit
query bounds, stable ordering, source locations, warnings, and provenance. Unsupported or invalid
requests return structured rejections rather than widening the analysis silently.

The product remains Python-only and evidence-only: it does not import or execute target code,
infer semantic concepts, assign quality scores, or recommend refactorings. The detailed admission
boundaries and remaining research work live in `BACKLOG.md`.

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

Call `research` with `repository_root` set to an absolute or runtime-relative repository directory,
an admitted `operation`, and that operation's explicit query fields. For example,
`python.names` requires `term`, while bounded Git operations require `since_unix_time` and `limit`.

## Design boundary

Repository analysis lives in framework-independent modules under `src/otter_kr`. The MCP server
only validates transport inputs and presents structured results. Language is explicit in each
report, leaving room for analyzers for other languages without changing the evidence contract.
