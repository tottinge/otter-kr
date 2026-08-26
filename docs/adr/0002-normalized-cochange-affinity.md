# ADR 0002: Normalize co-change affinity by pair count

- **Status:** accepted

## Context

A commit touching many files creates many pairs. Weighting every pair by `1/N` allows broad
commits to contribute more aggregate affinity than focused commits.

## Decision

For a commit with `N` eligible source files, each unique pair receives `1/C(N,2)`, or
`2/(N*(N-1))`. Single-file commits are excluded. Each eligible commit contributes one total
pair-affinity mass.

## Consequences

The formula is size-normalized but does not solve rename identity, merge policy, time bounds, or
minimum-observation rules. See KR-012a and KR-014.
