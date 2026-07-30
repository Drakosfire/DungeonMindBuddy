# Roadmap — Threat + Statblock Publication, Query, Placement, and Combat

**Status:** ACTIVE IMPLEMENTATION ROADMAP — PUBLICATION-FIRST REANCHOR  
**Date:** 2026-07-30  
**Repository anchor:** `main` after merged PR `#455` and the PR457 dispatch correction  
**Latest completed authoring foundation:** `SBW06c` merged in PR `#439`  
**Latest dogfood / unblocker slice:** PR `#454`  
**Immediate implementation authority:** [`../Plans/HANDOFF-pr457-sbw08-statblock-binding-contract.md`](../Plans/HANDOFF-pr457-sbw08-statblock-binding-contract.md)  
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

Hermes-grounded authoring remains a valuable entry path, not a prerequisite for publication, queryability, projection, placement, or combat:

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
| Accepted-revision prerequisite | OPERATOR-CONFIRMED | The GM manually completed create → generate → edit → validate → accept → hard reload → reopen at least twice through the normal product path. This is operator-reported product evidence, not automated or checked-in run evidence. |

### Dogfood evidence

#### Historical `R0-A` failure

The 2026-07-29 report remains valid historical evidence for the pre-unblocker product state:

```text
launcher → Plan → Tools → Statblock
→ create ThreatDraft
→ real provider generate
→ definition_invalid / HTTP 422
→ no candidate
```

PR `#454` synchronized the consumer contract and removed known timeout/provenance blockers. After that work, the GM manually completed the full accepted-revision lifecycle at least twice. The prerequisite is therefore closed for dispatch purposes. Do not create another proof-only R0-A PR unless a future regression reopens the gate.

#### `R0-B` — `IN_PROGRESS`, provisional capability pass

Hermes demonstrated:

- real multi-hop campaign investigation;
- uncertainty preservation and premise rejection;
- useful Threat directions;
- a provisional pasteable Threat description;
- pinned revision, matched nodes, source anchors, diagnostics, and recovery traces.

The remaining gaps are a reusable authoring artifact, evidence/query chips, explicit established/inferred/proposed/unknown state, and honest liveness. These are important authoring improvements but do not block the publication-first statblock path.

### Current critical gaps

- Accepted mechanics cannot yet be published as a governed create-or-connect Threat plus exact binding.
- A published Threat has no explicit Hermes query-and-hydration acceptance proof.
- Exact Threat mechanics are not projected from graph references.
- No durable generic placement contract exists.
- Plan, Build, and Ingest do not invoke one shared placement capability.
- Live combat still uses legacy artifact/path/title-shaped statblock identity.

## 4. Phase 0 — Accepted-revision prerequisite: closed

The required normal Workbench lifecycle has been manually confirmed at least twice:

```text
create ThreatDraft
→ real provider generate
→ edit
→ validate
→ accept
→ hard reload
→ reopen exact accepted identity
```

This is sufficient to begin the graph contract. Exact runtime IDs were not captured as a checked-in report, so do not represent this as CI or repository-attested evidence.

`R0-A-DIAGNOSTICS` remains a conditional future regression slice only. It is not the current next action.

**DOGFOOD BREAK 0:** satisfied for contract dispatch. Product graph publication still requires the governed `SBW09` path.

## 5. Phase I — Governed Threat publication

### `SBW08` / PR `#457` — Exact external-resource and Threat binding contract

Current dispatch authority: [`../Plans/HANDOFF-pr457-sbw08-statblock-binding-contract.md`](../Plans/HANDOFF-pr457-sbw08-statblock-binding-contract.md).

Freeze:

- the existing six-field exact mechanics locator;
- deterministic external statblock resource identity;
- exact immutable revision and digest;
- `ThreatStatblockBinding` identity and state;
- pinned-only v1 behavior;
- multiple-binding ambiguity behavior;
- stale revision behavior;
- mechanics-saved versus graph-published distinction;
- strict rejection of copied mechanics bodies.

Contract only. No product graph write, DungeonMind call, or Workbench/UI action.

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

Re-audit actual document load, local precedence, conflict, and reload behavior; dispatch only the missing capability.

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

Expose context-appropriate actions from Ingest, Build, Plan, Hermes results, graph inspection, and exact Threat projections. The initiating surface does not own the underlying write.

### `MAGIC-D4` — Place the same Threat from every relevant surface

Pass requires durable exact Threat/binding/revision/placement locators, editable contextual placement metadata, no copied or duplicate Threat identity, and no silent repinning.

**DOGFOOD BREAK 2:** Prepare one real scene using the placement path before combat integration.

## 8. Phase IV — Real combat integration

### `COMBAT01-contract`

Freeze exact source locator, insertion/idempotency, current-combat persistence, exact drilldown, migration/compatibility, and the rule that combat state never mutates graph or mechanics truth.

### `COMBAT01`

Evolve the existing server-backed `CombatRosterModule` beyond standalone JSON and legacy artifact/path references while preserving mutable runtime independence.

### `SBW15` — Exact `CombatantSeed`

Map one exact accepted revision or exact Threat placement to deterministic combat defaults and insert one or many runtime instances.

Mutable runtime state remains HP, initiative, conditions, notes, and defeated state.

### `MAGIC-D5` — Published Threat enters live combat

Pass requires:

- correct quantity creates distinct runtime instances;
- exact Threat/binding/revision/placement lineage survives reload;
- duplicate retry is deterministic or explicitly confirmed;
- combat changes do not alter graph truth or immutable mechanics;
- exact mechanics drilldown works from a roster row;
- legacy static/eval harnesses are not presented as the product integration.

## 9. Parallel authoring lane

These improve creation and editing but do not block publication now that the accepted-revision prerequisite is satisfied:

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

`MAGIC-D1` and `MAGIC-D2` remain desired end-to-end authoring proofs, but they do not block `SBW08–SBW10`.

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
| `R0-A` | `OPERATOR_CONFIRMED_PASS` | Closed for current dispatch; rerun only on future regression |
| `R0-B` | `IN_PROGRESS`; provisional grounding/description pass | Only the grounded-authoring enhancement lane |
| `MAGIC-D1` | DOGFOOD REQUIRED, parallel | Hermes-to-draft convenience proof |
| `MAGIC-D2` | DOGFOOD REQUIRED, parallel | Full connected authoring proof |
| `MAGIC-D3` | BLOCKED on `SBW08–SBW10` publication/query/projection implementation | Placement |
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
