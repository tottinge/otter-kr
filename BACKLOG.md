# Otter KR research backlog

This backlog turns `knowledge-representation-specification.md` and
`potential_specifications.yaml` into small, demonstrable research capabilities.
The product boundary is an evidence-only FastMCP server: deterministic tools report
observations, while an LLM using testing or refactoring skills interprets those observations and
chooses actions. The server never makes judgments, names concepts, recommends refactorings, or
assigns virtue scores.

The current shipped slice is `names`, which searches Python identifiers and returns source
locations, syntactic roles, and parse failures. Every item below is deliberately phrased as an
end-to-end admission, not as a component task.

## Reference implementation notes: `../gitminer-dash`

`../gitminer-dash` is a source of executable examples, not an authority over this project's
contract. Useful evidence-layer patterns to carry forward are:

- `insights.models.AnalysisSnapshot`: versioned, period-bounded snapshots with normalized paths;
- `insights.models.EvidenceRef`: small typed references (`kind`, `value`) that let a consumer cite
  observations without re-scanning the repository;
- `insights.snapshot_builder`: load a bounded commit window, sort deterministically, and retain a
  bounded set of commit references per file;
- `algorithms.file_changes`: per-file commit count, average changed lines, total change, and
  percent size change as separate observations;
- `algorithms.affinity_calculator`: ignore single-file commits, sort pair keys, accept iterators,
  and inject the weighting function for isolated tests;
- `repository_context`: explicit repository path plus bounded `since`/`until` history walks;
- `insights.evidence_builder`: attach canonical source references to ranked observations.

Do not carry over `insights.llm_client`, prompt construction, narrative generation, advisory
labels such as `coupling_pressure`, or UI-facing judgments. Those belong in the consuming LLM
workflow, not in this MCP evidence layer.

## Shared contract and rules

Every new tool must:

- accept a repository path or an already-established repository context;
- return machine-readable evidence with stable ordering, relative locations, counts, warnings,
  and provenance for each observation;
- never import, execute, modify, or infer semantic concept identity from target code;
- report unsupported inputs through a stable rejection (`unsupported_language`,
  `not_a_repository`, `invalid_query`, or `not_implemented`) rather than silently widening scope;
- preserve the current Python-only boundary until another language is explicitly admitted;
- carry a report version before its output is consumed by composite tools.

The shared path is:

`MCP request -> repository guard -> language adapter -> deterministic evidence -> structured report`

The first cross-cutting slice should establish a repository context and report envelope without
breaking the existing `names` contract. Later slices may add a versioned projection and deprecate
the initial shape deliberately.

## Delivery sequence

### Foundation

#### KR-001 — Establish a closed research boundary

- **Source:** both specifications; portability and evidence-layer constraints.
- **Admits:** one local directory supplied to one MCP tool.
- **Observable result:** a structured repository-context response identifies the resolved root,
  supported language (`python`), and stable rejection reasons for a missing directory, a file,
  and an unsupported language request.
- **Still rejected:** Git history, non-Python languages, semantic concepts, and all unregistered
  research operations.
- **Acceptance:** no absolute paths leak into relative evidence; invalid contexts never reach an
  analyzer; existing `names` behavior remains green.

#### KR-002 — Make evidence reports versioned and provenance-bearing

- **Source:** `output_contract`, `evidence_packet_example`, and Principle 2 (one authoritative
  representation).
- **Admits:** one report envelope around the existing `names` evidence.
- **Observable result:** each report has a schema version, source adapter, query/seed, counts,
  warnings, and evidence records with provenance.
- **Still rejected:** new research facts and composite interpretation.
- **Acceptance:** stable ordering and JSON serialization are tested; the old call remains available
  or has an explicit versioned migration path.

### Current-state evidence (no history required)

These slices answer “what exists now?” and can run on a copied source tree.

#### KR-003 — Inventory Python files and parse health

- **Admits:** Python file inventory for one repository context.
- **Observable result:** sorted files, byte/line counts, module classification, parse status, and
  syntax-error locations.
- **Still rejected:** symbols, imports, Git metadata, and non-Python files.
- **Acceptance:** hidden/environment directories are excluded by policy; unreadable and invalid
  files become warnings, not lost evidence.

#### KR-004 — Search Python names *(shipped)*

- **Admits:** exact and lexical-family identifier search for Python source.
- **Observable result:** definitions, parameters, assignments, and references with path, line,
  column, role, and parse failures.
- **Still rejected:** ownership claims, semantic concept identity, call-graph meaning, and other
  languages.
