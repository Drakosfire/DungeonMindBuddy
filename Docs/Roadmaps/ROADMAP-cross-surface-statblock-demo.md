# ROADMAP — Cross-Surface Statblock Demo

**Created:** 2026-07-25  
**Status:** ACTIVE INTEGRATION ROADMAP  
**Product anchor:** GitHub issue #410 — Cross-surface World Graph + hoisted agent continuity demo  
**Scope:** DungeonBuddy demo spine across Ingest, Build, Plan, Play, Hermes Agent Interaction, World Graph, and statblock authoring  
**Authority:** This roadmap coordinates existing workstreams. It does not replace the Campaign Supergraph tracker, Build handoffs, or the Threat/Statblock roadmap. Each owning workstream retains authority over its contracts and write boundaries.

---

## §0 Demo goal

Demonstrate that DungeonBuddy is not a collection of disconnected generators. It is a governed continuity layer connecting:

- what happened at the table;
- what the campaign knows;
- what the GM is currently creating;
- what is planned for the next session;
- and what is used during play.

The demo follows one Threat from recap prose into durable campaign memory, through agent-assisted design and structured mechanics generation, into Plan and Play without reconstructing its identity or copying its statblock between surfaces.

```text
Observed in play
→ extracted from recap
→ reviewed and accepted as World Graph memory
→ selected as persistent agent context
→ elaborated into a Threat brief
→ approved for statblock generation
→ rendered, edited, validated, and saved as immutable mechanics
→ bound to the same Threat graph object
→ referenced in Plan
→ resolved in Play
```

### Product invariant

> One durable World Graph, many disposable projections; one coherent Agent Interaction layer, many surface-specific toolsets; one object identity across the lifecycle; every durable write passes through an explicit authority boundary.

---

## §1 Target demo narrative

1. In **Ingest**, paste or load a session recap.
2. Run extraction and review the proposed memory.
3. Explicitly confirm the proposal into the World Graph.
4. Open a newly created or newly relevant Threat node from the recap projection.
5. Choose **Use as agent context**.
6. Navigate to **Build** or **Plan** without losing the active agent conversation or pinned Threat.
7. Continue the conversation while the new surface contributes its own document, session, and selection context.
8. Collaborate with Hermes to develop the Threat’s lore, role, behavior, appearance, encounter intent, and constraints.
9. Review a human-readable Threat brief.
10. Explicitly approve a typed handoff to the statblock generator.
11. Receive and semantically render a structured statblock candidate.
12. Edit the exact working definition.
13. Validate the exact definition and receive a digest-bound validation result.
14. Explicitly **Accept/Save mechanics** as an immutable statblock revision.
15. Explicitly bind the saved statblock revision to the original Threat through a governed graph proposal and confirmation.
16. In **Plan**, insert the same Threat node into the next session or encounter as a graph reference.
17. In **Play**, resolve the same Threat ID and exact statblock revision.
18. Optionally create Play-owned runtime combat state from the canonical mechanics without mutating the canonical statblock.

### Final acceptance proof

The demo must show all three identities agreeing across surfaces:

```text
Threat node ID
Agent thread ID
Statblock ID + selected revision ID + definition digest
```

---

## §2 Authority and ownership model

All surfaces consume the same World Graph, but they do not share unrestricted write authority.

| Surface or layer | Primary reads | Authorized writes |
|---|---|---|
| Ingest | source recap, extraction candidate, current World Graph | proposed recap memory; governed Graph Review confirmation |
| Build | World Graph context, authored source, exact ExtractionRun | worldbuilding source revisions; extraction launch; later governed proposals |
| Plan | session-focused graph projection, documents, external-resource bindings | planning document and graph references; no silent canonical graph mutation |
| Play | session/encounter projection, canonical mechanics, runtime state | Play-owned combat/runtime state and notes; no mechanics mutation |
| Agent Interaction | graph pointers, graph-admitted evidence, active surface context | typed proposals and explicit tool requests; never privileged direct writes |
| Statblock Workbench | ThreatDraft, candidate definition, validation receipt | immutable accepted mechanics revision |
| Graph Review / Kernel | graph proposal, evidence, authority state | canonical graph contribution through prepare/confirm semantics |

