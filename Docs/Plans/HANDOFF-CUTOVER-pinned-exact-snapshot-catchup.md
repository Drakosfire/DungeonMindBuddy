---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CUTOVER — pinned exact-snapshot catch-up
  - Flow: CUTOVER
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-CUTOVER-pinned-exact-snapshot-catchup.md
  - Implementation repository: Drakosfire/DungeonMind

  ## Predecessor gate
  - Do not dispatch until observational correspondence is merged and accepted.
  - The Buddy authority sync must record that predecessor as DONE before this slice starts.
  - Re-anchor Buddy and DungeonMind before dispatch; replace provisional predecessor pins below with exact merged truth.

  Prove that an already-adopted DungeonMind world which is STALE against a later
  sealed Buddy snapshot can atomically advance to that exact snapshot and return
  to CORRESPONDING without transferring product authority, dual-writing, or
  introducing product read switching.
---

# HANDOFF — pinned exact-snapshot catch-up

**Created:** 2026-08-17
**Status:** DRAFT SUCCESSOR HANDOFF — DO NOT DISPATCH until observational correspondence is merged, accepted, and recorded by the Buddy predecessor sync
**Canonical handoff path:** `Docs/Plans/HANDOFF-CUTOVER-pinned-exact-snapshot-catchup.md`
**Conversation/workstream:** `CUTOVER — pinned exact-snapshot catch-up`
**Flow / owner:** `CUTOVER`
**Direction:** DESIGN → CODE → REVIEW
**Buddy design parent:** PR #614 head `b270b1ea13d198ba0008e38cf6b5dedb64036bdf` — design-only parent, not yet a merged predecessor
**DungeonMind implementation base:** RE-ANCHOR AT DISPATCH — must be the exact merged observational-correspondence implementation head on `main`
**Suggested implementation branch:** `dnd/cutover-pinned-exact-snapshot-catchup-v1`
**Suggested implementation PR title:** `CUTOVER: prove pinned exact-snapshot catch-up`

> Repository authority: Buddy `AGENTS.md`, `Docs/Design/ARCHITECTURE-campaign-supergraph.md`, `Docs/Plans/PR-TRACKER-campaign-supergraph.md`, `Docs/Design/STATUS-world-graph-continuity-spine.md`, and `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`; DungeonMind `Docs/Architecture/ARCHITECTURE.md`, `Docs/Architecture/AUTHORITY.md`, checked-in contracts, ADRs, and the exact merged correspondence predecessor.
>
> This handoff is intentionally one slice ahead. It does not assert that correspondence implementation exists or is complete. Dispatch is forbidden until the predecessor is merged and the backward-looking Buddy authority sync records that fact.

## §1 Mission and merge-ready invariant

**Mission:** starting from an already-adopted DungeonMind world that is proven `STALE` against one later sealed Buddy snapshot, apply exactly that pinned snapshot as one atomic, replayable catch-up operation so the same correspondence checker reports `CORRESPONDING` for the incoming snapshot afterward.

**Merge-ready invariant:** given current DungeonMind head `D_A`, durable source snapshot identity `A`, and one later sealed Buddy snapshot `B`, a catch-up command pinned to `(world_id, D_A, A, B, exact bundle digest)` either:

1. atomically persists the B history/state required for reconstruction, publishes one immutable DungeonMind child revision `D_B`, advances the world head from `D_A → D_B`, writes one terminal catch-up receipt, and then satisfies the correspondence contract as `CORRESPONDING(B, D_B)`; or
2. performs no durable mutation and fails visibly because its expected parent/source identity, historical compatibility, payload integrity, or persistence precondition is false.

The operation does **not** transfer product authority. Buddy remains the authoritative writer/source for this slice. DungeonMind is catching up to one explicitly pinned source snapshot, not becoming the living writer.

### Why this is the next slice

Observational correspondence answers **“are these two states the same?”** It does not answer **“how do we make a stale adopted state current again?”** Writer transfer is unsafe until DungeonMind can first consume one later source snapshot without rebuilding from scratch, silently discarding history, or accepting concurrent ambiguity.

This slice therefore proves only:

```text
CORRESPONDING(A)
  → Buddy source advances to sealed B
  → correspondence reports STALE(A vs B)
  → explicit catch-up(A→B)
  → correspondence reports CORRESPONDING(B)
```

It does not prove an operational write freeze, live continuous replication, or writer ownership transfer. Those are later CUTOVER gates.

## §2 Predecessor gate and authority pins

### Mandatory dispatch gate

Before CODE dispatch, the steward must replace every provisional predecessor reference in this handoff with exact repository truth and record that update in the current authority state.

Required predecessor truth:

- Buddy PR #614 is merged and its final review-cycle count is recorded.
- The observational-correspondence DungeonMind implementation PR is merged.
- That implementation proves the exact `CORRESPONDING / STALE / MISMATCH / NOT_ADOPTED` contract and typed failure semantics from `HANDOFF-CUTOVER-observational-correspondence-drift.md`.
- Buddy tracker/status/roadmap/handoff record observational correspondence as completed prior work and this catch-up slice as current work.
- Product authority still remains Buddy and disposition remains `CUTOVER_NOT_READY`.

If any of those facts are false, **STOP — do not dispatch this handoff.**

### Historical source/adoption anchor

The known historical A snapshot remains useful as test ancestry, but must not be mistaken for the future implementation base:

- sealed Buddy bundle blob: `274cdd9e6d38d5a00aa43d780779e95a7919d975`
- bundle SHA-256: `90574dfc4101e4198c7fd96478d6f49e65aa534d0aa91fa41a9a17da9d49695f`
- source world revision A: `rev:0c644e56b45bcaac709012206e3e41c2`
- adopted DungeonMind revision for A: `rev:34b1f8e2625d5ba693fc726a2a1a4720`
- DungeonMind PR #34 merge: `d2204dd0901237d8b446b4f2363f896306e32e6f`

The actual catch-up implementation must use the exact merged correspondence predecessor as its repository base and may use a new sealed descendant fixture B created specifically for this proof.

## §3 Scope decision — pinned snapshot catch-up, not replication

### Selected mechanism

This slice selects a **whole-snapshot, expected-parent catch-up operation**.

It does not build CDC, a queue, event streaming, polling, or a background replicator. It consumes one explicit sealed Buddy `ExistingWorldAdoptionBundleV2`-compatible snapshot B and reconciles that complete authority snapshot into the already-adopted DungeonMind world.

Why this mechanism:

- the accepted CUTOVER source artifact is already a complete, sealed whole-world snapshot;
- correspondence already defines how to prove the resulting state equals that snapshot;
- atomic graph-head advancement and immutable revisions are already closed architecture;
- continuous replication would add a transport/operational system before basic stale→current recovery is proven;
- writer transfer does not require DungeonMind to continuously tail Buddy if an explicit quiesced final catch-up can later be proven.

### Explicitly not selected

- automatic polling for newer Buddy state;
- incremental event replication;
- dual writers;
- “latest snapshot” selection;
- mutable source paths or run IDs;
- product read switching;
- catch-up that silently starts from whatever DungeonMind head happens to be current;
- deleting the prior DND revision or historical rows to make B fit.

## §4 Catch-up contract

The exact names may be adjusted only during pre-dispatch re-anchor if the merged correspondence predecessor establishes a stronger repository naming convention. The semantic contract is fixed here.

```text
ExistingWorldSnapshotCatchupCommandV1
  schema_version = "dm_existing_world_snapshot_catchup_command_v1"
  catchup_id: str
  world_id: str
  expected_head_revision_id: str          # D_A
  expected_adopted_source_revision: str   # A
  bundle: ExistingWorldAdoptionBundleV2   # sealed B
  bundle_sha256: str
  expected_published_revision_id: str     # deterministic D_B
  caught_up_at: timezone-aware datetime

ExistingWorldSnapshotCatchupReceiptV1
  schema_version = "dm_existing_world_snapshot_catchup_receipt_v1"
  catchup_id: str
  world_id: str
  prior_head_revision_id: str             # D_A
  prior_source_revision: str              # A
  observed_source_revision: str            # B
  bundle_sha256: str
  published_revision_id: str              # D_B
  caught_up_at: datetime
```

### Deterministic identity

