# Plan — Hermes Campaign Authoring Foundation Reset

**Status:** ACTIVE RESET; Phase 1 product re-anchor accepted; initial Phase 0 cleanup slice complete; S1 gate rejected; broader gate open
**Created:** 2026-07-15  
**Primary goal anchor:** [`ANCHOR-hermes-campaign-sensemaking-goal.md`](../Design/ANCHOR-hermes-campaign-sensemaking-goal.md)  
**First proving domain:** statblocks  
**Re-anchor record:** [`REANCHOR-hermes-campaign-authoring-foundation-2026-07-15.md`](REANCHOR-hermes-campaign-authoring-foundation-2026-07-15.md)
**Implementation rule:** no new creative primitive begins until the remaining Phase 0 code/UI gate is accepted
**Phase 0 evidence:** [`../Reports/HERMES-PHASE-0-REFERENCE-SCAN.md`](../Reports/HERMES-PHASE-0-REFERENCE-SCAN.md)
**S1 dogfood evidence:** [`../Reports/HERMES-S1-LATEST-RECAP-DOGFOOD-2026-07-15.md`](../Reports/HERMES-S1-LATEST-RECAP-DOGFOOD-2026-07-15.md)

## Why this reset exists

Hermes currently has a useful read-only graph retrieval path, but the product goal is
larger:

> A GM can ask a free-form question, investigate existing campaign knowledge with
> Hermes, discuss what is missing, call a domain generation tool, review the result,
> and deliberately promote the result into durable corpus and graph memory.

The system must support both:

- campaign sensemaking, such as “What changed after the latest ingested recap?”;
- creative authoring, such as “Collect everything we know about Edge and help me
  create a statblock / town / NPC / encounter.”

The current code and document set grew through several narrower experiments:
graph lookup, evidence presentation, Live retrieval, Hermes graph tools, statblock
generation, graph review, preview unions, and corpus overlays. Their useful pieces
must be retained, but their competing product assumptions must not continue to define
the architecture.

This plan deliberately allows aggressive archiving, deletion, and replacement.
History remains available in Git and dated archives; active working space should
contain only the current model.

## North-star experience

As a GM, I can speak naturally about my campaign and ask Hermes to help me think,
retrieve, clarify, create, and remember.

Hermes should feel like a knowledgeable co-GM:

- it gathers what is already known;
- it explains what is solid, partial, inferred, or missing;
- it asks useful questions when a creative request is underspecified;
- it turns the conversation into a typed packet for a domain tool;
- it presents a draft rather than silently changing canon;
- it prepares a clear promotion plan;
- it commits only after explicit confirmation;
- it can retrieve and use the newly promoted result afterward.

The graph is an important memory and authority system. It is not a reason to stop
being useful whenever the graph is incomplete.

## Core design decisions

### 1. Separate retrieval, authoring, and promotion

Do not turn `GraphRetrievalSession` into a general-purpose god object.

Keep a small, read-only retrieval/evidence boundary for:

- world, campaign, focus, revision, and admissibility;
- referents and accepted claims;
- admitted source reads;
- gaps, conflicts, and retrieval trace.

Add a separate server-owned creative workflow boundary for:

- multi-turn clarification;
- working requirements;
- generation packets;
- draft artifacts;
- review state;
- promotion plans;
- confirmation and commit receipts.

### 2. Use generic workflow primitives with domain-specific schemas

Locations, NPCs, statblocks, and encounters should not each get a bespoke Hermes
agent. They should share:

- `AuthoringIntent`;
- `CreativeOperationSession`;
- `GenerationPacket`;
- `DraftArtifact`;
- `PromotionPlan`;
- `CommitReceipt`.

Each artifact type supplies its own strict schema, generator adapter, review
projection, and graph/corpus promotion mapper.

### 3. Free-form text remains free-form

Buttons may populate useful starting questions or carry optional application context,
but the user’s text remains an agent task. Internal classification may help Hermes
choose a route; it must not turn the product into a hidden form or a brittle intent
menu.

The server may inject ambient facts such as the active campaign, current revision,
selected node, and latest recap reference. It must not require the user to know those
internal identifiers.

### 4. Generated artifacts are not canon

The lifecycle is:

```text
retrieved canon
  → conversation and clarification
  → generated draft
  → human review
  → promotion preview
  → explicit confirmation
  → corpus + graph commit
  → post-commit verification
```

Background work may prepare and validate a promotion plan. It must not silently
publish generated material as campaign truth.

