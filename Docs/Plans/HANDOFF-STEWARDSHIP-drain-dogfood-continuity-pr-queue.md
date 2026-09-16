# HANDOFF — STEWARDSHIP: drain DOGFOOD-CONTINUITY PR queue

**Created:** 2026-09-15  
**Status:** ACTIVE — stewardship recovery mission, not an implementation PR  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Canonical path:** `Docs/Plans/HANDOFF-STEWARDSHIP-drain-dogfood-continuity-pr-queue.md`  
**Flow / owner:** `DOGFOOD-CONTINUITY / stewardship`  
**Starting integration anchor:** `main@dcd28bbda295beaca1010e81f3da9c92ec835707`  
**PR topology:** `recovery-serial` — one active merge candidate at a time; no new implementation PRs until the existing queue is drained and post-queue acceptance is adjudicated  
**One-line mission:** convert the accidental #722–#726 fan-out into a deliberate serial queue, integrate each already-built capability against real `main`, run one fresh pristine structural acceptance from that actual integrated state, and stop before opening any successor PR.

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process:
> [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). The process law
> was tightened during this recovery so PR topology is now handoff authority and
> `serial` is the default.

---

## §1 Finish line and recovery invariant

This mission exists because one acceptance effort accumulated five open PRs without
an explicit decision to run five concurrent lanes.

The open PRs are not five independent product capabilities. They are one acceptance
harness plus four production repairs discovered serially by running that harness:

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

The recovery invariant is:

> **At any point in this mission exactly one existing implementation PR is the active merge candidate. Every later PR is parked. The active PR is rebased/updated against actual current `main`, formally reviewed on that exact head, merged or deliberately closed, and state authority is synchronized before the next parked handoff becomes ACTIVE. No new implementation PR is opened while the queue remains. Synthetic/cherry-picked combined heads are diagnostic evidence only, never integration authority.**

The user preference **“do not ask before opening the PR; just do it”** remains valid
and is now interpreted narrowly:

```text
ACTIVE code handoff explicitly authorizes one assigned PR
  → worker opens/updates that PR without asking

worker discovers another defect / successor
  → worker does not open another PR
  → steward owns whether that future work is serial, stacked, or independent
```

For this recovery, the answer is already decided: **serial**.

---

## §2 Current truth at recovery handoff

Re-anchor every item before acting; repository/GitHub truth wins if a head moved.
The snapshot that triggered this recovery was:

| Queue | PR | Capability | Observed head | Recovery disposition |
|---:|---:|---|---|---|
| 1 | #722 | Fresh current-corpus admission acceptance harness | `bb79a11320cc03624d8468a3097c646bdcddd950` | **ACTIVE merge candidate first** |
| 2 | #723 | Endpoint-kind eligibility at Candidate Graph Admission | `e7b1447738f6332c9ce0fec3dbaba46d51d00e37` | PARKED; handoff now durable BLOCKED on `main` |
| 3 | #724 | Blocked cross-class ID disambiguation | `a62065eed4d59897190707f3d5f6ca28ad672486` | PARKED; handoff now durable BLOCKED on `main` |
| 4 | #725 | Exact durable object-ID continuity | `812d5d6ee2699571fd3c08dc5616725927a8b6f3` | PARKED; handoff changed ACTIVE → BLOCKED |
| 5 | #726 | Exact durable relationship-ID continuity | `7293fd6904197678c05b5ffd909634f9eb940d99` | PARKED; handoff changed ACTIVE → BLOCKED |

Process/authority repair already completed before this handoff was landed:

- `AGENTS.md` now makes PR topology handoff authority and defaults to serial;
- `Docs/Process/STEWARD-CYCLE.md` requires topology/open-PR reconciliation before dispatch;
- the code-agent HANDOFF template requires `PR topology` + explicit `PR authorization`;
- the external-agent rule/runbook distinguish opening the assigned PR from spawning another PR;
- design-agent process mirrors were refreshed;
- #723 and #724 handoffs were landed on `main` as BLOCKED parked successors;
- #725 and #726 handoffs were changed to BLOCKED parked successors.

### Existing synthetic dogfood evidence

A combined/cherry-picked acceptance head containing #723–#726 previously completed
44/44 sessions with no STOP. Preserve that as strong diagnostic evidence that the
known repair set is coherent together.

It is **not** the final structural acceptance authority because those changes were
not yet integrated through real `main` history. Do not throw the evidence away;
do not promote it into a merge claim either.

