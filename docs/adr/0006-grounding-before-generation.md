# ADR 0006: Ground generative craftsmanship with inspectable evidence

- **Status:** accepted

## Context

LLMs can generate code quickly, but ungrounded generation tends toward primitive solutions and weak
knowledge representation. The intended human/agent collaboration should support the judgment of a
skilled software craftsperson: clear representations, appropriate design, deliberate tests, and
maintainable change. The MCP is one foundation for that collaboration.

## Decision

This project supplies an evidence layer, not an autonomous designer. It should make code and its
history easier for humans and agents to understand, inspect, cite, and question. Generative skills
may interpret the evidence and propose tests, refactorings, or designs; the MCP must provide the
grounding needed to evaluate those proposals without deciding their correctness or taste.

Backlog slices should therefore prefer evidence that improves representation understanding,
decision traceability, and progressive investigation over broad automation or impressive-looking
summaries.

## Consequences

Reports need locations, provenance, explicit uncertainty, and enough surrounding context to support
craft judgments. An evidence item is a citeable lead, not a privileged truth: a consumer should be
able to verify it by reading the referenced files, inspecting Git objects, or using another tool.
Composite tools organize evidence for a decision but do not make the decision. Dogfooding should
test whether a skilled reviewer can understand, reproduce, and challenge a conclusion from the
evidence packet. See KR-032 through KR-041.
