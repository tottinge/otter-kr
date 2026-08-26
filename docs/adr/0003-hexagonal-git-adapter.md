# ADR 0003: Use capability-shaped ports for Git evidence

- **Status:** accepted

## Context

History tools need different Git capabilities, and we want to compare implementations without
coupling MCP handlers or report schemas to one library. The Git executable provides the most direct
behavioral reference for the initial implementation.

## Decision

Research tools depend on small Python protocols that express their evidence needs. An infrastructure
adapter initially fulfills those protocols with safe Git subprocess calls. MCP handlers never call
Git directly, and Git/library-specific objects do not cross into evidence reports. A fake adapter
is used for unit tests; the real adapter has integration tests.

## Consequences

Adding a Git need first adds or narrows a port, then implements it in the adapter, then admits it in
a tool. A future Dulwich or pygit2 adapter remains possible without changing tool contracts. See
KR-011a and the Git-history sequence.