`catchup_id` is caller/steward supplied but content-bound. The application layer must bind the command to the canonical bundle bytes, source revision identity, expected parent, and deterministic published revision before any mutation. Same `catchup_id` + changed bound payload is an idempotency conflict.

`expected_published_revision_id` is computed from the new DungeonMind graph revision bytes using the existing revision-ID discipline. The published DND revision is a child of `expected_head_revision_id`; the incoming Buddy source revision is provenance, not the DND graph parent.

### Required publication shape

The new DungeonMind graph revision:

- uses the same world identity;
- contains the exact graph semantics represented by sealed B;
- records `parent_revision_id = expected_head_revision_id`;
- records the catch-up operation in its operation/contribution provenance under the repository's existing revision contract;
- is immutable after insert;
- becomes current only through one expected-parent head CAS.

## §5 Historical compatibility contract

Catch-up is not permission to rewrite history.

Before mutation, B must be compatible with the already-durable A history under these rules:

1. `world_id` must match exactly.
2. Every prior immutable source revision, evidence record, identity decision, and immutable contribution payload that B references or carries with an existing ID must reconstruct to the same canonical fingerprint as the durable record.
3. New immutable IDs may be appended.
4. Existing mutable lifecycle state may advance only through transitions already legal in DungeonMind contracts/repositories. This includes source-artifact current-revision pointers and contribution lifecycle where the merged repository already defines legal mutation.
5. B must include a complete history closure sufficient for the correspondence checker to prove B after catch-up.
6. Catch-up must not delete old durable history merely because B no longer selects it as current.
7. Same ID + incompatible immutable payload is `PersistenceIntegrityError` or the repository's existing exact identity-conflict error; never overwrite.
8. If the repository cannot express a required legal source/contribution lifecycle transition atomically inside the catch-up unit of work, **STOP and split** rather than adding an ad-hoc bypass.

This contract deliberately avoids claiming that arbitrary B is a safe semantic descendant merely because its revision string differs. Compatibility is proven from exact identity/history closure plus expected prior source pin; there is no “newer timestamp means descendant” rule.

## §6 Atomicity and recovery

The persistence owner must perform one all-or-nothing unit of work containing every durable mutation required for B:

```text
validate + bind command
  → verify existing catch-up replay/conflict
  → verify current DND head == expected_head_revision_id
  → verify currently adopted/corresponding source == expected_adopted_source_revision
  → validate B historical compatibility
  → persist new/advanced source + contribution + identity + evidence state
  → insert immutable graph revision D_B
  → expected-parent CAS head D_A → D_B
  → insert normal head event
  → insert terminal catch-up receipt
COMMIT
```

Any failure before commit leaves all A state and `D_A` readable and unchanged.

### Replay

- exact same command after success returns the original receipt;
- exact replay creates no second graph revision, head event, or history mutation;
- same `catchup_id` with different bound content fails conflict with zero mutation;
- replay does not require current head still equals `D_B` if the exact durable terminal receipt proves the original operation, matching the repository's historical-receipt discipline.

### Response-loss recovery

A thrown catch-up call may perform one exact durable-receipt probe by `(world_id, catchup_id)`.

- exact matching receipt → return recovered success;
- no receipt → propagate failure/unknown according to existing repository error discipline;
- nonmatching receipt/content → integrity/conflict failure;
- do not infer success from “head looks like B,” timestamps, arbitrary history scans, or latest rows.

If existing errors cannot truthfully represent the outcome-unknown case without ambiguity, the implementation may add one versioned catch-up-specific outcome-unknown error **only if explicitly re-briefed before code changes**. Do not silently invent it outside the lease.

## §7 Source stability and what this slice does not prove

This operation consumes one pinned snapshot B. It does **not** prove Buddy stayed frozen before or after the operation.

Acceptance therefore has two separate claims:

1. **Catch-up correctness:** after applying B, correspondence against B is `CORRESPONDING`.
2. **Source-currentness:** if Buddy later produces C, correspondence against C is `STALE` again. Catch-up does not silently chase C.

That is intentional. The later authority-transition design owns the real quiescence/freeze boundary and the no-gap handoff from Buddy writer to DungeonMind writer.