### 5. Graph incompleteness becomes useful context

The system must distinguish:

- accepted graph canon;
- explicit recap/source evidence not yet promoted;
- Hermes inference;
- creative proposal;
- missing or conflicting information.

An absent graph claim should normally produce a disclosed memory gap or a request to
promote knowledge—not a blank answer when an admitted recap or source provides useful
context.

## Phase 0 — aggressive archive and demolition pass

**Priority:** first  
**Outcome:** a clean working space with one understandable active design surface and
no accidental reliance on superseded experiments.

This phase is an inventory, archive, and deletion pass. It is not a feature sprint.

### 0A. Establish the active document set

Create a short active-document index containing only:

1. the accepted goal anchor;
2. this high-level plan;
3. one active architecture document;
4. one active user/agent stories document;
5. one active evaluation document;
6. one current implementation checklist after construction begins.

Everything else must be classified as:

- active reference;
- historical evidence;
- superseded proposal;
- generated/run artifact;
- duplicate or disposable.

### 0B. Archive stale documents

Aggressively archive superseded Hermes and graph-interaction material, including
dated handoffs, old PR-specific anchors, replaced UX stories, design-reset packets,
and plans whose sequencing assumptions no longer hold.

Archive rather than delete documentation during the first pass so the reasoning is
recoverable. The archive must include a small index stating:

- why the document was superseded;
- which active document replaces it;
- which lessons remain valid;
- whether any tests or code still reference it.

The original `.cursor/plans/hermes_graph_dogfood_4f95fo9e.plan.md` remains untouched.
Its completed work is historical input, not active sequencing authority for this
reset.

### 0C. Remove or quarantine obsolete backend code

Candidate demolition set, subject to reference checks:

- legacy Live/Hermes product switching and fallback paths;
- CLI/one-shot Hermes product code;
- legacy markdown-only statblock generation;
- the model-facing five-tool graph catalog;
- anchor-presence grounding and legacy citation fallbacks;
- duplicate classifier and acceptance paths;
- preview-only operation names whose implementations are generic search aliases;
- dead command constants and disabled lifecycle stubs with no owner;
- test fixtures that prove synthetic grounding but not useful behavior.

Quarantine first when a path is still referenced by a non-product consumer. Product
code must have one declared path; historical adapters must be explicitly labeled.

### 0D. Clean the UI working surface

Keep the existing calm answer-first foundation, but remove or hide artifacts that
make the UI feel like a retrieval debugger:

- default Live/Hermes backend picker;
- grounding-first answer kickers;
- packet sufficiency and retrieval freshness as primary content;
- always-visible graph/anchor IDs;
- ingest proof drawers inside the conversation;
- duplicate session semantics and history stores;
- trace-on-by-default behavior;
- old statblock and graph-review affordances that do not participate in the new
  workflow.

Retain evidence, trace, revision, and diagnostics as secondary inspection surfaces.
The primary surface should be conversation, draft review, and promotion review.

### 0E. Archive and code gate

Do not leave Phase 0 based on a file count alone. The exit artifact must contain:

- active document index;
- archive index;
- code demolition map;
- UI cleanup map;
- reference-scan results;
- list of retained compatibility adapters;
- list of known broken or stale tests;
- explicit deletions/quarantines approved for the next implementation phase.

#### Current gate state

The initial reference-checked cleanup slice is complete:

- code demolition map, UI cleanup map, and reference-scan report exist;
- retained S0 systems and compatibility adapters are listed;
- the dead Hermes CLI/context slice, superseded five-tool adapter, dead Plan toolbar,
  and Plan backend picker were removed;
- the retained graph retrieval, source-anchor, continuity, and v2 statblock adapter
  gates are green.

The known UI failure families were triaged and the UI baseline is green. The
deterministic S1 latest-recap resolver is also green, but the three-trial real
Plan/Hermes dogfood reproduced a generic graph-empty abstention: Hermes did not
name the latest recap, comparison boundary, or memory lag. The S1 gate is
therefore rejected.

The broader Phase 0 gate remains open for the S1 route repair and rerun, plus
deferred Live/planner/Graph Review migrations. No new creative workflow primitive
begins during that open gate.

## Phase 1 — explicit re-anchor

**Priority:** immediately after Phase 0  
**Outcome:** the cleaned repository and the people working in it agree on the same
goal before new primitives are built.

The re-anchor must answer:

