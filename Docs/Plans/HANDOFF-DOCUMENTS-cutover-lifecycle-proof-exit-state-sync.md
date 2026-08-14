---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: CUTOVER — lifecycle-proof exit state sync
  - Flow: DOCUMENTS
  - Direction: STEWARD → DOCUMENTS → REVIEW
  - Handoff: Docs/Plans/HANDOFF-DOCUMENTS-cutover-lifecycle-proof-exit-state-sync.md
  - Branch: documents/cutover-lifecycle-proof-exit-state-sync

  ## Verification pointer
  - Implementation predecessor: PR #585
  - PR #585 head: `7c339a23d77b4465ca0adeda015859215b65285d`
  - PR #585 merge: `0fe9f88cfafda38319145e88d0f8b354d53830ca`
  - Review cycles: 2
  - Canonical input: `rev:0c644e56b45bcaac709012206e3e41c2`
  - PR #585 fixture SHA-256:
    `c31e8c156b3d66f389f67dcdb92b28a4e7c4d0a6ae77e3f0604b99cf38940531`

  Record the already-proven PR #585 lifecycle exit atomically across the
  mutable CUTOVER state authorities and author the dispatch-ready
  Captain/Thrin alias-package successor handoff.

  This PR changes documentation/state authority only. It does not re-run
  the lifecycle proof, mutate Eldyrwild, construct alias package rows, or
  change DungeonMind contracts.
---

# HANDOFF — record lifecycle-proof CUTOVER exit and ready alias package

**Created:** 2026-08-14
**Status:** ACTIVE — required post-merge state-authority synchronization
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOCUMENTS-cutover-lifecycle-proof-exit-state-sync.md`
**Conversation/workstream:** `CUTOVER — lifecycle-proof exit state sync`
**Flow / owner:** `DOCUMENTS`
**Direction:** STEWARD → DOCUMENTS → REVIEW
**Design base:** `0fe9f88cfafda38319145e88d0f8b354d53830ca`
**Suggested branch:** `documents/cutover-lifecycle-proof-exit-state-sync`
**PR title:** `DOCUMENTS: record lifecycle-proof CUTOVER exit`

> Repository law: [`AGENTS.md`](../../AGENTS.md).
> Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md).
>
> This PR closes the development cycle opened by PR #585.
>
> Do not dispatch the dependent Captain/Thrin implementation until this state
> sync is merged and `main` has been re-anchored to that merge.

---

## §1 Mission and merge-ready invariant

### Mission

Atomically advance every mutable CUTOVER state authority from:

```text
identity lifecycle through alias_remove:
  future / READY / active

ATTRIBUTE_ASSERTION:
  not currently authorized as 0

Captain + Thrin alias package:
  BLOCKED
```

to the already-proven post-PR #585 state:

```text
identity lifecycle through alias_remove:
  DONE

ATTRIBUTE_ASSERTION:
  0 under a fresh current passed proof-derived policy

EVIDENCE_PROVENANCE:
  2
  exactly Captain + Thrin Branchborn

Captain + Thrin alias package:
  READY after this state-sync merges
```

and create the dispatch-complete successor handoff:

```text
Docs/Plans/HANDOFF-CUTOVER-alias-assertion-package-after-shadow-alias-remove.md
```

### Merge-ready invariant

Every mutable authority touched by this PR must agree on these exact facts:

```text
PR #585:
  head:
    7c339a23d77b4465ca0adeda015859215b65285d
  merge:
    0fe9f88cfafda38319145e88d0f8b354d53830ca
  review cycles:
    2

canonical Eldyrwild:
  world:
    eldyrwild
  revision:
    rev:0c644e56b45bcaac709012206e3e41c2
  payload SHA:
    0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2

historical merge-only proof on current head:
  reconstructable:
    16 / 28
  unresolved:
    12
  current-policy authority:
    NO

current lifecycle-through-alias_remove proof:
  reconstructable:
    28 / 28
  unresolved:
    []
  passed:
    true

fresh source-history policy:
  policy_id:
    identity_lifecycle_history_v1
  source:
    exact current passed proof

current remeasurement:
  ATTRIBUTE_ASSERTION:
    0
  EVIDENCE_PROVENANCE:
    2
  IDENTITY_HISTORY:
    20
  CONTRIBUTION_HISTORY:
    5291

remaining EVIDENCE_PROVENANCE:
  node:node:captain-lysandra-ironveil:field:aliases
  node:node:thrin-branchborn:field:aliases

relationships:
  canonical:
    323 / 314 / 9 / 3
  migration projection:
    323 / 318 / 5 / 3

five dual-sense relationship STOPs:
  unchanged

CUTOVER:
  NOT_READY
