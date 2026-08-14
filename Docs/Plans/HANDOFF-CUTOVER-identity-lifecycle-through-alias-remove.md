---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: CUTOVER — prove identity lifecycle through alias_remove
  - Flow: CUTOVER
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-CUTOVER-identity-lifecycle-through-alias-remove.md
  - Branch: cutover/identity-lifecycle-through-alias-remove

  ## Verification pointer
  - Implementation predecessor: PR #583 live/replay exit
  - PR #583 head: 2cacc7cbdf77977e86daf29ed2b9058f94d54e70
  - PR #583 merge: 299579bd3c3f78a9393ae3c97c57a1dfd6b155ed
  - Canonical input: rev:0c644e56b45bcaac709012206e3e41c2
  - Historical predecessor: PR #575 merge-only identity-lifecycle proof
  - Verification: exact §7 results from implementation handback

  This PR extends the diagnostic identity-lifecycle proof through alias_remove,
  regenerates source-history policy from a current passed proof, and remeasures.
  It does not mutate the World Graph and does not package Captain / Thrin.
---

# HANDOFF — prove identity lifecycle through alias_remove

**Created:** 2026-08-13  
**Status:** READY — do not dispatch until `HANDOFF-DOCUMENTS-cutover-exact-six-live-exit-state-sync.md` merges to `main`.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-CUTOVER-identity-lifecycle-through-alias-remove.md`  
**Conversation/workstream:** `CUTOVER — prove identity lifecycle through alias_remove`  
**Flow / owner:** `CUTOVER`  
**Direction:** DESIGN → CODE → REVIEW  
**Design base:** post-live Eldyrwild `rev:0c644e56b45bcaac709012206e3e41c2` recorded by the exact-six live-exit state sync  
**Suggested branch:** `cutover/identity-lifecycle-through-alias-remove`  
**PR title:** `CUTOVER: prove identity lifecycle through alias_remove`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process:
> [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md).
>
> **Dispatch gate:** Before the first code change, fetch/re-anchor current
> `origin/main`, prove it is a descendant of the live-exit state-sync merge,
> prove this canonical handoff exists on that base, and prove the tracker names
> `cutover-identity-lifecycle-through-alias-remove` as `READY`. Record the exact
> dispatch-base SHA in the implementation handback.
>
> Prove the post-#583 survivor lifecycle from durable merge + later
> `alias_remove` history. Regenerate source-history policy from that current
> passed proof. Remeasure. Do not mutate the World Graph. Do not classify by
> field name, count, or the locked #575 element-ID set. Do not dispatch
> Captain/Thrin from this slice.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Merge-only proof** | PR #575's diagnostic: reconstruct `identity_state` / `merged_into` / `last_identity_decision_id` only when the pointed decision is an active `merge`. Historical contract; still required on the #575 world. |
| **Current lifecycle proof** | The same durable-element reconstructability test, extended so a merge survivor whose `last_identity_decision_id` now names a later active `alias_remove` is still reconstructable from merge + that later decision. |
| **Stale #575 policy** | The locked 28-ID `identity_lifecycle_history_v1` source-history set. It was generated from a fully passed merge-only proof. A 16/28 merge-only result cannot regenerate it. It is not current classification authority on `rev:0c644e56…`. |
| **Policy regeneration** | `source_history_policy_from_identity_lifecycle_proof` on a current proof that `passed=true` with zero unresolved rows. No hardcoded allowlist. |

The flow identifier `CUTOVER` is the owner for this slice.

## §1 Mission and merge-ready invariant

**Mission:** Extend the diagnostic identity-lifecycle proof so the post-#583 Eldyrwild survivor state is reconstructable from durable merge history plus later `alias_remove` decisions; regenerate source-history policy from that current passed proof; remeasure `ATTRIBUTE_ASSERTION` against `rev:0c644e56b45bcaac709012206e3e41c2`.

**Merge-ready invariant:** Against that exact live head, the current lifecycle proof reconstructs every current identity-lifecycle shadow field from durable identity authority; `source_history_policy_from_identity_lifecycle_proof` accepts that proof; remasurement uses only that regenerated policy; the historical #575 merge-only fixture still reproduces; canonical World Graph head, tree, contributions, identity decisions, aliases, and relationship inventories are unchanged; Captain/Thrin are not packaged.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern the PR? | **Yes.** Current reconstructability → current policy → remasurement. No mutation. |
| Most likely failure | Reusing the locked #575 28-ID set, or treating 16/28 merge-only reconstructability as a passed proof. |
| Second likely failure | Silently admitting `alias_remove` under the merge-only rule without proving merge + later `alias_remove`. |
| Third likely failure | Breaking the historical #575 fixture while extending the prover. |
| Stop condition | Any unresolved current lifecycle field; any other decision kind (`split`, `unmerge`, …); any World Graph mutation; any Captain/Thrin package work. |

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | `AGENTS.md`; tracker; continuity status; exact-six live-exit state sync; PR #575 handoff §8.4 |
| Canonical input | `rev:0c644e56b45bcaac709012206e3e41c2` / payload `0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2` |
| Implementation predecessor | PR #583; head `2cacc7cb…`; merge `299579bd…`; 3 review cycles; live/replay proven |
| Historical predecessor | PR #575 merge-only proof; merge `d32c244e…`; fixture SHA `1a2cd8f9…` |
| Observed merge-only result on the cleaned head | reconstructable **16/28**; 12 unresolved because six survivors' `last_identity_decision_id` + `identity_state` now name `alias_remove` |
| Named successor | Captain/Thrin alias assertion package, **only after** this proof authorizes classification and remasurement still shows `EVIDENCE_PROVENANCE = 2` |
| What remains false | Captain/Thrin package; `ATTRIBUTE_ASSERTION` currently authorized as 0; five relationship STOPs; durable adoption; Case B; `CUTOVER_READY` |
| Runtime ownership | Isolated measurement only. No live World Graph mutation. |
| State-authority sync set after merge | tracker; continuity status; this handoff completion; Backlog Case C item. Successor Captain/Thrin handoff is authored only if remasurement still selects those two alias blockers. |

### Why the locked #575 policy is not current authority

PR #575's contract:

```text
classify SOURCE_MIGRATION_HISTORY
  only when an exact proof demonstrates current stored values
  are reconstructable from durable identity authority

