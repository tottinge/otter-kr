# ADR 0004: Characterize with fixtures, references, and blind discovery

- **Status:** accepted

## Context

This repository has little history, while real repositories do not provide exact correctness
oracles. Plausible reports and LLM agreement are insufficient evidence of MCP correctness.

## Decision

Use planted temporary Git fixtures for executable correctness oracles, mature Python repositories
pinned to immutable revisions for scale and triangulation, and blind discovery targets for
usefulness. The default dogfooding set is `gitminer-dash`, `quizzology`, `OpenModelica`, and
`otter-kr`: a long-history reference, a medium application, a warning-heavy edge case, and the
self-hosting project. Additional repositories, including `boxed/mutmut`, may be added when a slice
needs a distinct corpus characteristic. Retain raw packets, versions, queries, warnings, and
hypotheses separately. Generated workspaces under the gitignored `dogfood/` directory are
disposable; only minimized fixtures and golden packets are versioned.

## Consequences

Dogfooding measures correctness, reproducibility, traceability, and operational cost separately.
Discrepancies become regression fixtures or explicit limitations. See KR-036 through KR-041.