```

The #585 sealed report remains:

```text
tests/fixtures/dungeonmind_kernel/
  eldyrwild_cutover_identity_lifecycle_through_alias_remove_v1.json

SHA-256:
  c31e8c156b3d66f389f67dcdb92b28a4e7c4d0a6ae77e3f0604b99cf38940531
```

### Named successor

After this state-sync merges:

```text
cutover-alias-assertion-package-after-shadow-alias-remove
  → READY
```

Its dispatch base is **this state-sync PR's merge SHA / then-current `main`**,
not PR #585's merge SHA directly.

### Pre-dispatch critique

| Question                                    | Answer                                                                                                                           |
| ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Is this independently useful?               | **Yes.** It restores repository state authority after #585 and opens the next legal dispatch gate.                               |
| Why not dispatch Captain/Thrin immediately? | `AGENTS.md` requires atomic state-authority sync before dependent dispatch. Current tracker/status are stale.                    |
| Most likely failure                         | Updating the tracker but leaving status/backlog/#585 handoff claiming lifecycle proof is still active.                           |
| Second likely failure                       | Promoting Case B merely because ATTRIBUTE and alias EP are now expressible. Five relationship package-construction STOPs remain. |
| Third likely failure                        | Reusing the historical #577 handoff/branch as current authority. #577 remains closed unmerged and superseded.                    |
| Scope-expansion signal                      | Any runtime/code/fixture/World Graph edit.                                                                                       |
| Architecture churn needed?                  | **No.** No architecture invariant changed.                                                                                       |
| Roadmap churn needed?                       | **No**, unless re-anchor finds a roadmap statement that directly contradicts current state.                                      |

---

## §2 Authority and observed state

### Repository state

At design time:

```text
main:
  0fe9f88cfafda38319145e88d0f8b354d53830ca

PR #585:
  merged
```

The implementation branch must start from that SHA or a current valid
descendant.

If `main` advances before dispatch:

```text
re-anchor
→ verify #585 remains ancestor
→ inspect whether any new change alters this CUTOVER state
→ record actual dispatch base in handback
```

### Why this sync is required

Current mutable authorities still contain pre-#585 state:

```text
PR tracker:
  lifecycle proof = READY
  Captain/Thrin = BLOCKED

continuity status:
  lifecycle proof = active
  ATTRIBUTE_ASSERTION not authorized as 0

Backlog Case C:
  lifecycle proof still listed before Captain/Thrin

#585 HANDOFF:
  status = READY
```

Those statements were correct before #585 merged and are stale now.

### Historical #577 authority

PR #577 remains:

```text
closed:
  true

merged:
  false

head:
  b31bbc32b98c170c44f75de3fa1e8e252e7d0555

disposition:
  forensic STOP / SUPERSEDED
```

It may be cited as evidence that Captain and Thrin were source-grounded.

Do not:

```text
reopen #577
merge #577
extend #577
cherry-pick #577 wholesale
treat its eight-alias world as current
```

---

## §3 Observable paths

| Path                    | Current stale claim                      | Required post-sync claim                                   |
| ----------------------- | ---------------------------------------- | ---------------------------------------------------------- |
| Tracker active sequence | lifecycle proof READY                    | lifecycle proof DONE; Captain/Thrin package READY          |
| Continuity status       | lifecycle proof active                   | Captain/Thrin package is next dependent CUTOVER slice      |
| #585 handoff            | READY                                    | DONE / HISTORICAL with merge + two review cycles           |
| Backlog Case C          | prove lifecycle first                    | lifecycle complete; next action is exact-two alias package |
| Successor handoff       | absent                                   | dispatch-complete and gated on this sync merge             |
| Architecture            | unchanged                                | unchanged                                                  |
| Roadmap                 | no relevant transition owned here        | unchanged                                                  |
| World Graph             | exact current revision                   | unchanged                                                  |
| Blocker ledger          | execution report says ATTRIBUTE 0 / EP 2 | documentation agrees with that report                      |
| Case B                  | blocked                                  | still blocked                                              |

---

## §4 Files in scope — exact write lease

This is one guarded atomic state-authority transaction.

| Action | Path                                                                              | Purpose                                                               |
| ------ | --------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Create | `Docs/Plans/HANDOFF-DOCUMENTS-cutover-lifecycle-proof-exit-state-sync.md`         | Own this transition                                                   |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md`                                    | #585 DONE; Captain/Thrin successor READY; anchor current              |
| Modify | `Docs/Design/STATUS-world-graph-continuity-spine.md`                              | Record proven lifecycle result and new active successor               |
| Modify | `Docs/Plans/HANDOFF-CUTOVER-identity-lifecycle-through-alias-remove.md`           | Mark #585 slice DONE/HISTORICAL and record merge/review/exit evidence |
| Modify | `Backlog.md`                                                                      | Advance Case C action from lifecycle proof to Captain/Thrin package   |
| Create | `Docs/Plans/HANDOFF-CUTOVER-alias-assertion-package-after-shadow-alias-remove.md` | Dispatch-complete successor contract                                  |