---

## §3 Queue freeze — effective immediately

Until §5 completes:

```text
NO new implementation PRs
NO #727 repair PR
NO successor branch created merely because a known/novel STOP is observed
NO paid full-corpus acceptance between each already-known repair
NO treating a synthetic combined head as equivalent to main
NO chain-dispatch after merge without state sync + re-anchor
```

Existing PRs #723–#726 may remain open on GitHub while parked. Their existence is
transport state, not authorization for concurrent implementation work.

Only the front-of-queue handoff is ACTIVE. Later handoffs remain BLOCKED and hold
no write lease.

If a parked PR receives incidental bot/CI updates, do not treat that as lane
activation.

---

## §4 Per-PR drain protocol

Apply this exact protocol to each queue item before moving to the next:

```text
1. re-anchor exact current main + exact PR head
2. confirm this PR is the front-of-queue handoff
3. activate its handoff on main if it was BLOCKED
4. rebase/update the existing PR onto exact current main
5. inspect cumulative diff after rebase
6. if diff is empty because predecessors absorbed it:
     close/supersede truthfully; do not manufacture a merge
7. otherwise run the handoff's focused owning-boundary evidence
8. issue a formal review judgment against the exact rebased head
9. finding-led fixes stay in this same PR when they belong to its invariant/lease
10. if a genuinely separate next defect is discovered:
      record it as a steward handback / possible BLOCKED future handoff
      DO NOT open another PR
11. when merge-ready, merge this PR
12. perform its backward-looking state-authority sync
13. mark/record completion truthfully
14. re-anchor actual main
15. only then activate the next parked handoff
```

A rebase itself creates a new exact review head. Prior reviews remain historical
evidence but do not approve the rebased integration head automatically.

### What counts as an integration fix

A rebase may expose a conflict because an earlier queue item changed the same seam.
Resolve that conflict inside the current PR only when the resolution preserves the
current handoff invariant and remains inside its write lease.

If integration requires redesigning another capability or changing a second durable
contract, stop and return to stewardship. Still do **not** open another PR.

---

## §5 Required drain order

### Phase A — #722 acceptance harness

**Current role:** only ACTIVE merge candidate at recovery start.

Review #722 as the harness capability it was designed to be:

```text
fail-closed --preflight / --execute runner
exact current-corpus manifest freeze
pristine isolated authority
strict chronological one-pass processing
exact candidate forwarding
first-failure STOP
revision/head chain verification
no skip / resume / repair / model override
```

Production seams remain read-only in this PR.

The harness does **not** need the later production repairs already merged in order
to be a valid harness. It may merge with structural acceptance still HOLD. Its job
is to expose truthfully whether current production code passes.

If #722 review reveals a harness defect, fix #722. If it reveals another production
defect, record it but do not open a repair PR during queue recovery.

After #722 merges and sync completes, activate #723.

### Phase B — #723 admission endpoint-kind eligibility

Use:
`Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-admission-endpoint-kind-eligibility-v1.md`

Before review:

- change handoff BLOCKED → ACTIVE on `main` after re-anchor;
- rebase existing #723 onto actual current `main`;
- rerun its focused Candidate Graph Admission evidence;
- formally review the new exact head.

After merge/sync, activate #724.

### Phase C — #724 blocked cross-class ID disambiguation

Use:
`Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-blocked-cross-class-id-disambiguation-v1.md`

Rebase onto actual `main` containing #722 + #723, review its exact identity-resolution
invariant, merge/sync, then activate #725.

### Phase D — #725 exact durable object-ID continuity

Use:
`Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-exact-id-identity-continuity-v1.md`

Rebase onto actual `main` containing #722–#724. Preserve same-kind exact-ID precedence
and wrong-kind occupied-ID fail-closed behavior. Review exact rebased head, merge,
sync, then activate #726.

### Phase E — #726 exact durable relationship-ID continuity

Use:
`Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-exact-edge-id-continuity-v1.md`

#726 currently contains historical stacked ancestry from #725. After #725 is actually
merged:

- rebase #726 onto current `main`;
- verify the cumulative diff contains only the relationship-continuity slice and
  does not reintroduce #725 as duplicate diff;
- preserve direct-predicate and reverse-endpoint (`belongs_to → dnd5e:owns`)
  regressions;
- formally review the exact rebased head.

