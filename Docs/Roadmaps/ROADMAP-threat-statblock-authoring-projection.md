# Roadmap — Threat + Statblock Publication, Query, Placement, and Combat

**Status:** ACTIVE IMPLEMENTATION ROADMAP — PUBLICATION-FIRST REANCHOR  
**Date:** 2026-07-30  
**Repository anchor:** `main` after merged PR `#454`  
**Latest completed authoring foundation:** `SBW06c` merged in PR `#439`  
**Latest dogfood / unblocker slice:** PR `#454`  
**Immediate implementation authority:** close `R0-A` with one exact accepted statblock revision, then re-anchor `SBW08`  
**Implementation tracker:** [`../Plans/PR-TRACKER-threat-statblock-authoring-projection.md`](../Plans/PR-TRACKER-threat-statblock-authoring-projection.md)  
**Current re-anchor report:** [`../Reports/REPORT-threat-statblock-roadmap-reanchor-2026-07-30.md`](../Reports/REPORT-threat-statblock-roadmap-reanchor-2026-07-30.md)  
**Lifecycle decision:** [`../Design/DECISION-grounded-authored-world-object-lifecycle.md`](../Design/DECISION-grounded-authored-world-object-lifecycle.md)  
**Dogfood runbook:** [`../Runbooks/RUNBOOK-authored-world-object-magic-moment-dogfood.md`](../Runbooks/RUNBOOK-authored-world-object-magic-moment-dogfood.md)

## 1. Product goal

The critical statblock architecture proof is:

```text
accepted immutable statblock revision
→ governed create-or-connect Threat publication
→ exact ThreatStatblockBinding in the World Graph
→ Hermes can query the Threat by name, role, relationship, or campaign context
→ the exact bound mechanics can be hydrated and projected
→ the same Threat can be placed from Plan, Build, Ingest, and object projections
→ the exact placement or revision can enter live combat
→ mutable combat state reloads without mutating graph truth or statblock mechanics
```

Hermes-grounded authoring remains valuable, but it is an entry path into this lifecycle rather than a prerequisite for proving publication, queryability, projection, placement, or combat integration:

```text
Hermes research
→ grounded authoring artifact
→ ThreatDraft
→ accepted immutable statblock revision
→ the same publication lifecycle
```

The statblock effort is not complete at valid JSON, saved mechanics, or a graph node. It is complete only when one exact authored resource becomes a queryable, projectable, placeable, and combat-usable campaign object.

## 2. Authority and state boundaries

These states remain distinct:

```text
ThreatDraft
generated candidate
local working copy
validation receipt
accepted immutable statblock revision
published Threat
ThreatStatblockBinding
object placement
combatant runtime instance
```

Rules:

- DungeonMind owns generated statblock contract semantics.
- Buddy owns draft orchestration, validation presentation, accepted-mechanics persistence, publication operations, projections, placements, and combat activation.
- The World Graph owns governed campaign identity and relationships.
- Exact consumers pin exact revision identity; no `latest` fallback.
- Saved mechanics are not automatically published.
- Publication is not placement.
- Placement is not combat runtime state.
- Mutable combat changes never alter the graph or immutable statblock mechanics.

## 3. Current truth

### Completed foundation

| Slice | Status | Proven capability |
|---|---|---|
| `SBW01` | MERGED `#386` | Server-owned DungeonMind statblock client/readiness boundary. |
| `SBW02` | MERGED `#387` | Durable versioned `ThreatDraftV1` CRUD. |
| `SBW03` | MERGED `#388` | Exact draft-version candidate generation contract. |
| `SBW04` | MERGED `#397` | Shared semantic renderer and candidate Workbench. |
| `SBW05a–c` | COMPLETE `#398`, `#402`, `#404` | Dedicated editing plus authoritative complete-definition validation. |
| `SBW07 contract/a–c` | COMPLETE `#405–#409` | Immutable accepted statblock/revision persistence. |
| `SBW06 contract/a–c` | MERGED through `#439` | Revise contracts, lineage, durable attempts, proposal inspection, and retry behavior. |
| PR `#454` | MERGED | R0 evidence, current provider-contract sync, generation timeout alignment, freestanding provenance honesty, and Hermes UX unblockers. |

