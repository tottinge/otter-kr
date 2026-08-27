# ADR 0007: Use the MCP as evidence during refactoring sessions

- **Status:** accepted

## Context

Refactoring and TDD decisions should be grounded in the same deterministic evidence layer that
the project delivers to other coding agents. Reusing the MCP during development can expose stale,
duplicated, or incomplete representations before a change is committed. The MCP remains stateless
and evidence-only; the consuming agent still interprets observations and chooses actions.

## Decision

Start a fresh MCP stdio server at the beginning of each refactoring or TDD session. Establish a
baseline with narrow, relevant queries, record the repository revision and working-tree state, and
re-query after material edits. Stop the server before final verification and the atomic commit
protocol. A post-commit smoke query is optional.

Queries must be token-frugal: prefer bounded counts, selected locations, and relevant records over
complete reports, and do not repeat unchanged evidence in every agent prompt.

The Git adapter's tracked-file boundary is intentional. New untracked files are not visible to
MCP analysis until they become Git-known; do not stage files merely to make them analyzable. Use
direct tests or a temporary tracked fixture when new-file evidence is required.

## Consequences

Evidence gathered during a session is tied to an explicit repository state and can be challenged
by reading the cited source, inspecting Git, or rerunning the MCP. Restarting avoids stale process
state but adds a small process and query cost. Full reports remain available for focused validation,
but routine sessions should use summarized evidence. This workflow does not make the MCP a design
authority and does not permit it to infer semantic judgments.
