# Roadmap — Threat + Statblock Publication, Query, Placement, and Combat

**Status:** ACTIVE IMPLEMENTATION ROADMAP — PUBLICATION-FIRST  
**Date:** 2026-08-01  
**Repository anchor:** `25ca4b941ce80e9cfa336c41c59667b9a3ed771d` — current `main`; the preceding placeholder/revert pair has no net file effect  
**Latest completed Threat implementation:** `SBW09b` merged in PR `#467`  
**Latest Threat authority:** PR `#471` established SBW09c1 proposal authority  
**Immediate implementation authorities:**
- [`../Plans/HANDOFF-sbw09c1-threat-publication-proposal.md`](../Plans/HANDOFF-sbw09c1-threat-publication-proposal.md)
- [`../Plans/HANDOFF-sbw09c2a-operation-revision-lookup.md`](../Plans/HANDOFF-sbw09c2a-operation-revision-lookup.md) after its docs authority merges

**Implementation tracker:** [`../Plans/PR-TRACKER-threat-statblock-authoring-projection.md`](../Plans/PR-TRACKER-threat-statblock-authoring-projection.md)  
**Publication re-anchor:** [`../Reports/REPORT-sbw09c-publication-reanchor-2026-08-01.md`](../Reports/REPORT-sbw09c-publication-reanchor-2026-08-01.md)  
**Lifecycle decision:** [`../Design/DECISION-grounded-authored-world-object-lifecycle.md`](../Design/DECISION-grounded-authored-world-object-lifecycle.md)  
**Dogfood runbook:** [`../Runbooks/RUNBOOK-authored-world-object-magic-moment-dogfood.md`](../Runbooks/RUNBOOK-authored-world-object-magic-moment-dogfood.md)

## 1. Product goal

```text
accepted immutable statblock revision
→ durable publication operation pinned to exact source + graph parent
→ explicit create-or-connect Threat resolution
→ exact durable no-write publication proposal
→ exact operation-to-immutable-revision recovery lookup
→ proposal-bound governed Threat + exact binding commit with durable receipt
→ Hermes query + exact mechanics hydration
→ exact Threat projection
→ durable cross-surface placement
→ exact placement/revision into live combat
→ mutable runtime state without mutating graph truth or mechanics
```

Hermes-grounded authoring remains a valuable entry path, not a prerequisite for publication.

The statblock effort is not complete at valid JSON, saved mechanics, identity resolution, proposal preparation, or graph commit alone. It is complete when one exact authored resource becomes queryable, projectable, placeable, and combat-usable through durable exact identity.

## 2. Authority and state boundaries

Distinct states:

```text
ThreatDraft
generated candidate
local working copy
validation receipt
accepted immutable statblock revision
publication operation
Threat identity resolution
reviewed graph proposal
commit intent / receipt
published Threat
ThreatStatblockBinding
object placement
combatant runtime instance
```

Rules:

- DungeonMind owns generated statblock contract semantics.
- Buddy owns draft orchestration, validation presentation, accepted-mechanics persistence, publication operations/proposals/receipts, projections, placements, and combat activation.
- The World Graph owns governed campaign identity and relationships.
- Exact consumers pin exact revision identity; no `latest` fallback.
- Saved mechanics are not automatically published.
- An operation is not an identity decision.
- An identity decision is not a proposal.
- A proposal is not a commit receipt.
- A receipt must resolve exact immutable revision authority; current head is not publication history.
- Publication is not placement; placement is not combat state.
- Mutable combat state never alters graph or immutable mechanics truth.

## 3. Completed foundation and current truth

| Slice | Status | Proven capability |
|---|---|---|
| `SBW01–05` | COMPLETE through `#404` | Client/readiness, drafts, generation, renderer, editing, validation. |
| `SBW07` | COMPLETE `#405–#409` | Immutable accepted mechanics persistence. |
| `SBW06` | COMPLETE through `#439` | Revise contracts, lineage, durable attempts, proposal/retry behavior. |
| PR `#454` | MERGED | Provider sync, timeout alignment, provenance honesty, Hermes UX unblockers. |
| Accepted-revision prerequisite | OPERATOR-CONFIRMED | Create→generate→edit→validate→accept→reload→reopen completed at least twice. |
| `SBW08` | MERGED `#457` | Strict external statblock resource + exact immutable `ThreatStatblockBinding`; no copied mechanics. |
| `SBW09a` | MERGED `#462` | Durable exact-source / expected-parent operation. |
| `SBW09b` | MERGED `#467` | Exact Threat candidate review and explicit create/connect/refuse decision. |