### Raw dogfood results

#### `R0-A` — `FAIL_PRODUCT`

The real provider was reachable. The observed path was:

```text
launcher → Plan → Tools → Statblock
→ create ThreatDraft
→ real provider generate
→ definition_invalid / HTTP 422
→ no candidate
```

The product correctly refused to manufacture a candidate, but the UI collapsed useful field/reference diagnostics into a generic validation sentence. Edit, validate, accept, and reload were therefore unreachable.

PR `#454` synchronized the current consumer contract and removed known timeout/provenance blockers. The gate remains open until the merged path is rerun and produces one exact accepted `(statblock_id, revision_id, digest)` that survives reopen.

#### `R0-B` — `IN_PROGRESS`, provisional capability pass

Hermes demonstrated:

- real multi-hop campaign investigation;
- uncertainty preservation and premise rejection;
- useful Threat directions;
- a provisional pasteable Threat description;
- pinned revision, matched nodes, source anchors, diagnostics, and recovery traces.

The remaining gaps are a reusable authoring artifact, evidence/query chips, explicit established/inferred/proposed/unknown state, and honest liveness. These are important authoring improvements but do not block the publication-first statblock path.

### Current critical gaps

- No current accepted revision has completed the merged real-provider path and reload proof.
- Generation validation diagnostics are not presented at field/reference granularity.
- Accepted mechanics cannot be published as a governed create-or-connect Threat plus exact binding.
- A published Threat has no explicit Hermes query-and-hydration acceptance proof.
- Exact Threat mechanics are not projected from graph references.
- No durable generic placement contract exists.
- Plan, Build, and Ingest do not invoke one shared placement capability.
- Live combat still uses legacy artifact/path/title-shaped statblock identity.

## 4. Phase 0 — Close the accepted-revision prerequisite

### `R0-A-RECOVERY`

Rerun the normal Workbench path on merged `main`:

```text
create ThreatDraft
→ real provider generate
→ edit one shipped dedicated numeric field
→ validate
→ accept
→ hard reload
→ reopen exact accepted identity
```

Pass requires:

- real provider/auth path;
- no mock or corpus-promotion fallback;
- one nontrivial campaign ThreatDraft;
- candidate generation succeeds under the current contract;
- exact accepted `(statblock_id, revision_id, digest)` survives reload;
- failures retain structured stage and diagnostic information.

If generation still returns `definition_invalid`, dispatch only the narrowest owning-boundary slice needed to:

1. preserve provider field/reference diagnostics end to end;
2. identify whether producer output, contract sync, or Buddy presentation owns the miss;
3. rerun the same draft without manufacturing hidden state.

A normal ThreatDraft library, expanded typed editor, and Revise-with-AI cleanup are useful but do not block publication unless the rerun proves otherwise.

**DOGFOOD BREAK 0:** Do not begin product graph publication without one exact accepted revision.

## 5. Phase I — Governed Threat publication

### `SBW08` — Exact external-resource and Threat binding contract

Re-anchor to current Kernel, graph governance, and projection contracts. Freeze:

- exact external statblock resource locator;
- exact immutable revision and digest;
- `ThreatStatblockBinding` identity and state;
- ownership and deletion behavior;
- multiple-binding selection policy;
- stale revision behavior;
- mechanics-saved versus graph-published distinction.

Contract only. No product graph write.

### `SBW09a` — Durable publication operation

Represent:

- expected graph revision;
- planned create/connect contribution;
- exact accepted mechanics locator;
- partial completion;
- retry;
- cancellation;
- stale state;
- server-success / graph-failure recovery.

### `SBW09b` — Create-or-connect Threat resolution

The GM can:

- create a new Threat;
- connect accepted mechanics to an existing Threat;
- inspect likely matches;
- refuse an incorrect merge;
- avoid silent duplicate identity.

### `SBW09c` — Governed Threat + exact binding commit

Preview and confirm the contribution through the existing graph-governance path. A graph failure must be retryable without recreating or changing the accepted statblock revision.

## 6. Phase II — Queryability, hydration, and projection

