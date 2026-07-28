# Decision — Grounded Authored World Object Lifecycle

**Status:** ACCEPTED PRODUCT / ARCHITECTURE DECISION  
**Date:** 2026-07-28  
**Applies to:** Hermes, World Graph, Build, Plan, Ingest / Graph Review, generated-resource workbenches, and Play / Combat  
**First proving domain:** Threat + Statblock  
**Second proving domain:** Item + Item Mechanics

## 1. Decision

DungeonBuddy will treat statblock generation as the first implementation of a broader **grounded authored world object lifecycle**.

The product is not complete when a generator can emit valid mechanics. The product is complete when a GM can move through one continuous, inspectable loop:

```text
ask a deep campaign question
→ recover forgotten graph/source context
→ develop an editable object description
→ send the grounded draft to a specialized generator
→ review, edit, validate, and accept
→ persist an exact immutable generated resource revision
→ create or connect the corresponding world object
→ publish the exact object/resource binding through governed graph review
→ open and place the object from relevant surfaces
→ activate an exact placement/resource in runtime systems such as combat
```

This loop is the north-star acceptance criterion for the statblock effort.

## 2. Product north star

The intended magic moment is:

> The GM asks Hermes about something deep and partly forgotten in the campaign. Hermes searches the admitted unioned graph and source context, explains what is known, distinguishes inference from fact, and writes an editable description for a new or existing world object. The GM sends that grounded description to the appropriate generator, adjudicates the output, accepts it, publishes it to the graph, and immediately uses the same object from Build, Plan, Ingest, or Play without recreating identity or copying data between disconnected tools.

The first complete example is Threat + Statblock. The architecture must make the next object generator cheaper to add without forcing all object types into statblock-specific assumptions.

## 3. Canonical object model

### 3.1 World object

A world object is the campaign thing that exists in canon or planned campaign state.

Examples:

- Threat
- Item
- Location
- NPC
- Faction
- Encounter

The World Graph owns world identity, relationships, authority, visibility, and revision-fenced publication.

### 3.2 Generated resource revision

A generated resource is a specialized artifact that interprets, depicts, or operationalizes a world object.

Examples:

- a statblock revision attached to a Threat;
- item mechanics attached to an Item;
- a map asset attached to a Location or Encounter;
- a portrait attached to an NPC;
- an encounter package attached to an Encounter.

Generated resources may have independent immutable revision history. Acceptance of a generated resource does not, by itself, create or change graph canon.

### 3.3 Binding

A binding explicitly connects one world object to one exact generated resource revision.

```text
WorldObjectResourceBinding
  world_object_ref
  resource_kind
  resource_id
  revision_id
  digest
  binding_role
  authority
  visibility
```

Bindings never resolve through an implicit “latest” fallback when exact identity is required.

### 3.4 Placement

A placement records one contextual use of a world object in a document, scene, encounter, map, or other host.

```text
ObjectPlacementV1
  placement_id
  world_object_ref
  host_locator
  pinned_resource_refs[]
  quantity?
  role?
  trigger?
  visibility
  notes?
  local_overrides?
```

A graph binding is not a placement. A Markdown embed is not automatically a placement. Placement owns contextual use such as “twelve Under-Hymn Brood arrive beneath the western wall on escalation tick two.”

### 3.5 Runtime instance

A runtime instance is mutable operational state derived from an exact placement or resource revision.

Examples:

- combatant instance;
- initiative, current HP, conditions, defeated state;
- active shop stock;
- a mutable exploration or travel state.

Runtime mutation must never alter graph truth or immutable generated mechanics.

## 4. Shared lifecycle contracts

The architecture should expose shared seams while keeping domain logic in adapters.

```text
GraphRetrievalSession
  → GenerationPacket
  → DraftArtifact
  → Candidate / Proposal
  → AcceptedResourceRevision
  → PromotionPlan
  → CommitReceipt
  → ObjectProjection
  → ObjectPlacement
  → RuntimeSeed / RuntimeInstance
```

The first implementation may use Threat- and statblock-specific concrete types. Shared interfaces should be extracted only where the completed Threat path proves the seam.

Expected adapter boundaries:

- `RetrievalContextAdapter`
- `DraftAdapter`
- `GeneratorAdapter`
- `CandidateRenderer`
- `CandidateValidator`
- `ResourcePersistenceAdapter`
- `GraphPublicationAdapter`
- `ProjectionAdapter`
- `PlacementAdapter`
- `RuntimeAdapter`

