# ADR 0005: Optimize evidence for token economy

- **Status:** accepted

## Context

The MCP serves a human user through an LLM agent. The main cost concern is unnecessary model
context, not raw computation time. The server must help the agent make well-grounded design
decisions without supplying judgments or inferred concepts.

## Decision

Evidence tools produce deterministic, compact, citeable reports. They return the smallest complete
representation of the requested observation, use stable ordering and identifiers, separate raw
facts from metadata and warnings, and support bounded queries before broad scans. Repeated facts
are referenced rather than reprinted where the contract permits. The server never compresses away
provenance merely to save tokens and never replaces evidence with a judgment. Evidence is not an
authority: every observation must include enough source coordinates, revisions, and reproduction
details for an LLM to verify it with this MCP, Git, file reads, or other available tools.

## Consequences

Report schemas should be designed for selective retrieval and progressive expansion. Golden packets
must test both content and stable serialization. We measure token/context size and traceability,
not just wall-clock performance. See KR-002, KR-017a, KR-030, KR-031, and KR-040.
