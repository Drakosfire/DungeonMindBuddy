---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: CUTOVER — prove identity lifecycle through alias_remove
  - Flow: CUTOVER
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-CUTOVER-identity-lifecycle-through-alias-remove.md
  - Branch: cutover/identity-lifecycle-through-alias-remove

  ## Verification pointer
  - Dispatch authority: PR #584 merge `ad6dd2507d4f5ed2c5cc24e9c0c8b50df2e65ca9`
  - Implementation predecessor: PR #583
  - PR #583 head: `2cacc7cbdf77977e86daf29ed2b9058f94d54e70`
  - PR #583 merge: `299579bd3c3f78a9393ae3c97c57a1dfd6b155ed`
  - Canonical input: `rev:0c644e56b45bcaac709012206e3e41c2`
  - Historical proof predecessor: PR #575
  - Verification: exact §7 results from implementation handback

  Prove the current post-#583 identity lifecycle through the ordered
  `merge → alias_remove` history, regenerate source-history policy from that
  fully passed proof, and remeasure ATTRIBUTE_ASSERTION.

  This PR is diagnostic/non-publishing. It does not mutate Eldyrwild and does
  not package Captain or Thrin Branchborn.
---

# HANDOFF — prove identity lifecycle through alias_remove

**Created:** 2026-08-13
**Status:** DONE / HISTORICAL — do not redispatch
**Canonical handoff path:** `Docs/Plans/HANDOFF-CUTOVER-identity-lifecycle-through-alias-remove.md`
**Conversation/workstream:** `CUTOVER — prove identity lifecycle through alias_remove`
**Flow / owner:** `CUTOVER`
**Direction:** DESIGN → CODE → REVIEW
**Design base:** `ad6dd2507d4f5ed2c5cc24e9c0c8b50df2e65ca9`
**Suggested branch:** `cutover/identity-lifecycle-through-alias-remove`
**PR title:** `CUTOVER: prove identity lifecycle through alias_remove`

### Completion record

```text
DONE / HISTORICAL — do not redispatch.

PR: #585
implementation head: 7c339a23d77b4465ca0adeda015859215b65285d
merge: 0fe9f88cfafda38319145e88d0f8b354d53830ca
review cycles: 2

canonical: rev:0c644e56b45bcaac709012206e3e41c2
payload: 0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2

historical merge-only proof on current head:
  reconstructable 16 / 28
  unresolved 12
  current-policy authority: NO

current lifecycle-through-alias_remove proof:
  reconstructable 28 / 28
  unresolved []
  passed true

fresh source-history policy:
  policy_id identity_lifecycle_history_v1
  source exact current passed proof

current remeasurement:
  ATTRIBUTE_ASSERTION = 0
  EVIDENCE_PROVENANCE = 2
  IDENTITY_HISTORY = 20
  CONTRIBUTION_HISTORY = 5291

remaining EVIDENCE_PROVENANCE:
  node:node:captain-lysandra-ironveil:field:aliases
  node:node:thrin-branchborn:field:aliases

relationships:
  canonical 323 / 314 / 9 / 3
  migration 323 / 318 / 5 / 3

five dual-sense relationship STOPs: unchanged
CUTOVER_NOT_READY remains true

fixture:
  tests/fixtures/dungeonmind_kernel/eldyrwild_cutover_identity_lifecycle_through_alias_remove_v1.json
  SHA-256 c31e8c156b3d66f389f67dcdb92b28a4e7c4d0a6ae77e3f0604b99cf38940531
```

Successor: [`HANDOFF-CUTOVER-alias-assertion-package-after-shadow-alias-remove.md`](HANDOFF-CUTOVER-alias-assertion-package-after-shadow-alias-remove.md). Dispatch after the required DOCUMENTS lifecycle-proof exit state-sync merges; do not dispatch from `0fe9f88…` directly.

