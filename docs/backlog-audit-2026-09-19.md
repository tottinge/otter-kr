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
| KR-052 | active | remaining KR-020–022a provenance, location, filter, and formula characterization |
| KR-053 | active | remaining KR-023–031 end-to-end family, transition, uncertainty, and cache characterization |

The carrier-guard and variable-cluster sequence (KR-042–049) is admitted and regression-tested;
future work must preserve its evidence-only boundary. None of the active items authorizes semantic
judgments, root-cause claims, refactoring recommendations, or generated objects in the MCP.

## Ordering rule

Complete KR-050 and KR-051 first so later acceptance work has reproducible fixtures and reference
packets. Then close KR-052 and KR-053 in dependency order, splitting any item that admits more than
one new evidence shape. Update this file and `BACKLOG.md` in the same commit as each acceptance
change.
