# User and Agent Stories — Hermes Campaign Authoring Foundation

**Status:** PROPOSED ACTIVE DESIGN; re-anchor required before implementation  
**Created:** 2026-07-15  
**Goal anchor:** [`ANCHOR-hermes-campaign-sensemaking-goal.md`](ANCHOR-hermes-campaign-sensemaking-goal.md)  
**Architecture:** [`ARCHITECTURE-hermes-campaign-authoring-foundation.md`](ARCHITECTURE-hermes-campaign-authoring-foundation.md)  
**Plan:** [`PLAN-hermes-campaign-authoring-foundation-reset.md`](../Plans/PLAN-hermes-campaign-authoring-foundation-reset.md)

## User stories

### U1 — Understand campaign movement

As a GM, I can ask:

> What changed after the latest ingested recap?

Hermes gives me a selected, engaging account of how the campaign moved, what matters,
what became more urgent, what remains unresolved, and what deserves prep attention.
Evidence is available for inspection but does not dominate the answer.

### U2 — Investigate an existing entity

As a GM, I can ask:

> Collect everything we know about this threat.

Hermes gathers relevant graph memory, admitted recap/source material, relationships,
and known gaps. It explains what is solid, partial, inferred, and missing without
pretending absent graph fields are settled facts.

### U3 — Collaborate on a statblock

As a GM, I can ask Hermes to help create a statblock for an existing threat or
creature. Hermes discusses the current picture, asks only consequential clarifying
questions, builds a typed packet, invokes the statblock generator, and presents a
draft for review.

### U4 — Promote deliberate memory

As a GM, I can inspect what adding the draft would change in the corpus and graph. I
confirm once. The server writes through the governed promotion path and shows the
resulting revision, links, warnings, and receipt.

### U5 — Use newly promoted memory

As a GM, after promotion I can ask what the new artifact is connected to or use it
when assembling an encounter. Hermes retrieves it through the same canonical memory
path.

## Agent stories

### A1 — Investigate before deciding

As Hermes, when a question is broad or initial deterministic retrieval is empty, I
use available bounded context and retrieval tools before concluding that nothing
useful can be said.

### A2 — Make uncertainty useful

As Hermes, I distinguish durable graph fact, admitted recap/source evidence, inference,
creative proposal, conflict, and unknown. I can say that a recap contains useful
material not yet promoted into campaign memory.

### A3 — Clarify only what matters

As Hermes, I ask focused questions only when the next useful retrieval or generation
step is materially underspecified. I do not interrogate the GM for fields that do not
affect the next decision.

### A4 — Request typed generation

As Hermes, I provide a server-validated domain packet to a generator and receive a
typed, noncanonical draft artifact. I do not write arbitrary files, invent
provenance, or commit graph/corpus changes.

### A5 — Preserve authority at promotion

As Hermes, I can explain and propose promotion, but only the server and explicit GM
confirmation can create durable campaign memory.

## Interaction invariants

- Free-form text is the primary interaction contract; populated workflow buttons are
  optional starting context, not hidden forms.
- The answer leads with meaning. Claim IDs, source status, revision, and trace are
  supporting inspection surfaces.
- A completed comparison with no accepted delta is different from an unknown or failed
  comparison.
- A generated artifact remains a draft until explicit promotion.
- Conversation continuity can resolve intent but never becomes factual authority.
- Facts, source detail, inference, proposal, and gap have distinct support states.
