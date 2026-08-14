---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: CUTOVER — exact-six alias live-exit state sync
  - Flow: DOCUMENTS
  - Direction: STEWARD → DOCUMENTS → REVIEW
  - Handoff: Docs/Plans/HANDOFF-DOCUMENTS-cutover-exact-six-live-exit-state-sync.md
  - Branch: documents/cutover-exact-six-live-exit-state-sync

  ## Verification pointer
  - Implementation predecessor: PR #583
  - PR #583 head: 2cacc7cbdf77977e86daf29ed2b9058f94d54e70
  - PR #583 merge: 299579bd3c3f78a9393ae3c97c57a1dfd6b155ed
  - Review cycles: 3 distinct reviewed heads
  - Dispatch gate: canonical Eldyrwild live apply + replay + retry + remeasurement
    already proved EVIDENCE_PROVENANCE 8→2
  - Verification: exact live-exit evidence recorded in the implementation handback
    for this documentation PR

  This PR records already-proven current state. It does not perform the live
  mutation, does not re-authorize ATTRIBUTE_ASSERTION=0 from the locked #575
  policy, and does not implement the identity-lifecycle or Captain/Thrin
  successors.
---

# HANDOFF — record exact-six CUTOVER live exit

**Created:** 2026-08-13  
**Status:** ACTIVE — one documentation/state-authority capability after a proven live exit  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOCUMENTS-cutover-exact-six-live-exit-state-sync.md`  
**Conversation/workstream:** `CUTOVER — exact-six alias live-exit state sync`  
**Flow / owner:** `DOCUMENTS`  
**Direction:** STEWARD → DOCUMENTS → REVIEW  
**Design base:** `299579bd3c3f78a9393ae3c97c57a1dfd6b155ed`  
**Suggested branch:** `documents/cutover-exact-six-live-exit-state-sync`  
**PR title:** `DOCUMENTS: record exact-six CUTOVER live exit`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process:
> [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md).
>
> **This PR is not the live operation.** The canonical live apply, replay,
> retry, and blocker remeasurement were completed from merged `main` before
> this branch was created. Observed values below replace every placeholder.

## §1 Mission and merge-ready invariant

**Mission:** Atomically advance every mutable CUTOVER state authority from
“exact-six implementation merged, live exit still pending” to the exact
post-live state actually proven after PR #583, including the stale-proof finding
that the locked #575 merge-only policy is not current `ATTRIBUTE_ASSERTION`
authority, and author the dispatch-complete identity-lifecycle-through-alias_remove
successor handoff.

**Merge-ready invariant:** every current mutable authority agrees on the same
facts:

1. PR #583 is merged:
   - implementation head
     `2cacc7cbdf77977e86daf29ed2b9058f94d54e70`;
   - merge
     `299579bd3c3f78a9393ae3c97c57a1dfd6b155ed`;
   - **3 review cycles**;
2. the canonical exact-six live operation has completed successfully;
3. the actual live parent, resulting revision, and payload SHA are recorded from
   observed evidence, never predicted;
4. six and only six merge-shadow aliases are no longer current identity truth;
5. the six governed `alias_remove` decisions replay exactly;
6. retry is `already_applied` / no-op and creates no new revision;
7. Captain and Thrin Branchborn remain current and independently source-backed;
8. original merge decisions, redirects, merged-away identities,
   contributions, evidence, and source authority remain intact;
9. canonical relationship inventory remains `323 / 314 / 9 / 3`;
10. the migration projection relationship inventory remains
    `323 / 318 / 5 / 3`;
11. remeasurement proves `EVIDENCE_PROVENANCE = 2`;
12. the two remaining alias blockers are exactly Captain and Thrin Branchborn;
13. `ATTRIBUTE_ASSERTION` is **not currently authorized as 0**. The merge-only
    #575 proof reconstructs 16/28 on the cleaned head (12 unresolved because
    six survivors' `last_identity_decision_id` + `identity_state` now name
    `alias_remove`). The locked #575 28-ID policy cannot be regenerated from
    that partial proof, so it is not current classification authority;
14. live measurement updates the identity/contribution history ledger:
    `IDENTITY_HISTORY` `14 → 20` and `CONTRIBUTION_HISTORY` `5285 → 5291`
    because the six new `alias_remove` identity decisions are durable history
    rows. Those counts are observed, not predicted;
15. the five dual-sense relationship STOPs remain outside this transition;
16. `CUTOVER_NOT_READY` remains true;
17. `cutover-eldyrwild-identity-shadow-alias-remove` becomes `DONE`;
18. `cutover-identity-lifecycle-through-alias-remove` becomes the sole
    dependent `READY` CUTOVER slice;
19. the Captain/Thrin alias assertion package remains `BLOCKED` until that
    current lifecycle proof passes, regenerates source-history policy, and
    remeasures.

If any one of these statements cannot be supported by the live evidence, this
PR does not advance the state machine.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern the PR? | **Yes.** This is one atomic current-state transition after one proven live exit. |
| Most likely failure | Writing the expected `8→2` result into docs before it was actually measured. |
| Second likely failure | Marking #583 `DONE` because the PR merged while canonical live replay is still unproven. |
| Third likely failure | Copying pre-live `IDENTITY_HISTORY=14` / `CONTRIBUTION_HISTORY=5285` as current after six new identity decisions existed. |
| Fourth likely failure | Claiming `ATTRIBUTE_ASSERTION=0` from the locked #575 policy after the merge-only proof dropped to 16/28, then promoting Captain/Thrin to `READY`. |
| Easiest authority to accidentally over-update | Roadmap / architecture. Neither changes because of this live data transition. |
| Stop condition | Any disagreement among live head, replay, retry, remaining alias blockers, keeper lineage, relationship inventories, or current identity-lifecycle proof authority. |

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | `AGENTS.md`; `PR-TRACKER-campaign-supergraph.md`; `STATUS-world-graph-continuity-spine.md`; `HANDOFF-CUTOVER-eldyrwild-identity-shadow-alias-remove.md` |
| Implementation predecessor | PR #583 |
| Implementation head | `2cacc7cbdf77977e86daf29ed2b9058f94d54e70` |
| Implementation merge | `299579bd3c3f78a9393ae3c97c57a1dfd6b155ed` |
| Review-cycle count | **3** |
| Repository base | `299579bd3c3f78a9393ae3c97c57a1dfd6b155ed` (`origin/main` at dispatch; is the #583 merge) |
| Runtime predecessor | Canonical Eldyrwild live application using the merged #583 package |
| Named successor | `cutover-identity-lifecycle-through-alias-remove` |
| What remains false | Current `ATTRIBUTE_ASSERTION=0` authorization; identity-lifecycle-through-alias_remove not implemented; Captain/Thrin package not implemented; EVIDENCE_PROVENANCE not yet zero; five relationship STOPs remain; DungeonMind durable-adoption seam remains; product-authority cutover remains blocked |
| Runtime/state ownership | This DOCUMENTS lane performs **no World Graph mutation** |
| Parallel collision boundary | Do not edit `Docs/Sources/design-agent/**`; those are non-authoritative export mirrors |

### Observed live-exit evidence

```text
repository:
  main / dispatch base = 299579bd3c3f78a9393ae3c97c57a1dfd6b155ed

before live apply:
  actual canonical Eldyrwild head = rev:5a7c13ae45c49a65b402920499be72ed
  parent payload = 2632870ef70638969503de788cfdec97acd490875deff3e2630ac91dc96fe974
  complete exact-six status/preflight = eligible

live apply:
  expected parent = rev:5a7c13ae45c49a65b402920499be72ed
  published = true
  resulting revision = rev:0c644e56b45bcaac709012206e3e41c2
  resulting payload SHA = 0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2
  six distinct package decision IDs =
    identity-decision:cad289933720e2c5
    identity-decision:045e447237353ccc
    identity-decision:05b5668d773648bf
    identity-decision:ef5c3950517c705e
    identity-decision:33d03a555ff0bc61
    identity-decision:668e4292aa9c047f

post-apply:
  all six exact aliases absent from current survivor alias surfaces
  Captain present with locked assertion/contribution/source lineage
  Thrin Branchborn present with locked assertion/contribution/source lineage
  original six introducing merge decisions unchanged
  all six redirects remain active
  merged-away identities remain historical / merged-away
  contribution index unchanged (93 contribution records)

replay:
  rebuild_from_contributions(compare_revision_id=result, publish=False)
    → rebuild_equivalent_to_pinned_revision
  rebuild_from_contributions(publish=False)
    → rebuild_equivalent_to_head
  no retired alias resurrects

retry:
  already_applied / no-op
  published = false
  canonical head remains rev:0c644e56b45bcaac709012206e3e41c2
  no seventh alias_remove decision
  no new revision

relationships:
  canonical = 323 / 314 / 9 / 3
  migration projection = 323 / 318 / 5 / 3
  #566 kind-repair current_kind values unchanged

blocker ledger:
  EVIDENCE_PROVENANCE = 2
  IDENTITY_HISTORY = 20
  CONTRIBUTION_HISTORY = 5291
  ATTRIBUTE_ASSERTION = not currently authorized
    locked #575 policy still mechanically reports 0, but that policy was
    minted from a fully passed merge-only proof and cannot be regenerated
    from the current 16/28 result. Do not treat 0 as current authority.

remaining EVIDENCE_PROVENANCE:
  node:node:captain-lysandra-ironveil:field:aliases
  node:node:thrin-branchborn:field:aliases

IDENTITY_HISTORY / CONTRIBUTION_HISTORY delta:
  parent identity_decisions = 7 → result = 13 (+6 alias_remove)
  IDENTITY_HISTORY formula (redirects + merge_records + decisions):
    7 + 0 + 7 = 14 → 7 + 0 + 13 = 20
  CONTRIBUTION_HISTORY absorbs the six new identity_decision ledger rows:
    5285 → 5291

identity-lifecycle re-proof:
  a fresh merge-only proof on the new head reconstructs 16/28 rows.
  The 12 unresolved fields are the six survivors'
  last_identity_decision_id + identity_state, because those pointers now
  name alias_remove rather than merge. PR #575 required explicit proof or
  STOP on a new identity-decision kind. This state-sync records the STOP
  as sequencing fact: do not claim ATTRIBUTE_ASSERTION = 0, and do not
  dispatch Captain/Thrin, until a current lifecycle proof through
  alias_remove passes and regenerates policy.

disposition:
  CUTOVER_NOT_READY
```

## §3 Dispatch gate — live evidence already exists

This branch was created only after the evidence in §2 was observed from
merged `main`. Do not copy pre-live placeholders into current authority.

## §4 Files in scope — exact write lease

This state update is one guarded transaction.

| Action | Path                                                                              | Purpose                                                                                      |
| ------ | --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Create | `Docs/Plans/HANDOFF-DOCUMENTS-cutover-exact-six-live-exit-state-sync.md`          | Own this guarded authority transition                                                        |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md`                                    | Mark exact-six DONE; identity-lifecycle-through-alias_remove READY; Captain/Thrin BLOCKED   |
| Modify | `Docs/Design/STATUS-world-graph-continuity-spine.md`                              | Record actual canonical post-live state and active successor                                 |
| Modify | `Docs/Plans/HANDOFF-CUTOVER-eldyrwild-identity-shadow-alias-remove.md`            | Mark implementation/live slice DONE/HISTORICAL and record exit evidence                      |
| Modify | `Backlog.md`                                                                      | Record EVIDENCE_PROVENANCE 8→2 and retarget Case C action to the current lifecycle proof     |
| Create | `Docs/Plans/HANDOFF-CUTOVER-identity-lifecycle-through-alias-remove.md`           | Dispatch-complete current-lifecycle-proof successor contract                                 |

Review Cycle 1 withdraws the previously drafted Captain/Thrin READY handoff
(`HANDOFF-CUTOVER-alias-assertion-package-after-shadow-alias-remove.md`). It is
not part of the merge-ready lease. Cumulative diff versus the dispatch base
must not contain that path.

**Bounded discovery exception:** None.

All six paths must move together. A partial current-state update is not
merge-ready.

## §5 Explicitly out of scope

Do not modify:

```text
Backlog-DONE.md
Docs/Roadmaps/ROADMAP-campaign-supergraph.md
Docs/Design/ARCHITECTURE-campaign-supergraph.md
Docs/Plans/HANDOFF-DOCUMENTS-cutover-alias-remove-state-sync.md
Docs/Plans/HANDOFF-CUTOVER-alias-assertion-package-after-575.md
Docs/Sources/design-agent/**
src/graph_memory/**
apps/live_control_server/services/eldyrwild_identity_shadow_alias_remove.py
scripts/apply_eldyrwild_identity_shadow_alias_remove.py
tests/test_eldyrwild_identity_shadow_alias_remove.py
out/**
canonical/live World Graph data
DungeonMind repository files
```

Do not:

* rerun or alter the live mutation from this branch;
* reinterpret the six retired aliases as source history;
* claim `ATTRIBUTE_ASSERTION = 0` from the locked #575 policy;
* change merge semantics;
* remove Captain or Thrin;
* package Captain or Thrin in this PR;
* promote Captain/Thrin to `READY`;
* clear the five relationship STOPs;
* start DungeonMind Case B;
* declare CUTOVER ready;
* refresh the design-agent export mirror.

`Backlog-DONE.md` is intentionally not in the lease: the active
`EVIDENCE_PROVENANCE` backlog item is not done yet. Live exit moved the alias
count 8→2, but Case C cannot package Captain/Thrin until a current
identity-lifecycle proof re-authorizes classification.

## §6 Required authority transitions

### PR tracker

Update the repository anchor to `299579bd3c3f78a9393ae3c97c57a1dfd6b155ed`.

Transition:

```text
cutover-eldyrwild-identity-shadow-alias-remove
  READY
→ DONE
```

Its DONE record must include the observed PR, live, replay, retry, and
`EVIDENCE_PROVENANCE 8 → 2` facts from §2.

Transition:

```text
cutover-identity-lifecycle-through-alias-remove
  (absent)
→ READY
```

Required outcome text:

```text
Extend the diagnostic identity-lifecycle proof so post-#583 survivor state is
reconstructable from durable merge + later alias_remove history. Pass against
rev:0c644e56…. Regenerate source-history policy from that current passed proof.
Remeasure ATTRIBUTE_ASSERTION. No World Graph mutation.
```

Keep:

```text
cutover-alias-assertion-package-after-shadow-alias-remove
  BLOCKED
```

until the current lifecycle proof authorizes classification and remasurement
still selects the two Captain/Thrin `EVIDENCE_PROVENANCE` blockers. Do not
author a dispatch-complete Captain/Thrin handoff in this PR.

`dungeonmind-whole-world-authority-cutover` remains `BLOCKED`.

### Continuity status

The active CUTOVER slice becomes:

```text
cutover-identity-lifecycle-through-alias-remove
```

Record the observed canonical revision/payload, unchanged relationship
inventories, `EVIDENCE_PROVENANCE = 2`, remaining Captain/Thrin alias blockers,
exact-six DONE with live/replay proof, `ATTRIBUTE_ASSERTION` not currently
authorized, and `CUTOVER_NOT_READY`.

### Exact-six handoff

Change its status to:

```text
DONE / HISTORICAL — do not redispatch
```

Append a compact completion record with the exact PR, review-cycle, live,
replay, retry, and observed blocker facts.

Do not rewrite the design sections merely to make them read in past tense.
Preserve the original contract as historical evidence.

### Backlog

Keep:

```text
[READY] CUTOVER Case C Buddy EVIDENCE_PROVENANCE after identity-lifecycle history
```

Update current context to the proven `EVIDENCE_PROVENANCE = 2` remainder and
the stale-proof finding. Next Case C action is the current lifecycle proof,
not Captain/Thrin packaging. Do not archive this backlog item yet.

## §7 Successor handoff contract

Create:

```text
Docs/Plans/HANDOFF-CUTOVER-identity-lifecycle-through-alias-remove.md
```

Suggested branch:

```text
cutover/identity-lifecycle-through-alias-remove
```

PR title:

```text
CUTOVER: prove identity lifecycle through alias_remove
```

Status:

```text
READY — do not dispatch until this state-sync PR merges.
```

The successor extends the diagnostic identity-lifecycle proof so the post-#583
survivor state is reconstructable from durable merge + later `alias_remove`
history, regenerates source-history policy from that current passed proof, and
remeasures `ATTRIBUTE_ASSERTION` against `rev:0c644e56b45bcaac709012206e3e41c2`
without mutating the World Graph.

It must keep the historical #575 merge-only fixture reproducing. It must refuse
to mint policy from the 16/28 merge-only result. Captain/Thrin packaging is
explicitly out of scope.

## §8 Evidence required to merge this DOCUMENTS PR

Before review, record the full live evidence used as input and verify the six
leased files agree.

Required checks:

```bash
git merge-base --is-ancestor \
  299579bd3c3f78a9393ae3c97c57a1dfd6b155ed HEAD

uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-DOCUMENTS-cutover-exact-six-live-exit-state-sync.md \
  --local-only

git diff --check
```

Review the cumulative changed paths against the actual state-sync dispatch
base:

```bash
git diff --name-only 299579bd3c3f78a9393ae3c97c57a1dfd6b155ed...HEAD
```

Expected exactly:

```text
Backlog.md
Docs/Design/STATUS-world-graph-continuity-spine.md
Docs/Plans/HANDOFF-CUTOVER-eldyrwild-identity-shadow-alias-remove.md
Docs/Plans/HANDOFF-CUTOVER-identity-lifecycle-through-alias-remove.md
Docs/Plans/HANDOFF-DOCUMENTS-cutover-exact-six-live-exit-state-sync.md
Docs/Plans/PR-TRACKER-campaign-supergraph.md
```

Positive consistency scan:

```text
PR #583
2cacc7cbdf77977e86daf29ed2b9058f94d54e70
299579bd3c3f78a9393ae3c97c57a1dfd6b155ed
3 review cycles
EVIDENCE_PROVENANCE = 2
16/28
ATTRIBUTE_ASSERTION not currently authorized
cutover-identity-lifecycle-through-alias-remove
CUTOVER_NOT_READY
rev:0c644e56b45bcaac709012206e3e41c2
```

Negative consistency scan:

```text
exact-six = READY
EVIDENCE_PROVENANCE = 8 as current state
ATTRIBUTE_ASSERTION = 0 as current authorized state
Captain/Thrin package = READY
CUTOVER_READY
Case B = READY
```

Historical sections may still contain old values when explicitly labeled as
historical. Do not mechanically erase history.

## §9 Review handback

The implementation handback must include:

```text
state-sync dispatch base SHA
PR #583 head + merge SHA
PR #583 review-cycle count = 3

live parent revision
live result revision
live result payload SHA
six alias_remove decision IDs

replay proof result
retry proof result

post-live blocker ledger
remaining exact two blocker IDs
keeper lineage proof

canonical relationship inventory
migration relationship inventory

changed paths vs §4
positive/negative authority consistency checks

explicit statements:
  no live mutation occurred from this DOCUMENTS branch
  ATTRIBUTE_ASSERTION is not currently authorized as 0
  no identity-lifecycle proof implementation occurred
  no Captain/Thrin package implementation occurred
  CUTOVER remains NOT_READY
```

## §10 Acceptance rubric

* [ ] PR #583 merge facts are recorded exactly.
* [ ] Review-cycle count is 3.
* [ ] Canonical live exit was proven before branch dispatch.
* [ ] Actual live parent/result/payload are recorded from evidence.
* [ ] Replay reconstructs the cleaned current head.
* [ ] Retry is no-op/already-applied.
* [ ] Exact six are retired and no seventh alias is touched.
* [ ] Captain and Thrin remain source-grounded.
* [ ] `EVIDENCE_PROVENANCE = 2`.
* [ ] Exact remaining alias blockers are Captain + Thrin.
* [ ] Merge-only identity-lifecycle proof on the cleaned head is recorded as 16/28.
* [ ] `ATTRIBUTE_ASSERTION` is not claimed as currently authorized 0.
* [ ] Observed `IDENTITY_HISTORY = 20` and `CONTRIBUTION_HISTORY = 5291` are recorded.
* [ ] Relationship inventories are unchanged.
* [ ] Five relationship STOPs remain untouched.
* [ ] Exact-six slice is `DONE`.
* [ ] Identity-lifecycle-through-alias_remove successor is `READY`.
* [ ] Captain/Thrin package remains `BLOCKED`.
* [ ] `CUTOVER_NOT_READY` remains true.
* [ ] All six state-sync files move atomically.
* [ ] No runtime/code/live-data path is changed.
* [ ] Roadmap and architecture remain untouched.
* [ ] Design-agent export mirror remains untouched.

## Stop conditions

Stop instead of merging if:

* canonical live apply/replay evidence is absent;
* observed live parent/result cannot be pinned;
* replay differs from the published head;
* retry publishes again;
* any of the six aliases remains current;
* Captain or Thrin disappears or loses its locked source lineage;
* `EVIDENCE_PROVENANCE` is not exactly 2;
* a third EVIDENCE_PROVENANCE blocker exists;
* relationship inventories drift;
* the state-sync claims `ATTRIBUTE_ASSERTION = 0` as current authority;
* the state-sync promotes Captain/Thrin to `READY`;
* the state-sync diff is partial;
* a worker proposes runtime code or graph mutation in this PR;
* a worker proposes starting Case B;
* a worker proposes declaring CUTOVER ready.
