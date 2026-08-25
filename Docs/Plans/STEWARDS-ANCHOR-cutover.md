# STEWARD'S ANCHOR — CUTOVER

**Status:** CUTOVER_COMPLETE — DungeonMind is living Eldyrwild World Graph authority; native DungeonMind reads are production (#633 `DONE`); D.1 native governed writes are `DONE` (#634); remaining debt is D.2 mounted-writer migration then D.3 graph-engine demolition (D.2A `DOING`)  
**Line of work:** `CUTOVER`  
**Created:** 2026-08-17  
**Completed:** 2026-08-18 (live D_A→D_B)  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Current Buddy `main`:** `65d13dcca8162b5eccd0c81dd4235dec93c8cd0c` (merge of PR #633). **#633 accepted head:** `ebb57adebe063b9c81fd4caa9a1274cfd6d6fb01`. **Cycle 2 approval:** `5011598382`. **#632 merge:** `54779636750ebf7a639aef8a6184cc61ead9c860`. **Historical #631 merge:** `ffc39ab394ea55b00dc8b2a0fd41be0448635600`.  
**Buddy integration tip at completion:** `18bcb18475ac30679ebec84bec17c4e81390f674` (merge of Buddy PR #620)  
**DungeonMind authority anchor:** `c5d3688587b0f5d506e0f7d64f33eb0628bac896` (merge of DungeonMind PR #45 — R.3a native read-context optimization; Buddy runtime pin of this slice. Historical R.3 pin was PR #43 `519b2c96…`)  
**Completed implementation handoffs:** Buddy PR #619 (`6c2fe9d37dcecf34e025db8373fce072de30b62e`) + Buddy PR #620 (`18bcb18475ac30679ebec84bec17c4e81390f674`; 4 review cycles; final PASS review `4966969478`) + parent [`HANDOFF-CUTOVER-whole-world-authority-transfer.md`](HANDOFF-CUTOVER-whole-world-authority-transfer.md)  
**Live authority:** DungeonMind PostgreSQL (`dungeonmind_cutover_live@127.0.0.1:54329`); head `D_B = rev:680c246047d67f9fe0293ee90526f670`; parent `D_A = rev:34b1f8e2625d5ba693fc726a2a1a4720`; Buddy local World Graph writer fail-closed under `DUNGEONMIND_WORLD_GRAPH_AUTHORITY=dungeonmind`  
**Steward process:** [`../Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md)  
**Repository law:** [`../../AGENTS.md`](../../AGENTS.md)

---

## 0. Why this document exists

This is the first document a fresh CUTOVER design/review steward should read.

The workstream has crossed an important boundary: the migration-preparation program has done its job. Exact Eldyrwild adoption, real PostgreSQL persistence, observational correspondence, and exact adopted-membership integrity have all been implemented and exercised. The next useful evidence comes from attempting the authority transfer itself.

A fresh steward is not being handed a blank design problem. They inherit a settled direction and are expected to carry it through implementation, review, live cutover, concrete repairs, and old-authority retirement.

The steward must not restart the workstream as another readiness investigation merely because historical trackers or handoffs still contain conservative sequencing language.

The operating posture is:

```text
attempt the cutover
→ observe concrete failures
→ repair the exact failing boundary
→ resume the cutover
→ prove the first DungeonMind-owned mutation survives reload
→ retire Buddy World Graph write authority
```

Not:

```text
invent another generalized preparation layer
→ prove more synthetic scenarios
→ delay authority transfer until no uncertainty remains
```

---

## 1. Steward mission

The CUTOVER steward owns this outcome:

> **Move durable World Graph authority for Eldyrwild from Buddy's file-backed World SuperGraph to DungeonMind's adopted PostgreSQL world, while preserving exact identity, governed GM-confirmed publication, product read behavior, and a truthful rollback/fix-forward boundary.**

The steward owns continuity until one of these terminal states is reached:

### Successful terminal state

```text
DungeonMind is the durable World Graph authority.
Buddy product reads consume DungeonMind authority.
The normal governed Buddy write workflow publishes through DungeonMind.
At least one post-cutover DungeonMind-owned child revision has committed.
That revision survives process/reload reconstruction through the product path.
Buddy's old product World Graph write path is disabled or removed.
State-authority documents record the new ownership truth.
```

### Legitimate stop state

A newly observed, reproducible invariant failure makes safe authority transfer impossible without a bounded repair. The steward records the exact failing boundary, authors or amends one repair handoff, fixes it, and returns to cutover.

A generic `CUTOVER_NOT_READY` is not a legitimate terminal state.

---

## 2. Current repository truth at pickup

### 2.1 DungeonMind migration proof chain is complete enough to cut over

Treat these as completed predecessor facts unless current repository truth disproves them:

- **Buddy PR #609** repaired contribution evidence identity and sealed the final Eldyrwild adoption bytes. The exact repaired bundle was accepted by unchanged DungeonMind PostgreSQL in empty-target, retry, conflict, rollback, recovery, and readback scenarios.
- **DungeonMind PR #34** independently proved exact Eldyrwild existing-world adoption at the owning PostgreSQL boundary.
- **DungeonMind PR #35** added read-only observational correspondence and proved exact A → `CORRESPONDING`, valid later source identity → `STALE`, coherent reconstructable divergence → `MISMATCH`, and typed integrity/unavailable failures without mutating the world.
- **DungeonMind PR #36** added receipt V3 with exact adopted-membership hashing across source artifacts, source revisions, contributions, and identity decisions; it also closed PostgreSQL and in-memory writer-exclusion gaps during V2→V3 promotion. PR #36 merged as `9a19584d31baea77f590d7726e508b144c7dd39d`.

Do not reopen those capabilities as speculative design work. A regression discovered during cutover is a bug/repair, not permission to replay the whole preparation program.

### 2.2 Exact Eldyrwild authority snapshot A

```text
world_id:
  eldyrwild

Buddy source revision A:
  rev:0c644e56b45bcaac709012206e3e41c2

Buddy graph payload SHA-256:
  0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2

sealed adoption bundle Git blob:
  274cdd9e6d38d5a00aa43d780779e95a7919d975

sealed bundle SHA-256:
  90574dfc4101e4198c7fd96478d6f49e65aa534d0aa91fa41a9a17da9d49695f

DungeonMind adopted revision D_A:
  rev:34b1f8e2625d5ba693fc726a2a1a4720

receipt V3 membership SHA-256:
  538195e399158bfb4fafce01f9c5af3c63e2137f70694fdead7a26e5800e0890
```

The adopted shape is the proved `469 objects / 323 relationships / 3 secondary aspects / 5 aspect-selected relationships` state.

### 2.3 No observed snapshot B exists

At steward dispatch, Buddy had advanced substantially since #609, but comparison from the #609 merge `7922b6108cf9e05787f9c79cddcee9347edb0b44` to then-current main found no changes to the Eldyrwild World Graph payload, the adoption producer, the sealed bundle, or World Graph persistence.

Therefore the parked `cutover/design-pinned-snapshot-catchup` handoff is not current work.

Its own mission begins only when a later valid Buddy snapshot B is actually observed as `STALE` against adopted A. Do not implement a synthetic B merely to satisfy historical sequencing.

### 2.4 Known state-authority contradiction

At this anchor's creation, `Docs/Plans/PR-TRACKER-campaign-supergraph.md` and related Campaign Supergraph status/roadmap text still lagged the actual repository state: they described receipt V3 as next and the authority cutover as blocked even though #36 is merged and the direct steward authority-transfer handoff has been committed.

This is known stale process state, not product truth.

The fresh steward must reconcile the active authority set before or as part of the next implementation dispatch, consistent with `AGENTS.md` atomic state-authority sync law. Do not let stale sequencing text resurrect the parked catch-up path.

Expected mutable authority set to inspect:

```text
Docs/Plans/PR-TRACKER-campaign-supergraph.md
Docs/Roadmaps/ROADMAP-campaign-supergraph.md
Docs/Design/STATUS-world-graph-continuity-spine.md
Docs/Plans/HANDOFF-CUTOVER-exact-membership-receipt-v3.md
Docs/Plans/HANDOFF-CUTOVER-whole-world-authority-transfer.md
```

Architecture changes only if its claims truly changed.

### 2.5 R.3 direct-read cutover truth

R.3 (`cutover/direct-dungeonmind-production-reads`) retired Buddy graph hydration from the production read path. In `dungeonmind` authority mode:

```text
DungeonMind authority
        ↓
DungeonMind native projection/retrieval (R.1/R.2)
        ↓
thin product DTO adapter (apps/live_control_server/integrations/dungeonmind/)
        ↓
Buddy product
```

Settled facts a successor steward should not re-litigate:

- **Reads are pure consumers of one exact DungeonMind published revision.** The projection service and all five retrieval operations dispatch to the direct adapter when authority mode is `dungeonmind` and no explicit non-production root override is in play. The adapter never reconstructs a graph, replays contributions, or opens the frozen Buddy store.
- **The A→D_A bridge is receipt-derived.** `ExistingWorldAdoptionReceiptV3.source_provenance.source_world_revision_id` (Buddy A) maps to `published_revision_id` (D_A) from the receipt alone; `head.json` is never read on the direct path. Proven by `test_direct_reads_succeed_with_frozen_buddy_store_missing`.
- **Hydration is retired for production reads and for the normal exact-run write path.** `integrations/dungeonmind/world_graph_writes.py` owns DND prepare/confirm. Hydration entry points in `world_graph_authority.py` fail closed. Remaining kernel writers (Threat publication commit, worldbuilding/first-world) are D.2.
- **The R.3a pin is `SWITCH_READY` and native-read switch #633 is `DONE`.** DungeonMind PR #45 landed the read-context optimization (~20.7s → ~115 ms native). Buddy's adapter rerun of the sealed v2 witness is 0 blocking / 0 errored / 199 approved. Product-path campaign projection is ~0.85s (factory rebuild) / ~0.55–0.75s (reused services); retrievals 120–226 ms. Remaining projection cost is Buddy DTO mapping, not DungeonMind N+1 and not factory rebuild. `DUNGEONMIND_WORLD_GRAPH_DIRECT_READ` is retired: `dungeonmind` + production root is native, with no rollout toggle. Hermes latest-recap comparison facts come from that same native projection. Remaining CUTOVER debt is write-side/runtime demolition: D.1 removes governed-write hydration; D.2 migrates mounted leftover writers; D.3 deletes the graph engine.
- **Prewarm and projection recipes are no-ops in `dungeonmind` mode.** The Buddy resident runtime and projection cache have no consumer on the read path; the coordinator lifecycle stays intact so app startup is authority-mode agnostic.
- **Focus is presentation, not admission.** Session focus flags (`anchored_to_focus_session`, `is_focus_session_evidence`) are recomputed by the adapter from admitted DungeonMind provenance (evidence session id + artifact campaign), matching the legacy kernel's rule. The Plan seam (world scope + campaign-qualified session focus) is therefore supported without narrowing scope or dropping focus.
- **Adopted artifacts are GM-classified by governed V4 repair, not Buddy mutation.** DungeonMind PR #43 plus the 2026-08-23 live Eldyrwild repair transformed the V3 adoption into receipt V4 (historical M0 preserved, sanctioned M1 `16d3161d…`, manifest `83 / 83 / 93 / 13`) without rewriting D_A or the current head. The dormant Buddy scripts that mutated `source_artifacts` and recomputed V3 `membership_sha256` are deleted; they have no recovery role.

The R.3 semantic witness harness (`scripts/compare_direct_dungeonmind_world_graph_reads.py`) is a **supported-contract checker** under vocabulary v2. Zero-difference against the Buddy kernel is not the merge bar. R.3a compares the supported-contract R.3 direct result to the optimized direct result.

The previous 199-blocker tally is historical evidence against corrupted V3 state. The frozen V4 vocabulary-v1 stop point was 200 blocking + 2 errored. The current evidence is the 2026-08-24 sealed vocabulary-v2 witness: **0 blocking, 0 errored, 199 approved semantic divergence** (exact-identity ledger; PLAYER ∩ 390 GM-only = ∅). Durable record: [`../Benchmarks/BASELINE-r3-direct-dungeonmind-current-reads.md`](../Benchmarks/BASELINE-r3-direct-dungeonmind-current-reads.md). Anchor `emit-revalidate-open` was Case A (adapter product-local join): DungeonMind `resolve_source_anchor` succeeded; recap spans are sliced from digest-pinned parent bytes. The former direct-read gate is historical.

---

## 3. Locked steward decisions

These are settled unless current code or a live cutover failure produces contradictory evidence.

### 3.1 Preparation is over

Do not dispatch another generic:

- adoption readiness audit;
- whole-world conformance audit;
- shadow-only comparison program;
- synthetic PostgreSQL ingestion proof;
- migration reconnaissance;
- continuous replication/CDC design;
- dual-write system;
- generalized catch-up mechanism without actual drift.

We have enough evidence to attempt transfer.

### 3.2 Final validation is part of cutover, not a prerequisite program

The authority-transfer procedure should include, immediately before switching authority:

```text
Buddy graph writes quiesced
→ exact V3 receipt/member checkpoint valid
→ current sealed Buddy A reports CORRESPONDING
```

That is the opening phase of the cutover transaction. It is not a reason to postpone cutover into a new project.

### 3.3 Catch-up is conditional recovery only

Reactivate the pinned-snapshot catch-up design only when the live pre-switch evaluator returns genuine `STALE` for a valid later snapshot B while adopted V3 membership remains intact.

Other outcomes mean:

```text
CORRESPONDING → proceed with authority transfer
MISMATCH → repair the exact divergent adopted state or source assumption
integrity error → repair the exact integrity failure
unavailable → restore the dependency and retry
NOT_ADOPTED → investigate wrong environment/world; do not silently re-adopt
```

### 3.4 Rollback ends at the first DungeonMind-owned child revision

Before the first post-switch DungeonMind-owned mutation commits, Buddy remains frozen and read routing can be returned to the old Buddy snapshot without creating divergent histories.

After DungeonMind publishes the first authoritative child `D_B` from `D_A`, the histories have diverged by design. From that point:

```text
DungeonMind is ahead.
Do not re-enable Buddy World Graph writes.
Operational failures are fix-forward incidents.
```

A rollback of product routing after `D_B` must not imply restoring Buddy as writer authority.

### 3.5 Do not port every dormant writer before cutover

The cutover must make the normal governed GM-confirmed World Graph mutation path work through DungeonMind.

Dormant maintenance/repair writers may remain fail-closed until a real consumer requires them. Do not delay the authority switch to rebuild every historical mutation utility.

### 3.6 Buddy still owns product and runtime concerns outside World truth

Moving World Graph authority does not move everything into DungeonMind.

Buddy continues to own, unless a separate accepted design says otherwise:

- source/original rich documents and product composition;
- Plan/Build/Play UI composition;
- Playable/Runbook durable preparation state;
- live Run state;
- Combat runtime state such as HP, initiative, conditions, defeat state;
- Hermes/product orchestration;
- user/session/application concerns that are not durable World Graph truth.

DungeonMind becomes authority for the adopted durable World Graph and its governed mutation history.

---

## 4. Known implementation seams — inspect, do not assume

The active implementation handoff already authorizes bounded discovery. A fresh steward should verify these seams against current main before dispatch/review:

### Buddy runtime pin

At the last audit, Buddy `pyproject.toml` still pinned DungeonMind runtime `f2e273804d7e4e2f5bcaf4c964525f8ccb0c4e92`, predating #34/#35/#36. The cutover implementation must deliberately repin or otherwise run against the accepted DungeonMind authority implementation; merging #36 alone does not change Buddy's runtime.

### Buddy read authority

Current Buddy World Graph retrieval/projection services still resolve the file-backed `world_graph_root()` and call `graph_memory.kernel` against Buddy's World SuperGraph storage. Those product seams must consume DungeonMind authority after the switch while preserving exact revision identity and expected failure behavior.

### Buddy write authority

Buddy still has file-backed World SuperGraph publication and contribution/identity stores. These are old authority paths, not future dual writers.

The normal governed product mutation path must be traced from the real GM confirmation/review action to the durable graph publication boundary. Prefer routing that existing governed intent into DungeonMind's existing finalized-review/publication authority rather than inventing a second mutation model.

### DungeonMind governed publication

DungeonMind already has durable contribution review and finalized-review publication machinery with exact parent revision checks, deterministic revision identity, atomic publication, replay/recovery semantics, and PostgreSQL repositories. Reuse existing authority wherever it matches the product workflow.

If the live cutover proves a missing public seam, repair that exact seam in DungeonMind. Do not use the absence of a convenient adapter as justification for another generalized migration layer.

---

## 5. Steward operating loop

The fresh agent owns the CUTOVER line as a designer/reviewer, not merely one document.

### Step 1 — re-anchor

Read current repository state, not this document's creation snapshot.

Establish:

```text
Buddy main SHA
DungeonMind main SHA
active CUTOVER PRs and branches
current dependency pin
current authority-transfer handoff
current tracker/roadmap/status agreement or contradiction
current Eldyrwild source head
current adopted DungeonMind head/receipt schema
```

If current truth materially differs, state the consequence before dispatch.

### Step 2 — repair sequencing authority if still stale

Bring the mutable Campaign Supergraph authority set into agreement with:

```text
#34 adoption DONE
#35 correspondence DONE
#36 exact membership V3 DONE
#37 governed review publication DONE (merge 2edc07ff27a21b1c83aed847edf95b77d297910e)
Buddy #619 authority transfer adapter MERGED — forward-fix predecessor with known repair debt
pinned catch-up CONDITIONAL / not dispatched absent STALE
authority completion repair CURRENT
```

Do not pre-mark authority transfer complete.

### Step 3 — dispatch/own the active authority-transfer implementation

Primary handoff:

`Docs/Plans/HANDOFF-CUTOVER-dungeonmind-authority-completion.md`

The intended Buddy branch is:

`cutover/dungeonmind-world-graph-authority-completion`

The intended PR is:

`CUTOVER: complete DungeonMind World Graph authority`

Amend the implementation handoff only when current code proves a material seam/lease change. Preserve the mission and locked decisions above.

### Step 4 — review every distinct implementation head by the transfer invariant

The review question is not "did tests pass?"

It is:

> While Buddy's old World Graph writer is quiesced, does the product read and governed mutation path move coherently to the exact adopted DungeonMind world, with safe failure before first DND-owned mutation and no path capable of creating competing Buddy history afterward?

Trace at minimum:

- dependency/runtime selection;
- final correspondence/checkpoint gate;
- read routing;
- exact revision identity through consumers;
- GM-confirmed mutation routing;
- DungeonMind publication parent/head CAS;
- response-loss/retry behavior;
- process/reload behavior;
- rollback before first DND child;
- fail-closed old Buddy writes after authority transfer.

### Step 5 — merge when the implementation is merge-ready

Do not wait for every possible runtime problem to be simulated.

The code must make the transition operable and safe enough to attempt. Remaining uncertainty is resolved by the real cutover attempt.

### Step 6 — operate the cutover

The expected live sequence is:

```text
1. Confirm exact environment/world/database identities.
2. Quiesce Buddy World Graph writes.
3. Promote/verify V3 receipt if the live receipt is still V2.
4. Run final exact correspondence against current frozen Buddy source.
5. If CORRESPONDING, switch product reads to DungeonMind.
6. Switch the normal governed GM-confirmed writer to DungeonMind.
7. Exercise ordinary reads through the product path.
8. Perform one controlled real governed World Graph mutation.
9. Verify DungeonMind published child D_B from the expected D_A/head.
10. Reload/restart and prove the product resolves D_B correctly.
11. Declare DungeonMind World Graph authority.
12. Disable/delete the old Buddy product write authority.
```

If step 4 reports `STALE`, pause transfer and reactivate the exact-snapshot catch-up design against the real B. Do not fabricate B before this happens.

### Step 7 — repair concrete failures and resume

A failure gets a bounded repair packet with:

```text
observed failure
exact environment/identity
failing boundary
expected invariant
minimal repair owner/repository
owning-boundary evidence
cutover resume point
```

Keep repairs as small as possible. A repair may live in DungeonMind or Buddy depending on the owner of the failed seam.

### Step 8 — retire old authority after the first surviving DND-owned write

Once `D_B` survives reload through the real product path, the steward should aggressively remove or hard-disable the replaced Buddy World Graph writer path from product use.

Do not leave a hidden fallback writer "just in case." That turns a migration into indefinite split-brain risk.

---

## 6. Review history lessons to preserve

Do not repeat the exact failure classes that earlier review cycles already taught us to guard:

### Evidence identity collision

The first real PostgreSQL acceptance found that one raw Buddy evidence ID could bind two immutable payloads. #609 fixed exported evidence identity. Preserve exact content-bound evidence identity; never normalize back to the raw Buddy ID at the persistence boundary.

### Cardinality is not membership

#35 showed that matching table/graph counts do not prove adopted history membership. #36 added exact `(record_id, record_fingerprint)` membership hashing across all four history families. Do not replace V3 membership proof with counts or graph-only equality.

### Promotion proof must be inside the writer-excluding boundary

#36 review found a PostgreSQL TOCTOU gap and then an analogous in-memory gap. Promotion/correspondence safety cannot depend on "we checked immediately before." Preserve the writer-excluding serialization semantics.

### Product authority is different from migration correctness

#34–#36 proved adoption and correspondence, not product routing. The current task exists precisely because those proofs are finished. Do not mistake their intentionally limited authority claims for evidence that another migration proof is required.

---

## 7. What should trigger a new design decision

The steward may reopen architecture only when real current evidence forces it.

Examples:

- the normal governed Buddy mutation cannot be expressed through DungeonMind's existing review/publication model without changing durable semantics;
- switching reads would destroy a currently required product behavior because DungeonMind lacks a representable query/projection contract;
- current Buddy graph has genuinely advanced and correspondence returns `STALE`;
- the adopted database reports `MISMATCH` or integrity failure that cannot be repaired under existing contracts;
- a required consumer depends on Buddy-only operational state that was mistakenly treated as World truth;
- post-`D_B` recovery requires a durable operator action not represented by current authority contracts.

When this happens, design the smallest repair that unblocks the cutover and name the exact resume point.

Do not convert a single failed seam into a broad redesign of the migration.

---

## 8. Explicit non-goals for this steward

Unless a concrete cutover failure promotes them, do not spend the workstream on:

- general CDC/streaming replication;
- automatic polling for newer Buddy snapshots;
- long-lived dual writes;
- multi-world migration framework design;
- arbitrary version migration support beyond the current accepted contracts;
- universal operator console for graph migration;
- broad performance optimization;
- Play/Runbook/Combat authority migration;
- product feature cleanup unrelated to the authority switch;
- ontology expansion;
- dormant maintenance writer parity before a real consumer requires it.

---

## 9. Source-of-truth reading order for the next steward

At pickup, read in this order:

1. **This document** — steward mission and locked decisions.
2. [`HANDOFF-CUTOVER-dungeonmind-authority-completion.md`](HANDOFF-CUTOVER-dungeonmind-authority-completion.md) — current implementation/operation payload; [`HANDOFF-CUTOVER-whole-world-authority-transfer.md`](HANDOFF-CUTOVER-whole-world-authority-transfer.md) — parent transfer contract (merged #619 adapter plus this completion slice).
3. [`../../AGENTS.md`](../../AGENTS.md) — repository operating law.
4. [`../Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md) — design/dispatch/review/re-anchor process.
5. Current `main`, open CUTOVER PRs/branches, and current worktrees/runtime state.
6. `Docs/Plans/PR-TRACKER-campaign-supergraph.md`, `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`, and `Docs/Design/STATUS-world-graph-continuity-spine.md` — reconcile them to current repository truth; they may be stale at pickup.
7. `HANDOFF-CUTOVER-exact-membership-receipt-v3.md` only for #36 predecessor invariants and review lessons.
8. DungeonMind current `main`, especially existing-world adoption/correspondence, review publication, service bootstrap, repository wiring, and PostgreSQL adapter tests.
9. Historical PR descriptions/reports only when needed to explain an invariant already present in current code.

Repository reality beats this anchor if the work has advanced since creation. When it does, update the anchor only if the operating truth changed materially.

---

## 10. Steward pickup prompt

Use this as the default prompt for a fresh CUTOVER designer/reviewer:

```text
You now own the CUTOVER workstream as steward/designer until durable World Graph
product authority has transferred from DungeonMindBuddy to DungeonMind and the
old Buddy product writer is retired.

Start by reading:

1. Docs/Plans/STEWARDS-ANCHOR-cutover.md
2. Docs/Plans/HANDOFF-CUTOVER-dungeonmind-authority-completion.md
3. AGENTS.md
4. Docs/Process/STEWARD-CYCLE.md

Then re-anchor both repositories and active PRs before acting.

Important inherited decisions:

- The migration preparation program is complete enough to attempt cutover now.
- DungeonMind #34 adoption, #35 correspondence, #36 exact membership V3, and #37
  governed review publication are completed predecessors, not work to redispatch.
- Buddy #619 (authority transfer adapter) is merged; its known repair debt is
  owned by the active authority-completion handoff, not by a new design gate.
- No later Buddy World Graph snapshot B has been observed; do not implement the
  parked pinned-snapshot catch-up unless the final live correspondence check
  actually returns STALE.
- Final V3/correspondence validation is phase 1 of the cutover transaction, not
  another readiness project.
- We expect to discover some integration problems by attempting the switch. Fix
  concrete failures at their owning boundary and resume; do not respond by
  inventing generalized preparation infrastructure.
- Before the first DungeonMind-owned child revision commits, routing rollback to
  frozen Buddy is allowed. After that first DND-owned mutation, Buddy writes stay
  off and failures are fix-forward.
- The normal governed GM-confirmed publication path must move. Dormant writers do
  not need parity unless a real consumer proves otherwise.

Your first responsibilities are:

1. establish current Buddy and DungeonMind main SHAs and active CUTOVER work;
2. reconcile stale Campaign Supergraph tracker/roadmap/status state if still
   necessary;
3. dispatch or continue the authority-transfer implementation handoff;
4. review each distinct PR head against the authority-transfer invariant;
5. merge when operable and safe enough to attempt the real cutover;
6. own the live cutover attempt and author bounded repair handoffs for concrete
   failures;
7. after the first DungeonMind-owned mutation survives reload, retire the old
   Buddy World Graph writer and synchronize authority documents.

Do not ask whether we should prepare more. Ask what concrete invariant prevents
us from switching authority right now, and either prove it holds or fix the
failure.
```

---

## 11. Fast pickup test

Before dispatching or reviewing code, the fresh steward should be able to answer:

1. What exact Buddy snapshot is currently authoritative?
2. What exact DungeonMind revision/receipt represents its adopted state?
3. Has a real later source snapshot B appeared?
4. Which current product read paths still use Buddy file-backed World Graph storage?
5. Which normal governed mutation path must publish through DungeonMind?
6. What is the rollback boundary before the first DND-owned mutation?
7. What changes after the first DND-owned child revision commits?
8. Which old Buddy product write paths must be disabled after success?
9. What current tracker/status documents are stale?
10. What exact new evidence would justify stopping the cutover rather than fixing forward?

If those answers require another broad reconnaissance project, the steward has lost the thread. Re-anchor current code and the active authority-transfer handoff instead.