do not classify by field name
do not classify by count
do not classify by a hardcoded element-ID allowlist

if another identity-decision kind is encountered:
  prove it explicitly, or STOP
```

`source_history_policy_from_identity_lifecycle_proof` accepts a proof only when
`passed=true` and unresolved is empty, then reduces it to admitted element IDs.

After #583, `alias_remove` updates each affected survivor's
`last_identity_decision_id`. The merge-only prover therefore reconstructs 16/28
on `rev:0c644e56…` and cannot mint a current policy. Continuing to apply the
old 28-ID set is stale-proof authority, even if the underlying fields are still
identity lifecycle rather than world properties.

## §3 Observable proof extension

Keep the merge-only rows that still reconstruct:

```text
7 merged_into on merge sources
7 last_identity_decision_id on merge sources
1 last_identity_decision_id + 1 identity_state on the uninvolved survivor
= 16 reconstructable merge-only rows
```

Extend only the 12 unresolved survivor rows. For a node whose
`last_identity_decision_id` names an active `alias_remove`:

```text
1. the decision exists, is active, and kind is alias_remove
2. the node is the alias_remove subject (canonical survivor)
3. an earlier active merge names this node as target
4. identity_canon_state remains canonical
5. stored identity_state remains survivor
6. merge-source merged_into / last_identity_decision_id still name that merge
7. no guessed decision ID is created
```

`identity_state=survivor` after `alias_remove` is still merge-survivor
bookkeeping: `alias_remove` does not unmerge. Reconstruct it from merge + the
later `alias_remove` pointer, not from field name.

Refuse:

```text
split / unmerge / any other decision kind
alias_remove with no earlier proving merge
alias_remove whose subject is not this node
using the locked #575 28-ID set as an allowlist
classifying from a partial (unresolved != []) proof
mutating the World Graph to make the old proof pass
```

### A. State / fallback matrix

| Observable path | Exact success | Ordinary miss | Integrity failure |
|---|---|---|---|
| Merge-only row on `rev:0c644e56…` | still reconstructable | unresolved | fail closed |
| Survivor `last_identity_decision_id` → `alias_remove` | reconstructable from merge + alias_remove | unresolved | fail closed |
| Historical #575 fixture | still 28/28 merge-only pass | STOP; do not break historical reproduction | fail closed |
| Policy mint | only from current passed proof | refuse | fail closed |
| `split` / `unmerge` | not admitted | STOP | fail closed |

## §4 Files in scope — expected bounded lease

| Action | Path |
| ------ | ---- |
| Modify | `apps/live_control_server/integrations/dungeonmind_kernel/identity_lifecycle_history_conformance_v1.py` |
| Modify | `tests/test_identity_lifecycle_history_conformance_v1.py` |
| Create | `apps/live_control_server/services/cutover_identity_lifecycle_through_alias_remove.py` |
| Create | `scripts/build_cutover_identity_lifecycle_through_alias_remove.py` |
| Create | `tests/test_cutover_identity_lifecycle_through_alias_remove.py` |
| Create | `tests/fixtures/dungeonmind_kernel/eldyrwild_cutover_identity_lifecycle_through_alias_remove_v1.json` |

If current architecture proves the successor can call the extended prover
without a new service/script pair, trim the lease during pre-dispatch design
review rather than carrying dead machinery. Do not modify the locked #575
service, fixture, or canonical revision pins except to keep them reproducing.

If a Kernel identity-decision semantic change is required:

```text
STOP
→ return to stewardship
```

**Bounded discovery exception:** None beyond the lease-trim rule above.

## §5 Explicitly out of scope

```text
src/graph_memory/**
canonical/live World Graph data
Captain / Thrin alias assertion package
the six retired merge-shadow aliases as package rows
reusing the locked #575 28-ID allowlist as current policy
five dual-sense relationship STOPs
DungeonMind Case B / durable adoption
CUTOVER_READY declaration
Docs/Sources/design-agent/**
Docs/Roadmaps/ROADMAP-campaign-supergraph.md
Docs/Design/ARCHITECTURE-campaign-supergraph.md
HANDOFF-cutover-identity-lifecycle-history-after-571.md design rewrite
```

## §6 Implementation contract

```text
Input:
  rev:0c644e56b45bcaac709012206e3e41c2
  historical #575 merge-only fixture still reproducible
  current merge-only diagnostic = 16/28 on that head

Output:
  current lifecycle proof passed, unresolved = []
  source-history policy minted from that proof
  remasured ATTRIBUTE_ASSERTION under that policy
  successor fixture sealing the current proof/policy/remeasurement

Invariant:
  classify only what the current proof reconstructs;
  do not mutate graph truth;
  do not break #575 historical reproduction

Failure behavior:
  unresolved current field → no policy, no ATTRIBUTE_ASSERTION=0 claim
  other decision kind → STOP
  #575 fixture drift → STOP

Trust boundary:
  Verifies: current stored values from durable merge + alias_remove history
  Records/trusts without proving: nothing from the locked #575 ID set
```

Remeasurement procedure:

```text
1. inventory ATTRIBUTE_ASSERTION under LEGACY (empty proven-set) policy
   on rev:0c644e56…
2. run the current lifecycle proof on that same store
3. require proof.passed and unresolved = []
4. require ATTRIBUTE_ASSERTION IDs == proof.element_ids
   (do not assume count 28)
5. policy = source_history_policy_from_identity_lifecycle_proof(proof)
6. remasure v5 with that policy
7. record ATTRIBUTE_ASSERTION, EVIDENCE_PROVENANCE, IDENTITY_HISTORY,
   CONTRIBUTION_HISTORY, relationship inventories
```

Do not treat `EVIDENCE_PROVENANCE = 2` as this slice's success criterion.
That count is already the live-exit fact. This slice authorizes or refuses
`ATTRIBUTE_ASSERTION` classification.

## §7 Evidence required to merge

The successor must prove:

```text
actual canonical input:
  rev:0c644e56b45bcaac709012206e3e41c2
  payload 0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2

merge-only diagnostic on that head (not current authority):
  reconstructable 16/28
  12 unresolved survivor last_identity_decision_id + identity_state

current lifecycle proof:
  passed = true
  unresolved_element_ids = []
  every remaining identity-lifecycle field reconstructable
  alias_remove rows prove merge + later alias_remove, not merge alone

historical reproduction:
  PR #575 fixture still passes under the merge-only contract

policy:
  minted by source_history_policy_from_identity_lifecycle_proof
  refused on the 16/28 merge-only result
  not equal to a hardcoded copy of the #575 ID set unless the current
  proof independently produces that same set

remeasurement:
  ATTRIBUTE_ASSERTION recorded from the regenerated policy
  EVIDENCE_PROVENANCE still 2 unless measurement proves otherwise
  IDENTITY_HISTORY remains 20
  CONTRIBUTION_HISTORY remains 5291
  relationship inventories unchanged

mutation:
  canonical World Graph head unchanged
  identity decisions unchanged
  aliases unchanged
```

Exact verification commands belong in the implementation handback. At minimum:

```bash
uv run pytest -q tests/test_identity_lifecycle_history_conformance_v1.py \
  tests/test_cutover_identity_lifecycle_history_after_571.py \
  tests/test_cutover_identity_lifecycle_through_alias_remove.py
uv run ruff check <leased Python paths>
git diff --check
git diff --name-only <dispatch-base>...HEAD
```

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR/branch/head SHA;
2. exact dispatch/base SHA actually used;
3. confirmation the canonical input is `rev:0c644e56…` / `0640d7ef…`;
4. actual changed paths versus §4, including any lease-trim;
5. merge-only 16/28 diagnostic still observed and not used as policy input;
6. current proof passed / unresolved empty / reconstructable count;
7. confirmation policy mint refuses the 16/28 merge-only result;
8. remasured `ATTRIBUTE_ASSERTION` / `EVIDENCE_PROVENANCE` / history counts;
9. confirmation the #575 historical fixture still reproduces;
10. confirmation canonical World Graph was not mutated;
11. confirmation Captain/Thrin were not packaged;
12. named successor still false until remasurement selects it.

## §9 Acceptance rubric

- [ ] Exactly one independently useful capability from §1 is delivered and proved by §7.
- [ ] Current lifecycle proof passes on `rev:0c644e56…` with zero unresolved rows.
- [ ] Policy is minted from that current proof, not from the locked #575 ID set.
- [ ] `source_history_policy_from_identity_lifecycle_proof` still refuses a partial proof.
- [ ] Historical #575 fixture still reproduces.
- [ ] Canonical World Graph is unchanged.
- [ ] Captain/Thrin package is not implemented.
- [ ] Five relationship STOPs remain.
- [ ] No generic Kernel file is changed unless stewardship authorized a split.
- [ ] Actual changed paths stay inside the reviewed lease.

## Stop conditions

Stop and report instead of expanding when any of these appears:

- preflight drift against `rev:0c644e56b45bcaac709012206e3e41c2`;
- any current lifecycle field remains unresolved after the intended extension;
- `split`, `unmerge`, or another unproven decision kind is required;
- the #575 historical fixture stops reproducing;
- a required generic Kernel change;
- a worker proposes live World Graph mutation;
- a worker proposes classifying from the locked #575 allowlist;
- a worker proposes packaging Captain/Thrin in this PR;
- a worker proposes Case B or `CUTOVER_READY`.

Report:

```text
Stop condition:
Invariant clause affected:
Why current mission cannot absorb it:
Required evidence now missing:
Affected paths/ownership layers:
Proposed successor or re-brief:
State-authority update needed:
```
