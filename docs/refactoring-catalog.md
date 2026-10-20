# Refactoring situation catalog

This catalog maps observable repository situations to the refactoring skills that
can investigate and act on them. It is a bridge between otter-kr's deterministic
evidence and otter-skills' judgment. It is not a smell detector, a quality score,
or a refactoring recommendation engine.

## How to use the catalog

For each situation:

1. Ask otter-kr for the listed observations.
2. Separate observations from the hypothesis they may support.
3. Read the cited source, callers, tests, and—when useful—bounded history.
4. Apply the named skill's improvement test before changing code.
5. Make the smallest behaviour-preserving move, then rerun focused and fast tests.

An observation can be intentional, coincidental, or incomplete. Repeated text is
not automatically repeated knowledge, and a high count is not automatically a
problem. The consumer owns interpretation, testing, and the choice to refactor.

## Catalog

| Situation to investigate | otter-kr evidence | Hypothesis to test | Smallest candidate moves | Primary skill; supporting skills |
| --- | --- | --- | --- | --- |
| Duplicate helpers or algorithms | `python.duplicates`; `python.duplicates.compact`; `python.neighborhood.structural` | Two implementations express one rule, rather than coincidentally sharing shape | Compare semantics; extract one authoritative helper, or leave independent code alone | `representation-refactor-review`; `code-review-zom-drift`; `unit-testing` |
| Repeated literal or magic value | `python.literals`; `python.names` | A repeated value is shared policy or domain knowledge | Introduce a named constant or policy; keep coincidental values separate | `representation-refactor-review`; `code-object-naming` |
| Repeated parameter, field, or argument group | `python.groups`; `python.variable_cluster`; `python.external_field_rules` | A primitive cluster is an undeclared value object or owner | Gather the group; introduce a type only when construction rules, invariants, or behaviour also travel together | `representation-refactor-review`; `code-review-zom-drift`; `unit-testing` |
| Numbered or parallel representations | `python.names`; `python.variable_cluster`; `python.groups`; structural neighborhood | One concept is pretending to be many (`item1`, `item2`, parallel helpers, repeated branches) | Replace twins with a collection, value object, table, or one owner | `code-review-zom-drift`; `representation-refactor-review` |
| Long conditional or branch-heavy function | `python.complexity`; `python.discriminations`; `python.carrier_guards` | Many cases or rules lack an explicit representation | Extract a decision, replace a conditional with a table, or introduce named state/policy | `representation-refactor-review`; `unit-testing` |
| Scattered handling of an enum or type code | `python.discriminations`; `python.names`; `python.neighborhood.structural` | One variation point has many knowledge owners or competing dialects | Gather the rule; replace type-code branching with a table, policy, or state representation when evidence supports it | `representation-refactor-review`; `code-review-zom-drift` |
| Repeated guards or predicate rules around one carrier | `python.carrier_guards`; `python.external_field_rules`; `python.variable_cluster` | A rule or state distinction is encoded repeatedly and may have a missing owner | Name and centralize the rule, or introduce a state/policy object; preserve independent tests | `representation-refactor-review`; `unit-testing` |
| External functions repeatedly manipulate one object's fields | `python.external_field_rules`; `python.external_field_rules.history`; `python.names` | Behaviour or invariants may belong with the data (possible feature envy / missing type) | Move one cohesive operation behind the object's boundary, or introduce a value object; first verify invariants and coupling | `representation-refactor-review`; `legacy-code-safety`; `unit-testing` |
| A name or concept has competing local dialects | `python.names`; `python.imports`; exact/lexical/structural neighborhoods; `python.term_change_evidence` | The repository uses multiple names or representations for one concept | Rename one vocabulary, add a boundary translation, or make the distinction explicit | `code-object-naming`; `representation-refactor-review` |
| A symbol's ownership and test safety are unclear | `python.tests`; `python.imports`; `python.neighborhood`; `git.review_packet` | A refactoring lacks a trustworthy safety boundary or the concept has unclear callers | Characterize first, establish a seam, then refactor in small steps | `legacy-code-safety`; `unit-testing` |
| A file or concept changes with many unrelated partners | `git.hotspots`; `git.cochange.file`; `git.cochange.pair`; `git.review_packet` | A boundary may be resisting change, or the files may simply share a workflow | Inspect recurring co-change and current ownership; split a boundary only when a real change becomes easier | `representation-refactor-review`; `legacy-code-safety` |
| A change keeps reopening the same scattered locations | `git.term_change_evidence`; `git.branch_additions`; `git.history`; `git.line_origins` | Shotgun surgery or divergent change may indicate missing ownership | Gather one rule or introduce a seam at the actual change boundary | `representation-refactor-review`; `unit-testing` |
| Dead, obsolete, or ghost representation | `python.names`; `python.imports`; `git.history`; `git.branch_additions`; `git.line_origins` | Zero is pretending to be one: stale parameters, branches, flags, or abstractions still teach a false dialect | Delete or inline after callers/tests/history confirm the behaviour is gone | `representation-refactor-review`; `legacy-code-safety`; `unit-testing` |
| A new feature is about to widen an existing branch or protocol | `python.complexity`; `python.discriminations`; `git.review_packet`; `git.hotspots` | The next case may be cheaper to admit through a clearer representation first | Tidy the smallest seam, then admit one case with a focused test | `iterative-story-split`; `unit-testing`; `representation-refactor-review` |

## Situation-to-skill index

The catalog currently gives these skills a concrete evidence path:

- `representation-refactor-review`: representation, ownership, SPOT, ZOM, virtue
  balance, and the improvement test.
- `code-review-zom-drift`: repeated, parallel, numbered, and scattered
  representations.
- `code-object-naming`: vocabulary drift, vague names, and rename candidates.
- `legacy-code-safety`: uncertain behaviour, missing seams, and characterization
  before a risky refactor.
- `unit-testing`: focused red/green evidence and behaviour-preserving refactoring.
- `iterative-story-split`: a refactoring seam that should be admitted one case at a
  time while default-rejecting the rest.

These are hand-offs, not a required pipeline. The evidence determines which skill
is appropriate; a row may be discarded after source inspection.

## Deliberately partial or unsupported situations

Conventional refactoring catalogs include situations that otter-kr cannot currently
establish reliably from its Python evidence. They should remain explicit gaps rather
than labels inferred from weak signals:

- pure runtime performance problems;
- semantic feature envy without observable field or call evidence;
- parallel inheritance hierarchies;
- message chains and hidden runtime dispatch;
- speculative generality, unless history exposes obsolete behaviour;
- API compatibility or generated-code constraints;
- cross-language duplication and dynamic Python behaviour;
- proof that a conditional is better represented by polymorphism rather than a table.

The next useful additions are evidence operations that close one of these gaps with
a narrow, reproducible contract—not a detector that emits a conventional smell name.

## Design rule for future entries

Add a row only when it can state all of the following:

- what otter-kr can observe and cite;
- what remains a consumer hypothesis;
- which skill can test the hypothesis and choose a move;
- what evidence would disqualify the move;
- how Working and the peer virtues will be checked after the change.

This keeps the MCP evidence-only boundary intact while making its value to
otter-skills discoverable.