Do not build a universal object factory before the Threat vertical slice works end to end.

## 5. Hermes handoff contract

Hermes must be able to move from a grounded answer into an authored draft without discarding provenance or silently passing the whole conversation as authority.

The handoff should preserve a turn-scoped context envelope equivalent to:

```text
AuthoredObjectContextV1
  world_id
  campaign_id
  graph_revision_id
  retrieval_session_id
  selected_node_ids[]
  admitted_source_anchor_ids[]
  factual_summary
  disclosed_inferences[]
  unresolved_questions[]
  operator_authored_description
```

The user-authored or user-approved description is the creative input to the generator. Source anchors explain what grounded it. Neither the agent answer nor the generated draft becomes canon without explicit review and governed publication.

## 6. Surface responsibilities

### Hermes

- investigate broad free-form questions;
- use admitted unioned graph and source context;
- distinguish fact, inference, creative proposal, and unknown;
- create or seed an editable domain draft;
- never publish canon autonomously.

### Generated-resource workbench

- create, reopen, and revise drafts;
- generate typed candidates through a real provider;
- render, edit, validate, compare, and accept;
- persist exact immutable resource revisions;
- surface saved-versus-published truth honestly.

### Ingest / Graph Review

- create or connect world object identity;
- review relationships, authority, visibility, and evidence;
- attach or replace exact generated-resource bindings through preview/confirm;
- expose placement or runtime actions through shared capabilities without owning those stores.

### Build and Plan

- open exact object projections;
- insert references or exact resource embeds;
- create contextual placements;
- preserve pinned identity through reload;
- never silently follow a newer resource revision.

### Play / Combat

- create mutable runtime instances from exact placements or resource revisions;
- preserve the originating Threat, binding, revision, and placement locators;
- support reload and drilldown to the exact mechanics used;
- keep HP, initiative, conditions, and defeat state outside graph/mechanics authority.

## 7. Combat reanchor

The original Mireward static combat page remains a useful interaction sketch, but it is not the current product boundary.

A server-backed `CombatRosterModule` now exists in `apps/live-control-ui` and persists current combat through the live-control server. However:

- current combat is still a standalone combat JSON store;
- combat entities carry legacy source, title, artifact, or path-shaped statblock references;
- the roster does not resolve a graph Threat plus exact accepted statblock revision as authoritative input;
- the old generated Statblock View remains corpus-promotion-oriented and its add-to-combat action is disabled;
- there is no complete exact-revision insertion, reload, and drilldown path from the new statblock lifecycle.

Therefore combat completion requires both:

1. a combat integration foundation that evolves the live module and durable combat contract; and
2. the exact-revision statblock adapter that creates deterministic runtime seeds and inserts them.

`SBW15` must not be treated as a thin UI button over the current state.

## 8. Cross-surface capability model

Plan, Build, Ingest, and Play should not independently implement incompatible object actions.

Relevant surfaces should resolve a shared capability set for an exact object locator, filtered by host and permissions:

```text
Open object
Inspect evidence and history
Edit world identity
Generate or revise attached resource
Attach an existing resource revision
Insert reference
Place in this document / scene / encounter
Add exact placement or revision to combat
```

The capability implementation may route to graph review, document placement, generator workbench, or combat. The initiating surface does not become the authority for every resulting write.

## 9. Generalization rule

Threat + Statblock is the first complete proving domain.

Item + Item Mechanics is the second proof because it shares grounding, drafting, generation, review, persistence, graph binding, and placement while differing from combat and creature mechanics.

The second proof must reuse the established lifecycle and reveal which seams are truly general. Maps and locations come later because binary assets, geometry, and spatial ownership add separate complexity.

## 10. Non-goals

This decision does not:

- replace the World Graph with conversation memory;
- make generated output canon automatically;
- require every world object to have a generated resource;
- require every generated resource to map one-to-one to a world object;
- allow “latest revision” fallbacks for pinned consumers;
- collapse graph bindings, document embeds, placements, and runtime instances into one record;
- authorize a broad generic framework before the Threat path is dogfooded.

## 11. Acceptance

The decision is proven only when the cumulative dogfood gates in the active roadmap pass with real campaign data and reloadable durable state.
