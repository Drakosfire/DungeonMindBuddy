# Roadmap — Grounded Threat + Statblock Magic Moment

**Status:** ACTIVE IMPLEMENTATION ROADMAP — REANCHORED  
**Date:** 2026-07-28  
**Repository anchor:** `main` at `ff553bd81fc82e65d92ddbd1d05af5fc03f1adc7`  
**Latest completed slice:** `SBW06c` merged in PR `#439`  
**Next implementation slice:** re-anchor `SBW06d` only after Reboot Gates `R0-A` and `R0-B` are recorded  
**Architecture decision:** [`../Design/DECISION-grounded-authored-world-object-lifecycle.md`](../Design/DECISION-grounded-authored-world-object-lifecycle.md)  
**Implementation tracker:** [`../Plans/PR-TRACKER-threat-statblock-authoring-projection.md`](../Plans/PR-TRACKER-threat-statblock-authoring-projection.md)  
**Dogfood runbook:** [`../Runbooks/RUNBOOK-authored-world-object-magic-moment-dogfood.md`](../Runbooks/RUNBOOK-authored-world-object-magic-moment-dogfood.md)

## 1. Product goal

Deliver one complete, grounded authored-world-object loop:

```text
Hermes query across admitted unioned graph + sources
→ inspectable answer about a deep or forgotten campaign subject
→ editable Threat description grounded in exact graph/source context
→ ThreatDraft
→ real statblock generation
→ review, edit, validate, revise, accept
→ immutable exact statblock revision
→ governed create-or-connect Threat publication
→ exact Threat + statblock binding in the graph
→ projection and placement from Ingest, Build, and Plan
→ exact import into the live combat tracker
→ mutable combat state with reload and exact drilldown
```

The statblock effort is the first full implementation of the grounded authored world object lifecycle. It is not complete at “valid statblock JSON,” “saved mechanics,” or “graph node exists.”

## 2. Blocking dogfood rule

This roadmap contains intentional dogfood breaks.

A dependent implementation lane does not begin merely because tests pass. At each break:

1. run the capability against real campaign data;
2. let the GM experience the product behavior directly;
3. record the result using the dogfood runbook;
4. distinguish pass, friction, architectural miss, and unavailable dependency;
5. update the next handoff before continuing.

Synthetic fixtures prove boundaries. They do not substitute for these product gates.

## 3. Current truth

### Completed foundation

| Slice | Status | Proven capability |
|---|---|---|
| `SBW01` | MERGED `#386` | Server-owned DungeonMind statblock client/readiness boundary. |
| `SBW02` | MERGED `#387` | Durable versioned `ThreatDraftV1` CRUD. |
| `SBW03` | MERGED `#388` | One exact draft version generates one typed candidate. |
| `SBW04` | MERGED `#397` | Shared semantic renderer and read-only real-candidate workbench. Live-provider proof debt remains. |
| `SBW05` | COMPLETE `#398`, `#402`, `#404` | Complete-definition editing and authoritative preview validation. |
| `SBW07` | COMPLETE `#405–#409` | Immutable accepted statblock/revision persistence. |
| `SBW06a–c` | MERGED through `#439` | Revise proposal lineage, durable status, and Workbench revise UX. |

### Current gaps that block the magic moment

- Workbench draft creation records a graph revision but does not yet capture selected graph nodes and admitted source anchors from a real Hermes investigation.
- The first full unioned-graph query-to-description experience has not been recorded as a blocking product proof.
- Real-provider and current consumer-contract compatibility must be proven end to end; checked-in Buddy contracts may lag the current Server shape.
- Saved mechanics are not yet published as a governed Threat + exact binding.
- The roadmap has no implemented generic placement contract.
- Plan, Build, and Ingest do not yet share one object capability path for placement.
- The live combat roster is server-backed, but it is not graph- or exact-revision-backed. Current combat state remains standalone JSON with legacy artifact/path references.
- The existing generated Statblock View is tied to the older corpus-promotion lifecycle and does not provide the new accepted-revision-to-combat path.

## 4. Reboot gates before new broad implementation

### `R0-A` — Statblock live dependency proof

**Question:** Can the already-merged Workbench create, generate, edit, validate, revise, accept, and reload one statblock against the real current provider and contracts?

**Pass requires:**

- real provider/auth path;
- current OpenAPI / generated types / fixtures reconcile;
- one nontrivial campaign ThreatDraft;
- exact accepted `(statblock_id, revision_id, digest)` survives reload;
- failures are classified honestly;
- no mock or corpus-promotion fallback is treated as success.

A failure produces a narrow contract-sync or provider-readiness slice before `SBW06d`.

### `R0-B` — Unioned graph sensemaking proof

**Question:** Can Hermes answer a deep, forgotten campaign question using the admitted unioned graph and source context, then write an editable Threat description grounded in what it found?

**Pass requires:**