A successful catch-up is therefore **necessary but not sufficient** for cutover.

## §8 Implementation ownership and expected write lease

Repository: `Drakosfire/DungeonMind` only.

The exact file lease must be finalized after the correspondence predecessor merges. Expected ownership is:

| Action | Expected path | Purpose |
|---|---|---|
| Create | `src/dungeonmind/contracts/existing_world_snapshot_catchup.py` | Versioned command/receipt contracts |
| Modify | `src/dungeonmind/contracts/__init__.py` | Public contract export |
| Create | `src/dungeonmind/application/existing_world_snapshot_catchup.py` | Bind/validate/recovery application seam |
| Modify | `src/dungeonmind/application/repositories.py` | Catch-up repository port + durable aliases |
| Create/Modify | `src/dungeonmind/infrastructure/memory/existing_world_snapshot_catchup.py` or established memory UoW location | Atomic in-memory implementation |
| Create/Modify | `src/dungeonmind/infrastructure/postgres/existing_world_snapshot_catchup.py` or established PostgreSQL UoW location | Atomic PostgreSQL implementation |
| Modify | repository bootstrap/export files proven necessary by current convention | Wire the new repository seam |
| Create | one next-numbered migration under `migrations/versions/` if a durable catch-up receipt table is required | Terminal receipt persistence |
| Create | `tests/unit/test_existing_world_snapshot_catchup.py` | Contract/application/replay/failure proof |
| Create | `tests/integration/test_postgres_existing_world_snapshot_catchup.py` | Owning-boundary atomicity + recovery + correspondence proof |
| Reuse | exact historical A fixture plus one new sealed descendant B fixture under established test fixture location | A→B proof corpus |

### Lease rule

This table is a design ownership map, not yet a dispatchable path lease because the predecessor may establish exact modules or exports that should be reused. Before CODE dispatch, steward must replace alternatives/wildcards above with exact paths and the exact migration filename based on then-current DungeonMind `main`.

No Buddy runtime files are part of the DND implementation lease.

## §9 Backward-looking Buddy authority sync

Because the implementation repository is DungeonMind while Campaign Supergraph sequencing authority lives in DungeonMindBuddy, predecessor maintenance is cross-repository.

Before this catch-up implementation dispatches, the steward direct guarded Buddy sync must record the **completed observational-correspondence predecessor** across the mutable authority set. It should normally include:

- `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
- `Docs/Design/STATUS-world-graph-continuity-spine.md`
- `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`
- `Docs/Plans/HANDOFF-CUTOVER-observational-correspondence-drift.md`
- this handoff only if its status/pins materially change at dispatch

Required meaning:

- correspondence implementation is recorded with exact PR/head/merge/review-cycle evidence;
- observational correspondence is `DONE`;
- pinned snapshot catch-up becomes current work;
- this catch-up implementation is **not** pre-marked complete;
- Buddy remains product authority;
- `CUTOVER_NOT_READY` remains true;
- actual quiescence, writer transfer, product read switch, first post-cutover mutation, rollback operator workflow, and Buddy demolition remain unresolved.

No standalone routine documentation PR is created for that sync.

## §10 Evidence required to merge

The implementation PR must prove at the owning persistence boundary:

| Guarantee | Required proof |
|---|---|
| A starts corresponding | merged correspondence checker reports `CORRESPONDING` for exact A against D_A |
| B is a valid later sealed snapshot | canonical bytes/hash/schema/world identity validate; correspondence before catch-up reports `STALE` against D_A |
| Exact catch-up succeeds | one command publishes D_B, one head CAS/event, one receipt |
| B corresponds afterward | same merged correspondence checker reports `CORRESPONDING` for B against D_B |
| Graph parent continuity | D_B parent is exactly D_A |
| Historical compatibility | prior immutable fingerprints remain unchanged; legal mutable lifecycle transitions only |
| No deletion shortcut | A historical records required for audit remain durable after B |
| Exact replay | identical retry returns same receipt; no new revision/head event/history writes |
| Changed replay | same catchup_id with changed bundle/parent/source pin fails with zero mutation |
| Stale DND parent | head changed away from expected D_A → fail closed; no partial writes |
| Wrong prior source | expected_adopted_source_revision does not match durable A → fail closed |
| Mid-transaction failure | every injected precommit failure stage leaves complete A counts/head/history/receipt state unchanged |
| Response loss | exact terminal receipt recovers success; no heuristic success inference |
| Source advances again | after successful B catch-up, checking valid C yields `STALE`; no auto-catch-up |
| Product authority | Buddy still owns writes; no product route/read switch introduced |

### Minimum count/identity ledger

The integration proof must record before/after counts for every table mutated by catch-up, including at minimum:

- worlds
- graph revisions
- world graph heads
- head events
- source artifacts
- source revisions
- graph contributions
- identity decisions
- evidence refs
- existing-world adoption receipt(s)
- snapshot catch-up receipts

Use exact equality assertions for replay and rollback cases, not “nonzero” smoke checks.

### Baseline discipline

Run focused unit/integration tests, the existing adoption suite, the merged correspondence suite, `pyright`, leased-path Ruff, `git diff --check`, and exact changed-path inspection. Any inherited repo-wide failure must be compared base/head and reported truthfully rather than called green.

## §11 Required review handback

Record:

1. Review Cycle N and exact implementation PR/head SHA;
2. exact correspondence predecessor PR/merge/review-cycle evidence from the Buddy sync;
3. exact implementation base SHA;
4. exact A source revision + D_A revision;
5. exact B bundle blob/hash/source revision + resulting D_B revision;
6. pre-catch-up `STALE` result and post-catch-up `CORRESPONDING` result;
7. D_A→D_B parent/head-event proof;
8. exact durable row/count/fingerprint delta for successful catch-up;
9. replay, changed-replay, stale-parent, wrong-source, injected-failure, and response-loss evidence;
10. proof no old historical authority was silently deleted or rewritten;
11. actual changed paths versus the final dispatch lease;
12. confirmation Buddy remains product authority and `CUTOVER_NOT_READY`.

## §12 Acceptance rubric

- [ ] Correspondence predecessor is merged, accepted, and recorded before implementation dispatch.
- [ ] One explicit pinned A→B catch-up capability is delivered.
- [ ] B is selected by exact sealed identity, never latest/time/path inference.
- [ ] Catch-up is expected-parent and expected-prior-source pinned.
- [ ] B durable history is compatibility-checked before mutation.
- [ ] One atomic unit publishes D_B and its terminal receipt or leaves A wholly unchanged.
- [ ] D_B is an immutable child of D_A.
- [ ] The merged correspondence checker proves `STALE` before and `CORRESPONDING` after.
- [ ] Exact replay is no-op/idempotent; changed replay fails closed.
- [ ] Response-loss recovery uses the exact receipt only.
- [ ] Old durable history is not deleted to force equality.
- [ ] If source advances again after B, correspondence reports `STALE`; no background replication exists.
- [ ] No product read switch, writer transfer, dual-write path, or Buddy demolition is introduced.
- [ ] Product authority remains Buddy and disposition remains `CUTOVER_NOT_READY`.

## Stop conditions

Stop and report rather than expanding if:

- observational correspondence is not merged and accepted;
- the merged correspondence API cannot be reused directly for before/after proof;
- catch-up requires automatic polling/CDC/replication to be useful;
- the existing DungeonMind persistence model cannot atomically reconcile B without a broader source/contribution lifecycle redesign;
- B conflicts with existing immutable IDs or requires destructive history rewrite;
- implementing catch-up requires product read routing or writer ownership transfer;
- a required path falls outside the finalized dispatch lease;
- response-loss recovery cannot be made exact without a separately designed durable operation identity;
- the source-stability/writer-freeze problem is being solved inside this slice rather than left to the next authority-transition design.

## Named successor

After this implementation is truthfully merged and its predecessor sync is complete, the next CUTOVER design slice is:

**quiescence + atomic living-write authority transition**

That successor owns:

- the Buddy write-freeze/quiescence boundary;
- the final source-head stability check;
- the no-gap/no-dual-writer handoff;
- product read/write authority switch semantics;
- rollback boundary before the first post-cutover mutation.

It must not be dispatched merely because this handoff exists. Pinned snapshot catch-up must first be proven against real durable DungeonMind state.