**Bounded discovery exception:** none.

All six paths move as one transaction.

If another current-state document must change to remove an actual contradiction,
STOP and return the discovered path to stewardship rather than editing it
silently.

---

## §5 Explicitly out of scope

Do not modify:

```text
Backlog-DONE.md
Docs/Roadmaps/ROADMAP-campaign-supergraph.md
Docs/Design/ARCHITECTURE-campaign-supergraph.md
Docs/Sources/design-agent/**
Docs/Plans/HANDOFF-CUTOVER-alias-assertion-package-after-575.md

apps/**
src/**
scripts/**
tests/**
out/**
canonical/live World Graph data
DungeonMind repository files
```

Do not:

```text
rerun or alter the canonical lifecycle operation
change #585's sealed fixture
reconstruct Captain/Thrin package rows
modify conformance classification
modify alias values
add/remove identity decisions
clear relationship STOPs
start DungeonMind Case B
start existing-world adoption
declare CUTOVER_READY
```

The old:

```text
Docs/Plans/HANDOFF-CUTOVER-alias-assertion-package-after-575.md
```

stays historical and `SUPERSEDED / DO NOT DISPATCH`.

---

## §6 Required authority transitions

### 6.1 PR tracker

Update repository anchor to the current merged state:

```text
0fe9f88cfafda38319145e88d0f8b354d53830ca
```

Record:

```text
cutover-identity-lifecycle-through-alias-remove
  READY
→ DONE
```

with:

```text
PR:
  #585

head:
  7c339a23d77b4465ca0adeda015859215b65285d

merge:
  0fe9f88cfafda38319145e88d0f8b354d53830ca

review cycles:
  2

current proof:
  28 / 28
  passed
  unresolved []

remeasurement:
  ATTRIBUTE_ASSERTION = 0
  EVIDENCE_PROVENANCE = 2
  IDENTITY_HISTORY = 20
  CONTRIBUTION_HISTORY = 5291
```

Transition:

```text
cutover-alias-assertion-package-after-shadow-alias-remove
  BLOCKED
→ READY
```

Required outcome:

```text
Reconstruct exactly the two remaining source-grounded current-node aliases,
Captain and Thrin Branchborn, as revision-bound DungeonMind-compatible alias
assertion package rows. Generate alias-package classification authority only
from a complete current proof. Remeasure EVIDENCE_PROVENANCE. No World Graph
mutation.
```

Keep:

```text
dungeonmind-whole-world-authority-cutover
  BLOCKED
```

Five dual-sense relationship STOPs still block package-construction closure.

### 6.2 Continuity status

Replace the active lifecycle-proof description with:

```text
Active CUTOVER slice:
  cutover-alias-assertion-package-after-shadow-alias-remove

Predecessor:
  PR #585 DONE

Current classification:
  ATTRIBUTE_ASSERTION = 0
    authorized from current lifecycle proof

Current EVIDENCE_PROVENANCE:
  2

Remaining aliases:
  Captain
  Thrin Branchborn

Five relationship STOPs:
  unchanged

Case B:
  forbidden while package-construction blockers remain

CUTOVER:
  NOT_READY
```

### 6.3 #585 handoff

Transition:

```text
Status:
  READY
→ DONE / HISTORICAL
```

Record:

```text
PR #585
head 7c339a23…
merge 0fe9f88…
2 review cycles
fixture c31e8c15…
```

Do not rewrite its implementation contract.

### 6.4 Backlog

Advance the existing Case C item rather than creating duplicate state.

Change its current action from:

```text
prove lifecycle
→ then package Captain/Thrin
```

to:

```text
lifecycle proof complete in PR #585;
next action is exact Captain + Thrin package;
ATTRIBUTE_ASSERTION=0;
EVIDENCE_PROVENANCE=2;
five relationship STOPs remain after alias work;
Case B remains blocked.
```

Do not move the item to `Backlog-DONE.md`; Case C package construction is not
complete yet.

### 6.5 Author the successor HANDOFF

Create exactly:

```text
Docs/Plans/HANDOFF-CUTOVER-alias-assertion-package-after-shadow-alias-remove.md
```

using the steward-authored successor contract supplied with this handoff.

Its status before this state-sync merges must say:

```text
READY AFTER STATE-SYNC MERGE
```

Its dispatch rule must say:

```text
re-anchor after this DOCUMENTS PR merges;
branch from that merge / current main;
record exact dispatch-base SHA;
do not dispatch directly from 0fe9f88…
```

