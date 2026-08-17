---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: CUTOVER — observational correspondence and snapshot drift
  - Flow: CUTOVER
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-CUTOVER-observational-correspondence-drift.md
  - Design PR: steward-designated CUTOVER design PR
  - Implementation repository: Drakosfire/DungeonMind

  ## Verification pointer
  - Buddy design base: `1d8ec2d24439648644dff87857a85b4bf83efda9`
  - DungeonMind implementation base: `d2204dd0901237d8b446b4f2363f896306e32e6f`
  - Accepted source bundle blob: `274cdd9e6d38d5a00aa43d780779e95a7919d975`
  - Accepted DungeonMind revision: `rev:34b1f8e2625d5ba693fc726a2a1a4720`

  Define and prove the first read-only CUTOVER correspondence contract: an exact
  Buddy authority snapshot can be classified against the adopted DungeonMind
  world as corresponding, stale, or mismatched without switching reads/writes
  or introducing a second writer.
---

# HANDOFF — observational correspondence and snapshot drift

**Created:** 2026-08-17
**Status:** ACTIVE DESIGN HANDOFF — implementation may dispatch only after this CUTOVER design PR is accepted/merged and the §2 steward Buddy sync has landed
**Canonical handoff path:** `Docs/Plans/HANDOFF-CUTOVER-observational-correspondence-drift.md`
**Conversation/workstream:** `CUTOVER — observational correspondence and snapshot drift`
**Flow / owner:** `CUTOVER`
**Direction:** DESIGN → CODE → REVIEW
**Buddy design base:** `1d8ec2d24439648644dff87857a85b4bf83efda9`
**DungeonMind implementation base:** `d2204dd0901237d8b446b4f2363f896306e32e6f`
**Suggested implementation branch:** `dnd/cutover-observational-correspondence-drift-v1`
**Suggested implementation PR title:** `CUTOVER: prove observational correspondence and snapshot drift`