### `SBW10a` — Threat query and exact mechanics hydration

Make queryability an explicit contract and product proof.

Hermes must be able to retrieve a published Threat through ordinary campaign questions by:

- exact or alias name;
- role or capability;
- graph relationship;
- location, faction, event, or campaign context.

The query result resolves:

```text
Threat identity
→ exact ThreatStatblockBinding
→ exact accepted statblock revision
→ hydrated mechanics from the owning store
```

The graph stores the exact binding, not a copied statblock definition.

Pass probes include:

- “What threats can damage fortifications?”
- “Which threats are connected to Mireward?”
- “Show the mechanics for the insectoid siege creature.”
- “What statblock is bound to this Threat?”

### `SBW10b` — Exact-revision Threat projection

Open compact and full Threat views from graph/object references. Default presentation prioritizes useful game information:

- role and threat kind;
- important mechanics;
- encounter relevance;
- connected graph objects;
- exact bound revision status.

Evidence, provenance, and internal scores remain inspectable without dominating the default projection.

### `MAGIC-D3` — Publish, query, hydrate, and reopen

Experience:

```text
accepted exact revision
→ create or connect Threat
→ governed publish
→ reload graph revision
→ find the Threat through Hermes
→ open exact mechanics projection
```

Pass requires:

- no duplicate or silent merge;
- exact binding survives reload;
- mechanics-saved and graph-published remain distinct;
- graph failure is recoverable;
- at least one relationship/capability query finds the Threat without exact-name prompting;
- projection hydrates the exact bound revision;
- a newer mechanics revision does not silently move the binding.

**DOGFOOD BREAK 1:** Use the published Threat from both Hermes and graph inspection before placement work begins.

## 7. Phase III — Durable placement and shared surface capabilities

### `SBW11` — Re-audit Plan hydration only

The original handoff predates current shared canvas and authoring foundations. Re-audit actual document load, local precedence, conflict, and reload behavior; dispatch only the missing capability.

### `SBW12` — Exact revision embed

Embed an exact Threat/statblock reference in Markdown/Tiptap with honest unresolved state and shared renderer identity. An embed is not a placement.

### `AOW03` — `ObjectPlacementV1`

Implement the first durable placement contract with a Threat extension:

- exact Threat identity;
- exact binding identity;
- exact pinned statblock revision;
- host document/scene/encounter locator;
- quantity;
- role;
- trigger;
- visibility;
- notes;
- local encounter adjustments.

A placement is durable and reloadable. It does not copy mechanics and does not silently follow a newer revision.

### `AOW04` — Shared capability routing

Expose context-appropriate actions from:

- Ingest / node editing;
- Build;
- Plan;
- Hermes results;
- graph inspection;
- exact Threat projections.

At minimum:

- open;
- inspect evidence/history;
- open exact mechanics;
- attach or revise resource;
- insert reference/embed;
- place in current host;
- add exact placement or revision to combat when available.

The initiating surface does not own the underlying write.

### `MAGIC-D4` — Place the same Threat from every relevant surface

Pass requires:

- Ingest can attach/rebind mechanics and invoke placement without owning placement storage;
- Build and Plan create durable contextual placements;
- exact Threat, binding, revision, and placement locators survive reload;
- quantity, role, trigger, and notes are visible and editable where appropriate;
- no copied or duplicate Threat identity;
- newer mechanics do not silently repin existing placements.

**DOGFOOD BREAK 2:** Prepare one real scene using the placement path before combat integration.

## 8. Phase IV — Real combat integration

### `COMBAT01-contract`

Freeze:

- exact Threat/binding/revision/placement source locator;
- insertion and idempotency semantics;
- current-combat persistence;
- exact drilldown;
- migration/compatibility for existing saves;
- no graph or mechanics mutation from combat state.

### `COMBAT01`

Evolve the existing server-backed `CombatRosterModule` beyond standalone JSON and legacy artifact/path references while preserving mutable runtime independence.

### `SBW15` — Exact `CombatantSeed`

Map one exact accepted revision or exact Threat placement to deterministic combat defaults and insert one or many runtime instances.

Mutable runtime state remains:

