# Roadmap — Threat + Statblock Publication, Query, Placement, and Combat

**Status:** ACTIVE IMPLEMENTATION ROADMAP — PUBLICATION-FIRST  
**Date:** 2026-08-01  
**Repository anchor:** `35c3d34c6db44371cba81eb65883b2b76e011cad` — current main after merged PR `#469`; PR `#467` is the latest completed Threat-publication implementation  
**Latest completed publication foundation:** `SBW09b` merged in PR `#467` (with SBW09a in PR `#462` and SBW08 in PR `#457`)  
**Immediate implementation authority:** [`../Plans/HANDOFF-sbw09c1-threat-publication-proposal.md`](../Plans/HANDOFF-sbw09c1-threat-publication-proposal.md); dispatch only after this authority merges and the exact immutable main SHA is recorded  
**Implementation tracker:** [`../Plans/PR-TRACKER-threat-statblock-authoring-projection.md`](../Plans/PR-TRACKER-threat-statblock-authoring-projection.md)  
**Current re-anchor report:** [`../Reports/REPORT-sbw09c-publication-reanchor-2026-08-01.md`](../Reports/REPORT-sbw09c-publication-reanchor-2026-08-01.md)  
**Lifecycle decision:** [`../Design/DECISION-grounded-authored-world-object-lifecycle.md`](../Design/DECISION-grounded-authored-world-object-lifecycle.md)  
**Dogfood runbook:** [`../Runbooks/RUNBOOK-authored-world-object-magic-moment-dogfood.md`](../Runbooks/RUNBOOK-authored-world-object-magic-moment-dogfood.md)

## 1. Product goal

The critical architecture proof is:

```text
accepted immutable statblock revision
→ durable publication operation pinned to exact source + graph parent
→ explicit create-or-connect Threat resolution
→ exact durable no-write publication proposal
→ proposal-bound governed Threat + exact binding commit
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

The statblock effort is not complete at valid JSON, saved mechanics, an identity decision, or a graph node. It is complete only when one exact authored resource becomes a queryable, projectable, placeable, and combat-usable campaign object.

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
- Buddy owns draft orchestration, validation presentation, accepted-mechanics persistence, publication operations, proposals, projections, placements, and combat activation.
- The World Graph owns governed campaign identity and relationships.
- Exact consumers pin exact revision identity; no `latest` fallback.
- Saved mechanics are not automatically published.
- A publication operation is not an identity decision.
- An identity decision is not a reviewed proposal.
- A reviewed proposal is not graph publication.
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
| `SBW09a` | MERGED `#462` | Durable no-write publication operation pinned to one exact source snapshot and expected parent with replay/stale/retry lineage. |
| `SBW09b` | MERGED `#467` | Exact revision-pinned Threat candidate review plus durable explicit create-new/connect-existing/refuse identity resolution. |

Current critical gaps:

- The exact operation and identity decision cannot yet become a durable reviewed publication proposal.
- Accepted mechanics cannot yet be committed as a governed Threat + exact binding.
- A committed publication has no durable Threat-specific receipt/recovery contract.
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

PR `#457` proves deterministic external resource identity, strict pinned binding identity, immutable round-trip/projection, multiple bindings without an implicit winner, and rejection of copied mechanics and typed collisions.

### `SBW09a`

PR `#462` proves that later publication never needs to reconstruct source or parent authority from mutable current state.

### `SBW09b`

PR `#467` proves that the system preserves the GM's exact create-new, connect-existing, or refuse decision and never promotes a ranked name/alias candidate into identity authority automatically.

## 5. Phase I — Governed Threat publication

### `SBW09a` — Durable publication operation ledger — MERGED `#462`

Historical authority: [`../Plans/HANDOFF-sbw09a-publication-operation-ledger.md`](../Plans/HANDOFF-sbw09a-publication-operation-ledger.md).

Proven no-write capability:

```text
mechanics-saved ThreatDraft
+ exact AcceptedMechanicsRef
+ caller-reviewed expected World Graph parent
→ durable publication source snapshot
→ ready/stale/cancelled/superseded operation lifecycle
→ exact reload and explicit retry lineage
```

No identity resolution, proposal, graph contribution, graph mutation, DMS call, or ThreatDraft mutation occurs.

### `SBW09b` — Explicit create-or-connect Threat resolution — MERGED `#467`

Historical authority: [`../Plans/HANDOFF-sbw09b-threat-identity-resolution.md`](../Plans/HANDOFF-sbw09b-threat-identity-resolution.md).

Proven no-write capability:

- revision-pinned Threat-only candidate inspection;
- exact candidate-set digest and full candidate snapshots;
- explicit `create_new`, `connect_existing`, or `refuse` decision;
- deterministic proposed Threat ID for create-new;
- exact reviewed target node ID for connect-existing;
- replay-safe durable decision and explicit supersession;
- no graph, mechanics, or ThreatDraft mutation.

