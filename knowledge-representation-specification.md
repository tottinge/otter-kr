# Knowledge Representation for Software Development
## Specification for Human and Agentic Software Development
### Draft 0.1

---

# 1. Purpose

Software development is the continual improvement of a representation while preserving correct behavior.

The representation includes every software artifact used to express knowledge:

- names
- values
- types
- data structures
- algorithms
- functions
- modules
- tests
- interfaces
- architectural boundaries

Programming is therefore more than producing executable instructions. It is the progressive refinement of the representation so that it more faithfully expresses the knowledge discovered during development.

Correct behavior is the first requirement of software.

Beyond correctness, every change should leave the representation easier to understand, easier to modify, easier to extend, and more faithful to the knowledge it expresses.

This specification defines principles, evaluation criteria, evidence, and operational skills for improving software representations.

It is intended for both human developers and coding agents.

---

# 2. Scope

This specification applies equally to:

- new development
- maintenance
- refactoring
- code review
- architectural review
- AI-assisted development
- agentic software development

It is independent of:

- programming language
- framework
- architecture
- paradigm
- development methodology

This specification does not replace XP, TDD, DDD, Clean Code, SOLID, or other engineering practices.

Instead, it attempts to provide a common representation-centered foundation from which those practices can be understood and operationalized.

---

# 3. Definitions

## Representation

A representation is the collection of software structures used to express knowledge.

Knowledge may be represented through:

- names
- constants
- enumerations
- data structures
- algorithms
- types
- interfaces
- relationships
- tests
- architecture
- documentation

Representations exist to communicate knowledge to both machines and people.

Executable behavior alone is insufficient.

---

## Knowledge

Knowledge is any fact, relationship, rule, constraint, policy, invariant, behavior, or concept that the software must preserve.

Examples include:

- a payment has a currency
- an order has states
- customer identifiers are unique
- taxes vary by jurisdiction
- passwords must be hashed
- retries stop after three failures

Knowledge may be represented procedurally or structurally.

Whenever practical, structural representations are preferred because they make knowledge explicit.

---

## Representation Evolution

Representation evolution is the process of replacing an adequate representation with a better one as understanding increases.

Better does not mean larger.

Better means the representation more faithfully expresses the knowledge currently understood while improving the Eight Code Virtues.

---

## Experiment

A representation change is an experiment.

The experiment succeeds only if:

- observable behavior is preserved unless intentionally changed,
- the Eight Code Virtues improve or remain unchanged,
- future similar changes become easier.

---

# 4. Fundamental Principles

The following principles define the philosophy of this specification.

These principles are stable.

Operational skills, heuristics, and implementation techniques derive from them.

---

## Principle 1

Software is primarily a representation of knowledge.

Executable behavior is necessary but not sufficient.

---

## Principle 2

Knowledge should have one authoritative representation.

The same fact should not be represented independently in multiple locations.

---

## Principle 3

Representations should evolve as understanding evolves.

Today's understanding should not remain encoded in yesterday's representation.

---

## Principle 4

Working software is the primary constraint.

No improvement in representation justifies loss of correct behavior.

---

## Principle 5

Representations should become simpler over time.

Growth in functionality should not require proportional growth in complexity.

---

## Principle 6

Every change should make future similar changes easier.

The easiest time to improve a representation is while it is already being modified.

---

## Principle 7

Every refactoring is an experiment.

Do not assume a representation is better.

Evaluate it.

Keep it only if it improves the overall representation.

---

## Principle 8

Evidence precedes abstraction.

Representations should evolve because the code demonstrates the need.

Not because the developer anticipates it.

---

## Principle 9

Existing representations are preferred over new ones.

Before introducing a new representation, determine whether an equivalent already exists in:

- the language
- the type system
- the standard library
- the framework
- project libraries
- existing domain abstractions

New representations should exist only when existing ones no longer naturally express the required knowledge.

---

## Principle 10

Programming is discovery.

Design is not merely implemented.

It is discovered through observation, experimentation, and evaluation.

Representations therefore evolve continuously.

---

# 5. Evaluation

Representations SHALL be evaluated using the Eight Code Virtues.

The virtues are evaluation criteria.

They are not implementation techniques.

They are not design patterns.

They are not heuristics.

Every non-trivial change SHOULD be evaluated against each virtue.

Working is the primary constraint.

The remaining virtues are evaluated together.

Tradeoffs between virtues are sometimes necessary.

When tradeoffs exist, Working takes precedence.

No other virtue has automatic priority over another.

The objective is continual improvement of the overall representation.

---

## Working

The software behaves correctly.

It satisfies its intended behavior.

Tests should demonstrate this behavior whenever practical.