- HP;
- initiative;
- conditions;
- notes;
- defeated state.

### `MAGIC-D5` — Published Threat enters live combat

Pass requires:

- correct quantity creates distinct runtime instances;
- exact Threat/binding/revision/placement lineage survives reload;
- duplicate retry is deterministic or explicitly confirmed;
- combat changes do not alter graph truth or immutable mechanics;
- exact mechanics drilldown works from a roster row;
- legacy static/eval harnesses are not presented as the product integration.

## 9. Parallel authoring lane

These improve creation and editing but do not block publication after `R0-A-RECOVERY` succeeds:

| ID | Outcome |
|---|---|
| `R0-B` closeout | Capture final authoring trace/verdict without treating it as publication authority. |
| `AOW01` | Grounded authored-object context envelope. |
| `AOW02` | Hermes “Develop as Threat” action. |
| `AUTHORING-ARTIFACT` | Stable editable/copyable markdown artifact with provenance kept adjacent. |
| `GRAPH-CHIPS` | Response evidence chips and query node anchors. |
| `AUTHORING-LIBRARY` | Browse/reopen/update ThreatDrafts and accepted mechanics. |
| `SBW06d` | Revise from exact accepted locator; no latest fallback. |
| Revise UX cleanup | GM-facing instruction flow rather than transport/ID choreography. |
| Editor expansion | Dedicated speed, attack, damage, and save controls. |
| Liveness/telemetry | Honest long-turn state and privacy-safe operational traces. |

`MAGIC-D1` and `MAGIC-D2` remain desired end-to-end authoring proofs, but they no longer block `SBW08–SBW10` when one exact accepted revision already exists.

## 10. Later revision evolution and media

| Slice | Outcome |
|---|---|
| `SBW13` | Append immutable child revision and compare exact parent/child. |
| `SBW14` | Governed adoption of one child revision for one Threat binding. |
| Embed/placement repin successors | Explicitly move one chosen pinned consumer. |
| `SBW16` | Optional image generation with typed partial outcomes. |
| `SBW17` | Durable image selection/binding and projection slots. |
| `SBW18` | Deferred 3D reconnaissance. |
| `AOW05` | Prove lifecycle reuse with Item + Item Mechanics. |

## 11. Gate ledger

| Gate | Current status | Blocks |
|---|---|---|
| `R0-A` | `FAIL_PRODUCT`; rerun required after PR `#454` | First accepted revision and `SBW08` product continuation |
| `R0-B` | `IN_PROGRESS`; provisional grounding/description pass | Only the grounded-authoring enhancement lane |
| `MAGIC-D1` | DOGFOOD REQUIRED, parallel | Hermes-to-draft convenience proof |
| `MAGIC-D2` | DOGFOOD REQUIRED, parallel | Full connected authoring proof |
| `MAGIC-D3` | BLOCKED on exact accepted revision and publication implementation | Placement |
| `MAGIC-D4` | BLOCKED on published queryable Threat | Combat |
| `MAGIC-D5` | BLOCKED on exact placements/combat contract | Core statblock roadmap completion |
| `AOW05` | DEFERRED | General authored-object architecture claim |

## 12. Dispatch discipline

Every implementation handoff must contain:

- one mission and one invariant;
- exact current base SHA and dependencies;
- bounded path allowlist;
- durable contracts and transition tables before stateful implementation;
- success, miss, failure, retry, reload, stale, and predecessor behavior;
- the exact dogfood gate enabled;
- a demolition declaration;
- tests at the owning boundary;
- stop conditions that report architectural mismatch instead of widening scope.

Pre-designed handoffs are strategic inputs, not dispatch-ready authority. Re-anchor each slice against current code and product evidence.

## 13. Completion

The core Threat + Statblock roadmap is complete when:

```text
one exact accepted revision
→ governed published Threat
→ Hermes query + exact hydration
→ exact projection
→ durable cross-surface placement
→ exact live-combat activation and reload
```

The connected authoring experience is complete when `MAGIC-D1` and `MAGIC-D2` also pass.

The general architecture claim is complete only when `AOW05` proves a second object type through the same publication, query, projection, placement, and activation seams.
