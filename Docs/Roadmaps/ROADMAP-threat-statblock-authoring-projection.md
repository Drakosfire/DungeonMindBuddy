# Roadmap — Threat + Statblock Publication, Query, Placement, and Combat

**Status:** ACTIVE IMPLEMENTATION ROADMAP — PUBLICATION-FIRST  
**Date:** 2026-08-01  
**Repository anchor:** `36def9e102c3e58f0ad00cd8ad7a4fbfe15de594` — re-anchor base for SBW09c2b authority PR `#474` (contains merged `#476` + `#478`)  
**Latest completed Threat implementations:** `SBW09c1` merged in PR `#478`; `SBW09c2a` merged in PR `#476`  
**Latest Threat authority:** PR `#473` established SBW09c2a operation-to-revision lookup authority  
**Immediate implementation authority:**
- [`../Plans/HANDOFF-sbw09c2b-threat-publication-commit-recovery.md`](../Plans/HANDOFF-sbw09c2b-threat-publication-commit-recovery.md) — ACTIVE / NEXT PUBLICATION IMPLEMENTATION; re-anchored against merged c1/c2a; after this authority merges, the implementation PR records that immutable `origin/main` SHA in its body before code changes  
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
→ exact contribution-operation-to-immutable-revision recovery lookup
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
- Any durable commit intent permanently claims its proposal and blocks proposal supersession.
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
| `SBW09c1` | MERGED `#478` | Exact durable no-write publication proposal; sealed create/connect effect; replay/supersession; operation-scoped lifecycle lock. |
| `SBW09c2a` | MERGED `#476` | Public exact contribution-operation→immutable revision lookup; plural zero/one/many; manifest identity hardening. |

Current critical gaps:

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

### `SBW09c1`

PR `#478` proves a deterministic sealed create/connect effect can be durably proposed, replayed, and superseded with zero graph mutation and zero storage artifacts on refused or not-found paths.

### `SBW09c2a`

PR `#476` proves one exact contribution operation ID resolves to zero/one/many immutable revision manifests across the complete store, independent of head, with manifest world/revision identity hardening.

## 5. Phase I — Governed Threat publication

### `SBW09a` — MERGED `#462`

Exact immutable source snapshot, accepted-mechanics locator, expected parent, ready/stale/cancelled/superseded lifecycle, replay, and retry lineage. No graph write.

### `SBW09b` — MERGED `#467`

Revision-pinned Threat candidates plus durable explicit create-new/connect-existing/refuse resolution. No graph write.

### `SBW09c1` — Exact durable no-write proposal — MERGED `#478`

Authority: [`../Plans/HANDOFF-sbw09c1-threat-publication-proposal.md`](../Plans/HANDOFF-sbw09c1-threat-publication-proposal.md).

```text
exact operation + exact identity resolution
→ deterministic create/connect effects
→ sealed-proposal verification + expected-contribution reconstruction
→ durable exact review proposal
→ reload/replay/supersede without graph mutation
```

Create-new seals the Threat node, authored fields, resource, and binding. Connect-existing seals only resource and binding; it never rewrites the existing Threat. Refuse cannot produce a proposal. The merged service holds one operation-scoped `.proposal.lock` across every proposal mutation and dependency/graph read, creates zero storage artifacts on refused or not-found paths, computes the expected Graph contribution ID at prepare time, and returns `resolution_id=null` rather than a sentinel on GET failure paths.

### `SBW09c2a` — Exact operation-to-revision lookup — MERGED `#476`

Authority: [`../Plans/HANDOFF-sbw09c2a-operation-revision-lookup.md`](../Plans/HANDOFF-sbw09c2a-operation-revision-lookup.md).

```text
exact world_id + exact contribution operation_id
→ scan one immutable revision-ID snapshot
→ load every typed manifest with identity hardening
→ return zero / one / many exact matches in deterministic order
```

Why this is separate:

- `WorldGraphRevision.operation_ids` is immutable publication evidence; merged publication records the Graph contribution ID there.
- After a process crash, current head may have advanced or rolled back.
- `merge_contribution_to_revision` checks the original expected parent before idempotent-noop recovery.
- Application code must not scan storage internals or choose the first match.

Merged public signature: `find_world_graph_revisions_by_operation_id(root, world_id, operation_id) -> tuple[WorldGraphRevision, ...]`; plural zero/one/many semantics; results ordered by `(created_at, revision_id)` as evidence order only; `WorldGraphIntegrityError` when a manifest's embedded world/revision identity disagrees with its store path; no durable writes.

### `SBW09c2b` — Proposal-bound commit, durable recovery, exact verification — ACTIVE / NEXT PUBLICATION IMPLEMENTATION