### Required distinctions

The UI must keep these states visibly separate:

```text
source draft
extraction candidate
inspect-only candidate
validated statblock candidate
mechanics saved
Threat/statblock binding proposed
graph binding confirmed
planned graph reference
Play runtime instance
```

None of these states may be presented as equivalent.

---

## §3 Shared backing and projection model

### 3.1 World Graph

The World Graph is the durable identity and relationship plane. Surface projections are bounded read models over an exact graph snapshot.

A projection request should remain neutral and revision-aware:

```text
world_id
campaign_id
revision_pin or head policy
focus
admissibility
scope_mode
seed_node_ids or query_text
bounds
```

Product-specific concepts such as “Plan projection” or “Play projection” belong in surface recipes, not in Kernel contracts.

### 3.2 Projection coordinator

Introduce or extract one app-level projection coordinator that owns:

- normalized request construction;
- in-flight request coalescing;
- short-lived warm caching;
- revision-aware invalidation;
- projection load telemetry;
- exact snapshot identity;
- surface-specific request recipes.

```text
ProjectionCoordinator
  ├── Ingest recipe
  ├── Build recipe
  ├── Plan recipe
  └── Play recipe
```

A cache is never an authority source. A World Graph commit must invalidate stale head projections.

### 3.3 Shared graph-object interaction

The same graph node ID must open through the same resolver and presentation contract from:

- recap prose chips;
- Graph Review;
- Plan reference chips;
- agent context chips;
- Play encounter objects.

Surface presentation may differ, but identity resolution, relationship traversal, evidence access, and external-resource binding must not be reimplemented per surface.

---

## §4 Hoisted Agent Interaction

### 4.1 Target composition

```text
AppChrome
  AgentInteractionProvider
    Route / Surface
      Ingest
      Build
      Plan
      Play
  AgentInteractionBar
  AgentInteractionPane
```

The Agent Interaction layer is orthogonal to the active work surface. A surface publishes context upward and contributes authorized tools; it does not own the conversation container.

### 4.2 Thread identity

Cross-surface continuity requires thread identity to be independent of the active route and document.

Target identity:

```text
world_id
campaign_id
thread_id
```

Active surface context is attached to the thread, not included in the thread’s identity:

```text
surface_id
document_id?
document_revision?
session_id?
active_graph_revision
selected_block?
runtime_encounter_id?
```

### 4.3 Pinned context ledger

Add a durable pointer-only ledger for context explicitly selected by the GM:

```text
PinnedContextRef
  ref_type
  ref_id
  label
  added_from_surface
  resolution_policy
  pinned_revision_id?
  last_resolved_revision_id
```

The ledger stores locators and revision metadata, never copied graph bodies or statblock definitions.

### 4.4 Required interaction

Every shared graph-object card should be able to expose:

```text
View relationships
View evidence
Use as agent context
Add to plan       // when Plan capability is active
Bind mechanics    // only when allowed and mechanics exist
```

### 4.5 Write policy

Hoisting the agent interface must not hoist all capabilities into every surface. The active surface supplies a capability manifest. Hermes may propose or invoke only the tools admitted by that surface and lifecycle state.

---

## §5 Durable Threat and statblock model

The graph object and mechanics resource are related but distinct.

```text
Threat graph node
  threat:<stable-id>

Threat --uses_statblock--> External statblock resource

External resource
  provider: dungeonmind
  statblock_id
  selected_revision_id
  definition_digest
```

The World Graph stores:

- Threat identity;
- external resource identity;
- exact selected revision;
- definition digest;
- binding role and policy;
- lifecycle and provenance.

The World Graph does **not** store `StatblockDefinitionV1`, rendered Markdown, copied rules text, or Play runtime state.

### Runtime separation

```text
canonical immutable mechanics
→ Play runtime instance
  current HP
  initiative
  conditions
  temporary effects
```

Runtime state may point back to the exact canonical mechanics revision but cannot mutate it.

---

## §6 Current-state assessment

This table is an integration snapshot, not a replacement for owning trackers.

