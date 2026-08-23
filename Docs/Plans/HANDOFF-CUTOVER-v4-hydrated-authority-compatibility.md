---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CUTOVER — V4 hydrated authority compatibility prerequisite
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-CUTOVER-v4-hydrated-authority-compatibility.md
  - Implementation repository: Drakosfire/DungeonMindBuddy

  ## Exact predecessor truth
  - Buddy implementation base: `b850b9f8126a8c8488d17b3bdb6f99a60a162338` (`main` at dispatch).
  - DungeonMind R.2b repair landed in PR #43 / merge `519b2c96fc42d22f3113cc9ca0d48bc70b6780e5` after four formal review cycles.
  - Buddy R.3 direct-read PR #629 remains paused. Its current head at dispatch is `c3e57d9f6f54c552da564babcdcb0e83f36740ea` and must not be edited in parallel with this prerequisite.
  - Live Eldyrwild authority remains on the corrupted V3 adopted-source state until this prerequisite merges and the steward-run repair sequence succeeds.

  Land the minimum Buddy compatibility needed for the currently deployed hydrated
  DungeonMind-authority path to serve either a V3 adoption receipt or the governed
  V4 repaired-adoption receipt from DungeonMind PR #43. Pin Buddy to that exact
  DungeonMind merge. Do not enable direct reads, perform the live repair, or solve
  R.3 semantic/performance blockers in this PR.
---

# HANDOFF — CUTOVER: V4 hydrated authority compatibility