> Repository authority: Buddy [`AGENTS.md`](../../AGENTS.md), [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md), [`Docs/Plans/PR-TRACKER-campaign-supergraph.md`](PR-TRACKER-campaign-supergraph.md), [`Docs/Design/STATUS-world-graph-continuity-spine.md`](../Design/STATUS-world-graph-continuity-spine.md), and [`Docs/Roadmaps/ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md).
>
> This is a rare steward-designated design PR. Routine state maintenance is not a design PR. The backward-looking Buddy authority sync for this completed design predecessor is a steward direct guarded commit after merge (§2); it must not pre-mark the implementation complete.

## §1 Mission and merge-ready invariant

**Mission:** CUTOVER can determine whether one exact Buddy authority snapshot and one durable DungeonMind adopted world are observationally the same authority state, so stale or incompatible snapshots fail visibly before any product read/write switch.

**Merge-ready invariant:** Given one exact Buddy adoption bundle identity and one durable DungeonMind world/adoption receipt, a read-only correspondence check returns a deterministic classification bound to both exact revisions: `CORRESPONDING` only when the durable DungeonMind state reconstructs the sealed source semantics and authority history represented by that bundle; `STALE` when the supplied Buddy authority snapshot is a different otherwise-valid source snapshot than the one DungeonMind adopted; and `MISMATCH`/integrity failure when the claimed same snapshot cannot be reconstructed equivalently. No classification may mutate either system or imply product-authority cutover.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes**, if the slice remains a read-only correspondence classifier/proof. Catch-up, writer transfer, read switching, rollback execution, and mutation are separate capabilities. |
| Most likely adversarial sequence | Exact #34 state corresponds → Buddy snapshot advances → checker silently keeps reporting current because only world ID/shape is compared. |
| Will §7 detect that failure? | Yes. A changed-but-valid source snapshot must classify `STALE`, while same-identity semantic/history corruption must classify `MISMATCH`. |
| Easiest owning boundary to under-test | History/evidence equivalence. Graph shape alone can stay 469/323/3/5 while correction, contribution, identity, or evidence authority drifts. |
| Fact that forces stop/split | Correspondence cannot be decided without introducing replication/catch-up, a second writer, a product read switch, or a new durable synchronization protocol. |

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | Buddy Campaign Supergraph architecture + tracker/status/roadmap at `1d8ec2d2…` |
| Completed predecessor | DungeonMind PR #34, head `935d3d9117442a92ef2dd8f11967fed20f863ea1`, merge `d2204dd0901237d8b446b4f2363f896306e32e6f`, Review Cycle 2 `4948479110` |
| Exact source snapshot | Git blob `274cdd9e6d38d5a00aa43d780779e95a7919d975`; bundle SHA-256 `90574dfc4101e4198c7fd96478d6f49e65aa534d0aa91fa41a9a17da9d49695f`; source world revision `rev:0c644e56b45bcaac709012206e3e41c2`; source graph payload `0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2` |
| Exact adopted state | adoption `adoption:eldyrwild:dungeonmind-v6:rev:0c644e56b45bcaac709012206e3e41c2`; published revision `rev:34b1f8e2625d5ba693fc726a2a1a4720`; payload `047214f19e3a2d22b1cf3e0596283844ef34853dd2e4f38d341c6b212ae320ef`; 469 objects / 323 relationships / 3 secondary aspects / 5 aspect-selected; 83/83 source revisions; 93 GraphContributionV2; 13 IdentityDecisionRecordV2 |
| Implementation owner | **DungeonMind**, because correspondence becomes true or false at the durable adopted-world/readback boundary. Buddy remains the source-authority producer and supplies exact bundle identity. |
| Named successor | catch-up/quiescence strategy and living-write ownership design |
| What remains false | Product reads/writes are not switched; DungeonMind is not the living writer; no catch-up occurs; no rollback workflow; no first post-cutover mutation; Buddy authority is not demolished. |
| Explicit non-goals | CDC/replication, dual writes, product routing, write ownership transfer, automatic re-adoption, catch-up execution, rollback execution, demolition |
| Runtime/state ownership | Read-only against an isolated PostgreSQL target seeded by #34 fixture/proof. No mutation of a shared product world. |
| Parallel collision hotspot | PostgreSQL integration database namespace; serialize with any other mutating DND integration lane. |

### Backward-looking atomic authority sync — steward Buddy commit, not the DND PR

The atomic document sync for **this completed design predecessor** lives in DungeonMindBuddy and cannot travel in the DungeonMind implementation PR. Per `AGENTS.md` (cross-repository sync follows the direct guarded steward rule), the steward applies it as a direct guarded Buddy commit after this design PR merges and before the DungeonMind implementation is dispatched. These edits are maintenance of facts already true at that point; they are not a claim that the implementation slice is complete.

Steward Buddy sync set:

- `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
- `Docs/Design/STATUS-world-graph-continuity-spine.md`
- `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`
- `Docs/Plans/HANDOFF-CUTOVER-observational-correspondence-drift.md`

Required meaning of that sync:

1. record this CUTOVER design PR as accepted/merged with its exact merge SHA and review-cycle count;
2. mark the **design gate** complete and the observational-correspondence implementation slice as the current implementation work;
3. preserve `CUTOVER_NOT_READY` and Buddy product authority;
4. keep catch-up/quiescence, living-write ownership, authority switch, first mutation, and demolition explicitly unresolved;
5. do **not** mark the implementation slice `DONE`, invent its merge SHA/review count, or advance the next successor as completed.

If those four Buddy authority paths have changed materially before the sync, re-anchor and reconcile them before editing; do not overwrite newer authority.

## §3 Observable paths and adversarial sequences

| Path | Required classification | Same §1 invariant? | Owning boundary |
|---|---|---:|---|
| Exact #34 bundle + exact #34 durable world | `CORRESPONDING` with exact source/adopted revision identities | Yes | DungeonMind durable readback + correspondence evaluator |
| Same exact bundle identity, durable graph/history corruption | `MISMATCH` / integrity failure; never `CORRESPONDING` | Yes | Durable readback reconstruction |
| Different valid Buddy source snapshot for same world | `STALE`; report adopted source revision and observed source revision | Yes | Correspondence evaluator |
| Unknown world/adoption | explicit unresolved/not-adopted result; no fallback to label/latest world | Yes | Repository lookup boundary |
| Retry same read-only check | deterministic same classification; no durable writes/head events | Yes | Service/repository boundary |

Adversarial sequences:

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| adopt exact A → check A → present valid changed snapshot B | first `CORRESPONDING`, second `STALE`; DND durable state unchanged | PostgreSQL integration |
| adopt exact A → alter reconstructed expected semantic/history field while claiming A | `MISMATCH`; shape-only equality cannot pass | contract/integration |
| check while no adoption receipt exists | explicit not-adopted/unresolved; no current-head guessing | repository/service test |
| run checker twice | byte/semantic-equivalent result; zero write/head/receipt delta | integration read-only proof |

## §4 Files in scope — implementation write lease

Repository: `Drakosfire/DungeonMind` only. The four Buddy authority paths in §2 are **not** in this lease; they are the steward's direct guarded Buddy commit after this design PR merges. A DungeonMind PR cannot edit DungeonMindBuddy.

Expected DND lease:

| Action | Path | Purpose |
|---|---|---|
| Create | `src/dungeonmind/contracts/existing_world_correspondence.py` | Versioned `ExistingWorldCorrespondenceResultV1` public contract |
| Modify | `src/dungeonmind/contracts/__init__.py` | Export the result contract under the established public-contract convention |
| Create | `src/dungeonmind/application/existing_world_correspondence.py` | Read-only correspondence evaluator/service seam |
| Create | `tests/unit/test_existing_world_correspondence.py` | Exact classification/identity/integrity contract |
| Create | `tests/integration/test_postgres_existing_world_correspondence.py` | Owning PostgreSQL proof including no-write and stale-snapshot sequence |
| Reuse only | `tests/fixtures/dungeonmind_dnd/eldyrwild_existing_world_adoption_bundle_v2.json` | Exact #34 accepted source fixture; bytes must remain unchanged |

**Bounded discovery exception:** one additional existing DungeonMind package export/`__init__` path (expected `src/dungeonmind/application/__init__.py`) may be modified only if the new application seam must be exported under the repository's established package convention. No repository/schema/migration mutation path is authorized by this exception.

No Buddy paths are authorized for the implementation worker; the §2 Buddy sync is steward-owned. No Buddy runtime/source/schema changes are authorized anywhere in this slice.

If repository inspection shows the owning DND contract/application module convention differs from the proposed paths above, stop before implementation and re-brief the lease rather than silently placing the contract elsewhere.

## §5 Explicitly out of scope / collision boundary

| Path/capability | Why out of scope |
|---|---|
| DND migrations / adoption write runtime | Existing adoption is under observation, not repair |
| Buddy producer semantics / sealed #34 fixture | Source authority under comparison, not mutation |
| Buddy product surfaces | Read switch is later |
| Any dual-write or replication worker | Separate catch-up/writer capability |
| Graph-head mutation APIs | Checker must remain read-only |

## §6 Implementation contract

```text
Input:
  exact ExistingWorldAdoptionBundleV2 bytes / parsed identity
  durable DungeonMind world_id + adoption receipt / adopted revision

Output:
  ExistingWorldCorrespondenceResultV1
    classification = CORRESPONDING | STALE | MISMATCH | NOT_ADOPTED
    world_id
    observed_source_revision
    adopted_source_revision?
    adoption_id?
    adopted_revision?
    exact comparison/evidence summary sufficient to diagnose mismatch class

Invariant:
  CORRESPONDING is impossible unless exact source identity and reconstructed durable
  semantic/history authority agree; changed valid source snapshot is STALE, not mismatch
  and not corresponding; checker performs no writes.

Failure behavior:
  malformed/integrity-invalid source input → fail closed / MISMATCH-or-contract error
  persistence unavailable → unavailable, never corresponding
  no receipt/world → NOT_ADOPTED

Replay / idempotency:
  same source + same durable state → identical classification/result
  changed valid source snapshot + same durable state → STALE
  retry after dependency failure → fresh read-only evaluation, no recovery write

Trust boundary:
  Verifies: exact source/adoption identities, durable graph semantic payload,
            source/contribution/identity/evidence reconstruction required by #34.
  Records/trusts without proving: whether a different source revision is a safe
            descendant to catch up automatically; product routing/writer ownership.
```

`ExistingWorldCorrespondenceResultV1` follows the repository's versioned public-contract convention: it lives in `src/dungeonmind/contracts/existing_world_correspondence.py` and is re-exported from `dungeonmind.contracts` like the other `*V1`/`V2` models. The read-only evaluator seam lives in `src/dungeonmind/application/existing_world_correspondence.py`.

No new persisted correspondence record is required in this slice. Correspondence is a derived observation over two durable authorities. If implementation discovers it needs durable sync checkpoints, cursor state, replication offsets, or operator-managed transitions, STOP and split.

## §7 Evidence required to merge

| Guarantee | Owning boundary | Evidence | Expected | Stop condition |
|---|---|---|---|---|
| Exact #34 state corresponds | PostgreSQL readback | focused integration | `CORRESPONDING`; exact source/adopted IDs; no row/head deltas | any inferred/current-head shortcut |
| Valid changed source is stale | correspondence service + PostgreSQL | adversarial integration | `STALE`; both source revision identities visible | auto-adopt/catch-up or `CORRESPONDING` |
| Semantic/history corruption is mismatch | contract/readback | unit + integration | `MISMATCH`/integrity failure even if graph counts match | shape-only comparison passes |
| Unknown adoption is explicit | repository/service | unit/integration | `NOT_ADOPTED`; no fallback | label/latest lookup |
| Checker is read-only/idempotent | PostgreSQL | before/after row/head/receipt counts + repeated result | zero durable mutation | any write/head event |
| #34 regression stays intact | existing #34 tests | focused regression | existing adoption suite remains green subject to truthful baseline | regression introduced |
| predecessor doc sync is backward-looking only | steward Buddy sync diff inspection | changed-path + semantic review | design predecessor recorded; implementation not pre-marked DONE | own future completion claimed |

Suggested exact commands in the DungeonMind implementation worktree:

```bash
uv run pytest -q tests/unit/test_existing_world_correspondence.py
DUNGEONMIND_DATABASE_URL='postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/dungeonmind' \
  uv run pytest -q tests/integration/test_postgres_existing_world_correspondence.py
DUNGEONMIND_DATABASE_URL='postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/dungeonmind' \
  uv run pytest -q tests/integration/test_postgres_eldyrwild_existing_world_adoption.py
uv run ruff check <leased DND paths>
uv run pyright

git diff --check
git diff --name-only <implementation-base>...HEAD
```

The DungeonMind implementation PR evidence is the DND command set above; its `git diff --name-only <implementation-base>...HEAD` must show only §4-leased DND paths.

The Buddy predecessor sync is verified by the steward in the DungeonMindBuddy checkout at sync time, not by the DND worker:

```bash
git diff --check
git diff --name-only <Buddy-pre-sync-main>...HEAD -- \
  Docs/Plans/PR-TRACKER-campaign-supergraph.md \
  Docs/Design/STATUS-world-graph-continuity-spine.md \
  Docs/Roadmaps/ROADMAP-campaign-supergraph.md \
  Docs/Plans/HANDOFF-CUTOVER-observational-correspondence-drift.md
```

Baseline failures must be compared base/head. Do not rewrite inherited failures as green.

## §8 Required review handback

Record:

1. Review Cycle N and exact implementation PR/head SHA;
2. exact design PR merge SHA and review-cycle count recorded by the predecessor doc sync;
3. exact source/adopted revision identities for `CORRESPONDING` proof;
4. exact changed-source identity pair for `STALE` proof;
5. mismatch case that proves graph counts alone cannot establish correspondence;
6. proof the checker produced no world/head/revision/receipt/history mutations;
7. complete §7 results and provenance;
8. actual DND changed paths versus the §4 lease, plus the steward Buddy predecessor-sync commit SHA and its four paths;
9. confirmation the Buddy doc sync looks backward only and does not mark this implementation complete;
10. confirmation product authority remains Buddy / `CUTOVER_NOT_READY`.

## §9 Acceptance rubric

- [ ] One read-only correspondence capability is delivered.
- [ ] Exact #34 state classifies `CORRESPONDING` at the PostgreSQL owning boundary.
- [ ] A different valid Buddy snapshot classifies `STALE` with both revision identities.
- [ ] Same-snapshot semantic/history corruption cannot pass as corresponding.
- [ ] Unknown/unavailable state fails visibly; no label/latest/current-head fallback exists.
- [ ] Repeated checks create no durable writes or head events.
- [ ] No replication, catch-up, writer transfer, product read switch, rollback workflow, or first post-cutover mutation is introduced.
- [ ] The completed design predecessor is recorded across Buddy tracker/status/roadmap/handoff by the steward's direct guarded sync after this design PR merges.
- [ ] That sync does not pre-mark the observational-correspondence implementation `DONE` or invent its future merge/review facts.
- [ ] Product authority remains Buddy and disposition remains `CUTOVER_NOT_READY`.

## Stop conditions

Stop and report rather than expanding if:

- correspondence requires a new durable sync/checkpoint format;
- deciding `STALE` requires executing catch-up or proving descendant replay safety;
- a second writer or product route switch is needed;
- the exact #34 fixture or DND runtime must be changed to make correspondence pass;
- a required path falls outside the lease;
- graph-shape equality cannot be strengthened to the required semantic/history equivalence with existing durable read APIs;
- predecessor docs cannot be synchronized without overwriting newer authority.

The successor design begins only after this implementation truthfully proves observational correspondence and staleness. That successor owns catch-up/quiescence strategy and living-write ownership; it is not part of this slice.
