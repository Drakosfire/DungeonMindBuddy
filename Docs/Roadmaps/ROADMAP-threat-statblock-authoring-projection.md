# Roadmap — Threat + Statblock Publication, Query, Placement, and Combat

**Status:** ACTIVE IMPLEMENTATION ROADMAP — PUBLICATION-FIRST  
**Date:** 2026-07-30  
**Foundation anchor:** `f450885493108ce5d0c46b5a0e9d4e42173e3c8c` — merged PR `#457`
**Authority-sync main:** `c371d43178a2b83da299319a047f93bae50d0959` — current `main` merge containing the unnumbered handoff and tracker correction
**SBW09a implementation base:** `c371d43178a2b83da299319a047f93bae50d0959` — or a later deliberate authority-sync commit
**Latest completed publication foundation:** `SBW08` merged in PR `#457`  
**Immediate implementation authority:** [`../Plans/HANDOFF-sbw09a-publication-operation-ledger.md`](../Plans/HANDOFF-sbw09a-publication-operation-ledger.md)  
**Implementation tracker:** [`../Plans/PR-TRACKER-threat-statblock-authoring-projection.md`](../Plans/PR-TRACKER-threat-statblock-authoring-projection.md)  
**Current re-anchor report:** [`../Reports/REPORT-threat-statblock-roadmap-reanchor-2026-07-30.md`](../Reports/REPORT-threat-statblock-roadmap-reanchor-2026-07-30.md)  
**Lifecycle decision:** [`../Design/DECISION-grounded-authored-world-object-lifecycle.md`](../Design/DECISION-grounded-authored-world-object-lifecycle.md)  
**Dogfood runbook:** [`../Runbooks/RUNBOOK-authored-world-object-magic-moment-dogfood.md`](../Runbooks/RUNBOOK-authored-world-object-magic-moment-dogfood.md)

## 1. Product goal

The critical architecture proof is:

```text
accepted immutable statblock revision
→ durable publication operation pinned to exact source + graph parent
→ explicit create-or-connect Threat resolution
→ governed Threat + exact binding commit
→ Hermes query + exact mechanics hydration
→ exact Threat projection
→ durable cross-surface placement
→ exact placement/revision into live combat
→ mutable runtime state without mutating graph truth or mechanics
```

Hermes-grounded authoring remains a valuable entry path, not a prerequisite for publication:

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
publication operation
Threat identity resolution
reviewed graph proposal
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
- A publication operation is not graph publication.
- Publication is not placement.
- Placement is not combat runtime state.
- Mutable combat changes never alter graph or immutable mechanics truth.

## 3. Completed foundation and current truth

| Slice | Status | Proven capability |
|---|---|---|
| `SBW01` | MERGED `#386` | Server-owned DungeonMind statblock client/readiness boundary. |
| `SBW02` | MERGED `#387` | Durable versioned `ThreatDraftV1` CRUD. |
| `SBW03` | MERGED `#388` | Exact draft-version candidate generation contract. |
| `SBW04` | MERGED `#397` | Shared semantic renderer and candidate Workbench. |
| `SBW05a–c` | COMPLETE `#398`, `#402`, `#404` | Dedicated editing plus authoritative validation. |
| `SBW07 contract/a–c` | COMPLETE `#405–#409` | Immutable accepted statblock/revision persistence. |
| `SBW06 contract/a–c` | MERGED through `#439` | Revise contracts, lineage, durable attempts, proposal inspection, retry behavior. |
| PR `#454` | MERGED | Provider-contract sync, generation timeout alignment, provenance honesty, Hermes UX unblockers. |
| Accepted-revision prerequisite | OPERATOR-CONFIRMED | GM completed create → generate → edit → validate → accept → hard reload → reopen at least twice. |
| `SBW08` | MERGED `#457` | Strict external statblock resource and exact immutable `ThreatStatblockBinding` in World Graph revisions and projections; no copied mechanics; deterministic identity; fail-closed collisions. |

Current critical gaps:

- There is no durable publication operation pinned to an exact mechanics-saved source and expected graph parent.
- The GM cannot choose create-new versus connect-existing for publication.
- Accepted mechanics cannot yet be committed as a governed Threat + exact binding.
- A published Threat has no Hermes query/hydration acceptance proof.
- Exact Threat mechanics are not exposed in the product projection.
- No durable generic placement contract exists.
- Live combat still uses legacy artifact/path/title-shaped statblock identity.

## 4. Evidence gates already closed

### `R0-A`

The normal real-provider Workbench lifecycle was manually confirmed at least twice:

```text
create ThreatDraft
→ generate
→ edit
→ validate
→ accept
→ hard reload
→ reopen exact accepted identity
```

