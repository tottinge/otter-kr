# otter-kr

Deterministic source-repository evidence for coding agents, exposed through FastMCP.
The evidence layer answers what exists in a repository; the calling agent remains responsible
for interpretation and engineering judgment.

## Current capability

Operation-specific stateless tools expose deterministic Python and Git evidence operations. The
legacy `research` tool remains as a compatibility router for clients that cannot yet select typed
tools directly. Current Python evidence covers tracked-file inventory and parse health, names, imports, tests, complexity,
repeated literals and groups, structural duplicates, type discriminations, exact/structural/
historical/behavioral neighborhoods, graph topology, seed-scoped carrier guards, and external
field affinity. Composite operations project seed evidence, term-change evidence, representation
inventories, and review
packets without adding design judgments.

Git evidence covers bounded history, snapshots, hotspots, normalized co-change at global/file/pair
scope, branch additions, temporal and commit-message distributions, topic commits and hunks,
first-parent topic walks and families, rename identity, and line origins. Reports retain explicit
query bounds, stable ordering, source locations, warnings, and provenance. Unsupported or invalid
requests return structured rejections rather than widening the analysis silently.

The product remains Python-only and evidence-only: it does not import or execute target code,
infer semantic concepts, assign quality scores, or recommend refactorings. The detailed admission
boundaries and remaining research work live in `BACKLOG.md`.

## Evidence layer for refactoring skills

otter-kr is intended to provide citeable, deterministic evidence for
[otter-skills](https://github.com/tottinge/otter-skills) and other refactoring skills. It reports
facts such as locations, counts, relationships, and history; an LLM or human uses those facts to
make and validate design decisions. The MCP deliberately does not replace the reasoning,
representation, testing, or refactoring skills that consume its evidence.

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

Prefer the operation-specific tools, such as `python_inventory`, `python_names`, and `git_history`.
Each typed tool names its required inputs directly: `python_names` requires `term`, while bounded
Git tools require `since_unix_time` and `limit`. The compatibility `research` router accepts the
same admitted operations and fields for older clients.

## Design boundary

Repository analysis lives in framework-independent modules under `src/otter_kr`. The MCP server
only validates transport inputs and presents structured results. Language is explicit in each
report, leaving room for analyzers for other languages without changing the evidence contract.