Authority: [`../Plans/HANDOFF-sbw09c2b-threat-publication-commit-recovery.md`](../Plans/HANDOFF-sbw09c2b-threat-publication-commit-recovery.md), re-anchored against the merged c1/c2a contracts in PR `#474`.

The handoff consumes one exact durable c1 proposal and the public c2a lookup.

```text
claim exact active proposal under its lifecycle lock
→ revalidate exact operation + active resolution + sealed effect
→ persist exact commit intent
→ one Kernel contribution merge against exact expected parent
→ persist committed-unverified authority immediately when publication is proven
→ recover crashes by exact expected contribution ID across immutable revisions
→ verify exact contribution/support/Threat/resource/binding/rebuild/projection
→ persist committed-verified or truthful committed-unverified state
```

Frozen properties:

- the merged c1 operation-scoped `.proposal.lock`, exposed as `threat_publication_lifecycle_lock`, is the sole proposal/commit lifecycle lock;
- once any valid commit record exists, c1 refuses new-proposal creation and supersession with `publication_proposal_busy` and an explicit commit-claim message (no new c1 result label);
- c1 no-artifact fast paths remain valid only when both the proposal ledger and the commit ledger are absent;
- contribution reconstruction uses `proposal.created_by` as `confirming_principal`; the c2b request actor is commit audit identity only;
- no assertion subset selection exists;
- the recovery lookup key is the exact expected Graph contribution ID, not the SBW09a publication operation ID;
- every uncertain Kernel outcome — including typed `published=False` — reconciles through c2a exactly once before terminal classification;
- zero matches plus unchanged original parent and full authority revalidation may permit at most one exact retry;
- one match becomes a recovery candidate only after core publication-proof checks (parent, integrity load, contribution digest, replay entry);
- a unique match that fails those checks is ambiguity; multiple matches remain integrity ambiguity despite deterministic result ordering;
- head advance or rollback cannot hide an existing immutable revision;
- current head is never substituted for committed revision identity;
- commit success plus verification failure remains committed-but-unverified and cannot retry;
- graph failure never recreates, revises, or repins accepted mechanics;
- no direct graph-file write or second graph-governance framework is introduced.

Dispatch remains gated: PR `#474` must merge, then one implementation PR records that immutable `origin/main` SHA in its own body before any code changes and branches from it. The handoff is never rewritten to embed its own post-merge hash. No c2b code exists before then.

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
| `SBW09c1` | `MERGED #478` | Commit unlocked |
| `SBW09c2a` | `MERGED #476` | Recovery unlocked |
| `SBW09c2b` | ACTIVE / NEXT PUBLICATION IMPLEMENTATION | Query/hydration unlocked |
| `MAGIC-D1/D2` | DOGFOOD REQUIRED / PARALLEL | Authoring convenience proofs |
| `MAGIC-D3` | BLOCKED on `SBW09c2b`, `SBW10a`, `SBW10b` | Placement |
| `MAGIC-D4` | BLOCKED | Combat |
| `MAGIC-D5` | BLOCKED | Core roadmap completion |
| `AOW05` | DEFERRED | General architecture claim |

## 12. Immediate sequence

```text
SBW09c1 proposal MERGED #478 ─┐
                              ├→ SBW09c2b handoff re-anchored (PR #474)
SBW09c2a lookup MERGED #476  ─┘
→ merge #474
→ open implementation PR recording that immutable origin/main SHA in its body
→ dispatch SBW09c2b commit/receipt/recovery/verify
→ SBW10a query/hydration
→ SBW10b exact projection
→ dogfood MAGIC-D3
→ AOW03/AOW04 placement
→ dogfood MAGIC-D4
→ COMBAT01/SBW15
→ dogfood MAGIC-D5
```

SBW09c1 and c2a merged without production-path overlap. c2b is now the sole next publication implementation; after its authority merges, the implementation PR records that immutable `origin/main` SHA in its body before any c2b code exists.

## 13. Dispatch discipline

Every implementation handoff contains one mission/invariant, exact base/dependencies, bounded allowlist, state/persistence/fallback/identity/concurrency matrices, exact gate enabled, demolition declaration, owning-boundary tests, and stop conditions.

Pre-designed handoffs are strategic inputs until re-anchored. SBW09c2b is now re-anchored against the merged c1/c2a contracts in PR `#474`; it must not dispatch until that amendment merges, after which the implementation PR records the resulting immutable `origin/main` SHA in its body before code changes.

## 14. Completion

The core roadmap is complete when one exact accepted revision becomes durably published, queryable/hydrated, exactly projected, durably placed, and activated/reloaded in live combat. The general architecture claim requires `AOW05` to prove a second object type.