This is operator-reported product evidence, not CI evidence. Do not dispatch another proof-only R0-A slice unless a future regression reopens it.

### `SBW08`

PR `#457` proves:

- deterministic external statblock resource identity;
- strict exact binding contract;
- immutable revision/digest pinning;
- contribution materialization and reload;
- revision-pinned typed projection;
- multiple bindings without implicit winner;
- rejection of copied mechanics and typed-object collisions.

The graph contract is complete enough to begin publication orchestration. It does not itself publish a product Threat.

## 5. Phase I — Governed Threat publication

### `SBW09a` — Durable publication operation ledger

Current dispatch authority: [`../Plans/HANDOFF-sbw09a-publication-operation-ledger.md`](../Plans/HANDOFF-sbw09a-publication-operation-ledger.md), from implementation base `c371d43178a2b83da299319a047f93bae50d0959` or a later deliberate authority-sync commit. No future PR number is assigned until a pull request opens.

Deliver one no-write capability:

```text
mechanics-saved ThreatDraft
+ exact AcceptedMechanicsRef
+ caller-reviewed expected World Graph parent
→ durable publication source snapshot
→ ready/stale/cancelled/superseded operation lifecycle
→ exact reload and explicit retry lineage
```

Required properties:

- server-owned snapshot, never client-supplied;
- complete publication-relevant ThreatDraft fields;
- exact accepted mechanics ref and canonical source digest;
- exact expected graph parent, never silent current/latest substitution;
- one active ready/stale operation per draft;
- exact operation replay and changed-input conflict;
- monotonic stale reasons for source or parent drift;
- source-drift retry leaves the stale operation active until explicit cancellation; only then may a new begin establish a new authority;
- exact retry replay detects an already-created child operation before enforcing the stale-active slot;
- atomic cancellation/retry lineage;
- publication ledger and ThreatDraft roots are `repo_root()` while World Graph reads use independently configured `world_graph_root()`;
- the public begin/read/refresh/cancel/retry route table, typed request/response envelopes, stable result codes, and HTTP mappings are frozen before implementation;
- nested accepted-mechanics wire fields reject omission before `AcceptedMechanicsRefV1` defaults can repair them;
- no DMS call, graph contribution, graph mutation, or ThreatDraft mutation.

Why this is separate:

- `ThreatDraftV1` is a current-state store, not a historical version archive;
- later create/connect and commit must not reconstruct authority from mutable current state;
- retry/recovery needs a durable root before it can safely own identity or graph effects.

What remains false after merge:

- no Threat identity choice;
- no graph proposal or confirmation token;
- no graph commit or publication receipt;
- no Workbench action.

### `SBW09b` — Explicit create-or-connect Threat resolution

Consumes one ready SBW09a operation.

The GM can:

- create a new Threat;
- connect accepted mechanics to an exact existing Threat;
- inspect likely matches;
- reject incorrect matches;
- avoid silent duplicate identity.

Required output is a durable or proposal-bound exact identity decision referencing the publication operation. Labels and aliases assist review but never become final durable identity by first-win fallback.

### `SBW09c` — Governed Threat + exact binding commit

Consumes the SBW09a operation plus the SBW09b identity decision.

Required flow:

```text
build exact Threat/resource/binding effects
→ prepare no-write review
→ confirm proposal-bound write against exact parent
→ immutable World Graph revision
→ verify exact Threat/resource/binding at committed revision
```

A graph failure must never recreate or change the accepted mechanics revision. Post-commit verification failure must retain the exact commit receipt and report committed-but-unverified truth.

The old bundled `HANDOFF-sbw09-governed-threat-binding-publication.md` is superseded research. It must not be dispatched as one PR.

## 6. Phase II — Queryability, hydration, and projection

### `SBW10a` — Threat query and exact mechanics hydration

Hermes retrieves a published Threat by:

- exact or alias name;
- role or capability;
- graph relationship;
- location, faction, event, or campaign context.

Resolution path:

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

Open compact and full Threat views from graph/object references. Default presentation prioritizes:

- role and threat kind;
- important mechanics;
- encounter relevance;
- connected graph objects;
- exact bound revision status.

Evidence, provenance, and internal scores remain inspectable without dominating the default projection.

### `MAGIC-D3` — Publish, query, hydrate, and reopen

```text
accepted exact revision
→ durable publication operation
→ explicit create/connect
→ governed publish
→ reload graph revision
→ find through Hermes
→ open exact mechanics projection
```

Pass requires:

