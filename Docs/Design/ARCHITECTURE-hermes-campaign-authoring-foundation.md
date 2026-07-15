# Architecture — Hermes Campaign Authoring Foundation

**Status:** PROPOSED ACTIVE DESIGN; re-anchor required before implementation  
**Created:** 2026-07-15  
**Goal anchor:** [`ANCHOR-hermes-campaign-sensemaking-goal.md`](ANCHOR-hermes-campaign-sensemaking-goal.md)  
**Plan:** [`PLAN-hermes-campaign-authoring-foundation-reset.md`](../Plans/PLAN-hermes-campaign-authoring-foundation-reset.md)

## Purpose

Hermes is a campaign sensemaking and authoring partner. The architecture must let a
GM ask a free-form question, investigate what is known, identify what is missing,
create a reviewed draft, and deliberately promote that draft into durable campaign
memory.

The graph remains a governed authority and memory boundary. It is not the whole
conversation and an incomplete graph is not, by itself, a reason to stop being useful.

## System shape

```text
free-form GM message
  → server-owned scope and revision
  → read-only retrieval/evidence session
  → Hermes interpretation and clarification
  → typed domain generation packet
  → noncanonical draft artifact
  → human review
  → promotion preview
  → explicit, revision-fenced commit
  → post-commit retrieval verification
```

## Boundaries

### Retrieval/evidence session

`GraphRetrievalSession` is a small, turn-scoped, read-only envelope. It owns:

- world, campaign, focus, admissibility, and revision;
- resolved referents and selected objects;
- accepted graph claims;
- admitted recap/source material and successful source reads;
- gaps, conflicts, and retrieval trace.

It does not own conversation lifecycle, generated drafts, or durable writes.

### Creative operation session

`CreativeOperationSession` is a separate server-owned workflow boundary for:

```text
gather → clarify → packet_ready → draft_ready → review
→ promotion_preview → awaiting_confirmation → committed | cancelled
```

It is campaign-scoped, revision-aware, bounded, resumable across user turns, and
never factual memory by itself.

### Domain generation

Every domain adapter receives a strict, server-validated `GenerationPacket` and
returns a typed `DraftArtifact`. The first proving adapter is statblocks. Locations,
NPCs, and encounters reuse the workflow kernel and add schemas and promotion
mappings rather than new conversational runtimes.

### Promotion

`PromotionPlan` previews corpus writes, graph node and edge assertions, source
references, authority/visibility, expected parent revision, conflicts, and overlap.
Only explicit GM confirmation can create a `CommitReceipt`. Generated output is never
canon merely because Hermes produced it.

## Product rules

1. User text remains free-form. Buttons may provide context or a suggested question,
   but they do not replace agent judgment with hidden intent forms.
2. Facts, admitted source detail, inference, creative proposal, and unknown remain
   distinct in both contracts and presentation.
3. Empty initial retrieval triggers bounded investigation when useful context exists.
4. “No changes found” is distinct from unknown, missing scope, failed retrieval, and
   unavailable source.
5. The primary UI leads with conversation and draft review. Evidence, revision, and
   trace remain inspectable secondary surfaces.
6. Server boundaries own scope, admissibility, revision, bounds, authority, and
   writes. Hermes chooses useful investigation and explains the result.

## First proving journey

The first end-to-end journey is:

> “What changed after the latest ingested recap?”

The server must identify the latest admitted recap and relevant before/after scope.
Hermes then selects meaningful changes, consequences, unresolved material, and prep
relevance. The answer distinguishes confirmed facts from inferences and disclosed
memory gaps without turning the main response into an evidence ledger.

The first authoring journey is:

> “Collect everything we know about this threat. What is missing? Help me create a
> statblock for it.”

Both journeys must use the same governed retrieval boundary and must not silently
write canon.

## Re-anchor gate

This document is an active design surface, not implementation authority yet. Phase 1
must reconcile it with the goal anchor, stories, evaluation contract, retained
systems, demolition decisions, and the statblock proving slice before new primitives
are built.