**Created:** 2026-08-23  
**Status:** ACTIVE — dispatch exactly one implementation capability  
**Workstream:** CUTOVER / World Graph runtime retirement  
**Direction:** DESIGN → CODE → REVIEW  
**Implementation repository:** `Drakosfire/DungeonMindBuddy`  
**Exact Buddy base:** `b850b9f8126a8c8488d17b3bdb6f99a60a162338`  
**Required DungeonMind pin:** `519b2c96fc42d22f3113cc9ca0d48bc70b6780e5` (merge of DungeonMind PR #43)  
**Suggested branch:** `cutover/v4-hydrated-authority-compatibility`  
**Suggested PR title:** `CUTOVER: accept repaired V4 adoption state on hydrated reads`  
**Predecessor:** DungeonMind R.2b — governed adopted-source classification repair  
**Named successor:** Buddy R.3 continuation — repaired-authority semantic witness and residual parity resolution  
**Later successor:** DungeonMind R.3a — reusable/materialized World Graph read context; not part of this slice

> **Dispatch ruling:** this is a small compatibility prerequisite, not a new
> authority migration and not the direct-read cutover itself. Its purpose is to
> break a real sequencing cycle: the live DungeonMind V4 repair is required to
> finish R.3 semantic parity, but applying that repair before landed Buddy code
> understands V4 would break the currently deployed hydrated compatibility path.
>
> Therefore V4 hydrated compatibility lands on Buddy `main` first. The live
> repair is a separate post-merge steward operation. Only after both are true do
> we rebase PR #629 and rerun the semantic witness.

---

## 1. Mission and merge-ready invariant

### Mission

Buddy's landed DungeonMind-authority hydrated runtime can bind and serve either
an existing V3 adoption receipt or DungeonMind's governed V4 repaired-adoption
receipt so that the live R.2b repair can be applied without requiring R.3 direct
reads to be merged or enabled.

### Merge-ready invariant

> With `DUNGEONMIND_WORLD_GRAPH_AUTHORITY=dungeonmind` and the R.3 direct-read
> rollout gate absent/off, the existing hydrated path accepts only explicitly
> supported typed V3/V4 adoption receipts, selects the receipt-defined adopted
> membership checkpoint exactly (`V3.membership_sha256`; V4
> `effective_membership_sha256` over the V4 manifest-selected adopted members),
> verifies that adopted membership before hydration, preserves existing V3 and
> frozen-store replay semantics, ignores legitimate post-adoption descendants
> for V4 membership, and fails closed on unsupported receipt schemas, missing
> adopted members, or checkpoint drift without mutating Buddy or DungeonMind
> authority.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes. Every path is the same receipt-binding / adopted-membership verification capability before existing hydration proceeds. |
| What adversarial sequence is most likely to falsify it? | V4 is written successfully → Buddy selects `membership_sha256` or reconstructs the wrong adopted subset → hydration rejects valid repaired authority or, worse, accepts a wrong subset. |
| Would the evidence below detect that failure? | Yes. The owning tests must use a real `ExistingWorldAdoptionReceiptV4`, prove exact M1/manifest selection, include descendants outside the manifest, and tamper one adopted row. |
| Which boundary is easiest to under-test? | `_verify_adopted_membership`; a binder-only test can pass while serve-time digest selection is still wrong. |
| What fact would force this slice to stop or split? | If V4 compatibility requires changing graph reconstruction semantics, direct-read routing, DungeonMind repair semantics, or a second production file outside the narrow authority adapter seam. |

---

## 2. Why this PR exists: break the sequencing cycle

The reviewed R.2b deployment order originally said to return to Buddy PR #629,
repin it, teach V4 compatibility, then apply the live repair. Current repository
truth exposes a circular dependency:

```text
R.3 parity needs repaired DungeonMind authority
        ↓
live repair writes V4
        ↓
landed/current Buddy hydrated reads must understand V4
        ↓
PR #629 cannot merge until repaired-authority parity is resolved
```

V4 support only on the paused #629 branch is not sufficient protection for the
currently landed product path.

The corrected sequence is:

```text
DungeonMind #43 merged
        ↓
THIS PR: land V4 hydrated compatibility on Buddy main
        ↓
post-merge steward: backup + dry-run + apply live R.2b repair
        ↓
prove landed hydrated reads still serve with direct-read gate off
        ↓
rebase Buddy #629 onto repaired-compatible main
        ↓
rerun R.3 semantic witness against trustworthy repaired authority
        ↓
resolve residual semantic blockers
        ↓
R.3 complete
        ↓
R.3a performance architecture
```

This PR is independently useful even if R.3 is delayed: landed Buddy becomes
forward-compatible with the one governed repaired-adoption receipt generation
DungeonMind now supports.

---

## 3. Context, authority, and exact predecessor truth

### Parent authorities

Read in this order before editing:

#### DungeonMindBuddy

1. `AGENTS.md`
2. `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
3. `Docs/Plans/STEWARDS-ANCHOR-cutover.md`
4. `Docs/Plans/HANDOFF-CUTOVER-direct-dungeonmind-production-reads.md`
5. this handoff
6. `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
7. `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`
8. `apps/live_control_server/integrations/dungeonmind_kernel/world_graph_authority.py`
9. `tests/test_cutover_dungeonmind_world_graph_authority.py`
10. `pyproject.toml` and `uv.lock`

#### DungeonMind

At exact merge `519b2c96fc42d22f3113cc9ca0d48bc70b6780e5`:

1. `Docs/Handoffs/HANDOFF-cutover-adoption-source-classification-repair.md`
2. `Docs/Decisions/ADR-0021-existing-world-adoption-repair.md`
3. `src/dungeonmind/contracts/existing_world_adoption.py`
4. `src/dungeonmind/application/existing_world_adoption_repair.py`
5. `src/dungeonmind/application/existing_world_correspondence.py`
6. `src/dungeonmind/infrastructure/postgres/existing_world_adoption.py`
7. `scripts/repair_existing_world_adoption_source_classification.py`

### Exact predecessor facts

- DungeonMind is already the living Eldyrwild World Graph authority.
- R.1 direct projection, R.2 direct retrieval, and R.2a read observability are landed.
- DungeonMind R.2b is landed in PR #43 at merge `519b2c96...`.
- R.2b introduces `ExistingWorldAdoptionReceiptV4` with:
  - `membership_sha256` = historical sealed M0;
  - `effective_membership_sha256` = sanctioned effective M1;
  - `membership_manifest` = exact adopted-member IDs for source artifacts,
    source revisions, contributions, and identity decisions;
  - one authenticated source-classification repair record.
- V1/V2/V3 semantics remain frozen in DungeonMind.
- Live Eldyrwild has **not** yet been repaired to V4.
- Buddy `main` still pins DungeonMind PR #37 merge `2edc07ff...` and only accepts V3.
- Buddy PR #629 is paused and direct reads are default-off.
- PR #629 head `c3e57d9f...` contains one provisional V4 compatibility edit using
  `getattr(receipt, "effective_membership_sha256", ...)`. Treat it as discovery
  evidence only; do not cherry-pick it as the implementation. It does not own
  the landed-main sequencing problem, exact dependency pin, explicit closed
  receipt typing, or complete V3/V4 membership proof required here.

### Exact live repair oracle retained for the post-merge operation

```text
DungeonMind sealed fixture:
  tests/fixtures/dungeonmind_dnd/eldyrwild_existing_world_adoption_bundle_v2.json

bundle SHA-256:
  90574dfc4101e4198c7fd96478d6f49e65aa534d0aa91fa41a9a17da9d49695f

D_A:
  rev:34b1f8e2625d5ba693fc726a2a1a4720

sealed adopted member counts:
  source artifacts:    83
  source revisions:    83
  contributions:       93
  identity decisions:  13
```

Do not copy the live database into git. Do not regenerate "equivalent" sealed
bundle bytes from Buddy.

---

## 4. Lane ownership, branch collision, and serialization

### This lane

```text
branch: cutover/v4-hydrated-authority-compatibility
base:   b850b9f8126a8c8488d17b3bdb6f99a60a162338
```

### Active overlapping PR

Buddy PR #629 currently owns a broad R.3 branch and touches the same authority
adapter/dependency seam.

**Serialization ruling:** freeze PR #629 while this prerequisite is active.
Do not add fixes, repins, witness updates, or cleanup commits to #629 until this
PR merges and the live repair sequence completes.

After this prerequisite merges, #629 must rebase onto the new Buddy main and
**drop the duplicate `c3e57d9f...` compatibility commit** as already-landed
predecessor work. Do not preserve the duplicate through a conflict resolution.

The stale historical branch `kernel/eldyrwild-dungeonmind-v4-repin` is hundreds
of commits behind main and owns no current write lease.

### Runtime/state collision

Even isolated worktrees can collide through the DungeonMind database.

- Unit tests: no live DB.
- Integration tests: disposable/test-only DB only.
- Never point CI or implementation verification at the live Eldyrwild DB.
- The live R.2b repair is explicitly post-merge steward work, not code-agent work.

---

## 5. Observable paths and adversarial sequences

### Observable-path inventory

| Path | Current behavior on Buddy main | Required behavior | Owning boundary |
|---|---|---|---|
| V3 bind | Accepts typed V3; uses `membership_sha256` | Unchanged | `bind_world_authority` |
| V3 adopted-membership verification | Selects sealed adopted subset through existing frozen-store compatibility logic; compares V3 digest | Unchanged | `_verify_adopted_membership` |
| V4 bind | Rejected as non-V3 | Accept typed V4 explicitly; bind effective M1 and exact manifest | `bind_world_authority` |
| V4 adopted-membership verification | Unsupported | Load exactly manifest-selected adopted members; compute M1; descendants outside manifest are ignored | `_verify_adopted_membership` |
| V4 valid hydrated read | Cannot serve | Existing hydration continues after successful V4 proof with direct-read gate off | existing authority read route + hydration |
| Unsupported receipt schema | Rejected as non-V3 | Still fail closed; no duck-typing acceptance | binder |
| Missing adopted manifest member | N/A | Fail closed before hydration | membership verifier |
| Mutated adopted V4 member | N/A | M1 mismatch; fail closed | membership verifier |
| Post-adoption descendant row | V3 strict/legacy behavior | V3 unchanged; V4 descendant outside manifest does not alter M1 | membership verifier |
| DungeonMind unavailable | Typed unavailable failure | Unchanged; no Buddy fallback | authority adapter |
| Explicit alternate test/tool root | Existing bypass behavior | Unchanged | route layer |
| Direct-read rollout | Not on main | Remains off/not introduced | configuration boundary |

### Adversarial sequences

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| Valid V4 receipt → later descendant contribution/source/identity exists → hydrate | Descendant is not folded into V4 adopted M1; hydration still succeeds | V4 manifest-selection test |
| Valid V4 receipt → one manifest-selected source artifact changes after receipt | Digest mismatch; hydration refuses service | V4 drift test |
| Valid V4 receipt → one manifest-selected ID is missing | Incomplete/adopted-member-missing failure; no hydration | V4 missing-member test |
| Unsupported receipt object happens to expose `effective_membership_sha256` | Rejected; no structural/`getattr` acceptance | closed-schema binder test |
| V3 receipt after dependency repin | Exact existing V3 behavior remains green | V3 regression tests |
| V4 compatibility PR merged → direct-read env absent/off | Product still routes through hydrated compatibility; no direct-read activation | route/config regression test |

---

## 6. Files in scope — exclusive write lease

Every implementation change must fit this table.

| Action | Path | Purpose |
|---|---|---|
| Existing | `Docs/Plans/HANDOFF-CUTOVER-v4-hydrated-authority-compatibility.md` | Checked-in authority for this slice |
| Modify | `pyproject.toml` | Pin DungeonMind exactly to PR #43 merge `519b2c96...` |
| Modify | `uv.lock` | Lock the exact DungeonMind pin; no floating dependency |
| Modify | `apps/live_control_server/integrations/dungeonmind_kernel/world_graph_authority.py` | Explicit V3/V4 receipt binding and V4 manifest/M1 adopted-membership verification |
| Modify | `tests/test_cutover_dungeonmind_world_graph_authority.py` | Owning V3/V4 compatibility and fail-closed evidence |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | Backward-looking sync: record DungeonMind R.2b merge/review completion and this prerequisite as active before R.3 resumes |
| Modify | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | Backward-looking sequencing sync only; do not mark this PR done |
| Modify if canonical mirror exists | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-campaign-supergraph.md` | Keep roadmap mirror byte-identical if roadmap changes |

### Bounded discovery exception

```text
Directory: tests/
Maximum additional paths: 1
Allowed path kinds: one existing cutover authority test helper/fixture only
Decision rule: only if the owning V3/V4 route proof cannot be expressed cleanly in
               tests/test_cutover_dungeonmind_world_graph_authority.py without
               duplicating an existing shared fixture.
```

If implementation needs any production path outside the table, stop and report
why. Do not broaden this PR into direct-read work.

---

## 7. Explicitly out of scope

| Path / capability | Why excluded |
|---|---|
| `apps/live_control_server/integrations/dungeonmind/world_graph_reads.py` | Belongs to paused R.3 direct-read PR #629 |
| `apps/live_control_server/services/world_graph_projection.py` | No direct-read routing changes here |
| `apps/live_control_server/services/world_graph_retrieval.py` | No direct-read routing changes here |
| R.3 witness scripts/baselines | Rerun only after live repair and #629 rebase |
| Buddy migration scripts that directly mutate DungeonMind | Removal belongs to resumed #629 after this predecessor lands; do not execute them |
| DungeonMind repair implementation | Already landed and reviewed in #43 |
| Live DungeonMind DB | No mutation in this PR or CI |
| R.3 semantic difference resolution | Must be based on post-repair witness evidence |
| R.3a caching / batching / parsed snapshot reuse | Performance successor after R.3 semantics freeze |
| `graph_memory` demolition | Later runtime-retirement slices |
| Play Surface / Agent Surface work | Parallel product lanes; no shared runtime ownership needed here |

No direct-read feature flag changes. No new fallback. No graph semantics change. No
receipt mutation. No source-artifact mutation. No generic repair code in Buddy.

---

## 8. Implementation contract

### 8.1 Exact dependency pin

Change Buddy from DungeonMind PR #37 merge:

```text
2edc07ff27a21b1c83aed847edf95b77d297910e
```

to exactly DungeonMind PR #43 merge:

```text
519b2c96fc42d22f3113cc9ca0d48bc70b6780e5
```

Update both `pyproject.toml` and `uv.lock`.

Do not pin to a branch or `main`.

### 8.2 Closed receipt dispatch

`bind_world_authority` must use the concrete DungeonMind contract types from the
pinned dependency.

Required semantics:

```text
ExistingWorldAdoptionReceiptV3
  accepted
  served_checkpoint = receipt.membership_sha256
  V3 adopted-member selection = existing behavior

ExistingWorldAdoptionReceiptV4
  accepted
  served_checkpoint = receipt.effective_membership_sha256
  adopted_member_manifest = receipt.membership_manifest

anything else
  fail closed
```

Do not use attribute presence (`getattr`, `hasattr`) as the schema discriminator.
V4 is a public typed contract now; consume it as one.

The internal `AuthorityBinding` may gain an optional typed/normalized manifest
field if that is the cleanest way to carry exact V4 membership IDs into the
verifier. Keep this internal; do not invent a new product wire contract.

### 8.3 V3 behavior is frozen

The dependency repin must not silently change existing V3 hydrated behavior.
Preserve:

- exact frozen Buddy A ↔ D_A receipt binding;
- existing V3 `membership_sha256` semantics;
- frozen-store contribution/identity selection and replay metadata;
- existing hydration version/cache behavior unless the V4 binding itself makes a
  narrowly required metadata-key change provable;
- existing unavailable/fallback behavior;
- local authority quiescence behavior.

If a clean V4 implementation requires changing V3 semantics, stop.

### 8.4 V4 membership is manifest-selected M1

For V4 only, the receipt manifest is the exact adopted-member selector.

Use these exact ID sets:

```text
membership_manifest.source_artifact_ids
membership_manifest.source_revision_ids
membership_manifest.contribution_ids
membership_manifest.identity_decision_ids
```

Load current DungeonMind rows for those IDs, prove all are present, and compute:

```text
existing_world_adoption_membership_sha256(
  source_artifacts=manifest-selected current artifacts,
  source_revisions=manifest-selected current revisions,
  contributions=manifest-selected current contributions,
  identity_decisions=manifest-selected current decisions,
)
```

That digest must equal:

```text
receipt.effective_membership_sha256
```

Later descendants outside the manifest are not adopted members and must not
change this digest.

Do not compare V4 current state to `receipt.membership_sha256`; that is M0 and is
historical sealed truth, not the effective served checkpoint.

Do not reconstruct V4 adopted IDs from filename conventions, Buddy IDs, source
URIs, current world rows, or inferred contribution references when the manifest
already names them exactly.

### 8.5 Frozen Buddy store remains compatibility-only

This slice does **not** eliminate frozen-store use from hydration. Existing V3
binding/replay metadata may continue to depend on it, and the old hydration
runtime remains until R.3.

For V4 membership selection, prefer the receipt manifest over frozen-store
inference. Frozen Buddy data must not override the V4 manifest or effective
checkpoint.

### 8.6 No mutation

All code in this PR is read-side compatibility.

It must not:

- invoke the DungeonMind repair operation;
- alter SourceArtifact rows;
- alter the adoption receipt;
- write a graph revision;
- advance graph head;
- enable direct reads;
- mutate the frozen Buddy store.

---

## 9. Acceptance proof matrix

Evidence must live at the authority adapter / route boundary, not just in a
helper.

### 9.1 Dependency

Prove:

- `pyproject.toml` exact pin is `519b2c96...`;
- `uv.lock` resolves the same commit;
- the pinned package exposes concrete `ExistingWorldAdoptionReceiptV4` and its
  manifest contract.

### 9.2 V3 regression

Existing V3 cutover tests remain green.

Add/retain direct evidence that:

```text
V3 receipt
→ binder accepts
→ binding checkpoint == membership_sha256
→ adopted membership verifier uses existing V3 behavior
→ valid V3 hydration/read remains successful
```

No V3 test should be weakened to make V4 pass.

### 9.3 V4 binder

Use a concrete `ExistingWorldAdoptionReceiptV4` from the pinned DungeonMind
package.

Prove:

```text
V4 receipt
→ binder accepts
→ binding checkpoint == effective_membership_sha256
→ exact membership manifest is carried to serve-time verification
```

### 9.4 Closed schema

Prove an unsupported/pre-V3 receipt or lookalike object is rejected even if it
has an `effective_membership_sha256` attribute.

### 9.5 V4 manifest exactness

Construct current authority state with:

- every manifest member present;
- at least one legitimate post-adoption descendant outside each practical
  family represented by the test;
- the exact V4 M1 computed only from manifest members.

Prove verification succeeds and descendants do not alter M1.

### 9.6 V4 fail-closed integrity

Independently prove at least:

```text
missing manifest-selected member → fail closed
mutated manifest-selected member → M1 mismatch / fail closed
wrong effective checkpoint       → fail closed
```

No hydration should proceed after any failure.

### 9.7 Route behavior with direct reads off

At the mounted authority-read seam, prove that a valid V4 receipt hydrates
through the real `_ensure_hydrated_revision` / `hydrate_world_graph` path —
membership verification, frozen replay-metadata loading, contribution replay,
rebuild, snapshot coverage, and cache publication — and returns a servable
`HydrationHandle`. Direct reads stay absent/off. Do not stub the hydration
machinery; a routing-only fake that replaces `_ensure_hydrated_revision` is not
this proof.

If the direct-read gate does not exist on `main`, prove this by keeping the test
strictly on existing hydrated routing rather than importing #629 code. A
portable fake repository plus a minimal frozen store is sufficient.

### 9.8 Full repository gates

At minimum:

```bash
uv lock
uv sync --frozen
uv run ruff check .
uv run pytest tests/test_cutover_dungeonmind_world_graph_authority.py
uv run pytest
```

If the repository's current CI/runbook requires additional checks, run them.
Report exact commands/results in the PR handback.

---

## 10. Backward-looking state-authority sync

This implementation PR consumes a completed cross-repository predecessor, so it
must atomically record that already-true state where Buddy's sequencing docs
claim current CUTOVER status.

Record only facts already known before this PR merges:

```text
DungeonMind R.2b / PR #43: DONE
merge: 519b2c96fc42d22f3113cc9ca0d48bc70b6780e5
formal review cycles: 4
purpose: governed V3→V4 adopted-source classification repair
live Eldyrwild repair: NOT YET APPLIED
Buddy R.3 / PR #629: still paused pending landed V4 compatibility + live repair
this compatibility prerequisite: ACTIVE / in implementation
```

Do **not** mark this PR done, invent its merge SHA/review count, mark the live
repair applied, or mark R.3 resumed/completed.

If the roadmap mirror is part of the active design-agent source set, keep it
byte-identical to the canonical roadmap in the same PR.

---

## 11. Review contract

Review this PR as a standalone prerequisite, not as a partial review of #629.

A review cycle is:

```text
one formal reviewer judgment against one distinct head SHA
```

Required reviewer questions:

1. Is the exact DungeonMind #43 merge pinned in both dependency authorities?
2. Is receipt dispatch concrete V3/V4 typing rather than structural duck typing?
3. Is V3 behavior unchanged?
4. Does V4 use `effective_membership_sha256`, never M0, for serve-time integrity?
5. Does V4 use the exact manifest-selected adopted subset and ignore descendants?
6. Do missing/mutated adopted members fail closed before hydration?
7. Does the direct-read rollout remain untouched/off?
8. Is there zero live repair/mutation code in the PR?
9. Does predecessor state sync say only what is already true?
10. Is PR #629 still frozen while this overlapping write lease is active?

No merge on green CI alone; all ten questions must be yes.

---

## 12. Stop conditions

Stop implementation and report before expanding scope if any of these occur:

- Buddy `main` is no longer exactly `b850b9f8126a8c8488d17b3bdb6f99a60a162338` before implementation begins; re-anchor the branch rather than silently continuing.
- DungeonMind PR #43 merge is not exactly `519b2c96...` or the V4 public contract differs from this handoff.
- V4 support requires a migration or a new Buddy durable schema.
- V4 support requires changing V3 membership/replay semantics.
- V4 support requires editing direct-read adapter/service paths from PR #629.
- V4 support requires executing or duplicating DungeonMind's repair logic in Buddy.
- Any implementation/test needs the live Eldyrwild database.
- The direct-read rollout gate must be enabled to make V4 hydration work.
- A path outside §6 is required and does not fit the single bounded test exception.
- PR #629 receives overlapping edits while this lane is active.
- The live repair has already been applied before this prerequisite lands; stop and assess current serving safety before continuing.

---

## 13. Definition of done for this PR

This PR is done when:

> Buddy `main`, pinned exactly to DungeonMind PR #43, can continue serving its
> existing hydrated DungeonMind-authority path from either an unchanged V3
> adoption receipt or the governed V4 repaired-adoption receipt, with V4
> integrity bound to the exact manifest-selected M1 checkpoint, V3 behavior
> unchanged, unsupported/corrupted state failing closed, direct reads still off,
> and no live authority mutation performed by the PR.

This does **not** mean Eldyrwild is repaired yet.

---

## 14. Post-merge steward operation — not part of PR implementation

After this PR is reviewed, merged, and landed on Buddy `main`, re-anchor before
any live mutation.

The steward/operator sequence is:

```text
1. Verify landed Buddy main includes this compatibility PR and exact DND pin.
2. Verify R.3 direct-read rollout remains off/default-off.
3. Backup/snapshot the live DungeonMind PostgreSQL database.
4. Use DungeonMind merge 519b2c96... and the exact sealed Eldyrwild fixture.
5. Prepare a human-reviewed explicit repair-intent JSON naming exact artifact IDs.
   - do not infer corrections from current IDs/URIs/filenames in the apply path
   - visibility repair may only be sealed None → effective GM
   - campaign repair may only be sealed campaign → None for sessionless worldbuilding
6. Run DungeonMind repair CLI with NO --apply.
7. Require:
   - exact bundle SHA 90574dfc...
   - manifest counts 83 / 83 / 93 / 13
   - exact D_A rev:34b1f8e...
   - exact requested field transitions only
   - unexpected_drift=0
8. Human-review the dry-run output.
9. Apply exactly once with --apply.
10. Re-read and verify:
    - receipt is V4
    - V4.membership_sha256 == sealed M0
    - V4.effective_membership_sha256 == repaired M1
    - manifest exact
    - D_A unchanged
    - current head unchanged
11. With Buddy direct-read gate off, run a landed hydrated read smoke against the
    repaired authority and require success.
12. If any step fails, stop. Do not rewrite V4, re-adopt, or repair around it.
```

The live repair result is operator evidence. Do not commit DB contents, live
receipt payloads, secrets, or backup artifacts.

---

## 15. Successor handoff: resume R.3 from repaired authority

Only after §14 succeeds:

1. Rebase PR #629 `cutover/direct-dungeonmind-production-reads` onto the new Buddy
   main.
2. Drop its provisional `c3e57d9f...` V4 compatibility commit as duplicate
   predecessor work.
3. Repin/lock conflicts should resolve to the already-landed DungeonMind #43 pin.
4. Remove the dormant Buddy contract-violating migration implementation rather
   than preserving it as historical recovery code.
5. Rerun the full direct-vs-hydrated R.3 semantic witness against repaired V4
   authority.
6. Treat the resulting blocker set as fresh evidence. Do not carry forward the
   old `199` count by assumption.
7. Classify every residual divergence using the existing R.3 vocabulary:

```text
representation only
new deterministic R.2 search ranking
product-local presentation join
intentionally retired legacy-only field
blocking semantic difference
```

8. Resolve actual remaining semantic blockers or stop for an explicit design
   decision.
9. Finish R.3 with the direct-read rollout gate still default-off if R.3a
   performance work is still required.
10. Then dispatch R.3a. Do not mix optimization into semantic cutover repair.

The project-end relationship remains:

```text
this PR
  → safe live V4 repair
  → trustworthy R.3 parity witness
  → R.3: Buddy no longer executes production graph reads
  → R.3a: make native reads fast enough
  → retire remaining Buddy write/compatibility graph-runtime consumers
  → static zero-consumer proof
  → delete graph_memory graph engine
```