- no duplicate or silent merge;
- exact operation/source/binding survives reload;
- mechanics-saved and graph-published remain distinct;
- graph failure is recoverable;
- relationship/capability query finds the Threat without exact-name prompting;
- projection hydrates the exact bound revision;
- newer mechanics do not silently move the binding.

**DOGFOOD BREAK 1:** Use the published Threat from both Hermes and graph inspection before placement work begins.

## 7. Phase III — Durable placement and shared capabilities

### `SBW11` — Re-audit Plan hydration only

Re-audit actual document load, local precedence, conflict, and reload behavior; dispatch only missing capability.

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

### `MAGIC-D4`

Pass requires durable exact Threat/binding/revision/placement locators, editable contextual metadata, no duplicate Threat identity, and no silent repinning.

**DOGFOOD BREAK 2:** Prepare one real scene using placement before combat integration.

## 8. Phase IV — Real combat integration

### `COMBAT01-contract`

Freeze exact source locator, insertion/idempotency, current-combat persistence, exact drilldown, migration/compatibility, and the rule that combat state never mutates graph or mechanics truth.

### `COMBAT01`

Evolve the server-backed `CombatRosterModule` beyond standalone JSON and legacy artifact/path references while preserving mutable runtime independence.

### `SBW15`

Map one exact accepted revision or exact Threat placement to deterministic combat defaults and insert one or many runtime instances.

Mutable runtime state remains HP, initiative, conditions, notes, and defeated state.

### `MAGIC-D5`

Pass requires:

- quantity creates distinct runtime instances;
- exact Threat/binding/revision/placement lineage survives reload;
- duplicate retry is deterministic or explicitly confirmed;
- combat changes do not alter graph truth or immutable mechanics;
- exact mechanics drilldown works from a roster row;
- legacy static/eval harnesses are not presented as product integration.

## 9. Parallel authoring lane

These improve creation/editing but do not block publication:

| ID | Outcome |
|---|---|
| `R0-B` closeout | Capture final authoring trace/verdict. |
| `AOW01` | Grounded authored-object context envelope. |
| `AOW02` | Hermes “Develop as Threat” action. |
| `AUTHORING-ARTIFACT` | Stable editable/copyable markdown artifact with adjacent provenance. |
| `GRAPH-CHIPS` | Response evidence chips and query node anchors. |
| `AUTHORING-LIBRARY` | Browse/reopen/update ThreatDrafts and accepted mechanics. |
| `SBW06d` | Revise from exact accepted locator; no latest fallback. |
| Revise UX cleanup | GM-facing instruction flow rather than transport choreography. |
| Editor expansion | Dedicated speed, attack, damage, and save controls. |
| Liveness/telemetry | Honest long-turn state and privacy-safe traces. |

`MAGIC-D1` and `MAGIC-D2` remain desired end-to-end authoring proofs, but they do not block `SBW09–SBW10`.

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
| `R0-A` | `OPERATOR_CONFIRMED_PASS` | Closed unless regression |
| `R0-B` | `IN_PROGRESS`; provisional grounding/description pass | Grounded-authoring enhancement lane only |
| `SBW08` | `MERGED #457` | Publication operation unlocked |
| `MAGIC-D1` | DOGFOOD REQUIRED, parallel | Hermes-to-draft convenience proof |
| `MAGIC-D2` | DOGFOOD REQUIRED, parallel | Full connected authoring proof |
| `MAGIC-D3` | BLOCKED on `SBW09a–c` and `SBW10a–b` | Placement |
| `MAGIC-D4` | BLOCKED on published queryable Threat | Combat |
| `MAGIC-D5` | BLOCKED on exact placements/combat contract | Core roadmap completion |
| `AOW05` | DEFERRED | General architecture claim |

## 12. Dispatch discipline

Every implementation handoff must contain:

- one mission and one invariant;
- exact authority-sync base SHA and dependencies; every base/head verification command must use that same SHA;
- bounded path allowlist;
- durable contracts and transition tables before stateful implementation;
- success, miss, failure, retry, reload, stale, concurrency, and predecessor behavior;
- the exact dogfood gate enabled;
- a demolition declaration;
- tests at the owning boundary;
- stop conditions that report architectural mismatch instead of widening scope.

Pre-designed handoffs are strategic inputs, not dispatch authority. Re-anchor each slice against current code and product evidence.

## 13. Completion

The core Threat + Statblock roadmap is complete when:

```text
one exact accepted revision
→ durable governed publication
→ Hermes query + exact hydration
→ exact projection
→ durable cross-surface placement
→ exact live-combat activation and reload
```

The connected authoring experience is complete when `MAGIC-D1` and `MAGIC-D2` also pass.

The general architecture claim is complete only when `AOW05` proves a second object type through the same publication, query, projection, placement, and activation seams.