> Repository law: [`AGENTS.md`](../../AGENTS.md).
> Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md).
>
> Re-anchor before the first implementation change. The actual dispatch base
> must be current `origin/main`, must be `ad6dd250…` or a descendant, and must
> still preserve the authority pins below.
>
> Record the exact dispatch-base SHA in the implementation handback.
>
> This is a proof-extension slice, not an identity mutation slice.

## §1 Mission and merge-ready invariant

### Mission

Extend the existing identity-lifecycle proof so the exact post-#583 Eldyrwild
state can reconstruct merge-survivor bookkeeping from durable ordered identity
history when:

```text
merge
  ↓
later alias_remove
  ↓
current survivor state
```

Then:

```text
require the current proof to pass with zero unresolved lifecycle elements;
mint source-history policy only from that passed proof;
remeasure ATTRIBUTE_ASSERTION;
prove the canonical World Graph is unchanged.
```

### Merge-ready invariant

Against exact canonical input:

```text
world:
  eldyrwild

revision:
  rev:0c644e56b45bcaac709012206e3e41c2

payload SHA:
  0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2
```

the implementation must prove:

```text
current identity-lifecycle candidates
==
exact lifecycle elements reconstructed from durable identity authority

current proof:
  passed = true
  unresolved_element_ids = []

source-history policy:
  generated only from that current passed proof

ATTRIBUTE_ASSERTION:
  remeasured under the generated policy
```

The PR must also preserve:

```text
historical PR #575 proof
canonical World Graph head
canonical payload/tree
identity decision ledger
identity redirects
node aliases
contributions
evidence/source authority
relationship inventories
```

### Named successor intentionally remaining false

This PR does not construct the remaining alias assertion package.

The following remains blocked until this PR merges and its remeasurement still
selects exactly the two source-grounded aliases:

```text
cutover-alias-assertion-package-after-shadow-alias-remove

Captain
Thrin Branchborn
```

## §2 Authority and current state

### Repository authority

PR #584 is merged:

```text
PR:
  #584

head:
  4219fc2a33c03a323bc12309d5ca93a27a6a7477

merge:
  ad6dd2507d4f5ed2c5cc24e9c0c8b50df2e65ca9
```

At handoff dispatch, `main` is expected to be that merge or a later valid
descendant.

### Canonical Eldyrwild authority

```text
world_id:
  eldyrwild

canonical revision:
  rev:0c644e56b45bcaac709012206e3e41c2

canonical payload SHA-256:
  0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2

canonical relationships:
  semantic       323
  represented    314
  residual         9
  uses_statblock   3

migration projection:
  semantic       323
  represented    318
  residual         5
  uses_statblock   3
```

### Current blocker facts

Post-#583 live/replay exit established:

```text
EVIDENCE_PROVENANCE = 2

remaining alias blockers:
  node:node:captain-lysandra-ironveil:field:aliases
  node:node:thrin-branchborn:field:aliases

IDENTITY_HISTORY = 20
CONTRIBUTION_HISTORY = 5291
```

`ATTRIBUTE_ASSERTION` is not currently authorized as zero.

### Why

PR #575 proved the pre-`alias_remove` lifecycle shape.

On the current canonical head the old merge-only proof now produces:

```text
reconstructable = 16 / 28
unresolved       = 12
```

The twelve unresolved elements are the six affected survivors':

```text
last_identity_decision_id
identity_state
```

because `remove_identity_alias()` legitimately changed their
`last_identity_decision_id` from the earlier merge decision to the later
`alias_remove` decision.

Therefore:

```text
locked #575 28-ID policy
!=
current proof authority
```

A partial proof must not mint policy.

### Existing source semantics

The current proof supports only:

```text
decision_kind == merge
```

and deliberately returns unresolved for another pointed decision kind.

The Kernel's `remove_identity_alias()`:

1. builds an active `alias_remove` decision
2. removes the materialized alias
3. writes `subject.state.last_identity_decision_id = alias_remove decision id`
4. appends the decision to `store.identity_decisions`

The identity decision ledger is append ordered.

Existing unmerge safety already relies on that ordering by scanning decisions
after a merge for later `alias_remove` decisions.