Code that does not work is incomplete.

No improvement in representation compensates for incorrect behavior.

---

## Unique

Every piece of knowledge should have one authoritative representation.

Duplication includes:

- duplicated algorithms
- duplicated facts
- duplicated validation
- duplicated constants
- duplicated policy
- duplicated behavior
- duplicated ownership

The objective is not merely eliminating repeated text.

It is eliminating repeated knowledge.

---

## Simple

The representation should require:

- fewer operations
- fewer operands
- fewer execution paths
- fewer independent decisions
- fewer unnecessary relationships
- fewer unnecessary elements

Complexity should exist only where the problem requires it.

Accidental complexity should continually decrease.

When choosing between equally capable representations, prefer the simplest representation that naturally expresses the observed knowledge.

This is the intended meaning of "Do the Simplest Thing That Could Possibly Work."

Simplicity describes the representation, not merely the implementation.

---

## Clear

The representation should communicate its intent to its audience.

Clarity is relational.

It depends on the relationship between the representation and the people who must understand it.

Names, organization, abstraction boundaries, and structure all contribute to clarity.

Whenever possible, structure should eliminate the need for explanation.

---

## Easy

The next similar change should require less effort.

Ease is measured by maintenance rather than construction.

Representations that reduce coordination, reduce change locations, and reduce cognitive effort are preferable.

Ease often results from improvements in the other virtues.

---

## Developed

Representations should mature as understanding matures.

Primitive representations are often appropriate initially.

As knowledge accumulates, representations should evolve to express richer concepts, relationships, constraints, and behavior.

A representation is developed when it appears to have been the natural expression of the current understanding from the beginning.

Development is therefore evolutionary rather than speculative.

---

## Brief

Representations should express ideas economically.

Every element should contribute knowledge.

Ceremony without knowledge should be removed.

Briefness is achieved through better representation rather than abbreviation.

---

## Coherent

The representation should reinforce itself.

Names, types, behavior, modules, tests, and architecture should describe the same concepts using the same vocabulary.

Knowledge that changes together should be represented together.

Knowledge that changes independently should be represented independently.

Coherence is achieved when the representation consistently expresses the same understanding at every level of the software.

---
````markdown
# 6. Operational Model

This specification defines an operational cycle for coding, refactoring, review, and design.

Every activity SHALL follow the same cycle.

```
Observe

↓

Infer

↓

Experiment

↓

Evaluate

↓

Repeat
```

This cycle is intentionally iterative.

Understanding is expected to improve throughout development.

Representations therefore evolve continuously rather than being completely designed in advance.

---

## 6.1 Observe

Observation is the collection of objective evidence from the existing representation.

Observations describe what the software currently contains.

Observations SHALL NOT include interpretation.

Examples include:

- repeated names
- repeated literals
- repeated parameter groups
- repeated field groups
- repeated helper functions
- repeated algorithms
- repeated validation
- repeated traversal
- repeated conditionals
- repeated switch statements
- repeated enum handling
- repeated test setup
- repeated module dependencies
- repeated ownership
- repeated changes to the same files

Observation answers only one question:

> What does the representation objectively contain?

---

## 6.2 Infer

Inference proposes explanations for observed evidence.

Unlike observations, inferences are hypotheses.

They may be correct or incorrect.

Examples include:

- these values appear to describe one concept
- this behavior appears to belong elsewhere
- this conditional may represent independent variation
- these methods appear to share ownership
- this abstraction may have become primitive
- this representation may no longer match current understanding

Inferences SHALL be supported by observations.

Unsupported speculation SHALL NOT drive refactoring.

---

## 6.3 Experiment

A representation change is an experiment.

Experiments SHOULD be the smallest change capable of improving the representation.

Large speculative redesigns reduce the ability to evaluate whether the representation actually improved.

Experiments may include:

- introducing a new type
- introducing a collection
- introducing a value object
- introducing an interface
- moving ownership
- replacing conditionals
- removing duplication
- deleting obsolete representations
- renaming
- simplifying algorithms

The goal is never "introduce a pattern."

The goal is improving the representation.

Patterns are merely possible outcomes.

---

## 6.4 Evaluate

Every experiment SHALL be evaluated.

Evaluation consists of two questions.

### Question 1

Did Working behavior remain correct?

If not,

the experiment failed.

---

### Question 2

Did the overall representation improve according to the Eight Code Virtues?

If not,

the experiment should be rejected or revised.

---

## 6.5 Repeat

Representation evolution is continuous.

Every successful change provides new evidence.

That evidence may suggest further improvements.

Development therefore alternates between understanding and improving the representation.

---

# 7. Evidence

Evidence guides representation evolution.

Evidence is objective.