| Capability | State | Notes |
|---|---|---|
| Revision-pinned World Graph projection | DONE | Generic graph projection and retrieval foundations are merged |
| Plan World Graph consumption | DONE / POLISH NEEDED | Plan reads graph objects and inserts reference chips |
| Hermes graph retrieval and same-thread continuity | DONE IN PLAN | Strong graph-grounded conversation exists, but it is not yet cross-surface |
| Shared app-level Agent Interaction provider | PARTIAL | Provider is hoisted, but thread scope currently includes surface/document |
| Warm projection cache | IMPLEMENTED IN PR #380 | Needs extraction into shared app-level ownership |
| Recap → Graph Review → World Graph | IMPLEMENTED / PACKAGING NEEDED | Core demo behavior is present in PR #380 but mixed with unrelated work |
| Recap World Graph projection and shared object navigation | IMPLEMENTED IN PR #380 | Needs narrow reconstitution and merge |
| Build source authoring and exact extraction handoff | STRONG | Build can publish exact source context to Agent Interaction |
| Worldbuilding graph promotion | BLOCKED BY AUTHORITY DESIGN | Not required for the first statblock demo |
| ThreatDraft and statblock generation | STRONG | Candidate generation, renderer, editor, and validation exist |
| Immutable mechanics acceptance | BACKEND DONE / UI ACTIVE | SBW07c provides the required Accept/Save product path |
| Agent-approved ThreatDraft creation | MISSING | Current workbench requires a disconnected/manual initiation path |
| Typed Threat → exact statblock binding | DESIGNED ONLY | SBW08 contract and SBW09 publication are the critical missing backend seam |
| Plan resolution of bound statblock | BLOCKED ON BINDING | Plan reference path exists; typed mechanics binding does not |
| Play World Graph migration | READY / NOT IMPLEMENTED | Campaign Supergraph PR009 remains the Play consumer lane |
| Play exact-revision Threat sheet | PLANNED | Requires binding projection and mechanics resolution |

### Overall interpretation

Architectural foundations are substantially ahead of the integrated product experience. The main gap is not another generator or another graph store. It is the continuity spine connecting already-proven systems.

---

## §7 Delivery sequence

Each slice must prove one independently useful capability. Do not recreate PR #380 as another omnibus integration branch.

### DEMO-00 — Freeze and decompose PR #380

**Goal:** preserve valuable integration work while separating demo-critical capabilities from repairs, benchmarks, and unrelated extraction changes.

Extract independently:

1. World Graph recap projection;
2. shared graph-object navigation;
3. Graph Review post-confirm authority transition;
4. projection cache and telemetry;
5. Ingest primary-path simplification;
6. extraction/identity hardening;
7. governed historical repair scripts.

**Exclude from the demo critical path:**

- Session-specific repair scripts;
- large benchmark artifacts;
- unrelated extraction experiments;
- Plan world-union default as an incidental architectural decision.

**Exit proof:** each retained capability has a narrow owner, tests, and a merge/reconstitution plan against current Build and statblock work.

---

### DEMO-01 — Shared World Graph projection spine

**Goal:** make Plan and Ingest consume the same graph projection coordinator and graph-object resolver.

**Deliverables:**

- app-level projection request/cache module;
- surface request recipes;
- revision invalidation;
- shared node/card open path;
- warm-load telemetry;
- no latest-ingest or preview-union compatibility fallback.

**Exit proof:** Plan and Ingest open the same node ID at the same graph revision; warm revisit is measurably faster; a confirmed graph commit invalidates stale head projection data.

---

### DEMO-02 — Cross-surface Agent Interaction continuity

**Goal:** preserve one Hermes conversation and selected graph context while moving among Ingest, Build, and Plan.

**Deliverables:**

- Agent Interaction Bar and Pane in app chrome;
- campaign/thread-level identity independent of surface/document;
- active surface context attachment;
- persistent pinned-context ledger;
- **Use as agent context** on shared graph-object cards;
- safe context clearing on rejected/unloaded source state;
- SPA navigation or equivalent reload-safe route continuity.

**Exit proof:** select a Threat in Ingest, ask Hermes about it, navigate to Build or Plan, and continue the same thread with the same pinned Threat plus newly published surface context.

---

