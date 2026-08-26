# ADR 0001: Stateless evidence-only MCP

- **Status:** accepted

## Context

The server supplies observations to an LLM that performs testing or refactoring work. It must not
make semantic judgments, retain repository context between calls, or turn associations into advice.

## Decision

Every research request supplies an explicit `repository_root` and query parameters. The server is
stateless and deterministic for a fixed repository revision and policy. Tools return structured,
versioned evidence or stable rejection codes; interpretation and action remain outside the MCP.

## Consequences

Calls are independently reproducible and easy to run against temporary repositories. Reports need
provenance and policy metadata. See KR-001 and KR-002.