Current critical gaps:

- No durable exact Threat publication proposal implementation yet.
- No public Kernel lookup from exact operation ID to all immutable matching revisions.
- No durable Threat commit intent/receipt or crash recovery.
- No governed Threat + binding commit product path.
- No Hermes query/hydration acceptance proof or exact Threat projection.
- No durable generic placement contract.
- Live combat still uses legacy path/artifact/title-shaped statblock identity.

## 4. Closed evidence gates

### `R0-A`

Operator-confirmed real-provider create→generate→edit→validate→accept→hard reload→reopen passed at least twice. This is product evidence, not CI evidence.

### `SBW08`

PR `#457` proves deterministic resource/binding identity, immutable round-trip/projection, explicit multiple-binding behavior, and rejection of copied mechanics or typed collisions.

### `SBW09a`

PR `#462` proves later publication need not reconstruct source or parent authority from mutable state.

### `SBW09b`

PR `#467` proves ranked names/aliases never silently become durable identity; create/connect/refuse is explicit and exact.

## 5. Phase I — Governed Threat publication

### `SBW09a` — MERGED `#462`

Exact immutable source snapshot, accepted-mechanics locator, expected parent, ready/stale/cancelled/superseded lifecycle, replay, and retry lineage. No graph write.

### `SBW09b` — MERGED `#467`

Revision-pinned Threat candidates plus durable explicit create-new/connect-existing/refuse resolution. No graph write.

### `SBW09c1` — Exact durable no-write proposal — NEXT PRODUCT CAPABILITY

Authority: [`../Plans/HANDOFF-sbw09c1-threat-publication-proposal.md`](../Plans/HANDOFF-sbw09c1-threat-publication-proposal.md).

```text
exact operation + exact identity resolution
→ deterministic create/connect effects
→ existing sealed-proposal verification
→ durable exact review proposal
→ reload/replay/supersede without graph mutation
```

Create-new seals the Threat node, authored fields, resource, and binding. Connect-existing seals only resource and binding; it never rewrites the existing Threat. Refuse cannot produce a proposal.

### `SBW09c2a` — Exact operation-to-revision lookup — READ-ONLY PREREQUISITE

Authority: [`../Plans/HANDOFF-sbw09c2a-operation-revision-lookup.md`](../Plans/HANDOFF-sbw09c2a-operation-revision-lookup.md) after merge.

```text
exact world_id + exact operation_id
→ scan one immutable revision-ID snapshot
→ load every typed manifest
→ return zero / one / many exact matches in deterministic order
```

Why this is separate:

- `WorldGraphRevision.operation_ids` is immutable publication evidence.
- Internal storage already enumerates revision IDs and loads manifests.
- The public Kernel cannot currently resolve by operation ID.
- After a process crash, current head may have advanced or rolled back.
- `merge_contribution_to_revision` checks the original expected parent before idempotent-noop recovery.
- Application code must not scan storage internals or choose the first match.

This slice is read-only and may run in parallel with SBW09c1 because their production allowlists do not overlap.

### `SBW09c2b` — Proposal-bound commit, receipt/recovery, exact verification — BLOCKED ON c1 + c2a

Consumes one exact durable c1 proposal and the public c2a lookup.

Required flow:

```text
load exact active proposal and verify sealed effect
→ explicit proposal-id/digest/parent-bound confirmation
→ persist exact commit intent before Kernel write
→ one Kernel contribution merge against exact expected parent
→ persist committed-unverified receipt immediately after merge
→ verify exact contribution, parent, Threat/resource/binding, rebuild, and pinned projection
→ persist verified/degraded/failed terminal receipt
```

Recovery requirements:

- exact replay checks durable receipt before dependencies;
- a `committing` intent searches immutable revisions by exact contribution/operation ID before any retry;
- zero matches + unchanged expected parent may retry the exact same contribution once;
- one match is a recovery candidate only after exact parent/contribution/effect verification;
- multiple matches fail closed as integrity ambiguity;
- head advance or rollback cannot hide an existing committed revision;
- commit success plus verification failure remains committed-but-unverified and must not retry;
- graph failure never recreates, revises, or repins accepted mechanics;
- no direct graph-file write or second graph-governance framework.

The active c1 proposal—not mutable ThreatDraft, operation, resolution, label, or current head—is the complete content authority. c2b must re-anchor against the actual c1 implementation and decide the exact proposal-claim/lock boundary before dispatch.