### `SBW09c1` — Exact durable no-write Threat publication proposal — NEXT

Current implementation authority: [`../Plans/HANDOFF-sbw09c1-threat-publication-proposal.md`](../Plans/HANDOFF-sbw09c1-threat-publication-proposal.md).

Consumes one exact ready SBW09a operation and one exact active create/connect SBW09b resolution.

Required flow:

```text
construct exact create-new or connect-existing effects
→ reuse existing sealed-proposal digest/verification authority
→ persist one exact review proposal
→ reload/replay/supersede without graph mutation
```

Create-new seals the exact Threat node, deterministic authored description/kind/role/tag attributes, external resource, and exact primary binding. Connect-existing seals only the external resource and exact binding; it does not rewrite the existing Threat. Refuse cannot mint a proposal.

### `SBW09c2` — Proposal-bound commit, receipt/recovery, and exact verification — BLOCKED ON `SBW09c1`

Consumes the exact durable SBW09c1 proposal.

Required flow:

```text
revalidate exact operation + active resolution + sealed proposal + parent
→ proposal-bound explicit confirmation
→ one Kernel contribution merge against exact expected parent
→ durable exact commit receipt / ambiguous-outcome recovery
→ verify Threat/resource/binding at exact committed revision
```

Required properties:

- no current-head/latest substitution;
- atomic Threat/resource/binding result or no graph revision;
- exact contribution/revision identity survives response loss and restart;
- retry reconciles a known receipt before any recommit;
- completed commit plus verification failure reports committed-but-unverified;
- graph failure never recreates, revises, or moves accepted mechanics;
- no direct graph-file write or second graph-governance framework.

A separate `SBW09c3` is not currently justified because existing graph governance already provides exact-revision rebuild/projection verification and honest post-commit verification statuses. Split again only if implementation reconnaissance proves a missing public recovery boundary.

The old bundled `HANDOFF-sbw09-governed-threat-binding-publication.md` remains superseded research and must not be dispatched.

## 6. Phase II — Queryability, hydration, and projection

### `SBW10a` — Threat query and exact mechanics hydration

Hermes retrieves a published Threat by exact/alias name, role or capability, graph relationship, and location/faction/event/campaign context.

```text
Threat identity
→ exact ThreatStatblockBinding
→ exact accepted statblock revision
→ hydrated mechanics from the owning store
```

The graph stores the exact binding, not a copied statblock definition. Zero/one/many binding behavior must be explicit; there is no implicit winner.

Pass probes include:

- “What threats can damage fortifications?”
- “Which threats are connected to Mireward?”
- “Show the mechanics for the insectoid siege creature.”
- “What statblock is bound to this Threat?”

### `SBW10b` — Exact-revision Threat projection

Open compact and full Threat views from graph/object references. Default presentation prioritizes role and threat kind, important mechanics, encounter relevance, connected graph objects, and exact bound revision status. Evidence/provenance remains inspectable without dominating the card.

### `MAGIC-D3` — Publish, query, hydrate, and reopen

```text
accepted exact revision
→ durable publication operation
→ explicit create/connect
→ durable reviewed proposal
→ governed publish
→ reload graph revision
→ find through Hermes
→ open exact mechanics projection
```

Pass requires no duplicate or silent merge; exact operation/source/resolution/proposal/binding survives reload; graph failure is recoverable; relationship/capability query finds the Threat without exact-name prompting; projection hydrates the exact bound revision; and newer mechanics do not silently move the binding.

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

Pass requires quantity creating distinct runtime instances; exact Threat/binding/revision/placement lineage surviving reload; deterministic or explicitly confirmed duplicate retry; combat state not altering graph/mechanics; exact mechanics drilldown from a roster row; and no legacy static/eval harness presented as product integration.

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
| `SBW09a` | `MERGED #462` | Identity resolution unlocked |
| `SBW09b` | `MERGED #467` | Publication proposal unlocked |
| `MAGIC-D1` | DOGFOOD REQUIRED, parallel | Hermes-to-draft convenience proof |
| `MAGIC-D2` | DOGFOOD REQUIRED, parallel | Full connected authoring proof |
| `MAGIC-D3` | BLOCKED on `SBW09c1–c2` and `SBW10a–b` | Placement |
| `MAGIC-D4` | BLOCKED on published queryable Threat | Combat |
| `MAGIC-D5` | BLOCKED on exact placements/combat contract | Core roadmap completion |
| `AOW05` | DEFERRED | General architecture claim |

## 12. Dispatch discipline

Every implementation handoff must contain one mission/invariant, exact base/dependencies, bounded path allowlist, durable state and transition matrices, success/miss/failure/retry/reload/stale/concurrency/predecessor behavior, the exact gate enabled, demolition declaration, owning-boundary tests, and stop conditions that report architectural mismatch instead of widening scope.

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