- **Acceptance:** existing five-test contract remains green.

#### KR-005 — Report direct Python imports and dependency edges

- **Admits:** statically visible `import` and `from ... import ...` edges.
- **Observable result:** source module, target module, imported names, relative-import level, and
  unresolved-import warnings.
- **Still rejected:** runtime imports, package installation metadata, call-graph edges, and cycles
  inferred across unresolved modules.

#### KR-006 — Report function-level complexity pressure

- **Admits:** Python functions and methods in one repository.
- **Observable result:** deterministic nesting, branch, line, and cyclomatic-style counts with
  function locations.
- **Still rejected:** language-specific execution-cost claims, performance diagnosis, and a global
  “badness” judgment.

#### KR-007 — Find repeated literals and constants

- **Admits:** repeated non-trivial literals in Python code, grouped by normalized value and source
  locations.
- **Observable result:** counts, locations, and literal-kind provenance.
- **Still rejected:** automatic extraction, semantic equivalence, and strings whose repetition is
  intentionally incidental.

#### KR-008 — Find repeated parameter and field groups

- **Admits:** repeated ordered parameter or attribute groups visible in Python AST structure.
- **Observable result:** grouped signatures/field sets, participating functions, and occurrence
  locations.
- **Still rejected:** a proposed value-object type or claim that a group is one concept.

#### KR-009 — Find duplicate helpers and near-duplicate algorithms

- **Admits:** exact structural helper duplication within Python source.
- **Observable result:** candidate pairs/groups, normalized structural fingerprints, and locations.
- **Still rejected:** semantic clone claims, automatic merging, and cross-language similarity.

#### KR-010 — Map enum/type discriminations

- **Admits:** Python `Enum` declarations and explicit comparisons/lookups involving one selected
  type.
- **Observable result:** all observed branches, lookups, and locations for that type.
- **Still rejected:** exhaustive semantic coverage claims and pattern matching in other languages.

#### KR-011 — Map tests to a selected symbol

- **Admits:** naming- and import-based relationships between Python tests and one symbol.
- **Observable result:** candidate tests, matched evidence, and explicit “no mapping found” output.
- **Still rejected:** runtime coverage claims, proof of execution, and test-quality judgment.

### Git-history evidence

These slices answer “what changed together, and how often?” They require a Git repository and a
bounded commit window. They must preserve file identity across renames before co-change scores are
trusted.

#### KR-012a — Freeze the co-change weighting contract *(decided)*

- **Decision:** use `1/C(N,2)` per pair, where `C(N,2)` is the number of unique file pairs in the
  commit. Each eligible commit contributes one total pair-affinity mass.
- **Source history:** the earlier draft specified a per-commit factor of `1/N`;
  `../gitminer-dash/algorithms/affinity_calculator.py` currently uses
  `2/(N*(N-1))`, which normalizes total pair mass instead.
- **History evidence:** `gitminer-dash` used `1/N` in its original October 2025 implementation
  (`9a91618`), then changed to `2/(N*(N-1))` in February 2026 (`f7d1284`). The later tests changed
  a two-file pair from `0.5` to `1.0`, while preserving `1/3` for each pair in a three-file
  commit. The commit message does not record a fuller rationale.
- **Admits:** one two-file commit and one three-file commit as executable contract examples.
- **Observable result:** pair scores, excluded single-file commits, sorted pair keys, and the
  exact weighting formula are visible in the report metadata.
- **Still rejected:** silently mixing formulas, interpreting the score as semantic coupling, and
  changing the formula through a UI or LLM prompt.
- **Acceptance:** write two-file, three-file, and broad-commit golden examples; expose the formula
  and invariant in report metadata; make the weighting function injectable for isolated tests.

#### Formula comparison

For a commit touching `N` files, there are `C(N, 2)` unique pairs:

| `N` | Earlier draft `1/N` per pair | Total mass | Adopted `1/C(N,2)` per pair | Total mass |
|---:|---:|---:|---:|---:|
| 2 | 0.5000 | 0.5000 | 1.0000 | 1.0000 |
| 3 | 0.3333 | 1.0000 | 0.3333 | 1.0000 |
| 4 | 0.2500 | 1.5000 | 0.1667 | 1.0000 |
| 10 | 0.1000 | 4.5000 | 0.0222 | 1.0000 |

The earlier specification captured “larger commits contribute less to each individual pair,” but
its total contribution grew as `(N-1)/2`. It therefore still let a broad mechanical change create
more aggregate affinity than a focused change. The adopted Gitminer revision incorporates
pair-count normalization, which makes commit size neutral in total mass and progressively dilutes
each pair as the commit widens.

