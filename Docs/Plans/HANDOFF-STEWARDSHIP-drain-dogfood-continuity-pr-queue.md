# HANDOFF — STEWARDSHIP: resolve #722–#726 and land #726

**Created:** 2026-09-15  
**Revised:** 2026-09-15 after explicit operator direction to finish the open-PR recovery  
**Status:** ACTIVE — stewardship execution mission; do not create another implementation PR  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Canonical path:** `Docs/Plans/HANDOFF-STEWARDSHIP-drain-dogfood-continuity-pr-queue.md`  
**Flow / owner:** `DOGFOOD-CONTINUITY / stewardship`  
**Execution anchor:** `main@e55584844105ae02447f0d75ae132bed7278418a`  
**PR topology:** `recovery-serial` — exactly one front-of-queue PR may be rebased/reviewed/merged at a time  
**PR authorization:** work only the already-open PRs `#722`, `#723`, `#724`, `#725`, `#726`; do not open `#727` or any replacement integration PR  
**Primary finish line:** **PR #726 is merged into real `main`; PRs #722–#725 are no longer ambiguous open work; every required predecessor capability is present on `main`; one fresh pristine current-corpus structural acceptance run is adjudicated from that real integrated state.**

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process:
> [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md).
> This handoff is the queue/topology authority for the accidental #722–#726 fan-out.

---

## §1 Mission and non-negotiable end state

Five open PRs accumulated from one acceptance loop without an explicit decision to
run five concurrent implementation lanes. Resolve that fan-out completely.

The intended causal chain is:

```text
#722  current-corpus structural acceptance harness
  ↓ exposed
#723  admission endpoint-kind eligibility repair
  ↓ exposed
#724  blocked cross-class node-id disambiguation
  ↓ exposed
#725  exact durable object-id continuity
  ↓ exposed
#726  exact durable relationship-id continuity
```

The executor is not done when #726 merely reviews cleanly. The mission ends only at:

```text
real main contains every still-required capability from #722–#726
#722 CLOSED (normally MERGED)
#723 CLOSED (normally MERGED)
#724 CLOSED (normally MERGED)
#725 CLOSED (normally MERGED)
#726 MERGED
no replacement repair/integration PR opened
one fresh pristine post-#726 acceptance run recorded against exact real-main SHA
repository authorities agree on the next single action
```

Expected disposition is **merge all five in order**. A predecessor PR may instead
be closed/superseded only if its exact intended capability is already present on
current `main` and the steward records concrete diff/behavior evidence proving that
merging it would add no required semantics. "It is old", "it conflicts", or "#726
contains related code" are not sufficient reasons to close it.

**#726 is different:** this mission specifically requires its relationship-ID
continuity capability to land. If #726's branch becomes mechanically unsuitable
after rebases, repair the existing #726 branch. Do not replace it with another PR.

---

## §2 Current snapshot — re-verify before each action

At this revision of the handoff:

| Order | PR | Capability | Observed head | GitHub state | Required disposition |
|---:|---:|---|---|---|---|
| 1 | #722 | Current-corpus structural acceptance harness | `bb79a11320cc03624d8468a3097c646bdcddd950` | OPEN / currently non-mergeable against advanced main | rebase, review, **merge unless proven redundant** |
| 2 | #723 | Admission endpoint-kind eligibility | `e7b1447738f6332c9ce0fec3dbaba46d51d00e37` | OPEN / currently non-mergeable | rebase after #722, review, **merge unless proven redundant** |
| 3 | #724 | Blocked cross-class ID disambiguation | `a62065eed4d59897190707f3d5f6ca28ad672486` | OPEN / currently non-mergeable | rebase after #723, review, **merge unless proven redundant** |
| 4 | #725 | Exact durable object-ID continuity | `812d5d6ee2699571fd3c08dc5616725927a8b6f3` | OPEN / currently non-mergeable | rebase after #724, review, **merge unless proven redundant** |
| 5 | #726 | Exact durable relationship-ID continuity | `7293fd6904197678c05b5ffd909634f9eb940d99` | OPEN / currently non-mergeable | rebase after #725, fresh formal review, **MERGE** |

Current process authority already repaired:

- PR topology is now handoff-owned and defaults to serial.
- `#723` and `#724` handoffs are durable on `main` as BLOCKED successors.
- `#725` and `#726` handoffs are BLOCKED while predecessors remain unresolved.
- opening the assigned PR without asking does not authorize another successor PR.
- a prior synthetic/cherry-picked combined head completed 44/44 sessions; that is
  useful diagnostic evidence but is not final integration authority.

Repository/GitHub truth beats this snapshot if a head moves. Re-anchor before every
rebase, review, close, or merge.

---

## §3 Queue law for this recovery

Exactly one queue item is active at a time.

```text
front PR
  → activate/reconcile its handoff authority
  → rebase existing branch onto exact current main
  → inspect resulting cumulative diff
  → run focused owning-boundary evidence
  → formal review against exact rebased head
  → fix findings in the SAME PR
  → merge or, for #722–#725 only, prove fully redundant and close
  → synchronize authority
  → re-anchor
  → advance one slot
```

