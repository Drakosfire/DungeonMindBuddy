# [IDEA] Graph V2 — semantic-frame kernel, contract factory, and corpus rejuvenation

**Captured:** 2026-07-28  
**Status:** LONG-TERM IDEA / ARCHITECTURE GOAL  
**Priority:** Deferred behind immediate Graph V1 containment and active product dogfood  
**Estimated scale:** approximately 40–55 small PRs for semantic Graph V2 plus rejuvenation and cutover; approximately 55–75 PRs if the broader authored-object software factory and Item proof are included

## Context

The active-edge semantic disagreement investigation exposed a contract mismatch in the current graph semantic center:

- durable edge identity is based on source + predicate + target;
- assertion identity includes additional semantic fields such as label and temporal scope;
- merge/rebuild may attach co-active assertions to one edge without enforcing the semantic agreement later required by projection;
- projection is the first stage that rejects an unreadable semantic state;
- accepted historical support, current fictional truth, and projected relationship state are not yet distinct concepts.

The immediate projection blocker is one malformed edge (`Baergrom —serves→ Caelynn`) whose assertions carry `predicate=serves` while source wording describes heal/revive events and one assertion carries `label=revives`. Eight other multi-active edges are legal under the current fingerprint, but they expose a broader modeling pressure: repeated attestations of persistent relationships and repeated discrete events use the same support/edge machinery.

This incident should be repaired intentionally in Graph V1 so current product work can continue. It also reveals a longer-term opportunity to replace the graph's semantic kernel before Threats, Items, Locations, Plans, placements, combat, and generated-object publication become deeply coupled to the current edge model.

## Long-term goal

Build **Graph V2** as a parallel semantic architecture capable of consuming arbitrary TTRPG prose without forcing every statement into a flat timeless edge.

The target durable flow is:

```text
canonical prose + authored inputs
→ source mentions and exact evidence anchors
→ immutable semantic assertions
→ governed resolution into semantic frame instances
→ derived current-state, relationship, history/event, timeline, and Hermes projections
→ governed authored-object publication, placement, and runtime activation
```

Graph V2 should distinguish at least:

- persistent relationships;
- discrete events;
- states;
- state transitions;
- attributes;
- identity and aliases;
- accepted historical knowledge versus currently valid fictional state;
- facts, beliefs, rumors, plans, prophecies, hypotheticals, and other modalities.

## Core semantic direction

### Predicate, source wording, and presentation are separate

- `predicate_id` is stable machine semantics.
- `surface_relation` preserves what the prose expressed.
- display labels are derived presentation and never silently determine semantic identity.
- unknown and ambiguous predicate mappings are legal states.
- campaign-specific predicates may extend a governed open-world vocabulary.

### Assertions are not frame identities

One source mention produces an immutable semantic assertion describing exactly what that source supports. Multiple partial assertions may resolve to one semantic frame instance.

Example:

```text
Assertion A: Baergrom revived Caelynn.
Assertion B: Baergrom revived Caelynn with a potion.
```

These assertions differ semantically because B contains an instrument, but they may still support the same event. Optional roles must enrich a frame without automatically fragmenting one occurrence into duplicate identities.

### Hybrid frame model

Use typed frame instances for:

```text
relationship | event | state | state_transition | attribute | identity
```

Participants use typed, extensible roles:

```text
actor | patient | target | instrument | location | beneficiary | source | destination | cause | purpose | campaign-specific roles
```

`instrument` is optional. When present, it is semantic; when absent, the assertion remains valid but incomplete.

### Time is explicit and typed

Graph V2 must distinguish:

- source time: where/when the assertion was recorded;
- occurrence time: when an event happened in the fiction;
- valid time: when a state or persistent relationship was true;
- transaction/revision time: when DungeonBuddy accepted or changed its interpretation.

Unknown, relative, interval, session-anchored, and campaign-calendar time must all remain representable without inventing precision.

### Projections are derived

Direct edges remain valuable for browsing and traversal, but they become projections rather than the primary semantic authority.

At minimum, derive:

- current-world graph;
- persistent-relationship graph;
- historical event graph;
- timeline projection;
- Hermes retrieval projection;
- surface-specific simplified edges and cards.

A published semantic head must pass canonical projection validation before becoming authoritative. Product reads must not be the first place a committed semantic incompatibility is discovered.

## Contract / software-factory direction

Explore a constrained **semantic domain factory** rather than a universal configuration engine.

A versioned domain contract may declaratively define:

- frame kind and canonical predicate;
- participant roles and cardinality;
- allowed object kinds;
- temporal and modality compatibility;
- identity anchors, discriminators, optional enrichment, and conflict-sensitive qualifiers;
- projection shapes and display forms;
- review requirements;
- generated schemas, types, validators, forms, fixtures, conformance tests, and documentation.

The handwritten semantic kernel owns invariants that configuration cannot redefine. Complex interpretation, event coreference, state reduction, and exceptional semantics use explicit typed extension code.

Do not allow the configuration language to become a Turing-complete replacement for ordinary code.

Treat the semantic-model factory and the authored-object workflow factory as related but separate systems:

1. **Semantic-model factory:** assertions, frames, roles, time, modality, resolution, and projections.
2. **Authored-object workflow factory:** ground → draft → generate → adjudicate → persist → publish → project → place → operate.

## Reuse boundary

Graph V2 is a reboot of the **semantic center**, not the whole graph platform.