### DEMO-03 — Ingested Threat to approved ThreatDraft

**Goal:** turn agent-developed prose into an explicit, typed, human-approved statblock-generation input.

**Deliverables:**

```text
propose_threat_draft
→ visible request preview
→ human confirmation
→ create_threat_draft
→ exact draft ID + version
→ generate_statblock_candidate
```

The request must carry:

- campaign/world scope;
- source Threat node ID;
- additional pinned graph node IDs;
- graph revision used;
- approved threat brief;
- optional planning/build document locator.

**Anti-goal:** no arbitrary Hermes graph write and no fabricated campaign or graph provenance.

**Exit proof:** the GM does not manually reconstruct IDs; the generated candidate retains exact ThreatDraft and graph-context provenance.

---

### DEMO-04 — Candidate review through immutable mechanics save

**Goal:** complete the real statblock workbench lifecycle.

**Deliverables:**

- semantic candidate rendering;
- editable exact definition;
- exact-definition validation;
- digest-bound receipt;
- explicit Accept/Save mechanics;
- immutable mechanics locator;
- pending reconciliation handling;
- clear “mechanics saved; not graph-published” status.

**Dependency:** merge and stabilize SBW07c.

**Exit proof:** after reload, the accepted immutable mechanics revision resolves by exact statblock ID, revision ID, and digest.

---

### DEMO-05 — Threat/statblock binding contract

**Goal:** implement the graph’s typed external statblock resource and exact Threat binding without copying mechanics into graph memory.

**Deliverables:**

- SBW08 typed external resource node;
- typed `uses_statblock` relationship state;
- exact revision/digest in semantic identity;
- materialize, reload, validate, traverse, and project;
- reject definition-shaped payloads.

**Exit proof:** a deterministic fixture round-trips exact binding metadata through an immutable graph revision and projection.

---

### DEMO-06 — Governed product Threat binding

**Goal:** bind saved mechanics to the actual Threat through a human-confirmed graph write.

**Deliverables:**

```text
saved mechanics
+ exact Threat node
→ preview binding proposal
→ review
→ confirm commit
→ new World Graph revision
```

Initial scope may support binding an existing Threat only. Generic graph relationship authoring is not required.

**Exit proof:** after reload, the Threat node projects the exact statblock binding and the previous mechanics-saved state remains distinguishable from graph-published/bound state.

---

### DEMO-07 — Plan consumption

**Goal:** make the upcoming session reference the same Threat and exact mechanics revision.

**Deliverables:**

- insert Threat graph reference into Plan board;
- shared Threat object card;
- typed binding projection;
- resolve and render exact statblock revision;
- no copied mechanics in planning Markdown.

**Exit proof:** Plan stores the Threat pointer, opens the same Threat ID, and renders the same exact mechanics revision saved in the workbench.

---

### DEMO-08 — Play projection and runtime adapter

**Goal:** make Play consume the same Threat object and canonical mechanics.

**Deliverables:**

- React Play route or durable Play surface configuration;
- session/encounter-focused World Graph projection;
- player/GM admissibility policy;
- shared Threat card;
- exact statblock resolution;
- optional **Add to combat** adapter producing Play-owned runtime state.

**Anti-goal:** no full combat automation requirement.

**Exit proof:** Play opens the same Threat ID and exact mechanics revision as Plan, then creates runtime state without mutating canonical mechanics.

---

### DEMO-09 — Repeatable end-to-end dogfood package

**Goal:** turn the integrated product path into a reliable demonstration rather than a one-off successful walkthrough.

**Deliverables:**

- one bounded recap fixture containing a demo Threat;
- seeded World Graph baseline;
- repeatable ingest and graph-review inputs;
- known-good agent prompt path;
- known-good ThreatDraft request;
- statblock generation fixture or stable live dependency plan;
- exact acceptance and binding receipts;
- Plan document target;
- Play session target;
- reset procedure;
- visible authority-state checklist;
- failure/recovery notes.

**Exit proof:** three complete trials pass without manual ID repair, hidden filesystem editing, or copying statblock payloads between surfaces.

---

## §8 Demonstration ladder

The roadmap should produce useful demos before the final complete loop.

