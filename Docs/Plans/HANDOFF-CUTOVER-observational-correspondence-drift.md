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
**Status:** DESIGN ACCEPTED — Buddy PR #614 merged `e1d2b4941f629f9cd6bcaf02a9bac5d7dca8e83a` (2026-08-17; 4 review cycles; accepting Cycle 4 `4953256382`); the §2 steward Buddy sync lands with this commit; the observational-correspondence implementation is the current CUTOVER work and may dispatch per §4/§7
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

## Completion record — design gate

- **Design PR:** Buddy #614; final head `b270b1ea13d198ba0008e38cf6b5dedb64036bdf`; merge `e1d2b4941f629f9cd6bcaf02a9bac5d7dca8e83a` (2026-08-17); 4 review cycles — Cycle 1 `4952698951` on `3d4ff31c…`, Cycle 2 `4953087216` on `5b4a15c6…`, Cycle 3 `4953155964` on `d92f65b7…`, accepting Cycle 4 `4953256382` on `b270b1ea…` (formal COMMENTs because reviewer == author).
- **What the design fixed:** the read-only `ExistingWorldCorrespondenceResultV1` contract — `CORRESPONDING` / `STALE` / `MISMATCH` / `NOT_ADOPTED` classifications, the closed six-check algebra, and typed failure semantics (`PersistenceIntegrityError` for malformed input, integrity-invalid durable bytes, or a dangling adoption receipt; `PersistenceUnavailableError` for unavailable persistence; `NOT_ADOPTED` only on a `get_for_world` receipt miss). The §4 lease is DND-only; the cross-repo Buddy predecessor sync is steward-owned (§2) and landed as a direct guarded commit.
- **What remains false:** the DungeonMind observational-correspondence implementation has not been dispatched or merged; §7 evidence does not exist yet. Product authority remains Buddy; disposition remains `CUTOVER_NOT_READY`. Catch-up/quiescence, living-write ownership, authority switch, first post-cutover mutation, and demolition remain unresolved.

## §1 Mission and merge-ready invariant

**Mission:** CUTOVER can determine whether one exact Buddy authority snapshot and one durable DungeonMind adopted world are observationally the same authority state, so stale or incompatible snapshots fail visibly before any product read/write switch.

**Merge-ready invariant:** Given one exact Buddy adoption bundle identity and one durable DungeonMind world_id, a read-only correspondence check returns a deterministic classification bound to both exact revisions: `CORRESPONDING` only when the durable DungeonMind state reconstructs the sealed source semantics and authority history represented by that bundle; `STALE` when the supplied Buddy authority snapshot is a different otherwise-valid source snapshot than the one DungeonMind adopted; `MISMATCH` when the claimed same snapshot reconstructs but diverges; `NOT_ADOPTED` only when no adoption receipt exists for the world; and a typed integrity error when input or durable bytes cannot be reconstructed at all — including when a receipt exists but its referenced world/revision/history/evidence is missing or integrity-invalid. No classification may mutate either system or imply product-authority cutover.

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
| Same exact bundle identity, durable graph/history divergence after successful reconstruction | `MISMATCH`; never `CORRESPONDING` | Yes | Durable readback reconstruction |
| Malformed input bundle or integrity-invalid durable bytes | typed `PersistenceIntegrityError`; no classification; never `CORRESPONDING` | Yes | Contract parse + integrity readback |
| Different valid Buddy source snapshot for same world | `STALE`; report adopted source revision and observed source revision | Yes | Correspondence evaluator |
| No adoption receipt for world_id (`get_for_world` miss) | `NOT_ADOPTED`; adopted_* fields null; no fallback to label/latest world | Yes | Repository lookup boundary |
| Receipt exists but referenced world/revision/history/evidence missing or integrity-invalid | typed `PersistenceIntegrityError`; no classification; never `NOT_ADOPTED` | Yes | Repository lookup + durable readback |
| Retry same read-only check | deterministic same classification; no durable writes/head events | Yes | Service/repository boundary |

Adversarial sequences:

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| adopt exact A → check A → present valid changed snapshot B | first `CORRESPONDING`, second `STALE`; DND durable state unchanged | PostgreSQL integration |
| adopt exact A → alter reconstructed expected semantic/history field while claiming A | `MISMATCH`; shape-only equality cannot pass | contract/integration |
| supply malformed bundle bytes claiming A | `PersistenceIntegrityError`; no classification emitted | unit contract |
| check while no adoption receipt exists | `NOT_ADOPTED`; no current-head guessing | repository/service test |
| receipt exists for world → referenced adopted durable state (world/revision/history/evidence) missing | `PersistenceIntegrityError`; no classification; never `NOT_ADOPTED` | repository/integration |
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
  durable DungeonMind world_id; the adoption receipt is retrieved
  independently via get_for_world(world_id), never inferred from
  world/label/latest state