1. Is Hermes primarily a campaign co-GM and authoring partner?
2. Is free-form text the primary interaction contract?
3. Is retrieval a safety/evidence boundary rather than the entire product?
4. Are generated artifacts drafts until explicitly promoted?
5. Is graph incompleteness a disclosed gap rather than an automatic conversation
   shutdown?
6. Is statblock generation the first proving domain?
7. Are locations, NPCs, and encounters later consumers of the same workflow kernel?

The product direction is now accepted and recorded in
[`REANCHOR-hermes-campaign-authoring-foundation-2026-07-15.md`](REANCHOR-hermes-campaign-authoring-foundation-2026-07-15.md).
The active anchor, architecture, stories, evaluation, and plan agree on the
campaign sensemaking/authoring direction.

The initial Phase 0C/0D cleanup slice and its reports are now complete. The current
bounded graph retrieval and continuity implementation is retained as the S0
foundation, not treated as proof that the authoring reset is complete. The UI
baseline is green, but broader cleanup remains gated by deferred adapter decisions
and a repaired, passing S1 latest-recap dogfood.

The re-anchor should also produce:

- current-state snapshot;
- active files and owners;
- retained systems;
- demolition decisions;
- first proving journey;
- explicit non-goals;
- next gate command or manual dogfood action.

The first conversational acceptance is the latest-recap change read. The first
full authoring proving domain is statblocks. These are sequential gates over the
same retrieval boundary, not competing product directions.

## Phase 2 — durable reusable primitives

Build the smallest reusable contracts needed by the statblock slice.

### Retrieval/evidence boundary

Retain or simplify the existing retrieval session so it can gather:

- graph claims;
- admitted recap/source material;
- selected objects and scenes;
- current revision;
- missing and conflicting information.

Add explicit support for an admitted latest-recap reference and memory-lag state.
Do not permit arbitrary model-selected filesystem discovery.

### Creative operation boundary

Introduce a multi-turn `CreativeOperationSession` with:

```text
gather → clarify → packet_ready → draft_ready → review
→ promotion_preview → awaiting_confirmation → committed | cancelled
```

It must be campaign-scoped, revision-aware, bounded, resumable across user turns,
and separate from factual graph memory.

### Typed packets and artifacts

`GenerationPacket` must be strict, server-validated, and assembled from:

- user brief;
- clarified requirements;
- retrieval claim IDs;
- successful source-read IDs;
- selected graph references;
- explicit uncertainty and open questions.

`DraftArtifact` must include:

- artifact kind and schema version;
- typed payload;
- rendered preview;
- warnings;
- provenance;
- digest;
- review actions;
- proposed links.

### Promotion boundary

`PromotionPlan` must preview:

- corpus writes;
- graph node assertions;
- graph edge assertions;
- source artifact/evidence references;
- visibility and authority;
- expected parent revision;
- conflicts and overlap.

Commit must be idempotent, revision-fenced, human-confirmed, and produce a receipt.
Corpus and graph promotion should be one logical workflow even if their physical
stores require recoverable multi-step execution.

## Phase 3 — statblock-first proving slice

**Goal:** prove the complete loop before adding other artifact classes.

Example journey:

> “Collect everything we know about this threat. What is missing? Help me create a
> statblock for it.”

Required behavior:

1. Hermes gathers relevant entity, scene, location, relationship, and source
   context.
2. Hermes explains the current picture in natural GM language.
3. Hermes asks only necessary questions about role, challenge, combat identity,
   terrain, party context, and desired tone.
4. The server validates a statblock `GenerationPacket`.
5. Hermes invokes the existing v2 statblock workbench adapter.
6. The UI presents the structured draft, warnings, and provenance.
7. The GM can revise, reject, or accept the draft.
8. The server prepares a corpus/graph `PromotionPlan`.
9. The GM confirms promotion explicitly.
10. The system creates or updates the appropriate statblock/threat node and links
    it to the target scene or encounter.
11. Hermes verifies the new revision and can retrieve the promoted artifact.

Do not extend the legacy planner path. Do not make corpus manifest activation the
final memory step. The proving slice must end in canonical graph/source retrieval.

## Phase 4 — promotion and memory convergence

Unify generated artifact promotion with the kernel contribution spine:

- promoted artifact becomes a governed source artifact;
- graph contribution creates or updates nodes and attributes;
- edge assertions are ordered after endpoint creation;
- source references retain artifact digest and locator;
- graph revision and corpus artifact share workflow provenance;
- retries are idempotent;
- partial failures are visible and recoverable;
- post-commit retrieval verifies the result.