### Demo A — Shared memory projection

```text
Ingest recap
→ confirm World Graph
→ open node in Ingest
→ open same node in Plan
```

Proves shared durable identity and surface projections.

### Demo B — Cross-surface co-GM continuity

```text
Select node in Ingest
→ Use as agent context
→ continue same conversation in Plan or Build
```

Proves hoisted agent continuity and pointer-only context.

### Demo C — Context to structured mechanics

```text
Agent-developed threat brief
→ human-approved ThreatDraft
→ generated candidate
→ render/edit/validate
```

Proves graph-grounded creative orchestration without privileged writes.

### Demo D — Durable mechanics and graph binding

```text
Accept/Save mechanics
→ confirm Threat binding
→ reopen Threat
→ exact revision resolves
```

Proves the graph/resource boundary.

### Demo E — Plan to Play continuity

```text
insert Threat in Plan
→ open Play
→ same Threat and exact statblock
→ runtime combat instance
```

Proves the complete lifecycle.

---

## §9 Critical path

```text
DEMO-00 PR #380 decomposition
  ↓
DEMO-01 shared projection spine
  ↓
DEMO-02 cross-surface Agent Interaction
  ↓
DEMO-03 agent-approved ThreatDraft
  ↓
DEMO-04 immutable mechanics save
  ↓
DEMO-05 typed graph binding contract
  ↓
DEMO-06 governed product binding
  ├──→ DEMO-07 Plan consumption
  └──→ DEMO-08 Play consumption
             ↓
          DEMO-09 repeatable dogfood package
```

### Parallel work that should not block the first complete demo

- shared MarkdownCanvas extraction after Build hardening;
- BLD-09 PDF/OCR lineage;
- worldbuilding-draft promotion semantics;
- database migration from `out/` runtime stores;
- statblock revision/rebinding UX;
- images, media, or 3D resources;
- generalized graph property authoring;
- multi-user and multi-device continuity;
- full combat automation.

---

## §10 Demo product language

### What the audience should understand

- The recap creates proposed memory, not instant truth.
- The GM decides what enters campaign memory.
- Hermes uses graph identities and admitted context rather than an invisible pile of pasted prose.
- The statblock generator creates a structured candidate, not a finished canonical asset.
- Validation is not saving.
- Saving mechanics is not publishing the Threat binding.
- Plan and Play resolve the same campaign object rather than receiving copies.
- Play runtime state is temporary operational state, not a mutation of canonical mechanics.

### Recommended summary

> DungeonBuddy turns what happened at the table into governed campaign memory, carries that context into collaborative planning and creation, and then projects the same accepted objects into live play. The graph stores identity and relationships; specialized systems own their exact data; the agent helps move work between them without becoming an unbounded writer.

---

## §11 Final definition of done

The statblock demo roadmap is complete when a GM can perform the complete target narrative and the system proves:

- one World Graph head/revision model backs all graph reads;
- each surface receives a bounded purpose-built projection;
- warm projection reuse never becomes authority;
- one Hermes thread survives at least Ingest → Plan/Build → Play navigation;
- one pinned Threat node remains explicit and inspectable throughout;
- the ThreatDraft handoff is visible and human-approved;
- candidate, validated, saved, bound, planned, and runtime states are distinct;
- accepted mechanics are immutable and exact-revision addressable;
- the Threat graph object binds to the exact mechanics revision without copying mechanics into graph memory;
- Plan and Play resolve the same Threat ID and mechanics locator;
- Play runtime state remains separate;
- three repeatable end-to-end trials pass without hidden manual repair.

---

## §12 Active references

- GitHub issue #410 — Cross-surface World Graph + hoisted agent continuity demo
- PR #380 — World Graph recap projection, shared object navigation, authority transition, projection cache, and mixed integration work
- `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
- `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`
- `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
- `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md`
- `Docs/Design/ANCHOR-plan-surface-agent-interaction.md`
- `Docs/Plans/HANDOFF-sbw07-persist-accepted-mechanics.md`
- `Docs/Plans/HANDOFF-sbw08-world-graph-statblock-binding-contract.md`
- `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`
- Build BLD-05 through BLD-09 handoffs and reports