This PR may therefore use durable decision-list position as lifecycle ordering
authority.

Do not invent timestamp ordering.

## §3 Pre-dispatch critique

| Question | Answer |
|---|---|
| One independently useful capability? | Yes. Current lifecycle reconstructability → current policy → remeasurement. |
| Does this mutate graph truth? | No. Diagnostic only. |
| Most likely incorrect shortcut | Treating any prior merge into the survivor as sufficient proof. |
| Second likely shortcut | Reusing the locked #575 element-ID set. |
| Third likely shortcut | Adding fields/schema churn merely to make lineage easier to expose. |
| Most important adversarial path | `merge → split/unmerge → alias_remove` must not be accepted as ordinary merge-survivor continuity. |
| Another adversarial path | A stale current pointer with a later state-mutating identity decision must not pass. |
| Historical risk | Breaking exact PR #575 reproduction while extending current semantics. |
| Stop condition | Generic Kernel behavior is insufficient; structured proof requires a new public schema; or current state includes lifecycle kinds beyond the bounded merge/`alias_remove` contract. |

## §4 Files in scope — exact expected write lease

| Action | Path |
|---|---|
| Modify | `apps/live_control_server/integrations/dungeonmind_kernel/identity_lifecycle_history_conformance_v1.py` |
| Modify | `tests/test_identity_lifecycle_history_conformance_v1.py` |
| Create | `apps/live_control_server/services/cutover_identity_lifecycle_through_alias_remove.py` |
| Create | `scripts/build_cutover_identity_lifecycle_through_alias_remove.py` |
| Create | `tests/test_cutover_identity_lifecycle_through_alias_remove.py` |
| Create | `tests/fixtures/dungeonmind_kernel/eldyrwild_cutover_identity_lifecycle_through_alias_remove_v1.json` |

### Lease-trim rule

If the current architecture proves the successor needs no dedicated service or
CLI wrapper, those paths may be removed from the lease during implementation
preflight.

Do not add substitute machinery merely to fill the expected lease.

There is no general bounded-discovery exception. If another path becomes
necessary, report it before editing.

This lane may read the exact canonical Eldyrwild world. It may not publish or
modify it. If canonical files are read during verification, capture tree/head
digests before and after and prove equality.

No shared server port or live service ownership is required. Use an isolated
worktree/checkout.

## §5 Explicitly out of scope

Do not modify:

```text
src/graph_memory/**
out/graph_memory/worlds/eldyrwild/**
canonical/live World Graph data
DungeonMind repository files

apps/live_control_server/integrations/dungeonmind_kernel/whole_world_conformance_v4.py
apps/live_control_server/integrations/dungeonmind_kernel/whole_world_conformance_v5.py

apps/live_control_server/services/cutover_identity_lifecycle_history_after_571.py
tests/fixtures/dungeonmind_kernel/eldyrwild_cutover_identity_lifecycle_history_after_571_v1.json

Docs/Design/ARCHITECTURE-campaign-supergraph.md
Docs/Roadmaps/ROADMAP-campaign-supergraph.md
Docs/Sources/design-agent/**
```

Do not:

- mutate Eldyrwild
- remove another alias
- add another identity decision
- change merge semantics
- change `alias_remove` semantics
- package Captain
- package Thrin Branchborn
- clear the five relationship STOPs
- start DungeonMind Case B
- exercise existing-world adoption
- declare `CUTOVER_READY`

### Historical schema preservation

Do not introduce a new lifecycle proof schema merely to represent the earlier
merge.

Keep:

```text
dmb_identity_lifecycle_history_conformance_v1
```

and its existing public row shape unless implementation proves that correctness
cannot be expressed without a schema change.

A required schema-v2/public-contract change is:

```text
STOP
→ return to stewardship
```

The historical #575 fixture must continue reproducing under its original
merge-only input.

## §6 Implementation contract

### 6.1 Preserve merge-only behavior

Existing merge-source proof behavior remains unchanged:

```text
merged_into
last_identity_decision_id
active redirect
merged_away state
```

