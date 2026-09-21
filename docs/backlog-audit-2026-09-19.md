# Backlog reconciliation — 2026-09-19

This is the current status snapshot for the roadmap. The 2026-09-02 audit remains useful as a
historical record, but its baseline predates the review-packet, term-evidence, and bounded-history
changes that are now shipped.

## Reconciled status

The implementation labels in `BACKLOG.md` are accurate for admitted capabilities KR-001 through
KR-049: each has production code, contract tests, and a documented rejection boundary. “Shipped”
does not mean that every possible characterization or study has been completed.

Recent evidence that changed the audit baseline includes:

- `6c2a630` and follow-on changes: review packets now support whole, file, multi-file, and revision
  scopes with names, dependencies, tests, history, and representation evidence.
- `7076657` and follow-on changes: term evidence is organized into citeable ownership,
  multiplicity, coupling, history, and representation dimensions with bounded locations.
- `c5ba1f9`: planted Git characterization now covers empty repositories, executable broad-commit
  affinity values, and explicit binary topic evidence.

## Active gaps

The following are follow-up work, not relabeling of shipped capabilities:

| Backlog item | Current disposition | Next evidence needed |
| --- | --- | --- |
| KR-050 | active | deterministic fixture IDs, negative relationship cases, and replay metadata |
| KR-051 | active | pinned mature-reference packets, independent score/history checks, and blind-study records |
| KR-052 | complete | structural, historical, behavioral, and topology evidence are characterized |
| KR-053 | complete | end-to-end family, transition, termination, uncertainty, and cache evidence are characterized |
| KR-054 | planned | compact duplicate evidence is split into measurement, identity, shape, operation, and usefulness slices |

The carrier-guard and variable-cluster sequence (KR-042–049) is admitted and regression-tested;
future work must preserve its evidence-only boundary. None of the active items authorizes semantic
judgments, root-cause claims, refactoring recommendations, or generated objects in the MCP.

## Ordering rule

KR-052 and KR-053 are complete. Continue with KR-050 and KR-051 only where additional replay
artifacts or mature-reference packets are still missing; update this file and `BACKLOG.md` in the
same commit as each study or packet change.
