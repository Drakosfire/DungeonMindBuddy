# Evaluation — Hermes Campaign Authoring Foundation

**Status:** PROPOSED ACTIVE DESIGN; re-anchor required before implementation  
**Created:** 2026-07-15  
**Goal anchor:** [`ANCHOR-hermes-campaign-sensemaking-goal.md`](ANCHOR-hermes-campaign-sensemaking-goal.md)  
**Architecture:** [`ARCHITECTURE-hermes-campaign-authoring-foundation.md`](ARCHITECTURE-hermes-campaign-authoring-foundation.md)  
**Plan:** [`PLAN-hermes-campaign-authoring-foundation-reset.md`](../Plans/PLAN-hermes-campaign-authoring-foundation-reset.md)

## Evaluation principle

The primary metric is useful, truthful, repeatable GM collaboration. A valid
grounding envelope, rich trace, or passing schema is not product success by itself.

Every proving slice needs:

1. deterministic contract checks;
2. agent-policy checks for investigation and clarification;
3. product-flow checks for answer and draft presentation;
4. real dogfood checks for usefulness and friction.

## Phase 0 archive gate

The repository must have:

- one named active Hermes document set;
- a dated archive index with replacement and retained-lesson notes;
- no active document claiming superseded ladder sequencing;
- reference scans for moved paths;
- a code/UI demolition map before deletion decisions;
- a list of retained compatibility adapters and known stale tests.

## Phase 1 re-anchor gate

The goal anchor, architecture, stories, evaluation, and plan must agree that:

- Hermes is a campaign sensemaking and authoring partner;
- free-form text remains a real agent task;
- retrieval is a governed evidence boundary, not the entire product;
- generated artifacts are drafts until explicitly promoted;
- graph incompleteness becomes useful disclosed context;
- statblocks are the first proving domain;
- later domains reuse the same workflow kernel.

## First sensemaking scenario

### Scenario S1 — latest recap change read

**Question:** “What changed after the latest ingested recap?”

Required behavior:

- identify the latest admitted recap and the comparison boundary;
- investigate beyond an empty first graph result when admitted context exists;
- select meaningful changes rather than listing every storage mutation;
- explain consequences, pressure, unresolved material, and prep relevance;
- distinguish confirmed graph/source facts from disclosed inferences;
- disclose recap material that has not become durable graph memory;
- distinguish no-change from unknown, retrieval failure, and unavailable source;
- keep support inspectable without making the answer a ledger.

## First authoring scenario

### Scenario S2 — statblock collaboration

**Question:** “Collect everything we know about this threat. What is missing? Help me
create a statblock for it.”

Required behavior:

- gather relevant claims, admitted sources, relationships, and gaps;
- ask only consequential clarifying questions;
- build and validate a strict `GenerationPacket`;
- invoke the v2 statblock workbench adapter;
- return a typed, noncanonical `DraftArtifact` with provenance and warnings;
- support review and rejection;
- produce a `PromotionPlan` without writing;
- require explicit confirmation for corpus/graph commit;
- return a `CommitReceipt` and verify post-commit retrieval.

## Required negative scenarios

- empty initial graph result but useful admitted recap;
- graph gap with no admitted source;
- source/graph disagreement;
- stale revision during promotion;
- rejected draft;
- duplicate confirmation;
- partial corpus/graph promotion;
- generated artifact incorrectly treated as canon;
- unsupported prose accepted as factual;
- arbitrary filesystem discovery requested by the model;
- conversation history leaking facts across campaigns or threads.

## Metrics

### Sensemaking

- meaningful-change selection precision;
- unnecessary abstention rate;
- supported factual statement rate;
- inference disclosure rate;
- memory-lag disclosure rate;
- partial-answer usefulness;
- source/graph conflict honesty;
- answer-to-support navigation success.

### Authoring

- clarification sufficiency and unnecessary-question rate;
- packet schema validity and semantic completeness;
- draft usefulness and revision success;
- promotion-plan conflict detection;
- commit idempotency;
- stale-revision rejection;
- post-promotion retrieval success.

### Operations

- retrieval and model latency;
- bounded tool count;
- duplicate rediscovery rate;
- trace and diagnostic usefulness;
- absence of autonomous durable writes.

## Acceptance rule

No phase is accepted because tests are green if the user-facing journey still feels
like a retrieval debugger, a citation adjudicator, or an empty evidence verdict.