must continue reconstructing from the original merge.

Existing historical merge-survivor behavior also remains valid when the node's
current pointer still names that merge.

Do not rewrite the old proof around the new special case.

### 6.2 Ordered identity-decision authority

Build an internal ordered view of `store.identity_decisions` with:

```text
decision_id → validated record
decision_id → durable list position
```

Fail closed on duplicate IDs exactly as today.

Durable list position is the ordering authority for this proof.

Do not sort by `created_at` or `decision_id` to invent lifecycle order.

### 6.3 Current alias_remove pointer

When a candidate survivor carries `last_identity_decision_id = X` and `X`
resolves to `alias_remove`, require all of the following.

Current decision integrity:

```text
decision.status == active
decision.decision_kind == alias_remove
decision.subject_node_id == current node
current node in decision.affected_node_ids
decision.target_node_id is None
decision.alias is nonblank
stored last_identity_decision_id == decision.decision_id
```

If any clause fails: unresolved.

### 6.4 Prove the causal merge, not merely any merge

The `alias_remove` must resolve to an earlier active merge that actually
materialized the alias being retired.

Find prior active merge decisions satisfying:

```text
merge.target_node_id == alias_remove.subject_node_id

alias_remove.alias case-insensitively belongs to:
  merge.merge_side_effects.aliases_added_to_target

merge list position < alias_remove list position
```

Require exactly one causal merge.

If zero causal merges, multiple causal merges, or missing `merge_side_effects`,
fail closed.

Do not accept "this node was merged at some point" as sufficient proof.

The retired alias must be causally attributable to the proving merge.

### 6.5 Prove the merge source still tells the same story

For the causal merge, require its source to remain consistent with the existing
merge proof:

```text
source node exists

source.memory_state == merged_away
source.identity_canon_state == merged_away
source.merged_into == survivor node id
source.last_identity_decision_id == causal merge decision id

exactly one active redirect from source
redirect.to_node_id == survivor node id
```

If the source-side durable state no longer agrees with the merge: unresolved.

### 6.6 Prove survivor continuity

The current target must remain:

```text
identity_canon_state == canonical
identity_state == survivor
```

The `alias_remove` itself does not establish `identity_state=survivor`.

The causal merge establishes the survivor role.

The later `alias_remove` establishes the current `last_identity_decision_id`.

Thus reconstruction is:

```text
identity_state:
  causal merge target
  + uninterrupted survivor lifecycle
  → survivor

last_identity_decision_id:
  current valid alias_remove
  → alias_remove decision id
```

### 6.7 Reject invalidating lifecycle between merge and alias_remove

Inspect durable identity decisions between the causal merge and current
`alias_remove`.

If a state-changing decision affecting the survivor is `split` or `unmerge`,
the narrow proof must refuse it.

Do not silently prove across those operations.

Current scope is `merge` and `alias_remove`.

If the exact current world requires a split/unmerge-aware proof:

```text
STOP
→ return to stewardship
```

Other earlier `alias_remove` decisions do not themselves invalidate survivor
status.

Another merge into the same canonical survivor does not automatically invalidate
survivor status, but it must not be used as a substitute for the exact causal
merge that introduced the alias currently being retired.

### 6.8 Reject a stale current pointer

After the pointed `alias_remove` decision, there must be no later active
state-mutating identity decision affecting that node that would make
`last_identity_decision_id` stale.

At minimum treat these as state-mutating for this check:

```text
merge
split
unmerge
alias_remove
```

If such a later decision exists: unresolved.

Do not accept a stale node-state pointer merely because the pointed decision is
otherwise valid.

### 6.9 Reuse one lineage proof for both survivor fields

Do not implement independent permissive logic for `last_identity_decision_id`
and `identity_state`.

Use one internal alias-remove survivor-lineage proof/result so both rows rely on
the same validated causal merge and current decision ordering.

This prevents the two fields from disagreeing about which history proved them.

### 6.10 Preserve v1 row/schema compatibility

For current alias-remove rows, existing row fields may describe the current
pointed decision:

```text
decision_id
decision_kind
decision_status
subject_node_id
target_node_id
```

with `lifecycle_role = merge_survivor`.

The causal predecessor merge may remain an internal validation fact if exposing
it structurally would change the v1 schema.

Tests must prove the predecessor merge is actually validated.

Do not encode unverified predecessor information only in prose.

If downstream consumption requires structured predecessor decision IDs:

```text
STOP
→ second contract / steward rebrief
```

### 6.11 Current proof result

Run the proof over the exact canonical store.

Current observed inventory is 28 candidate lifecycle fields, but correctness is
not `count == 28`.

Correctness is:

```text
exact current lifecycle candidate element IDs
==
exact proof.element_ids

proof.passed == true
proof.unresolved_element_ids == []
proof.reconstructable_count == len(proof.element_ids)
```

Record field counts as evidence. Do not make 28 the authorization mechanism.

### 6.12 Policy regeneration

Use only `source_history_policy_from_identity_lifecycle_proof(current_proof)`.

The existing policy constructor must continue refusing:

```text
passed = false
unresolved != []
non-reconstructable row
row/element-id drift
```

Specifically prove that the current merge-only 16/28 result cannot mint policy.

### 6.13 Remeasurement

On the same exact loaded canonical store:

1. analyze with LEGACY / empty proven lifecycle policy
2. collect exact `ATTRIBUTE_ASSERTION` IDs
3. run current lifecycle proof
4. require proof passed
5. require pre-policy `ATTRIBUTE_ASSERTION` IDs == `proof.element_ids`
6. mint policy from current proof
7. re-run whole-world v5 analysis with generated policy
8. record resulting blocker ledger

Do not inject locked #575 element IDs, expected blocker count, or expected
`ATTRIBUTE_ASSERTION=0` into the classifier.

Expected but never forced observation: `ATTRIBUTE_ASSERTION = 0`.

If it is not zero: record actual residual and STOP successor promotion.

### 6.14 Successor diagnostic report

Create one sealed successor report/fixture for this slice.

Suggested schema: `dmb_cutover_identity_lifecycle_through_alias_remove_v1`

It should contain enough evidence to reproduce:

```text
Buddy dispatch/base SHA
canonical revision
canonical payload SHA

legacy/current pre-policy ATTRIBUTE_ASSERTION inventory

historical merge-only diagnostic on current head
  reconstructable = 16
  unresolved = 12

current lifecycle proof
current exact element IDs
field counts
reconstructable count
unresolved IDs
passed

policy identity/source
post-policy blocker ledger

EVIDENCE_PROVENANCE
IDENTITY_HISTORY
CONTRIBUTION_HISTORY

canonical relationship inventory
migration relationship inventory

historical #575 reproduction result

World Graph mutation/tree/head proof

CUTOVER disposition
next-slice recommendation
```

The report is diagnostic evidence. It is not a new product API.

## §7 Evidence required to merge

### 7.1 Exact current-world proof

Required observation:

```text
canonical revision:
  rev:0c644e56b45bcaac709012206e3e41c2

payload:
  0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2
```

Historical merge-only diagnostic on that same head must remain visible:

```text
reconstructable:
  16 / 28

unresolved:
  12
```

Do not use that result as policy input.

### 7.2 Current lifecycle proof

Require:

```text
passed = true
unresolved_element_ids = []
reconstructable_count = candidate count

every alias_remove-backed survivor row proves:
  active current alias_remove
  exact subject
  exact causal earlier merge
  alias introduced by that merge
  correct durable ordering
  source merge state/redirect still intact
  canonical survivor state intact
  no invalidating split/unmerge
  no later stale-pointer-producing decision
```

### 7.3 Adversarial unit tests

At minimum add tests for:

| Sequence | Required result |
|---|---|
| merge → alias_remove | PASS |
| alias_remove with no earlier causal merge | FAIL |
| alias_remove before causal merge in durable decision order | FAIL |
| alias_remove alias not present in merge.aliases_added_to_target | FAIL |
| wrong alias_remove subject | FAIL |
| inactive alias_remove | FAIL |
| missing merge_side_effects | FAIL |
| ambiguous/multiple causal merge ownership | FAIL |
| merge → split → alias_remove | FAIL |
| merge → unmerge → alias_remove | FAIL |
| valid alias_remove pointer + later state-mutating decision | FAIL as stale pointer |
| historical ordinary merge survivor | PASS unchanged |
| merge-source merged_into/redirect proof | PASS unchanged |

Do not weaken a negative test merely because constructing the inconsistent
synthetic store requires direct model assembly.

The proof is specifically responsible for rejecting corrupted durable state.

### 7.4 Historical #575 reproduction

The locked historical fixture must still reproduce under its original
merge-only world.

Required:

```text
historical proof:
  passed = true

historical candidate set:
  unchanged

historical fixture:
  byte/digest equivalent under its existing verifier
```

Do not rewrite the historical fixture.

### 7.5 Policy factory

Prove:

```text
merge-only 16/28 current result
  → source_history_policy_from_identity_lifecycle_proof refuses

current fully passed proof
  → policy accepted
```

### 7.6 Current remeasurement

Record actual `ATTRIBUTE_ASSERTION`, `EVIDENCE_PROVENANCE`, `IDENTITY_HISTORY`,
and `CONTRIBUTION_HISTORY`.

Expected if the design hypothesis is correct:

```text
ATTRIBUTE_ASSERTION = 0
EVIDENCE_PROVENANCE = 2
IDENTITY_HISTORY = 20
CONTRIBUTION_HISTORY = 5291
```

Those are expected observations, not constants to force.

### 7.7 Relationship invariants

Require unchanged:

```text
canonical:
  323 / 314 / 9 / 3

migration:
  323 / 318 / 5 / 3
```

The five dual-sense STOP edges remain untouched.

### 7.8 No mutation

Capture before/after evidence proving:

```text
canonical head unchanged
canonical graph payload unchanged
World Graph tree digest unchanged
identity decision ledger unchanged
identity redirects unchanged
node aliases unchanged
contributions unchanged
```

This slice is non-publishing.

### 7.9 Captain/Thrin still not implemented

Confirm:

```text
Captain package row not created
Thrin package row not created
EVIDENCE_PROVENANCE package not sealed
```

The two source-grounded alias blockers remain only a measured successor input.

### 7.10 Verification commands

At minimum:

```bash
uv run pytest -q \
  tests/test_identity_lifecycle_history_conformance_v1.py \
  tests/test_cutover_identity_lifecycle_history_after_571.py \
  tests/test_cutover_identity_lifecycle_through_alias_remove.py

uv run ruff check \
  apps/live_control_server/integrations/dungeonmind_kernel/identity_lifecycle_history_conformance_v1.py \
  apps/live_control_server/services/cutover_identity_lifecycle_through_alias_remove.py \
  scripts/build_cutover_identity_lifecycle_through_alias_remove.py \
  tests/test_identity_lifecycle_history_conformance_v1.py \
  tests/test_cutover_identity_lifecycle_through_alias_remove.py

git diff --check

git diff --name-only <dispatch-base>...HEAD
```

If the implementation trims service/script paths, trim the Ruff list
accordingly.

The implementation handback must distinguish author-local tests, independently
rerun tests, GitHub Actions / commit status, and manual canonical-world
observation. Do not call author-local execution "CI green."

## §8 Required review handback

Record exactly:

```text
Review Cycle <N>

PR:
branch:
head SHA:

dispatch/base SHA:
current main relation:

actual changed paths:
lease deviations / trims:

canonical input:
  world
  revision
  payload SHA

historical merge-only current-head diagnostic:
  candidate count
  reconstructable
  unresolved IDs

current lifecycle proof:
  candidate count
  field counts
  reconstructable
  unresolved
  passed

alias_remove lineage proof:
  number of alias_remove-backed survivors
  exact current alias_remove decision IDs
  exact causal merge decision IDs
  confirmation ordering is list-order-derived
  confirmation no invalidating split/unmerge

policy:
  partial proof refused
  current proof accepted
  policy id

remeasurement:
  ATTRIBUTE_ASSERTION
  EVIDENCE_PROVENANCE
  IDENTITY_HISTORY
  CONTRIBUTION_HISTORY

relationships:
  canonical
  migration

historical #575 fixture:
  verification result

mutation proof:
  graph head before/after
  tree/payload equality
  identity ledger equality
  alias equality

named successor:
  Captain/Thrin package remains unimplemented
```

