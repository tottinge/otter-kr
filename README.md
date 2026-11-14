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

### Python structural complexity

Call `python_structural_complexity` with a `repository_root` and a `measure`. The report
gives a count and source location for each tracked Python function and method.
Each nested function is measured in its own row. Docstrings, decorators, defaults, and
signature annotations are outside the measured body.

- `operands` counts distinct declared parameters, body names, full dotted names, and
  typed literal values. A lambda or a dotted chain rooted in an expression such as
  `items[0].name` receives a function diagnostic.
- `operations` counts occurrences of assignments, arithmetic, Boolean and comparison
  operators, calls, attribute and subscript lookups, and collection displays.
  Augmented assignment contributes two operations. Each attribute hop contributes
  one. A collection display and a constructor call each contribute one operation
  in addition to any operations in their children. Control flow such as `if` and
  `return` contributes through its expressions and bodies. Ordinary `try` statements
  likewise contribute through their clauses. A `raise` contributes through its exception
  and cause expressions. A comprehension contributes one operation at the enclosing
  scope. Loops and other unadmitted syntax produce a function diagnostic.
- `paths` starts at one for straight-line code, ending a route at a return,
  an explicit raise, or fall-through. An `if` has two alternatives even with a compound condition.
  A loop contributes a zero-iteration and a populated alternative. A comprehension
  contributes one continuation at the enclosing scope. Two successive simple loops give three structural
  paths, and two nested loops give four. Each reachable sequential region adds
  its alternatives beyond the first, and each loop doubles the count for its body.
  An iterable expression contributes its alternatives before that loop's choice.
  A `try` with ordinary `except` clauses counts its body and each handler as
  structural alternatives. A following statement is reachable if any of those
  clauses can fall through. The measure does not resolve exception types or
  infer which expressions can raise. A conditional expression outside a comprehension
  adds two alternatives, with any choices in its condition counted before those alternatives.
  Loop `else`, `try` with `else` or `finally`, and `except*`
  produce a function diagnostic.

### Python function and class profiles

Pass an absolute `repository_root`, a repository-relative path to a tracked Python file,
and a dotted `qualified_name`. Use names such as `Class.method` or `outer.inner` for
nested definitions. These examples use the otter-kr checkout as the target repository.

```json
[
  {
    "tool": "python_function_profile",
    "arguments": {
      "repository_root": "/absolute/path/to/otter-kr",
      "path": "src/otter_kr/review_packet.py",
      "qualified_name": "collect_review_packet"
    }
  },
  {
    "tool": "python_function_profiles",
    "arguments": {
      "repository_root": "/absolute/path/to/otter-kr",
      "targets": [
        {"path": "src/otter_kr/server.py", "qualified_name": "_run_operation"},
        {"path": "src/otter_kr/python_graph.py", "qualified_name": "build_python_import_graph"}
      ]
    }
  },
  {
    "tool": "python_class_profile",
    "arguments": {
      "repository_root": "/absolute/path/to/otter-kr",
      "path": "src/otter_kr/evidence_graph.py",
      "qualified_name": "EvidenceGraph",
      "limit": 4
    }
  }
]
```

- A function profile includes its source span, cyclomatic complexity, primitive density
  from parameter annotations, and structural measures for operands, operations, and paths.
  It also reports locations for explicit `if` predicates, comparisons, and attribute reads
  and writes in the function body. Each site list shows up to 16 entries, with a total
  count and a truncation flag. Comprehension sites include source spans, counts of
  generators and filters, and flags for conditional results and nested comprehensions.
  These observations describe the comprehension's internal structure alongside the
  enclosing operation and path counts.
- A batch accepts 1–16 targets, parses each selected file once, and returns one profile per
  target in request order. Check each profile's `match_status` for missing, ambiguous,
  or unavailable definitions.
- A class profile includes its source span and primitive density for annotations in the
  class body. It profiles direct methods in source order, with a default limit of 8
  and a maximum of 16. Each method includes up to 16 observed read or write sites
  for directly annotated fields accessed through the receiver's name. Check
  `methods_truncated` and each method's field-access truncation flag.

A structural measure returns a diagnostic when its syntax rules cannot produce a count.
Other measurements in the same profile can still be available. For a change review, use
`git_review_packet_files` with the changed paths, a history start timestamp
(`since_unix_time`), and a `limit` to get file-level context. Then use
`python_function_profiles` to inspect the changed definitions and follow their source
locations. Check the packet's history and dependency truncation flags when using that
context to support a finding.

## Evidence layer for refactoring skills

otter-kr is intended to provide citeable, deterministic evidence for
[otter-skills](https://github.com/tottinge/otter-skills) and other refactoring skills. It reports
facts such as locations, counts, relationships, and history; an LLM or human uses those facts to
make and validate design decisions. The MCP deliberately does not replace the reasoning,
representation, testing, or refactoring skills that consume its evidence.

The [refactoring situation catalog](docs/refactoring-catalog.md) maps the current
evidence operations to hypotheses and otter-skills hand-offs without turning
heuristics into automatic smell labels.

## Develop with uv

Install the pinned environment and run all checks:

```shell
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Generate the provider contract directly from the live MCP schemas when a client cannot use
runtime tool discovery:

```shell
uv run otter-kr-contract > /tmp/otter-kr-contract.json
```

This is generated output, not a second interface definition. Do not hand-edit a provider guide's
tool names or fields; consume this contract or connect the provider directly to the MCP server.
Provider projects may keep curated workflow examples as JSON tests and validate them with
`uv run otter-kr-contract --validate-examples provider-examples.json`; unknown tools, fields, and
missing required arguments then fail in CI.

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