The normalized formula does **not** by itself incorporate the other protections named in our
specification: source-file filtering, explicit time bounds, rename identity, merge/bulk-change
classification, or any confidence/minimum-observation rule. Those remain separate evidence
dimensions and must not be smuggled into the weighting formula.

#### KR-012 — Establish Git history context and bounded walks

- **Admits:** one repository’s commits since an explicit `--since`/equivalent time boundary.
- **Observable result:** repository root, commit count, source-file filter policy, and a stable
  rejection when Git or the requested window is unavailable.
- **Still rejected:** scores, blame-based ownership, and unbounded history by default.

#### KR-013 — Rank current hotspots

- **Admits:** file-level change frequency and churn within the bounded history.
- **Observable result:** ranked files with commit count, average changed lines, total size/diff
  change where available, recent commit references, and time-window provenance.
- **Still rejected:** causal claims, code-quality ratings, and function-level ownership.
- **Reference sample:** `gitminer-dash/algorithms/commit_frequency.py`,
  `algorithms/file_changes.py`, and `insights.snapshot_builder.py`.

#### KR-014 — Calculate global weighted co-change intimacy

- **Admits:** commits touching at least two source files, weighted by `1/N` for a commit with `N`
  source files.
- **Observable result:** descending file pairs, scores, commit counts, and the files excluded by
  policy.
- **Still rejected:** static dependency claims and semantic coupling claims.
- **Reference sample:** `gitminer-dash/algorithms/affinity_calculator.py`; its normalized formula
  is deliberately subject to KR-012a rather than copied implicitly.

#### KR-015 — Scope co-change to one file

- **Admits:** a focus file and its ranked historical partners.
- **Observable result:** the same weighted score plus per-partner context, using the global algorithm
  without changing its meaning.
- **Still rejected:** arbitrary multi-file filters and semantic ownership.

#### KR-016 — Scope co-change to one file pair

- **Admits:** an explicit pair of files.
- **Observable result:** pair score, contributing commits, and window/filter context.
- **Still rejected:** pairwise scores for an unbounded set and conclusions about why the files change
  together.

#### KR-017 — Preserve file identity across renames

- **Admits:** Git rename detection during the existing history walk.
- **Observable result:** canonical file identity and scores that do not split at a path rename.
- **Still rejected:** content-semantic identity and rename inference outside Git evidence.

#### KR-017a — Emit bounded, citeable history snapshots

- **Admits:** one bounded history window projected into a versioned snapshot.
- **Observable result:** schema version, normalized period, total commits, per-file counts, and a
  bounded list of recent commit references.
- **Still rejected:** narrative summaries, recommendations, and unbounded raw commit payloads.
- **Reference sample:** `gitminer-dash/insights/models.py` and `insights/snapshot_builder.py`.

#### KR-018 — Detect repeatedly growing branches

- **Admits:** branch or conditional growth observable across successive commits for one file.
- **Observable result:** changed branch counts/locations over time and the commits contributing to
  growth.
- **Still rejected:** a refactoring recommendation or assertion that growth is harmful.

#### KR-018a — Report temporal and commit-message distributions

- **Admits:** commits grouped into explicit calendar windows and syntactically recognized commit
  message categories.
- **Observable result:** complete weekly rows (including empty weeks), min/max/average counts,
  raw message category, normalized category, and unknown-category counts.
- **Still rejected:** productivity claims, intent certainty, and narrative explanations.
- **Reference sample:** `gitminer-dash/algorithms/weekly_commits.py` and
  `algorithms/conventional_commits.py`.

### Cross-evidence neighborhoods

These slices combine already-shipped evidence categories. They must preserve edge provenance and
must not turn deterministic association into concept identity.

#### KR-019 — Grow an exact/lexical neighborhood

- **Admits:** one seed identifier, using exact-name and lexical-family passes only.
- **Observable result:** nodes, weighted edges, discovery pass, and ranked neighbors with reasons.
- **Still rejected:** structural, historical, and behavioral edges.

#### KR-020 — Add structural neighborhood edges

- **Admits:** repeated co-occurrence, shared files, imports, and explicit AST adjacency around an
  existing seed.
- **Observable result:** structural edges are added with separate provenance and weights.
- **Still rejected:** Git intimacy and call-graph claims.

#### KR-021 — Add historical neighborhood edges

- **Admits:** bounded co-change relationships for a seed’s files.
- **Observable result:** historical edges and scores are distinguishable from structural edges.
- **Still rejected:** semantic clustering and agent-authored interpretation.