Prior #726 Review Cycles remain useful finding history. The rebased integration head
still requires a fresh formal judgment.

Merge/sync #726. The implementation queue is then empty.

### Phase F — one pristine full structural acceptance from actual main

Only after #722–#726 are integrated through real `main`:

1. re-anchor exact `main` and record SHA;
2. recreate/migrate the pristine acceptance DB using the canonical harness contract;
3. run `--preflight`;
4. run one fresh full `--execute` over the frozen current corpus;
5. bind the acceptance report to the exact real-main SHA, manifest digest, production
   model policy digest/resolved model, runtime identity, and terminal World head.

Do **not** resume a historical run. Do not reuse the synthetic combined run as the
final witness.

#### If PASS

```text
STRUCTURAL CURRENT-CORPUS ACCEPTANCE = PASS
SEMANTIC MODEL SELECTION = HOLD
```

Update the acceptance REPORT/state authority by guarded steward sync on `main`.
Mark this recovery handoff COMPLETE. Re-anchor before designing/activating the named
semantic-truthfulness successor.

#### If STOP

Preserve the first failing boundary exactly. Do not open a PR from the runner or the
code agent.

The steward may author a **new BLOCKED successor handoff on `main`** for the newly
proven defect. Once this recovery mission is closed and repository authority is
coherent, re-anchor and decide whether that successor becomes the next single serial
implementation PR.

The queue recovery is still successful if it leaves one truthful new STOP rather
than five floating repair branches.

---

## §6 Why the old process allowed this

The old law correctly constrained write leases and parallel collisions, but it did
not make **PR topology itself** an explicit handoff-owned decision.

That omission interacted badly with a reasonable user preference:

> “Don’t ask whether to open the PR. The handoff already authorized the work.”

Without a topology field, an agent could overgeneralize that preference from:

```text
open the assigned PR without asking
```

to:

```text
when dogfood exposes the next repair, open that PR too
```

The permanent correction is now upstream:

```text
Steward decides topology
  ↓
HANDOFF records topology + exact PR authorization
  ↓
CODE worker executes assigned PR without ceremony
  ↓
new successor finding returns to steward
```

Default topology is serial. Stacked and parallel-independent work are explicit
exceptions, not emergent facts inferred from how many branches happen to exist.

---

## §7 Recovery evidence / stewardship checks

At every transition, record:

```text
current main SHA
front-of-queue PR + exact head
front handoff ACTIVE
later handoffs BLOCKED
observed open PR list
no new PR created
focused evidence result
formal review cycle / disposition
merge SHA or truthful close reason
state-authority sync completion
next activation decision
```

Before Phase F, the expected integrated production/harness ancestry is:

```text
main
  contains #722 harness
  contains #723 admission eligibility
  contains #724 blocked cross-class disambiguation
  contains #725 exact object-id continuity
  contains #726 exact relationship-id continuity
```

Do not infer this from PR titles. Verify actual merged commits/diffs and exact current
behavior.

---

## §8 Stop conditions

Stop the drain and return to stewardship if:

- a queue PR's invariant is no longer valid after rebasing onto current `main`;
- resolving a rebase requires a second independently useful contract;
- a queue PR needs files outside its handoff lease;
- the order #722 → #723 → #724 → #725 → #726 is disproven by an actual dependency;
- an already-merged predecessor makes a queue PR empty or obsolete;
- a new production failure requires architecture/ontology/model-policy changes;
- anyone proposes opening another implementation PR before this queue is drained;
- state authorities disagree after a merge.

An empty/obsolete PR is not a failure: close/supersede it truthfully and continue.

---

## §9 Completion rubric

This stewardship recovery is complete only when:

- [ ] no implementation PR beyond #722–#726 was opened during recovery;
- [ ] #722–#726 were each reviewed against actual integration ancestry, then merged or truthfully closed/superseded in declared order;
- [ ] at most one queue handoff was ACTIVE at a time;
- [ ] later queue handoffs remained BLOCKED until predecessor merge + sync + re-anchor;
- [ ] #726 did not duplicate #725 after final rebase;
- [ ] one fresh pristine full structural acceptance ran from actual post-queue `main`;
- [ ] final PASS or first STOP is bound to exact real-main authority;
- [ ] synthetic combined dogfood evidence is preserved as diagnostic history, not mislabeled as integration proof;
- [ ] process-law/template changes remain durable and mirrored for future design/code agents;
- [ ] repository state authorities agree on the next single action.