The old bundled SBW09 handoff remains superseded research.

## 6. Phase II — Queryability, hydration, and projection

### `SBW10a` — Threat query and exact mechanics hydration

Hermes retrieves published Threats by exact/alias name, role/capability, graph relationship, and campaign context.

```text
Threat identity
→ exact ThreatStatblockBinding
→ exact accepted statblock revision
→ mechanics from owning store
```

Zero/one/many bindings are explicit; there is no implicit winner.

Pass probes include fortification-damaging threats, Mireward-connected threats, insectoid siege mechanics, and exact bound statblock identity.

### `SBW10b` — Exact-revision Threat projection

Compact/full views prioritize role, threat kind, game-relevant mechanics, encounter relevance, connected graph objects, and exact revision status. Provenance remains inspectable without dominating the default card.

### `MAGIC-D3`

```text
accepted revision
→ operation
→ identity decision
→ proposal
→ governed commit + recoverable receipt
→ reload exact revision
→ Hermes discovery + hydration
→ exact Threat projection
```

Pass requires no duplicate/silent merge, exact lifecycle identity surviving reload, recoverable graph failure, relationship/capability discovery, exact mechanics hydration, and no silent rebinding to newer mechanics.

**DOGFOOD BREAK 1:** Use the published Threat from Hermes and graph inspection before placement work.

## 7. Phase III — Durable placement and shared capabilities

- `SBW11`: re-audit Plan hydration only.
- `SBW12`: exact revision embed; embed is not placement.
- `AOW03`: durable `ObjectPlacementV1` with exact Threat/binding/revision/host/quantity/role/trigger/visibility/notes/local adjustments.
- `AOW04`: shared capability routing; initiating surface does not own writes.
- `MAGIC-D4`: same exact Threat can be durably placed and reopened without repinning.

**DOGFOOD BREAK 2:** Prepare one real scene through placement before combat integration.

## 8. Phase IV — Real combat integration

- `COMBAT01-contract`: exact source locator, insertion/idempotency, persistence, drilldown, migration.
- `COMBAT01`: evolve live combat persistence beyond legacy statblock path/title identity.
- `SBW15`: deterministic exact-revision or exact-placement `CombatantSeed`.
- `MAGIC-D5`: distinct runtime instances, exact lineage/reload, no graph/mechanics mutation from combat state, exact drilldown.

## 9. Parallel authoring lane

R0-B closeout, AOW01/AOW02, authoring artifact/library, graph chips, SBW06d, revise UX, editor expansion, and liveness/telemetry remain parallel enhancements. `MAGIC-D1` and `MAGIC-D2` remain desired authoring proofs but do not block publication-first work.

## 10. Later revision evolution and media

`SBW13` immutable child revision, `SBW14` explicit binding adoption, explicit embed/placement repin successors, `SBW16–18` media work, and `AOW05` second-domain proof remain later.

## 11. Gate ledger

| Gate | Status | Blocks |
|---|---|---|
| `R0-A` | `OPERATOR_CONFIRMED_PASS` | Closed unless regression |
| `R0-B` | `IN_PROGRESS` | Grounded-authoring lane only |
| `SBW08` | `MERGED #457` | Operation unlocked |
| `SBW09a` | `MERGED #462` | Identity unlocked |
| `SBW09b` | `MERGED #467` | Proposal unlocked |
| `MAGIC-D1/D2` | DOGFOOD REQUIRED / PARALLEL | Authoring convenience proofs |
| `MAGIC-D3` | BLOCKED on `SBW09c1`, `SBW09c2a`, `SBW09c2b`, `SBW10a`, `SBW10b` | Placement |
| `MAGIC-D4` | BLOCKED | Combat |
| `MAGIC-D5` | BLOCKED | Core roadmap completion |
| `AOW05` | DEFERRED | General architecture claim |

## 12. Dispatch discipline

Every implementation handoff contains one mission/invariant, exact base/dependencies, bounded allowlist, state/persistence/fallback/identity/concurrency matrices, exact gate enabled, demolition declaration, owning-boundary tests, and stop conditions.

Pre-designed handoffs are strategic inputs until re-anchored. SBW09c2b must not dispatch from this roadmap alone; it must be rewritten against the merged c1 proposal contract and c2a public lookup.

## 13. Completion

The core roadmap is complete when one exact accepted revision becomes durably published, queryable/hydrated, exactly projected, durably placed, and activated/reloaded in live combat. The general architecture claim requires `AOW05` to prove a second object type.