Evidence does not prescribe solutions.

Evidence suggests where the representation may no longer naturally express the knowledge currently present.

Evidence is stronger when multiple independent observations support the same inference.

No single observation requires a representation change.

---

# 7.1 Existing Knowledge

Before introducing any new representation, determine whether an equivalent representation already exists.

Search, in order:

- language features
- type system
- standard library
- framework
- project libraries
- existing project abstractions
- existing domain concepts

Representing existing knowledge twice violates the Unique virtue.

Reimplementing existing behavior introduces additional maintenance obligations.

New representations SHOULD exist only when existing ones no longer naturally express the observed knowledge.

---

# 7.2 Zero-One-Many

Zero-One-Many (ZOM) is evidence that a representation may need to evolve.

It is not a design rule.

It is not a mandate to introduce abstraction.

It is an observation about multiplicity.

---

## Zero

When a concept no longer exists,

its representation SHOULD be removed.

Delete:

- dead code
- obsolete abstractions
- unused parameters
- unnecessary types
- obsolete branches

Unused representations increase cognitive load.

---

## One

Represent one thing directly.

Do not introduce speculative abstractions.

A single occurrence rarely provides enough evidence for generalization.

---

## Many

When a second genuine instance appears,

determine what has multiplied.

Do not simply continue extending a representation that naturally expressed only one instance.

Instead,

allow the representation to evolve.

---

Multiplicity may include:

- values
- parameters
- states
- rules
- behaviors
- implementations
- ownership
- relationships
- algorithms
- transitions

Each kind of multiplicity suggests different representation improvements.

The goal is not abstraction.

The goal is better representation.

---

# 7.3 Repeated Coincidence

Coincidental repetition frequently indicates undiscovered structure.

Observe repeated:

- parameter groups
- field groups
- validation
- calculations
- traversal
- branching
- helper functions
- test setup
- configuration

Repeated coincidence suggests that the current representation may be expressing one idea in several places.

Seek the representation that allows the knowledge to exist once.

---

# 7.4 Representation Ownership

Every piece of knowledge SHOULD have one authoritative owner.

Ownership may reside in:

- a type
- a module
- a function
- a table
- a configuration
- a service
- a protocol
- the language
- the standard library

Ownership SHOULD NOT be duplicated.

Ownership SHOULD NOT be ambiguous.

Questions useful during review include:

- Who owns this rule?
- Who owns this invariant?
- Who owns this behavior?
- Who owns this relationship?
- Why does this module know this?

Knowledge without a clear owner is unstable.

Knowledge with multiple owners is duplicated.

---

# 7.5 Naming

Names are the primary mechanism by which representations communicate knowledge.

Names SHOULD reveal:

- purpose
- responsibility
- relationship
- distinction

Names SHOULD NOT merely describe implementation.

Difficulty naming something frequently indicates an undeveloped representation.

Naming problems are often design problems rather than vocabulary problems.

Improve the representation before searching for increasingly clever names.

---

# 7.6 Coupling and Cohesion

Knowledge that changes together belongs together.

Knowledge that changes independently belongs separately.

Observe:

- variables manipulated together
- methods operating on the same data
- files repeatedly changing together
- concepts repeatedly introduced together
- unrelated behavior within one abstraction

High cohesion improves representation.

Unnecessary coupling weakens representation.

Representation boundaries SHOULD follow knowledge boundaries.

---

# 7.7 Simplicity Pressure

Representations naturally accumulate complexity.

Observe:

- increasing execution paths
- increasing conditionals
- increasing operands
- increasing relationships
- increasing ownership sites
- increasing special cases

These observations suggest that the current representation may have become too primitive.

The preferred response is to seek a simpler representation.

Not merely shorter code.

Not merely fewer classes.

The simplest representation is the one that expresses the observed knowledge with the fewest necessary operations, operands, execution paths, relationships, ownership sites, and independent decisions.

---

# 7.8 Representation Pressure

Representation pressure exists whenever the current representation resists change.

Evidence includes:

- repeated edits to the same locations
- growing conditionals
- repeated helper creation
- duplicated algorithms
- scattered validation
- increasing coordination
- repeated exceptions
- primitive groups growing together

Pressure does not identify the correct solution.

Pressure indicates that experimentation is warranted.

The goal of experimentation is to discover a representation that relieves the pressure while improving the Eight Code Virtues.

---
````

**End of Part 2.**

Part 3 will define the operational skills themselves (Observe Representation, Evaluate the Virtues, Existing Knowledge, Representation Evolution, Coding, Refactoring, Review, and Architectural Review), followed by operationalization guidance for coding agents. This is where the document becomes directly consumable as agent skills.
