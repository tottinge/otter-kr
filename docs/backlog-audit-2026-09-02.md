# Backlog acceptance audit — 2026-09-02

This audit compares every backlog item without a shipped marker to its stated observable result and
acceptance criteria. A matching module or test is evidence of progress, not sufficient evidence of
completion.

Baseline: `618a031`, clean `main`, synchronized with `origin/main`; `./full_test` passed 145 tests,
all checks, and formatting for 87 files. A fresh `python.inventory` MCP request reported 87 tracked
Python files with no warnings.

## Complete implementations with stale backlog labels

| Item | Evidence | Disposition |
| --- | --- | --- |
| KR-001 | `bab9577` established the reject-everything boundary; independence remains covered in `tests/test_server.py` | mark shipped historically |
| KR-002 | `7c1845b` added versioned rejection envelopes and deterministic query metadata | mark shipped |
| KR-003 | `ffb104a` added tracked Python inventory; parse and unreadable-file behavior has unit, MCP, and characterization coverage | mark shipped |
| KR-011b | `d21695e` admits plain and dotted module-import evidence with focused tests | mark shipped |
| KR-017a | `875efeb` emits versioned bounded snapshots with sorted files and bounded recent commits | mark shipped |
| KR-018 | `3e5a632` reports path-bounded branch additions and explicit skipped commits | mark shipped |
| KR-018a | `1764992` reports complete week rows and raw/normalized message categories | mark shipped |
| KR-019 | `618383a` emits exact/lexical nodes and separately identified edge reasons | mark shipped |

## Partial implementations requiring another admission

| Item | Existing evidence | Acceptance gap |
| --- | --- | --- |
| KR-020 | structural neighborhood reports shared-file and AST-adjacency edges | imports and repeated co-occurrence are not admitted as separate structural evidence |
| KR-021 | historical neighborhood emits bounded co-change weights | edges lack explicit window/filter provenance in the report |
| KR-022 | behavioral neighborhood reports calls, field access, and comparisons | shared field manipulation and selected-type behavior are not represented with citeable locations |
| KR-022a | graph topology reports counts, averages, connected-component IDs, and bridge scores | algorithm/filter parameters, cross-community edge totals, bridge ratios, and their formulas are absent |
| KR-023 | topic report validates a commit and lists parents and path changes | it does not carry hunk/content references; binary, rename, and merge statuses lack focused end-to-end acceptance coverage |
| KR-024 | hunk extraction preserves ranges, lines, normalized bodies, and fingerprints | initial, merge, binary, encoding, and duplicate-hunk uncertainty/status are mostly represented as an unexplained empty tuple |
| KR-025 | first-parent walk is bounded and reports merge/root/limit termination | candidate records omit touched path and diff-hunk evidence |
| KR-026 | exact normalized fingerprints are matched | match records omit hunk IDs, ranges, commit identity/distance, shared context, and explicit no-match candidates |
| KR-027 | context-line intersection is a distinct match method | raw ranges and normalized shared context are absent; range overlap is not implemented |
| KR-027a | Git porcelain blame yields commit, path, line, text, and status | reports omit source revision/range and do not characterize line shifts, repeats, deletions, or discontinuities end to end |
| KR-028 | matched fingerprints can become active family members under a limit | output is not an ancestry graph, match edges lack parent/child identities, and multiple-match branching is not preserved reliably |
| KR-029 | Git path changes become transition records | transitions are gathered for all walked changes rather than the active hunk family; unresolved identity is not tied to a family break |
| KR-030 | family report contains topic metadata, members, matches, unmatched hunks, skips, and budget | incomplete KR-025–029 evidence prevents the report from satisfying traceability acceptance |
| KR-031 | deterministic cache keys and hit/miss comparison exist | no cache stores or reuses topic-family output, and no request reports an actual cache hit or invalidation |
| KR-032 | seed projection preserves nodes, edges, counts, parse failures, and carrier guards | `locations` is always empty and provenance covers only the lexical neighborhood operation |
| KR-033 | inventory combines hotspots, duplicates, repeated groups, and distributions | branch growth and ownership-related observations named by the contract are absent |
| KR-034 | review packet combines scope, snapshot, and representation inventory | it cannot select changed files or a commit range and omits names, dependencies, and test evidence |
| KR-035 | term change evidence combines lexical neighborhood, bounded snapshot, and carrier guards | the contract's ownership, multiplicity, coupling, history, and existing-representation dimensions are not separately organized |
| KR-036 | planted Git fixtures cover rename, repeated edits, deletion, binary changes, a known fix/preimage pair, and merges | empty repositories, broad commits, executable affinity values, explicit binary evidence, and deterministic fixture IDs remain uncovered |
| KR-037 | current Python characterization independently checks inventory and parse health | names, imports, structures, test mappings, false-positive/negative observations, and resource bounds are not characterized |
| KR-038 | mature repositories and immutable revisions are recorded | the document explicitly defers path-specific triangulation and does not reproduce sampled scores/history edges independently |
| KR-039 | a blind-study protocol and fixed query budget are documented | no retained run packets, analyst ledger, unsupported-finding count, or second-analyst reproduction is present |
| KR-040 | one review packet was repeated byte-stably and its size recorded | thresholds were not fixed before a full run; latency, memory, warnings, correctness discrepancies, and reviewer traceability were not measured |
| KR-041 | a regression index and executable planted tests run under `full_test` | confirmed evidence deltas do not yet carry golden report/policy versions, and the documented useful blind queries are not replayed by the suite |

## Recommended closure order

1. Correct the eight stale shipped labels.
2. Close KR-020 through KR-022a so composite tools can depend on complete neighborhood evidence.
3. Close KR-023 through KR-031 in dependency order; do not call KR-030 or KR-031 complete while
   their underlying evidence is incomplete.
4. Close KR-032 through KR-035 after their source evidence is trustworthy.
5. Execute KR-036 through KR-041 as studies and regression work, not documentation-only claims.

Each acceptance gap should be delivered as a small separately reviewed commit. If completing an
item would admit more than one evidence shape, split it into lettered backlog slices before coding.