This phase must explicitly resolve the current distinction between:

- statblock corpus promotion;
- retrieval manifest overlay;
- graph contribution merge;
- graph review overlay;
- candidate graph preview.

There should be one declared production memory path.

## Phase 5 — reuse the workflow for other domains

Only after the statblock journey is useful:

- locations/towns use the same gather → clarify → packet → draft → promote loop;
- NPCs add identity, relationships, and location edges;
- encounters assemble existing entities, locations, threats, and statblocks;
- combat scenarios become typed planning artifacts before any play-time mutation.

Each domain adds schemas and promotion mappings, not another conversational runtime.

## User stories

### U1 — campaign sensemaking

As a GM, I ask:

> What changed after the latest ingested recap?

Hermes gives me an engaging account of how the campaign moved, what matters, what
became more urgent, what remains unresolved, and what may deserve prep attention.
Evidence is inspectable but does not dominate the answer.

### U2 — investigate an existing entity

As a GM, I ask:

> Collect everything we know about Edge.

Hermes gathers graph memory, admitted recap/source material, prior relationships,
and known gaps. It explains the current picture without pretending that missing graph
fields are settled facts.

### U3 — collaborate on a statblock

As a GM, I ask Hermes to help create a statblock for an existing threat or creature.
Hermes discusses the known canon, asks clarifying questions, packages the result,
calls the statblock generator, and presents a draft for review.

### U4 — promote deliberate memory

As a GM, I can see what adding the statblock would change in the corpus and graph.
I confirm once. The system writes through the governed promotion path and shows me
the resulting revision and links.

### U5 — use the new memory

As a GM, after promotion I can ask what the new threat is connected to or ask Hermes
to assemble it into a combat scenario. Hermes retrieves the new artifact through the
same canonical memory path.

## Agent stories

### A1 — investigate before deciding

As Hermes, when a question is broad or the initial graph result is empty, I use
available bounded context and retrieval tools before concluding that nothing useful
can be said.

### A2 — make uncertainty useful

As Hermes, I distinguish durable fact, source/recap evidence, inference, proposal,
and unknown. I can say “this is present in the recap but not yet in campaign memory”
without discarding the useful context.

### A3 — clarify only what matters

As Hermes, I ask focused questions when a tool packet cannot be safely or usefully
constructed. I do not interrogate the GM for fields that do not affect the next
decision.

### A4 — request typed generation

As Hermes, I provide a validated domain packet to a tool and receive a draft artifact.
I do not write arbitrary files, invent provenance, or commit graph/corpus changes.

### A5 — preserve authority at promotion

As Hermes, I can explain and propose promotion, but only the server and explicit GM
confirmation can create durable campaign memory.

## Evaluation philosophy

The primary success metric is not grounding-envelope validity. It is useful,
truthful, repeatable GM collaboration.

Every phase should measure:

- user usefulness and naturalness;
- recovery after sparse or empty graph results;
- clarity of fact/inference/proposal boundaries;
- clarification quality;
- packet completeness and correctness;
- draft usefulness;
- promotion safety and idempotency;
- post-promotion retrieval;
- latency and operational simplicity.

Required negative tests:

- empty initial graph result but useful admitted recap;
- graph gap with no admitted source;
- source/graph disagreement;
- stale revision during promotion;
- rejected draft;
- duplicate confirmation;
- partial corpus/graph promotion;
- generated artifact incorrectly treated as canon;
- unsupported prose accepted as factual.

## Non-goals during this phase

- autonomous worldbuilding writes;
- silent background canon promotion;
- durable Hermes session work before the statblock loop proves useful;
- broad GraphRAG or embedding expansion;
- preserving every historical adapter;
- building all artifact types before one proves the workflow;
- treating trace richness as product progress;
- adding new operation names without real semantics.

## Exit criteria for the reset

The reset is complete when:

1. The active document set is small, named, and noncontradictory.
2. Superseded documents and code are archived or removed with a reference record.
3. The UI presents conversation and drafts first, diagnostics second.
4. The goal and stories have been explicitly re-anchored.
5. Retrieval, creative workflow, draft, promotion, and commit boundaries are agreed.
6. The statblock proving slice has a typed end-to-end acceptance contract.
7. No generated artifact can become canon without explicit promotion.
8. The next implementation slice is small enough to falsify independently.

Until these criteria hold, do not add more Hermes graph fields, tools, continuity,
or domain-specific generation paths.