Also record any pre-existing test failures separately from head-introduced
failures.

## §9 Acceptance rubric

- [ ] Exactly one independently useful capability is delivered: current identity-lifecycle reconstruction through `alias_remove`.
- [ ] Actual dispatch base is current `main` descendant of PR #584 merge `ad6dd250…`.
- [ ] Exact canonical input remains `rev:0c644e56…` / `0640d7ef…`.
- [ ] Historical merge-only diagnostic remains visible as 16/28 on the current head.
- [ ] That partial result cannot mint source-history policy.
- [ ] Current lifecycle proof passes with zero unresolved rows.
- [ ] Alias-remove survivor proof is causal: the retired alias was introduced by the proving earlier merge.
- [ ] Decision ordering derives from durable decision-list position.
- [ ] Invalidating split/unmerge sequences fail closed.
- [ ] Stale current pointers fail closed.
- [ ] Existing merge-source proof behavior remains unchanged.
- [ ] Historical #575 fixture still reproduces.
- [ ] No v1 public proof schema churn was introduced.
- [ ] Policy is generated from the current passed proof only.
- [ ] `ATTRIBUTE_ASSERTION` is remeasured rather than hardcoded.
- [ ] `EVIDENCE_PROVENANCE`, history blockers, and relationship inventories are recorded from actual measurement.
- [ ] Canonical World Graph is unchanged.
- [ ] Captain/Thrin packaging is not implemented.
- [ ] Five relationship STOPs remain untouched.
- [ ] No generic Kernel file is modified.
- [ ] Actual changed paths remain within §4.

## Stop conditions

Stop and report rather than broadening this PR if any of the following occurs:

- current `main` is not a valid descendant of PR #584 merge
- canonical Eldyrwild revision/payload drifted before dispatch
- current lifecycle candidates include a required decision kind beyond `merge` / `alias_remove`
- correctness requires supporting `split`, `unmerge`, `alias_add`, or another lifecycle mutation
- correctness requires changing `src/graph_memory/**`
- correctness requires a new public lifecycle-proof schema
- historical #575 fixture cannot reproduce
- current candidate set contains lifecycle fields unrelated to the intended identity-history proof
- policy cannot be regenerated without modifying whole_world_conformance v4/v5
- World Graph mutation is proposed
- Captain/Thrin package work becomes necessary
- relationship STOP work becomes necessary
- DungeonMind adoption work becomes necessary

Report using:

```text
Stop condition:
Invariant clause affected:
Why current mission cannot absorb it:
Required evidence now missing:
Affected paths / ownership layers:
Proposed successor or re-brief:
State-authority update needed:
```

## Expected post-merge state-authority sync

Only after this implementation is merged and the exact result is known:

```text
PR-TRACKER:
  cutover-identity-lifecycle-through-alias-remove
    READY/DOING → DONE

STATUS:
  record current proof/policy/remeasurement result

this HANDOFF:
  DONE / HISTORICAL

Backlog Case C:
  advance from lifecycle proof to measured next blocker
```

If and only if the merged proof establishes:

```text
ATTRIBUTE_ASSERTION = 0
EVIDENCE_PROVENANCE = 2

remaining EVIDENCE_PROVENANCE exactly:
  Captain
  Thrin Branchborn
```

then the state-sync may promote:

```text
cutover-alias-assertion-package-after-shadow-alias-remove
  BLOCKED → READY
```

and author its dispatch-complete handoff.

Do not pre-authorize that transition from expected counts.