While this mission is active:

```text
NO #727
NO replacement "integration" PR
NO successor branch for a newly discovered defect
NO synthetic combined head promoted as repository truth
NO chain-dispatch before predecessor merge/close + state sync + re-anchor
NO paid 44-session rerun between already-known repairs
```

A newly discovered defect is recorded as evidence / a possible future BLOCKED
handoff. It does not create an implementation lane until this recovery is complete.

---

## §4 Rebase and authority-conflict rules

The old PR branches predate the process-authority repair now on `main`, so handoff
files may conflict during rebase. That conflict is expected and must not resurrect
stale authority.

For every queue PR:

1. preserve the **current canonical handoff on `main`** as authority;
2. preserve the PR's executable implementation and report evidence when still true;
3. do not let an old branch copy change `BLOCKED`/`ACTIVE`, topology, activation gate,
   predecessor state, or write-lease ownership back to stale values;
4. after predecessor resolution, the steward performs the narrow activation sync on
   `main` before the implementation branch is treated as active;
5. rebase the existing branch onto that exact activated `main`;
6. if code conflicts with already-merged predecessor behavior, resolve only inside
   the current handoff invariant/write lease; otherwise STOP for steward judgment.

An old review does not approve a rebased head. Every rebased implementation head
gets a fresh formal judgment.

---

## §5 Execute the queue

### A. Resolve #722 — land the harness first

Canonical handoff:
`Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md`

#722 owns the fail-closed harness, not a claim that production already passes.
Production seams remain read-only.

Required actions:

```text
rebase #722 onto exact current main
verify its cumulative diff is still only harness + tests + compact report
run its deterministic harness tests / lint / diff checks
formally review exact rebased head
merge #722 when merge-ready
record merge SHA + review-cycle count
sync #722 handoff/report authority truthfully
re-anchor main
```

It is valid for #722 to merge while structural acceptance is still HOLD. The harness
exists to expose production failures; the later repairs answer those failures.

Do not run the final paid/full 44-session acceptance here.

### B. Resolve #723 — endpoint-kind eligibility

Canonical handoff:
`Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-admission-endpoint-kind-eligibility-v1.md`

Activation gate: #722 resolved and state synced.

Required actions:

```text
activate #723 handoff on main
rebase existing #723 branch onto current main
preserve exact immutable candidate digest behavior
prove mapped-but-inexpressible endpoints receive sealed endpoint_kind_not_admitted disposition
prove legal edges remain confirmable
run handoff evidence
formal review exact rebased head
merge #723 unless exact capability is already proven present on main
sync / re-anchor
```

### C. Resolve #724 — blocked cross-class node-ID disambiguation

Canonical handoff:
`Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-blocked-cross-class-id-disambiguation-v1.md`

Activation gate: #723 resolved and state synced.

Required invariant:

```text
blocked cross-class exact-label collision
  → both identities remain distinct
  → kept node IDs are unique
  → deterministic survivor keeps original ID
  → other blocked member receives deterministic disambiguated ID
  → true same-class duplicate integrity remains fail-closed
```

Rebase, run focused evidence, formally review, merge unless already proven redundant,
sync, re-anchor.

### D. Resolve #725 — exact durable object-ID continuity

Canonical handoff:
`Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-exact-id-identity-continuity-v1.md`

Activation gate: #724 resolved and state synced.

Required invariant:

```text
candidate/proposed object ID equals existing parent same-kind durable object ID
  → resolved_existing before label/alias ambiguity
wrong-kind exact occupied ID
  → does not force confirm
label drift alone
  → does not invent CREATE_NEW into occupied durable ID
```

Rebase onto real `main` containing resolved #722–#724, run focused evidence, formally
review, merge unless already proven redundant, sync, re-anchor.

The #725 merge is the hard predecessor gate for #726.

### E. Land #726 — exact durable relationship-ID continuity

Canonical handoff:
`Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-exact-edge-id-continuity-v1.md`

Activation gate: #725 **merged/resolved on real main**, authority synced, and #726
handoff explicitly ACTIVE again.

Historical #726 findings remain relevant:

- Cycle 1 caught false collision for admitted reverse-endpoint predicates.
- The fix normalized candidate endpoints through the same admitted write mapping.
- Deterministic regressions now cover `belongs_to → dnd5e:owns` at classifier and
  identity-gate boundaries.
- Historical synthetic full-corpus run reached 44/44, but did not establish real-main
  integration acceptance.

Required #726 rebase rule:

```text
rebase existing #726 onto post-#725 current main
#725 object-ID code must disappear from #726's incremental diff
#726 incremental diff must retain relationship-context/classification/gate behavior
canonical main handoff topology/status wins any documentation conflict
```

Then run the exact #726 focused evidence, including direct-predicate and reverse
endpoint cases. Inspect the full cumulative diff against current main, not merely the
last fix commit.

Issue the next formal Review Cycle against that exact rebased head. If findings
remain, fix them in #726 and repeat review cycles until merge-ready.

**Then merge #726. Do not stop at APPROVE/HOLD-cleared.** Record:

```text
accepted #726 head SHA
final review-cycle number
merge SHA
focused evidence provenance
actual changed paths
confirmation that #725 is not duplicated in the final #726 diff
```

After merge, synchronize #726 completion and re-anchor exact `main`.

---

## §6 What "resolved" means for #722–#725

A predecessor PR is resolved only by one of these two dispositions:

### MERGED — normal/expected

Its capability is still required, focused evidence passes on its rebased head, review
accepts it, and the PR merges into `main`.

### CLOSED AS REDUNDANT — exceptional

Allowed only when all are true:

```text
current main already contains the exact capability
PR diff after rebase is empty or only stale transport/authority metadata
focused owning-boundary evidence passes on main
closure comment identifies exact main SHA and where the capability landed
no later PR depends on unmerged commits unique to the closed branch
```

Do not close a PR merely to reduce the count. Do not call a merge conflict
"superseded." Preserve causal history truthfully.

By the time #726 merges, #722–#725 must all be CLOSED by one of these dispositions.
There must be no ambiguous "parked for later" item left from this fan-out.

---

## §7 Final post-#726 structural acceptance

Only after #726 is merged and #722–#725 are resolved:

```text
re-anchor exact real main
confirm main contains every required capability
prepare one newly pristine dmb_current_corpus_acceptance_v1 DB at the canonical loopback target
run harness --preflight
run one fresh full harness --execute
process frozen corpus exactly once in chronological order
no resume / skip / repair / candidate substitution
```

Bind the report to:

```text
exact real-main SHA
manifest count + digest
production model-policy digest + resolved model
runtime/database/world identity
D0 genesis revision
terminal World head or first STOP head
model-call count
first failing boundary if any
```

### PASS outcome

Record exactly:

```text
STRUCTURAL CURRENT-CORPUS ACCEPTANCE = PASS
SEMANTIC MODEL SELECTION = HOLD
SEMANTIC TRUTHFULNESS / PRECISION / RECALL = NOT ESTABLISHED
```

Perform guarded state-authority sync and mark this stewardship handoff COMPLETE.
The next semantic-truthfulness work may then be designed from a clean single `main`.

### STOP outcome

A truthful STOP does **not** reopen the five-PR fan-out.

Record first failure and preserve artifacts. A new repair may be designed as a
BLOCKED handoff on `main`, but do not open its implementation PR until this recovery
is closed, state authority is coherent, and the steward explicitly activates one
next serial lane.

---

## §8 Evidence ledger required during execution

Maintain this table in this handoff or the owning reports as the queue advances:

| PR | Rebased head | Formal review cycle | Focused evidence | Resolution | Merge/close evidence |
|---:|---|---:|---|---|---|
| #722 | `<sha>` | `<N>` | `<result>` | MERGED / REDUNDANT | `<merge SHA or closure proof>` |
| #723 | `<sha>` | `<N>` | `<result>` | MERGED / REDUNDANT | `<merge SHA or closure proof>` |
| #724 | `<sha>` | `<N>` | `<result>` | MERGED / REDUNDANT | `<merge SHA or closure proof>` |
| #725 | `<sha>` | `<N>` | `<result>` | MERGED / REDUNDANT | `<merge SHA or closure proof>` |
| #726 | `<sha>` | `<N>` | `<result>` | **MERGED** | `<merge SHA>` |

At every queue transition also record:

```text
current main SHA
open PRs among #722–#726
front handoff ACTIVE
later handoffs BLOCKED
no #727 / replacement PR exists
state-authority sync complete
```

---

## §9 Stop conditions

Stop for steward judgment, but do not open another implementation PR, if:

- rebasing changes a queue PR's mission/invariant materially;
- a queue PR requires a path outside its canonical handoff lease;
- a supposedly redundant PR still owns executable semantics absent from main;
- #726 after #725 rebase still contains duplicate #725 implementation diff;
- integration requires ontology/model-policy/architecture redesign;
- state authorities disagree after a merge/closure;
- final acceptance exposes a new production defect.

Integration conflicts that are purely the expected consequence of serially landing
these already-known capabilities are fixed in the current PR when they remain inside
that PR's invariant and write lease.

---

## §10 Completion rubric

This handoff is COMPLETE only when all are true:

- [ ] no new implementation PR was opened during recovery;
- [ ] #722 is CLOSED as MERGED or rigorously proven redundant;
- [ ] #723 is CLOSED as MERGED or rigorously proven redundant;
- [ ] #724 is CLOSED as MERGED or rigorously proven redundant;
- [ ] #725 is CLOSED as MERGED or rigorously proven redundant;
- [ ] **#726 is MERGED into real main**;
- [ ] every required capability from the causal chain is present on real main;
- [ ] each rebased non-empty PR received a formal review on its exact integration head;
- [ ] #726's final diff does not duplicate #725;
- [ ] one fresh pristine full structural acceptance ran after #726 merge;
- [ ] final PASS or first STOP is bound to exact real-main authority;
- [ ] synthetic 44/44 evidence remains diagnostic history only;
- [ ] no #722–#726 PR remains ambiguously open/parked;
- [ ] repository state authorities agree on the next single action.