#### KR-022 — Add behavioral neighborhood edges

- **Admits:** statically visible calls, shared field manipulation, and selected enum/type behavior.
- **Observable result:** behavioral edges with evidence locations and edge reasons.
- **Still rejected:** dynamic dispatch certainty and inferred business concepts.

#### KR-022a — Report graph topology and bridge observations

- **Admits:** an already-built weighted file graph with an explicit algorithm, seed, and filtering
  parameters.
- **Observable result:** node/edge counts, average degree/edge weight, deterministic community IDs,
  cross-community edge totals, and bridge ratios/scores with their formulas.
- **Still rejected:** calling a file a bottleneck, architectural layer, or design problem.
- **Reference sample:** `gitminer-dash/algorithms/graph_statistics.py`,
  `insights/bridge_metrics_report.py`, and `algorithms/community_flow.py`.

### Topic change history (hunk-family ancestry)

This is a separate history capability from co-change affinity. Its seed is one topic commit, not
a file or term. The output is a graph or ordered family of prior change evidence. It may help a
consuming debugging/refactoring skill investigate where a defect was introduced, but the MCP must
never claim that a commit caused a defect.

`gitminer-dash/insights/fixback_scanner.py` provides useful starting mechanics: unified-diff hunk
extraction, line-number-independent fingerprints, first-parent diffs, merge exclusion, bounded
history, and explicit overlap evidence. It is narrower than this capability: it compares adjacent
file touches, favors short-term fix-like follow-ups, and hashes complete patch bodies. It does not
walk a topic backward through a recursive hunk family or establish line ancestry.

#### KR-023 — Validate and describe one topic commit

- **Admits:** one commit reference in one Git repository.
- **Observable result:** commit identity, parent identities, timestamp, message, changed paths,
  change types, and unified-diff hunk ranges/content references.
- **Still rejected:** any prior-commit matching, defect claims, and merge traversal unless an
  explicit policy is supplied.
- **Acceptance:** initial commits, missing commits, binary files, renames, and merge commits have
  explicit evidence/status rather than silent fallback.

#### KR-024 — Extract stable topic hunk evidence

- **Admits:** the topic commit's textual hunks for supported text files.
- **Observable result:** file identity, old/new ranges, added/deleted/context lines, normalized
  hunk body, and a deterministic fingerprint that excludes diff headers and line numbers.
- **Still rejected:** semantic equivalence, AST identity, and claims that matching means causation.
- **Acceptance:** identical edits at different line numbers match; changed context, duplicate hunks,
  encoding failures, and binary patches remain distinguishable or explicitly uncertain.

#### KR-025 — Walk backward through first-parent history

- **Admits:** prior commits touching files represented by the topic hunks, within an explicit
  commit/time/depth budget.
- **Observable result:** an ordered candidate stream with commit identity, parent, path, diff hunk
  evidence, and the traversal policy used.
- **Still rejected:** merge-parent expansion, unbounded history, and recursive family matching.
- **Acceptance:** traversal stops at the root, honors depth and time bounds, skips or reports merges
  according to policy, and never follows an unrelated file silently.

#### KR-026 — Match topic hunks to prior hunks

- **Admits:** exact normalized hunk-body matches between the active topic family and one prior
  candidate commit.
- **Observable result:** match records containing topic hunk ID, prior hunk ID, file identities,
  shared fingerprint/context, line ranges, commit distance, and match method.
- **Still rejected:** approximate matches, semantic matches, and “introduced defect” conclusions.
- **Acceptance:** no-match candidates are represented; duplicate fingerprints do not collapse
  unrelated locations; every match is traceable to both diffs.

#### KR-027 — Add line/context overlap matching

- **Admits:** a second deterministic matcher for hunks whose exact bodies changed but whose line
  context or mapped ranges overlap.
- **Observable result:** exact-match versus context-match method, overlap counts, normalized context,
  and the raw ranges used to calculate the match.
- **Still rejected:** a single opaque score with no components and semantic judgment about likely
  cause.
- **Acceptance:** the report preserves separate evidence for exact, context, and range matches so
  an LLM can choose how much trust to place in each.

#### KR-027a — Trace topic preimage lines to prior origins

- **Admits:** deleted or replaced lines from the topic hunk, resolved against the topic commit's
  first parent using Git blame or an equivalent line-origin operation.
- **Observable result:** prior origin commit, path, line range, source revision, and the exact
  preimage text used for the lookup.
- **Still rejected:** origin claims for newly added lines with no preimage, merge-parent ambiguity,
  and any assertion that the origin introduced a defect.