Expected to retain or adapt:

- canonical source corpus and exact evidence anchors;
- content-addressed immutable revisions;
- world/campaign/revision/admissibility boundaries;
- contribution ledgers and replay/rebuild discipline;
- governed prepare/preview/confirm publication;
- source provenance, visibility, and authority controls;
- entity IDs, aliases, redirects, and prior resolution decisions as hints;
- surface shells for Hermes, Plan, Build, Ingest, Graph Review, and Combat;
- the current graph and dogfood artifacts as regression and reconciliation evidence.

Expected to replace or deeply revise:

- durable edges as primary semantic authority;
- current assertion identity contract;
- edge support aggregation and merge semantics;
- overloaded `active` state;
- extraction packets that permit predicate/label semantic disagreement;
- read-time-only semantic integrity enforcement;
- flat projection of discrete events as timeless relationships.

Directional reuse estimate only:

- most of DungeonBuddy remains relevant;
- roughly half or more of surrounding graph infrastructure should remain reusable;
- most of the assertion/edge/merge/projection semantic core will require replacement or substantial revision.

## Rejuvenation strategy

Do not migrate the current graph mechanically in place. Run a new parallel ingestion pass from canonical prose:

```text
source corpus
├── Graph V1 extraction and current product head
└── Graph V2 assertion extraction
    → frame resolution
    → V2 projections
    → semantic reconciliation report
```

Use current graph identities and assertions as hints and comparison material, not as unquestioned semantic authority.

The rejuvenation comparison should measure meaning rather than only node/edge counts:

- retained and corrected entity identities;
- persistent relationships retained;
- discrete events recovered;
- current-state differences;
- unresolved and ambiguous assertions;
- malformed old predicates identified;
- history/current-state query quality;
- Hermes usefulness on real campaign questions.

Cut over through a strangler migration after dogfood, not a flag-day rewrite.

## Conservative scope estimate

Plan around approximately **40–55 small PRs** for:

- Graph V1 containment and safe projectability;
- frozen V2 semantic contracts;
- assertion/frame/role/time/modality kernel;
- storage and contribution integration;
- representative handwritten contracts;
- constrained contract compiler and generated conformance suite;
- V2 extraction and semantic mapping;
- relationship and event resolution;
- current-state/history/relationship/Hermes projections;
- rejuvenation runner and reconciliation;
- dual-read, cutover, and Graph V1 semantic-core demolition.

Plan around **55–75 PRs total** if the same program also completes the reusable authored-object workflow factory, migrates Threat + Statblock onto it, and proves reuse with Item + Item Mechanics.

These are planning ranges, not a committed roadmap. Re-estimate after a bounded reference implementation.

## Recommended proving strategy

Do not build the generic compiler first.

1. Freeze the semantic kernel distinctions.
2. Handwrite a deliberately varied reference set:
   - `member_of`;
   - `located_in`;
   - `owns`;
   - `revive`;
   - `attack`;
   - `become_destroyed`;
   - `known_as`;
   - one strange Eldyrwild-specific relation.
3. Carry those contracts through extraction, storage, resolution, and projections.
4. Identify actual repetition.
5. Build the constrained compiler from the proven reference implementations.
6. Migrate the references onto the generated path.
7. Run a difficult corpus rejuvenation cohort.
8. Prove real Hermes questions before promoting a V2 head.

## Promotion criteria

Keep this item at `IDEA` until all are true:

- the immediate Graph V1 projection blocker is resolved without hiding valid history;
- the authored Threat/Statblock magic-moment roadmap has resumed far enough to expose real semantic consumers;
- a bounded Graph V2 architecture investigation names the semantic kernel, reuse boundary, and migration strategy;
- representative corpus samples demonstrate that events, relationships, time, modality, and open predicates are materially needed;
- an owner and sequencing window exist for a multi-dozen-PR program.

Promoting this item to `READY` should create a design/reconnaissance phase, not immediately dispatch 40 implementation PRs.

## Anti-goals

- Do not block immediate R0-A statblock dogfood or bounded Graph V1 repairs on Graph V2.
- Do not weaken Graph V1 integrity merely because V2 is planned.
- Do not build a complete universal TTRPG ontology before ingestion.
- Do not force unknown prose into the nearest known predicate.
- Do not make YAML responsible for arbitrary semantic reasoning.
- Do not overwrite or reinterpret published V1 revisions in place.
- Do not declare success from structural count parity alone.
- Do not cut over before current-state and historical Hermes queries are demonstrably better.

## Surfaces when

Graph V2; graph semantic reboot; semantic frames; event versus relationship; temporal graph; valid time; occurrence time; assertion ledger; event coreference; semantic contract compiler; ontology compiler; software factory; corpus rejuvenation; current-state projection; history projection; arbitrary TTRPG prose; predicate/label mismatch; active assertion overload.

## References

- `Docs/Reports/REPORT-active-edge-semantic-disagreement-investigation.md`
- `Backlog.md` — active-edge semantic disagreement entry
- `src/graph_memory/kernel/contributions.py`
- `src/graph_memory/kernel/contribution_merge.py`
- `src/graph_memory/kernel/contribution_rebuild.py`
- `src/graph_memory/kernel/world_projection.py`
- `src/graph_memory/candidate_graph_to_contribution.py`
- `src/graph_memory/evidence/assertion_support.py`
- `Docs/Design/DECISION-grounded-authored-world-object-lifecycle.md`
- `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`