- a real question whose answer is not obvious from one recently opened file;
- no manual path targeting or preselected answer document;
- evidence spans the admitted unioned graph and, where needed, source reads;
- the answer distinguishes fact, inference, creative proposal, and unknown;
- Hermes produces an editable description suitable for a ThreatDraft;
- the result records graph revision, selected node IDs, admitted source anchors, and retrieval gaps.

This gate proves the first part of the magic moment even before the automated draft handoff exists.

**DOGFOOD BREAK 0:** Stop, run `R0-A` and `R0-B`, and re-anchor the next implementation handoff from observed friction.

## 5. Phase I — Grounded agent-to-draft handoff

### `AOW01` — Grounded authored-object context envelope

Persist or carry the exact retrieval context needed to seed a domain draft:

- world/campaign/revision;
- retrieval session;
- selected graph nodes;
- admitted source anchors;
- factual summary, inferences, gaps;
- operator-approved description.

No canon write. No generator invocation hidden inside retrieval.

### `AOW02` — Hermes “Develop as Threat” action

From the grounded answer, create or open a `ThreatDraft` without manually re-entering campaign scope or losing provenance.

The exact returned draft ID/version drives the Workbench. The action may be initiated from conversation, graph inspection, or a surface capability, but the draft store remains authoritative.

### `SBW06d` — Revise from exact accepted mechanics locator

Re-anchor the existing handoff after the reboot gates. Revise from exact `(statblock_id, revision_id, digest)` with no latest fallback.

### Authoring usability completion

Before the next gate, the Workbench must also support the real lifecycle needed for dogfood:

- browse and reopen existing ThreatDrafts;
- update the authored description/context intentionally;
- preserve local in-progress edits across ordinary dependency failures;
- show saved-versus-published state clearly.

### `MAGIC-D1` — Query to durable ThreatDraft

**Experience:** Ask Hermes about a forgotten subject, receive a grounded description, choose “Develop as Threat,” and arrive in the Workbench with the exact graph/source context attached.

**Pass requires reload:** the draft reopens with the same authored description, graph revision, selected nodes, and source anchors.

**DOGFOOD BREAK 1:** Stop and use this path on at least one real Campaign 2 subject before graph publication work proceeds.

## 6. Phase II — Complete connected statblock authoring

This phase closes the first generated-resource lifecycle without claiming graph truth.

Required capabilities:

- real provider generation from the grounded ThreatDraft;
- shared semantic candidate rendering;
- complete-definition edit and validation;
- revise proposal history from draft or accepted revision;
- accept one exact immutable statblock revision;
- browse/read accepted mechanics independently of the old corpus-promotion view;
- reload exact identity and digest.

### `MAGIC-D2` — Grounded description to accepted mechanics

**Experience:** Starting from the Hermes-created ThreatDraft, generate a statblock, edit a meaningful mechanic, validate, revise once, accept, close the browser, and reopen the exact accepted revision.

**Pass requires:** the GM can explain which prose came from campaign grounding, which mechanics were generated, what they edited, and what exact immutable revision was accepted.

**DOGFOOD BREAK 2:** Stop before graph publication. Record whether the Workbench feels like one connected authoring experience or several stitched tools.

## 7. Phase III — Governed Threat publication

### `SBW08` — World Graph external-resource and Threat binding contract

Re-anchor to current Kernel and projection contracts. Establish typed exact resource identity and `ThreatStatblockBinding` state. No product graph write in the contract slice.

### Split `SBW09` into reviewable capabilities

#### `SBW09a` — Publication plan and recoverable state

Create a durable/inspectable publication operation that can represent planned graph changes, expected revision, partial completion, retry, and cancellation.

#### `SBW09b` — Create-or-connect Threat resolution

The GM can:

- create a new Threat;
- connect the accepted statblock to an existing Threat;
- inspect likely matches and refuse an incorrect merge.

This is a separate invariant from committing the binding.

#### `SBW09c` — Governed Threat + exact binding commit

Preview and confirm the Threat/binding graph contribution through the existing graph governance path. Server success plus graph failure remains recoverable and truthfully displayed.

### `MAGIC-D3` — Accepted mechanics become a reusable graph object

**Experience:** Publish the accepted statblock as a new or existing Threat, reload the committed graph revision, and open the Threat with its exact mechanics binding and evidence.

**Pass requires:**

- no duplicate Threat when an existing object is intentionally selected;
- no silent existing-object merge;
- exact binding locator survives reload;
- “mechanics saved” and “published to graph” remain distinct;
- graph failure can be retried without recreating mechanics.

**DOGFOOD BREAK 3:** Stop and use the published Threat from graph inspection before implementing cross-surface placement.

## 8. Phase IV — Projection, shared capabilities, and placement

### `SBW10` — Exact-revision Threat projection

Open compact and full Threat views from graph/object references using the exact binding revision. Selection behavior must be explicit when multiple bindings exist.

### `SBW11` — Re-audit, do not dispatch as written

Current Plan document authoring and shared Markdown Canvas foundations have changed since the original handoff. Re-audit actual document load, local precedence, conflict, and reload behavior; split only the missing capability.