Output (returned only for a well-formed evaluation):
  ExistingWorldCorrespondenceResultV1
    schema_version = "dm_existing_world_correspondence_result_v1" (Literal)
    classification = CORRESPONDING | STALE | MISMATCH | NOT_ADOPTED
    world_id: str
    observed_source_revision: str        (identity derived from the supplied Buddy snapshot)
    adopted_source_revision: str | None  (from the durable receipt; null iff NOT_ADOPTED)
    adoption_id: str | None              (null iff NOT_ADOPTED)
    adopted_revision: str | None         (published DND revision; null iff NOT_ADOPTED)
    checks: list[ExistingWorldCorrespondenceCheckV1]

  ExistingWorldCorrespondenceCheckV1
    schema_version = "dm_existing_world_correspondence_check_v1" (Literal)
    check   = source_identity | graph_payload | source_history |
              contribution_history | identity_history | evidence_identity
    outcome = match | diverged | not_evaluated
    detail: str                          (operator diagnostic; "" when outcome is match)

  Classification algebra (closed):
    CORRESPONDING: all six checks match.
    STALE:         source_identity diverged; both source revisions reported;
                   every other check not_evaluated.
    MISMATCH:      source_identity match and at least one other check diverged;
                   checks past the first divergence may be not_evaluated.
    NOT_ADOPTED:   no adoption receipt for world_id (get_for_world miss);
                   adopted_* fields null; checks == [].

Evaluation order (receipt presence is decided before any comparison):
  1. parse/validate source input; malformed/integrity-invalid input raises
  2. receipt lookup via get_for_world(world_id); a miss classifies NOT_ADOPTED
  3. resolve the receipt's referenced world/revision/history/evidence;
     missing or integrity-invalid referenced state raises PersistenceIntegrityError
  4. compare reconstructed state; CORRESPONDING / STALE / MISMATCH per algebra

Invariant:
  CORRESPONDING is impossible unless exact source identity and reconstructed durable
  semantic/history authority agree; changed valid source snapshot is STALE, not mismatch
  and not corresponding; checker performs no writes.

Failure behavior — errors are raised, never returned as classifications:
  malformed/integrity-invalid source input
      → PersistenceIntegrityError; details.reason names the parse/schema/self-hash failure
  integrity-invalid durable bytes on readback
      → PersistenceIntegrityError; details.reason names the failed integrity check
      (distinct from MISMATCH: MISMATCH means reconstruction succeeded and diverged)
  receipt exists but its referenced world/revision/history/evidence is
  missing or integrity-invalid
      → PersistenceIntegrityError; no classification; never NOT_ADOPTED
      (receipt presence is established independently via get_for_world;
       a dangling/corrupt receipt is corrupted adopted state, not absence)
  persistence unavailable
      → PersistenceUnavailableError; no result; never corresponding
  no adoption receipt for world_id (get_for_world miss)
      → NOT_ADOPTED (a classification, not an error)
  No new error types are introduced; domain/errors.py is not in the lease.

Replay / idempotency:
  same well-formed source + same durable state → canonically equal result
  changed valid source snapshot + same durable state → STALE
  retry after any raised error → fresh read-only re-evaluation; errors are not
    cached, persisted, or converted into classifications; zero recovery writes

Trust boundary:
  Verifies: exact source/adoption identities, durable graph semantic payload,
            source/contribution/identity/evidence reconstruction required by #34.
  Records/trusts without proving: whether a different source revision is a safe
            descendant to catch up automatically; product routing/writer ownership.
```

`ExistingWorldCorrespondenceResultV1` follows the repository's versioned public-contract convention: it and the nested `ExistingWorldCorrespondenceCheckV1` live in `src/dungeonmind/contracts/existing_world_correspondence.py` and are re-exported from `dungeonmind.contracts` like the other `*V1`/`V2` models. The read-only evaluator seam lives in `src/dungeonmind/application/existing_world_correspondence.py`.

No new persisted correspondence record is required in this slice. Correspondence is a derived observation over two durable authorities. If implementation discovers it needs durable sync checkpoints, cursor state, replication offsets, or operator-managed transitions, STOP and split.

## §7 Evidence required to merge

| Guarantee | Owning boundary | Evidence | Expected | Stop condition |
|---|---|---|---|---|
| Exact #34 state corresponds | PostgreSQL readback | focused integration | `CORRESPONDING`; exact source/adopted IDs; no row/head deltas | any inferred/current-head shortcut |
| Valid changed source is stale | correspondence service + PostgreSQL | adversarial integration | `STALE`; both source revision identities visible | auto-adopt/catch-up or `CORRESPONDING` |
| Semantic/history divergence is mismatch | contract/readback | unit + integration | `MISMATCH` even if graph counts match | shape-only comparison passes |
| Malformed/integrity-invalid input fails closed | contract parse | unit | `PersistenceIntegrityError`; no classification; never `CORRESPONDING` | malformed input returns a classification |
| Missing receipt is explicit absence | repository/service | unit/integration | `get_for_world` miss → `NOT_ADOPTED`; adopted_* null; no fallback | label/latest lookup |
| Dangling receipt fails closed | repository/readback | unit + integration | receipt exists; referenced world/revision/history/evidence missing or invalid → `PersistenceIntegrityError`; no classification | dangling receipt classified `NOT_ADOPTED` or `MISMATCH` |
| Dependency unavailable is an error, not a state | service/repository | unit | `PersistenceUnavailableError`; no result; retry re-evaluates fresh | unavailable cached or returned as a classification |
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
5. mismatch case that proves graph counts alone cannot establish correspondence, plus the malformed-input, dangling-receipt, and dependency-unavailable typed-error proofs;
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
- [ ] `ExistingWorldCorrespondenceResultV1` carries the exact §6 schema identity, field nullability, closed check algebra, and raised-error failure semantics.
- [ ] A missing adoption receipt (`get_for_world` miss) classifies `NOT_ADOPTED`; a receipt whose referenced durable world/revision/history/evidence is missing or invalid raises `PersistenceIntegrityError`, never a classification; malformed input and unavailable persistence raise typed errors, never classifications; no label/latest/current-head fallback exists.
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