---

## §7 Evidence required to merge

### Exact changed paths

Run:

```bash
git diff --name-only <dispatch-base>...HEAD
```

Require exactly the §4 write lease.

### No stale sequencing claims

Repository search over the four mutable authorities must not leave a current
claim that:

```text
cutover-identity-lifecycle-through-alias-remove is READY/active

ATTRIBUTE_ASSERTION is not currently authorized as 0

Captain/Thrin packaging is BLOCKED on lifecycle proof

PR #585 is unmerged/active
```

Historical explanation is allowed when explicitly labeled historical.

### Exact execution evidence

Verify the recorded #585 fixture still exists and its bytes are untouched:

```text
tests/fixtures/dungeonmind_kernel/
  eldyrwild_cutover_identity_lifecycle_through_alias_remove_v1.json

SHA:
  c31e8c156b3d66f389f67dcdb92b28a4e7c4d0a6ae77e3f0604b99cf38940531
```

Do not regenerate it.

### Sequencing proof

The final docs must say:

```text
next:
  Captain/Thrin alias package

not yet:
  five relationship STOP resolution
  DungeonMind existing-world adoption
  product-authority cutover
```

The exact next slice is READY.

Case B remains BLOCKED.

### Mechanical checks

```bash
git diff --check

git diff --name-only <dispatch-base>...HEAD
```

No runtime test suite is required for a documentation-only PR.

If repository documentation validation exists, run the applicable command and
record it separately.

---

## §8 Required review handback

Record:

```text
Review Cycle <N>

PR:
branch:
head SHA:
dispatch/base SHA:

actual changed paths:

state transition:
  #585 lifecycle proof DONE
  Captain/Thrin package READY

recorded predecessor:
  PR #585
  head
  merge
  review cycles
  fixture SHA

recorded current ledger:
  ATTRIBUTE_ASSERTION
  EVIDENCE_PROVENANCE
  IDENTITY_HISTORY
  CONTRIBUTION_HISTORY

relationships:
  canonical
  migration

remaining package-construction blockers:
  Captain/Thrin before successor implementation
  five relationship STOPs

successor handoff:
  path
  status
  dispatch gate

stale-current-state search:
  result

git diff --check:
  result
```

---

## §9 Acceptance rubric

* [ ] PR #585 is recorded as `DONE`.
* [ ] #585 review-cycle count is exactly `2`.
* [ ] #585 merge SHA is `0fe9f88cfafda38319145e88d0f8b354d53830ca`.
* [ ] Current lifecycle proof is recorded as 28/28, passed, zero unresolved.
* [ ] Historical merge-only 16/28 result remains clearly historical/non-authoritative.
* [ ] `ATTRIBUTE_ASSERTION=0` is now explicitly authorized by the current passed proof.
* [ ] `EVIDENCE_PROVENANCE=2`.
* [ ] Remaining EP blockers are exactly Captain + Thrin Branchborn.
* [ ] `IDENTITY_HISTORY=20`.
* [ ] `CONTRIBUTION_HISTORY=5291`.
* [ ] Relationships remain `323/314/9/3` canonical and `323/318/5/3` migration.
* [ ] Five relationship STOPs remain.
* [ ] `CUTOVER_NOT_READY` remains.
* [ ] Captain/Thrin successor transitions `BLOCKED → READY`.
* [ ] Case B remains blocked.
* [ ] Old #577 remains historical/superseded.
* [ ] New successor handoff is dispatch-complete.
* [ ] No runtime/code/fixture/live-data path changed.
* [ ] Actual changed paths equal §4 exactly.
* [ ] No current mutable authority contradicts the new state.

---

## Stop conditions

Stop rather than expanding if:

```text
main no longer descends from PR #585 merge

#585 fixture digest differs from:
  c31e8c156b3d66f389f67dcdb92b28a4e7c4d0a6ae77e3f0604b99cf38940531

a new implementation PR changed the relevant blocker ledger after #585

current EVIDENCE_PROVENANCE is no longer exactly Captain + Thrin

a runtime/code change appears necessary

a roadmap/architecture change seems necessary for ceremony rather than an
actual changed claim

the successor cannot be described without resolving one of the five
relationship STOPs

Case B becomes the proposed next action before package construction clears
```

Report the contradiction to stewardship and do not partially synchronize.

---

## Post-merge dispatch

After this PR merges:

```text
1. re-anchor current main
2. verify this state-sync merge is current/ancestor
3. run steward preflight for:
   HANDOFF-CUTOVER-alias-assertion-package-after-shadow-alias-remove.md
4. dispatch:
   cutover/alias-assertion-package-after-shadow-alias-remove
```

Do not insert another documentation PR between this sync and that dispatch
unless new repository state makes the successor contract stale.
