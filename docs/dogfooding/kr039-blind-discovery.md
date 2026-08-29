# KR-039 blind discovery study protocol

Run date: 2026-08-29
Server: `otter-kr` FastMCP 3.4.7
Corpus: `gitminer-dash`, `quizzology`, `OpenModelica`, `otter-kr` at the revisions recorded in KR-038.

## Fixed query budget

Each repository receives exactly four read-only requests, in this order:

1. `python.inventory`
2. `python.graph_topology`
3. `git.review_packet` with `since_unix_time=1`, `limit=3`
4. `python.term_change_evidence` with the blinded term `run`, `since_unix_time=1`, `limit=3`

The analyst sees only returned evidence and does not receive a predeclared hotspot, defect, or
refactoring target. The MCP output is retained separately from the analyst log.

## Claim ledger

Every analyst entry must classify itself as one of:

- **directly observed** — present in the MCP response
- **consumer-derived** — calculated from returned evidence
- **unresolved** — a question requiring another bounded query

The MCP does not emit labels such as “bad design,” “root cause,” or “refactor candidate.”
Unsupported findings are recorded as unresolved rather than discarded.

## Reproduction record

The reproducible inputs are the pinned revisions, server version, operation order, term, and
history bounds above. A second analyst can replay the four requests per repository and compare
the serialized packets before writing any interpretation.
