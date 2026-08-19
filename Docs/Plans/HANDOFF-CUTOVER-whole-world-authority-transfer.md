---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CUTOVER — whole World Graph authority transfer
  - Flow: CUTOVER
  - Direction: STEWARD → CODE/OPERATE → REVIEW/REPAIR
  - Handoff: Docs/Plans/HANDOFF-CUTOVER-whole-world-authority-transfer.md
  - Primary implementation repository: Drakosfire/DungeonMindBuddy
  - DungeonMind repair repository: Drakosfire/DungeonMind only when a concrete cutover failure proves a missing public seam

  ## Steward mandate
  DungeonMind PR #36 is merged. The exact Eldyrwild snapshot already adopted into
  PostgreSQL is still the current Buddy World Graph authority snapshot. This PR
  is not another readiness, reconnaissance, shadow, catch-up, or migration-proof
  slice. Implement the authority switch, merge it, attempt the live cutover, and
  repair concrete failures as they appear.

  The parked pinned-snapshot catch-up design is not current work. It becomes
  relevant only if the final pre-switch correspondence check actually reports
  STALE for a later sealed Buddy snapshot.
---

# HANDOFF — whole World Graph authority transfer

**Created:** 2026-08-17  
**Status:** CUTOVER_COMPLETE — DungeonMind is living Eldyrwild World Graph authority; Buddy local writer authority retired/fail-closed  
**Conversation/workstream:** `CUTOVER — whole World Graph authority transfer`  
**Flow / owner:** `CUTOVER`  
**Direction:** STEWARD → CODE/OPERATE → REVIEW/REPAIR  
**Canonical handoff path:** `Docs/Plans/HANDOFF-CUTOVER-whole-world-authority-transfer.md`  
**Primary implementation repository:** `Drakosfire/DungeonMindBuddy`  
**Buddy dispatch base:** `9ff4f885a365231841204514c3b27d9e7da5f6bd` (`main` at steward dispatch)  
**DungeonMind authority base at completion:** `2edc07ff27a21b1c83aed847edf95b77d297910e` (merge of DungeonMind PR #37; superseded the #36 pin used at original dispatch)  
**Implementation PRs:** Buddy #619 (`6c2fe9d37dcecf34e025db8373fce072de30b62e`) + Buddy #620 (`18bcb18475ac30679ebec84bec17c4e81390f674`; 4 review cycles; final PASS `4966969478`)  
**Live D_A:** `rev:34b1f8e2625d5ba693fc726a2a1a4720`  
**Live D_B:** `rev:680c246047d67f9fe0293ee90526f670` (parent = D_A; canary `node:cutover-canary` / `Cutover Canary`)  
**Suggested Buddy branch:** `cutover/whole-world-authority-transfer`  
**Suggested Buddy PR title:** `CUTOVER: transfer World Graph authority to DungeonMind`

> **Steward ruling:** the preparation phase is over. Prior slices have already proven the exact adoption, PostgreSQL persistence, correspondence algebra, and exact adopted-membership checkpoint. The next useful evidence comes from attempting the real authority switch. A failure found while cutting over is a repair input, not evidence that another generalized preparation program should be invented.

---

## §0 Steward decision — stop preparing and attempt the cutover

The prior CUTOVER sequence was deliberately conservative. That work succeeded. It established enough truth to stop asking whether the migration is theoretically safe and start exercising the authority transition itself.

The current evidence chain is:

1. Buddy PR #609 sealed the final Eldyrwild adoption bytes after repairing contribution evidence identity. Unchanged DungeonMind accepted those exact bytes into PostgreSQL with empty-target adoption, exact retry, different-bundle conflict, precommit rollback, postcommit recovery, and graph readback.
2. DungeonMind PR #34 independently accepted the exact sealed Buddy bundle at the owning PostgreSQL boundary.
3. DungeonMind PR #35 proved the exact adopted A snapshot reports `CORRESPONDING`, coherent divergence reports `MISMATCH`, a genuinely different valid source snapshot reports `STALE`, and the evaluator performs zero writes.
4. DungeonMind PR #36 added receipt V3, exact adopted-membership hashing, supervised V2→V3 promotion, writer-excluding promotion boundaries, and the exact Eldyrwild membership proof. PR #36 is merged at `9a19584d31baea77f590d7726e508b144c7dd39d`.
5. Buddy `main` has advanced substantially since #609, but the advance is product/runtime/process work. The steward comparison from #609 merge `7922b6108cf9e05787f9c79cddcee9347edb0b44` to dispatch `main` found no changes to `graph_data/**`, the Eldyrwild adoption producer, the sealed adoption bundle, or Buddy World Graph persistence. The current producer still pins the exact A revision and payload already adopted by DungeonMind.

Therefore:

```text
There is no observed B snapshot to catch up to.
There is no evidence-driven reason to dispatch a synthetic A→B catch-up.
The next operation is the authority transfer itself.
```

### Parked catch-up disposition

`cutover/design-pinned-snapshot-catchup` and its draft `HANDOFF-CUTOVER-pinned-exact-snapshot-catchup.md` are **CONDITIONAL RECOVERY DESIGN, NOT CURRENT DISPATCH**.

Do not merge or implement that handoff merely because an older tracker called it next.

It becomes current only if the final live pre-switch correspondence check proves all of the following:

```text
incoming Buddy snapshot is valid
+ source identity differs from adopted A
+ adopted V3 membership remains intact
+ result == STALE
```

If no `STALE` exists, no catch-up capability is needed for this cutover.

### Forbidden disposition language

An implementation or review may not end with a generic:

```text
CUTOVER_NOT_READY
```

unless it names one **newly observed, reproducible failing invariant** from this handoff and the concrete boundary where it failed.

Prior proof categories are not valid reasons to restart readiness work.

---

## §1 Exact starting authority

### Buddy source snapshot A

```text
world_id: eldyrwild
source revision A: rev:0c644e56b45bcaac709012206e3e41c2
Buddy graph payload SHA-256:
  0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2
sealed bundle Git blob:
  274cdd9e6d38d5a00aa43d780779e95a7919d975
sealed bundle SHA-256:
  90574dfc4101e4198c7fd96478d6f49e65aa534d0aa91fa41a9a17da9d49695f
```

### DungeonMind adopted A

```text
adoption_id:
  adoption:eldyrwild:dungeonmind-v6:rev:0c644e56b45bcaac709012206e3e41c2
published DungeonMind revision D_A:
  rev:34b1f8e2625d5ba693fc726a2a1a4720
graph payload SHA-256:
  047214f19e3a2d22b1cf3e0596283844ef34853dd2e4f38d341c6b212ae320ef
shape:
  469 objects / 323 relationships / 3 secondary aspects / 5 aspect-selected relationships
```

### Receipt V3 checkpoint

The canonical exact adopted-membership digest for the sealed Eldyrwild bundle is:

```text
538195e399158bfb4fafce01f9c5af3c63e2137f70694fdead7a26e5800e0890
```

The checkpoint covers sorted `(record_id, record_fingerprint)` pairs for:

```text
source artifacts
source revisions
graph contributions
identity decisions
```

### Target database rule

The cutover target may be either:

1. the already-used persistent PostgreSQL instance containing adopted A; or
2. a clean designated cutover PostgreSQL database initialized now from the exact sealed A bundle using current DungeonMind.

Both are valid. Do not create a new migration architecture merely because the accepted integration proof used disposable databases.

The required starting state is simply:

```text
exact A durable in target PostgreSQL
+ receipt V3 installed
+ current durable membership == V3 checkpoint
+ correspondence(A) == CORRESPONDING
```

If an existing target still has a V2 receipt, run the merged supervised V2→V3 promotion. If a clean target is adopted under current DungeonMind, the V2 bundle directly emits V3.

---

## §2 Mission and terminal invariant

### Mission

Transfer **living Eldyrwild World Graph authority** from Buddy's file-backed World Supergraph to DungeonMind PostgreSQL now, while preserving Buddy product contracts and keeping source/Playable/runtime ownership where it already belongs.

The steward should attempt the live transition immediately after the required routing code merges. If the attempt exposes a defect, repair that exact defect and resume the same cutover. Do not return to generalized readiness work.

### Terminal cutover invariant

The cutover is complete only when all of these are true:

```text
1. The designated DungeonMind PostgreSQL world is V3-checkpointed and was
   CORRESPONDING to frozen Buddy A immediately before the switch.

2. Active Buddy product World Graph reads are served from DungeonMind durable
   authority, not out/graph_memory/worlds/<world_id>.

3. Buddy's local World Graph mutators are fail-closed while DungeonMind owns
   authority. No product path can silently continue a second graph history.

4. At least the normal governed GM-confirmed World Graph publication path can
   commit a new DungeonMind revision under the existing authority contracts.

5. One real post-cutover governed mutation commits D_A → D_B in DungeonMind,
   survives server/browser reload, and is visible through the normal Buddy
   product read path.

6. Buddy's frozen local graph tree remains unchanged from the quiescence
   checkpoint through the first DungeonMind-owned mutation.

7. No dual write occurs before, during, or after the transfer.
```

The first successful DungeonMind-owned mutation is the **point of no return by routing alone**. After it commits, DungeonMind has newer authoritative history than Buddy. From that point forward, failures are fixed forward; Buddy writes must not be re-enabled as an emergency shortcut.

---

## §3 Authority boundary after cutover

### Moves to DungeonMind authority

For Eldyrwild World Graph state:

- current graph head;
- immutable graph revisions;
- durable graph contributions and their lifecycle;
- identity decisions;
- adopted source-artifact/source-revision authority required by graph history;
- graph evidence bindings stored in the DungeonMind history plane;
- governed publication that advances the World Graph head.

### Remains Buddy-owned

This cutover does **not** move unrelated product authorities:

- source prose/files and source-opening UX;
- Runbooks / Playable Material;
- Play Run and Runtime progress;
- Combat runtime state;
- Plan/Build/Play surface composition;
- candidate extraction and preview/review UX before durable graph commit;
- source document authoring;
- non-graph product preferences/caches;
- any mechanics authority already separately owned by DungeonMind statblock contracts.

A Buddy candidate may still be prepared and reviewed in Buddy. The boundary that matters is the durable confirmation/publication: once accepted as World Graph truth, the durable write goes to DungeonMind.

---

## §4 Operating posture — cutover, observe, repair

This handoff intentionally changes the default engineering posture.

### Do not add another preparatory slice for

- a synthetic descendant snapshot B;
- CDC, polling, queues, or background replication;
- a dual-write period;
- a prolonged read-shadow period;
- another whole-world conformance inventory;
- another PostgreSQL ingestion simulation of exact A;
- another correspondence algebra proof unrelated to a newly observed failure;
- generalized migration infrastructure for future worlds;
- a universal cross-repository graph ORM;
- a new product feature used only as a canary;
- exhaustive migration of dormant historical exact-revision references before one fails in real use;
- broad deletion/cleanup before authority actually moves.

### Bounded discovery is implementation work, not a report

The implementation agent may inspect current callers to identify the exact read and confirmed-publication seams. That discovery must immediately drive code in the same cutover lane.

A report whose output is “here are the seams we should implement next” does not satisfy this handoff.

### Repair loop

```text
attempt cutover invariant
→ observe concrete failure
→ identify owning boundary
→ make smallest repair
→ review + merge repair
→ resume at the failed cutover step
```

Do not restart from step zero unless the failed invariant invalidates prior durable state.

---

## §5 Cutover execution sequence

This is one steward-owned operation. The routing implementation PR is followed immediately by the live switch under this same handoff; there is no new design handoff between merge and cutover attempt.

### Phase 1 — repin Buddy to accepted DungeonMind

Update Buddy's exact dependency from the historical #33 runtime pin to current accepted DungeonMind:

```text
9a19584d31baea77f590d7726e508b144c7dd39d
```

or an exact descendant containing a concrete repair discovered during this cutover.

Regenerate `uv.lock` normally. Do not track `latest` or a branch name.

The repin must preserve existing statblock/mechanics consumers while exposing the merged adoption/correspondence/V3 contracts.

### Phase 2 — establish the quiescence boundary

Before the final live correspondence check:

1. capture Buddy A head/revision/tree digests;
2. put **all local Buddy World Graph mutation primitives** behind one fail-closed authority/quiescence guard;
3. prove ordinary product mutation attempts cannot write local graph revision, contribution, or identity state while quiesced;
4. leave source authoring, Runbook, Play Runtime, and other non-graph workflows operational where practical.

Quiescence is not “we promise not to click the button.” It is enforced at the low owning boundary so a forgotten caller cannot create a second history.

The existing file-backed store remains readable during the pre-mutation rollback window, but not writable.

### Phase 3 — final pre-switch V3 correspondence

Against the designated target PostgreSQL database and the exact sealed A bytes:

```text
require V3 receipt
require exact membership checkpoint match
require correspondence(A) == CORRESPONDING
```

Disposition:

- `CORRESPONDING` → continue immediately;
- `STALE` with a valid later sealed Buddy snapshot → stop the switch and activate the parked pinned-snapshot catch-up design for the **observed** A→B only;
- `MISMATCH` → stop and repair the concrete divergence;
- integrity/unavailable error → stop and repair the target persistence/runtime problem;
- `NOT_ADOPTED` → adopt exact A into the designated target, then rerun this phase.

Do not turn any of these outcomes into a generalized new readiness program.

### Phase 4 — switch active product reads

Switch the existing Buddy World Graph service boundary to DungeonMind-backed reads while preserving Buddy's product-facing request/response contracts unless an exact contract repair is required.

Known current Buddy service seams include:

```text
apps/live_control_server/services/world_graph_projection.py
apps/live_control_server/services/world_graph_retrieval.py
```

Today those services resolve `world_graph_root()` and call Buddy `graph_memory.kernel` over the file-backed store. The cutover implementation should replace the authority behind those service seams, not rewrite Plan/Build/Play/Hermes independently.

Use current DungeonMind public application/repository/snapshot contracts. Do not reach from Buddy directly into DungeonMind PostgreSQL tables with ad-hoc SQL.

If a small stable adapter can preserve the existing Buddy projection/retrieval transport, prefer that to a product-wide rewrite.

### Phase 5 — preserve exact pre-cutover revision references

Pre-cutover product state may contain exact Buddy revision A:

```text
rev:0c644e56b45bcaac709012206e3e41c2
```

DungeonMind's adopted revision identity is:

```text
rev:34b1f8e2625d5ba693fc726a2a1a4720
```

The adoption receipt is the only accepted bridge between those identities.

Required compatibility rule:

```text
legacy Buddy A
  -- exact adoption receipt / source_provenance binding only -->
DungeonMind D_A
```

No `latest`, graph-shape match, label lookup, timestamp, or guessed revision mapping is allowed.

Existing exact A references must continue to open the exact adopted historical state. New authoritative revisions after cutover use DungeonMind revision identity.

If the active product contract requires an outward normalization from legacy A to D_A, make the smallest explicit transport repair. Do not invent a general revision dictionary.

A historical Buddy revision other than the exact adopted A may fail closed until real product use proves it must be supported. That is a concrete repair, not a pre-cutover blocker by assumption.

### Phase 6 — switch governed durable writes

The first required living writer is the normal GM-confirmed graph publication path, not every historical maintenance script.

Route the existing explicit-confirmation path to DungeonMind's governed contribution review/publication authority. Reuse current DungeonMind public contracts such as the finalized contribution review/publication services where they fit; adapt Buddy's existing review intent at the boundary rather than bypassing governance.

The cutover is allowed to leave dormant Buddy-only maintenance commands **fail-closed** instead of porting them speculatively. Any product-visible write path that is exercised after cutover and fails because it lacks a DungeonMind route becomes an immediate repair under §8.

Local Buddy graph mutation must remain disabled even when a DungeonMind write fails.

### Phase 7 — execute the first real DungeonMind-owned mutation

After the routing implementation is merged and the live read switch is healthy, perform one **real GM-approved World Graph mutation through the normal product workflow**.

Do not add a fake campaign fact merely to satisfy a test. Prefer the next genuine reviewed assertion/correction/publication the GM is willing to commit.

Required proof:

```text
before: DungeonMind head == D_A (or exact then-current DND head)
commit: normal governed Buddy product action writes DungeonMind only
after: DungeonMind head == D_B, parent(D_B) == prior DND head
Buddy local tree/head/contribution/identity digests unchanged
normal Buddy read path returns the new authoritative meaning
server/browser reload returns the same D_B state
exact retry/replay does not duplicate the mutation
```

### Phase 8 — declare point of no return and fix forward

The moment D_B commits:

```text
DungeonMind is living World Graph authority.
```

From then on:

- do not re-enable Buddy graph writes;
- do not switch to a dual-write repair;
- do not copy D_B back into Buddy and pretend Buddy is authoritative again;
- fix read/integration/product failures forward against DungeonMind;
- retain frozen Buddy A only as forensic/migration history until demolition is safe.

---

## §6 Rollback boundary

Rollback is intentionally asymmetric.

### Before the first DungeonMind-owned post-cutover mutation

If the read switch or product integration fails **before D_B exists**, the steward may:

1. switch active reads back to frozen Buddy A;
2. verify Buddy graph/head/history digests are unchanged from quiescence;
3. re-enable Buddy writes only after the DungeonMind path is no longer active;
4. repair the concrete cutover defect and retry.

Because neither authority advanced while Buddy was frozen, this rollback does not create divergent histories.

### After the first DungeonMind-owned post-cutover mutation

Routing rollback to Buddy writes is forbidden.

After D_B, Buddy A is stale by construction. Re-enabling Buddy writes would fork authority.

The recovery posture becomes:

```text
keep Buddy writes frozen
keep DungeonMind durable state intact
repair the product/read/write integration forward
```

A true reverse migration after D_B would be a separate emergency data-recovery operation requiring explicit steward authorization. It is not the normal rollback plan.

---

## §7 Concrete failure policy

A failure can stop the current switch step, but it cannot automatically create another preparation phase.

| Observed failure | Required action |
|---|---|
| Buddy no longer installs against current DungeonMind | repair the exact dependency/API incompatibility, repin, resume |
| V3 promotion/checkpoint fails | repair the exact durable membership discrepancy; do not switch |
| final correspondence is `STALE` | use the parked catch-up design for that observed B only |
| final correspondence is `MISMATCH` | repair/understand exact divergence; do not paper over it |
| DungeonMind target unavailable | repair database/service configuration and rerun same step |
| Buddy projection/retrieval cannot express DungeonMind snapshot | add the smallest explicit adapter at the shared service boundary |
| legacy exact A reference cannot open | repair the exact A→D_A receipt-bound compatibility seam |
| normal Graph Review publication lacks a DungeonMind public seam | add the smallest DungeonMind public capability, merge it, repin Buddy, resume |
| a dormant Buddy writer is invoked | fail closed; port it only if the workflow is actually needed |
| product regression before D_B | rollback reads to frozen A if useful, repair, retry |
| product regression after D_B | fix forward; Buddy writes remain disabled |

### Conditional DungeonMind repair rule

Do **not** pre-author a speculative DungeonMind repair PR.

If the Buddy implementation proves a required public DungeonMind read/write seam is absent, the steward may immediately dispatch one smallest DungeonMind repair from current `main`, citing:

- this handoff;
- the exact failing Buddy test/request;
- the missing public contract;
- the minimum new behavior required to resume the cutover.

That repair is part of this cutover operation. It does not require another generalized design/reconnaissance cycle unless the failure contradicts the locked authority model or requires semantic loss.

Buddy may use DungeonMind public application/repository APIs in-process where that is the existing integration model. Do not build a new HTTP service merely for layering ceremony, and do not import private PostgreSQL implementation details into Buddy.

---

## §8 Primary Buddy implementation write lease

The initial implementation lane is `Drakosfire/DungeonMindBuddy`.

Expected exact write set:

| Action | Path | Purpose |
|---|---|---|
| Modify | `pyproject.toml` | repin exact DungeonMind authority |
| Modify | `uv.lock` | lock accepted DungeonMind revision |
| Modify | `apps/live_control_server/config.py` | cutover database/authority configuration if required |
| Create | `apps/live_control_server/integrations/dungeonmind_kernel/world_graph_authority.py` | DungeonMind-backed read/write authority adapter and exact A→D_A binding |
| Modify | `apps/live_control_server/services/world_graph_projection.py` | route product projection reads through selected authority |
| Modify | `apps/live_control_server/services/world_graph_retrieval.py` | route object/neighborhood/evidence reads through selected authority |
| Modify | `src/graph_memory/world_supergraph/storage.py` | fail-close file-backed head/revision mutation while DungeonMind owns authority |
| Modify | `src/graph_memory/world_supergraph/contribution_store.py` | fail-close local contribution mutation while DungeonMind owns authority |
| Modify | `src/graph_memory/world_supergraph/identity_decision_store.py` | fail-close local identity mutation while DungeonMind owns authority |
| Create | `tests/test_cutover_dungeonmind_world_graph_authority.py` | owning cutover adapter/quiescence/revision-bridge proof |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | backward-looking #36 sync + current cutover dispatch truth |
| Modify | `Docs/Design/STATUS-world-graph-continuity-spine.md` | backward-looking #36 sync + current authority transition truth |
| Modify | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | replace speculative catch-up-first sequence with observed cutover sequence |
| Modify | `Docs/Plans/HANDOFF-CUTOVER-exact-membership-receipt-v3.md` | mark merged #36 implementation DONE/HISTORICAL with exact merge truth |

### Explicit bounded-discovery lease expansion

The current normal GM-confirmed publication entrypoint must be routed to DungeonMind, but this handoff does not guess its exact current module after months of product evolution.

The implementation agent is authorized to add **only** the exact current production confirm/publish route/service and its owning tests to this lease after static call-path discovery proves them necessary.

Before editing those extra paths, record in the implementation handback:

```text
exact path(s)
entrypoint/caller proving they are the current durable-confirmation path
why each path is required for DungeonMind write routing
```

This is an authorized lease expansion, not a stop/split condition.

Any other path expansion still follows normal steward rules.

### Runtime/state collision

This lane owns the designated CUTOVER PostgreSQL database and Eldyrwild World Graph authority switch while the live operation is executing. Parallel lanes may continue work that does not mutate Eldyrwild World Graph authority or the same cutover DB.

Do not run another Eldyrwild graph writer concurrently with the quiescence/cutover operation.

---

## §9 Read and write implementation constraints

### Read constraints

- preserve revision-pinned semantics;
- no current/latest fallback for exact references;
- preserve campaign/admissibility behavior at the Buddy product boundary;
- source opening may continue to resolve Buddy-owned source prose after graph evidence admission;
- cache/resident runtime may accelerate reads but never choose authority;
- a DungeonMind unavailable/integrity failure fails visibly rather than falling back silently to Buddy after authority has switched.

### Write constraints

- explicit GM confirmation remains required;
- expected-parent/CAS semantics remain required;
- a failed DungeonMind write does not fall back to Buddy;
- no dual-write transaction is introduced;
- no private SQL from Buddy into DungeonMind tables;
- durable success comes from DungeonMind receipt/revision authority, not “the Buddy graph looks updated.”

### Compatibility constraint

The file-backed Buddy store may remain present for pre-cutover historical reads and forensic comparison during this operation. Presence on disk is not authority.

After D_B, any use of Buddy A as a current-head fallback is a defect.

---

## §10 Evidence required for the implementation PR

The Buddy routing PR is merge-ready when its code can support the immediate live attempt and proves the following against current DungeonMind/PostgreSQL in automated integration where practical.

| Guarantee | Required evidence |
|---|---|
| Exact dependency | Buddy lock resolves exact DungeonMind #36 merge or named repair descendant |
| A→D_A identity bridge | only the exact adopted receipt maps legacy Buddy A to D_A; wrong source/revision fails closed |
| V3 precondition | target test DB can adopt/promote A and verify exact membership digest |
| Correspondence | exact A reports `CORRESPONDING` through current merged evaluator |
| Local quiescence | ordinary local head/contribution/identity mutations are rejected in DungeonMind-authority mode |
| Projection read | normal Buddy projection service returns correct Eldyrwild data backed by DungeonMind |
| Retrieval read | normal Buddy object/evidence/neighborhood path returns exact DungeonMind-backed data |
| Existing A reference | one real current product-style exact A reference remains openable after authority switch |
| No silent fallback | DungeonMind unavailable/integrity error does not read current Buddy A as if authoritative |
| Governed write | normal confirmed-publication integration can create one child DungeonMind revision in test PostgreSQL |
| Local store unchanged | Buddy file-backed graph/history digests are unchanged by the DungeonMind write test |
| Retry/recovery | exact publication retry/recovery does not duplicate the durable write |
| Restart | a fresh service process reads the new DungeonMind revision rather than process-local state |

Do not require a prolonged shadow soak. The active DungeonMind-backed test path is the proof.

Repository-wide baseline failures must be separated from head-introduced failures exactly as in prior CUTOVER reviews; inherited failures are not permission to ignore new failures and are not automatically blockers on this slice.

---

## §11 Live cutover checklist after merge

The steward executes this checklist **immediately after the routing implementation merges**. No new handoff is authored between merge and this attempt.

```text
[ ] Re-anchor Buddy main and exact DungeonMind pin.
[ ] Start/verify designated DungeonMind PostgreSQL target.
[ ] Adopt exact A or promote existing A receipt to V3.
[ ] Record V3 membership digest and D_A.
[ ] Capture frozen Buddy A head/tree/history digests.
[ ] Enable Buddy World Graph quiescence guard.
[ ] Prove one local graph mutation is rejected.
[ ] Run final exact A correspondence; require CORRESPONDING.
[ ] Switch active Buddy reads to DungeonMind.
[ ] Exercise Plan exact graph read.
[ ] Exercise Build/Recap/Hermes exact graph read where mounted.
[ ] Exercise Play exact graph reference if current Play route is mounted; do not block cutover on an unmerged Play feature.
[ ] Confirm one legacy A reference resolves through the receipt-bound D_A mapping.
[ ] Select one real GM-approved graph mutation.
[ ] Commit it through normal product confirmation into DungeonMind.
[ ] Record D_B and parent(D_B).
[ ] Re-read through normal Buddy product path.
[ ] Restart server/browser and re-read D_B.
[ ] Verify Buddy local graph/head/history digests remain frozen.
[ ] Declare point of no return: DungeonMind living authority.
```

If a box fails, apply §7 and resume at that box after repair.

---

## §12 State-authority synchronization owned by this slice

The implementation PR must perform the backward-looking synchronization that is already knowable at dispatch:

### Record as completed predecessor

DungeonMind PR #36:

```text
PR: #36
head: 6a249b483687c5f25c46298016c53dbb9afe4521
merge: 9a19584d31baea77f590d7726e508b144c7dd39d
review disposition: Review Cycle 3 PASS / no code changes requested
formal review: 4956825887
integration: green
inherited core lint baseline: tests/unit/test_dnd_world_object_v5.py:203 SIM300
```

### Current sequence meaning

Tracker/status/roadmap must say, in substance:

```text
DONE     exact adopted-membership receipt V3 / DungeonMind #36
DEFERRED pinned exact-snapshot catch-up — activate only on observed STALE
DOING    whole-world authority transfer — cut over now; repair concrete failures
BLOCKED  none of the old readiness/preparation categories by default
```

Do not pre-mark this authority-transfer handoff complete in the implementation PR.

### After live D_B success

Because live success becomes knowable only after the implementation merge, the steward performs a direct guarded state sync (or the next actual repair/cleanup PR carries it immediately) recording:

```text
DungeonMind is living Eldyrwild World Graph authority
first DND-owned revision D_B and its parent
Buddy local writer authority retired/fail-closed
CUTOVER_COMPLETE for whole-world authority transfer
```

Do not create a routine documentation-only PR solely for that completion record.

---

## §13 Stop conditions that genuinely reopen design

Most failures are repairs. Reopen architecture/design only if the live attempt proves one of these:

1. current Buddy A is not in fact the source state represented by the sealed bundle and the difference cannot be classified as a normal `STALE` descendant;
2. exact correspondence reports a reproducible semantic `MISMATCH` caused by loss in the accepted adoption representation rather than corruption/implementation defect;
3. a required current Buddy product behavior depends on semantic information that DungeonMind did not adopt and cannot recover without changing authority semantics;
4. the normal confirmed-publication workflow cannot be represented by DungeonMind's governed contribution/review/publication model without weakening explicit approval, expected-parent, or history guarantees;
5. the cutover would require intentional dual writers to preserve a required product invariant.

If none of those occurs, do not return to design.

---

## §14 Required implementation/review handback

Every review cycle should be able to answer these questions without reconstructing the project history:

```text
Buddy base/head:
DungeonMind exact pin:
changed paths vs §8 lease:
lease expansions and call-path evidence:

Target PostgreSQL setup:
A adoption/receipt schema:
V3 membership_sha256:
D_A:
final correspondence result:

Buddy frozen head/tree/history digests:
quiescence rejection proof:

DungeonMind-backed projection/retrieval proof:
legacy A→D_A reference proof:
no-fallback failure proof:

governed write test D_A→D_B:
parent(D_B):
Buddy local digests after D_B:
restart/reload proof:
retry/recovery proof:

Concrete cutover failures discovered:
repairs made or required:

CUTOVER disposition for this head:
  MERGE-READY FOR LIVE CUTOVER ATTEMPT
  or
  CHANGES REQUIRED — <exact reproducible blocker>
```

The reviewer should challenge actual correctness and authority boundaries. It should not manufacture another preparation gate because this work is high consequence.

---

## §15 Nonclaims

This handoff does not claim:

- every future world is automatically migrated;
- every dormant Buddy maintenance script is already ported;
- Play/Runbook/Combat state moves into DungeonMind;
- frozen Buddy graph files must be deleted before cutover;
- operational issues will not occur.

It claims something narrower and more useful:

```text
We have enough proof to attempt the Eldyrwild authority transfer now.
We will make the product use DungeonMind, observe what actually breaks,
and repair concrete failures without inventing more speculative preparation.
```