### `SBW12` — Exact revision embed

Embed an exact statblock revision in Markdown/Tiptap with honest unresolved state and shared renderer identity.

### `AOW03` — Generic object placement contract

Implement the first real `ObjectPlacementV1` with a Threat-specific extension for:

- exact Threat identity;
- exact pinned statblock revision;
- host document/scene/encounter locator;
- quantity, role, trigger, visibility, notes, and local encounter adjustments.

A placement is durable and reloadable. It is not merely an embed.

### `AOW04` — Shared object capability routing

Expose context-appropriate actions from:

- Ingest / node editing;
- Build;
- Plan;
- exact object projections.

At minimum:

- open;
- inspect evidence/history;
- attach or revise resource;
- insert reference/embed;
- place in current host;
- add exact placement or revision to combat when available.

### `MAGIC-D4` — Place the same Threat from every relevant surface

**Experience:** Use the same published Threat from Ingest, Build, and Plan without copying its mechanics or creating a second identity.

**Pass requires:**

- Ingest can attach/rebind exact mechanics and invoke placement without owning placement storage;
- Build and Plan create durable contextual placements;
- exact Threat and revision locators survive reload;
- quantity/role/trigger/notes are visible and editable where appropriate;
- a newer statblock revision does not silently move existing placements.

**DOGFOOD BREAK 4:** Stop and prepare a real scene with the new placement path before combat integration proceeds.

## 9. Phase V — Real combat integration

### `COMBAT01` — Live combat contract and module reanchor

The current `CombatRosterModule` is retained as the product surface, but its contract must evolve beyond standalone JSON and legacy artifact/path references.

This slice establishes:

- exact source locator fields for Threat, binding, revision, and optional placement;
- deterministic import/idempotency behavior;
- server-owned insert command;
- current-combat persistence and reload;
- exact statblock drilldown from a roster row;
- migration or compatibility behavior for existing combat saves;
- no graph or mechanics mutation from combat state changes.

### `SBW15` — Exact revision `CombatantSeed`

Map one exact accepted statblock revision or exact Threat placement to deterministic combat defaults and insert one or many runtime instances into the current combat encounter.

Keep mutable HP, initiative, conditions, notes, and defeated state in combat.

### `MAGIC-D5` — Published Threat enters live combat

**Experience:** From Plan, Build, Ingest, or the Threat projection, add an exact placed Threat to the live combat tracker, roll/set initiative, apply damage, advance turns, reload, and drill back to the exact mechanics used.

**Pass requires:**

- correct quantity creates distinct runtime instances;
- exact Threat/revision/placement lineage is retained;
- duplicate retry is deterministic or explicitly confirmed;
- mutable combat changes do not alter the graph or statblock revision;
- current combat survives reload;
- old static/eval harnesses are no longer presented as the product integration.

**DOGFOOD BREAK 5:** Run one real combat or rehearsal using imported graph-backed Threats before revision-evolution or media work is prioritized.

## 10. Phase VI — Revision evolution and media

These remain useful but are after the core magic moment:

| Slice | Outcome |
|---|---|
| `SBW13` | Append immutable child revision and compare to exact parent; no consumer moves. |
| `SBW14` | Governed adoption of one child revision for one Threat binding. |
| Placement/embed repin successors | Explicitly move one chosen pinned consumer; never implicit. |
| `SBW16` | Optional image generation with typed partial outcomes. |
| `SBW17` | Durable selected-image binding and projection slots. |
| `SBW18` | Deferred 3D reconnaissance only. |

## 11. Phase VII — Prove the architecture with a second object

### `AOW05` — Item Generator proving slice

Reuse the established lifecycle for Item + Item Mechanics:

```text
Hermes grounding
→ ItemDraft
→ typed item candidate
→ review/accept immutable mechanics
→ create/connect Item
→ exact binding
→ place in shop, treasure, NPC possession, or Plan
```

Do not begin by generalizing every statblock type. Reuse the proven seams, then change only what the Item domain requires.

**Architecture pass condition:** the Item path reuses retrieval, draft orchestration, publication, projection, capability routing, and placement without creating a second conversational runtime or a second graph-write system.

## 12. Dispatch discipline

Every implementation handoff must contain:

- one mission and one invariant;
- exact current base SHA and dependencies;
- bounded path allowlist based on current files;
- durable contracts and transition tables before stateful implementation;
- success, miss, failure, retry, reload, stale, and predecessor behavior;
- explicit dogfood gate enabled by the slice;
- a demolition declaration;
- tests at the owning boundary;
- stop conditions that report architectural mismatch instead of widening scope.

Pre-designed handoffs are not ready. Re-anchor every later SBW handoff before dispatch.

## 13. Completion

The core Threat + Statblock roadmap is complete only when `MAGIC-D1` through `MAGIC-D5` pass cumulatively with real campaign data.

The general architecture claim is complete only when `AOW05` proves a second object type through the same lifecycle.