- **Acceptance:** line shifts, repeated text, deleted files, and unavailable blame data produce
  explicit origin candidates or discontinuity records; the report distinguishes line origin from
  hunk-text similarity.

#### KR-028 — Expand a matched hunk family backward

- **Admits:** when a prior match is found, that prior hunk becomes an active family member and the
  walk continues toward its parent.
- **Observable result:** a bounded ancestry graph with parent/child match edges, family member
  commit IDs, hunk IDs, traversal depth, and termination reason.
- **Still rejected:** unlimited graph search, cross-file semantic propagation, and causal labels.
- **Acceptance:** family expansion is deterministic, deduplicated, budgeted, and preserves branches
  where multiple prior hunks match the active family.

#### KR-029 — Resolve path changes in a hunk family

- **Admits:** Git rename/copy evidence while following an active hunk family across paths.
- **Observable result:** path transition records, old/new path identities, rename evidence, and
  explicit discontinuities where identity cannot be established.
- **Still rejected:** content-only guesses presented as Git identity and silent family breaks.

#### KR-030 — Emit a topic family-history report

- **Admits:** the complete evidence graph from one topic commit under the selected policies.
- **Observable result:** topic metadata, family members ordered by ancestry, match edges, unmatched
  hunks, skipped commits, budgets, and provenance sufficient for a consumer to inspect every link.
- **Still rejected:** “this commit introduced the bug,” blame assignment, refactoring advice, or
  testing conclusions.
- **Acceptance:** a consuming debugging skill can cite a prior commit and hunk without rescanning
  raw Git history; incomplete evidence is visible in the report.

#### KR-031 — Cache and compare topic histories

- **Admits:** repeat requests for the same repository revision, topic commit, matching policy, and
  budget.
- **Observable result:** deterministic cache key, schema/policy version, cache hit/miss evidence,
  and identical family output for identical inputs.
- **Still rejected:** stale results after repository revision or policy changes.

### Composite evidence packages

#### KR-032 — Project a seed evidence report

- **Admits:** a user-supplied seed plus an existing evidence neighborhood.
- **Observable result:** a report that organizes matching nodes, edges, locations, counts, and
  provenance under the supplied seed without asserting what the seed means.
- **Still rejected:** concept identity, LLM reasoning, recommendations, and unsupported evidence
  re-derivation.

#### KR-033 — Inventory representation signals

- **Admits:** a bounded composite of hotspots, duplication candidates, branch growth, repeated
  groups, and ownership-related observations already available from prior tools.
- **Observable result:** raw counts, ranked locations, repeated structures, and links back to source
  evidence. Categories describe the measurement, not whether the code is good or bad.
- **Still rejected:** pressure judgments, virtue scores, automatic refactoring, and design advice.

#### KR-034 — Generate a review evidence packet

- **Admits:** a selected set of changed files or a commit range.
- **Observable result:** one deterministic, machine-readable packet for an agent or reviewer,
  including relevant names, dependencies, tests, history, and pressure signals.
- **Still rejected:** approval/rejection of the change and invented semantic conclusions.

#### KR-035 — Generate change-oriented evidence for one term

- **Admits:** one term mapped through the existing neighborhood and signal inventories.
- **Observable result:** evidence organized by names, ownership observations, multiplicity,
  coupling, history, and existing representations, with every item traceable to source data.
- **Still rejected:** proposing or applying a refactor, claiming that one design is correct, or
  making any virtue judgment.

## Backlog quality rules

Use the refactoring skills as review criteria, not as a reason to pre-build abstractions:

- **Working:** each slice has unit and MCP contract checks before widening the admission.
- **Unique:** one report schema, one weight policy, one repository-context policy, and one source
  of truth for each deterministic fact.
- **Simple:** prefer one additional evidence category or query mode per slice.
- **Clear/Easy:** names should distinguish observation (`cochange_score`) from interpretation
  (`candidate_concept` belongs to the consuming LLM, not this server); history windows and scope
  must be visible in results.
- **Developed:** introduce a type only when repeated evidence groups or edges demonstrate the need.
- **Brief:** derive composite reports from evidence rather than reprinting raw scans.
- **Coherent:** all tools use the same repository context, provenance, stable ordering, and reject
  vocabulary.

For every implementation slice, record observations and provenance in the server; keep inference
and action in the consuming LLM workflow. The server itself does not run the improvement test or
decide whether a representation is better. Keep the default rejection path permanently useful for
unsupported languages, unknown query modes, and unavailable evidence.
