# Steward Cycle — Design, Dispatch, Review, and Re-anchor One Slice

**Status:** ACTIVE PROCESS REFERENCE  
**Use for:** a design/review steward selecting and carrying one implementation capability through merge and state synchronization.  
**Foundational law:** [`AGENTS.md`](../../AGENTS.md)  
**External PR mechanics:** [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md)  
**Slice template:** [`.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md`](../../.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md)

This document owns **steward judgment**: what to read, how to decompose work, when parallel lanes are safe, what belongs in one handoff, how to review findings, and when the next slice may be dispatched.

It does not redefine repository law from `AGENTS.md`, provide the exact GitHub command runbook, or carry facts that belong in one slice's HANDOFF.

## Cycle

```text
RE-ANCHOR
  ↓
DECOMPOSE
  ↓
ALLOCATE LANES
  ↓
DESIGN ONE SLICE
  ↓
DISPATCH
  ↓
REVIEW CYCLE 1..N
  ↺ finding-led fixes
  ↓
MERGE
  ↓
ATOMIC STATE-AUTHORITY SYNC
  ↓
RE-ANCHOR / SELECT NEXT
```

## 1. Re-anchor

Before selecting work, establish current state from repository authority rather than chat history.

Read only the sources needed for the current workstream, in precedence order:

1. architecture/decision/contracts that own the behavior;
2. active roadmap/tracker/plan/checklist/status documents that actually claim current sequence or progress;
3. exact `main` and predecessor state;
4. current open PRs/active handoffs/parallel lanes that can collide;
5. attached/project-source context only after mapping it to repository authority;
6. historical handoffs/reports only as evidence.

Then state an explicit hypothesis:

```text
main is at <sha>
<predecessor> is actually true
<current state authorities> agree / disagree
<active lane A> owns <writes/runtime state>
<active lane B> owns <writes/runtime state>
<next candidate capabilities> remain false
```

If repository authorities disagree with each other or `main`, repair that contradiction before choosing the next dependent slice.

Detailed re-anchor discipline lives in `.cursor/rules/anchor.mdc`.

## 2. Decompose candidate capabilities

List candidate **outcomes**, not files or layers.

Use a compact worksheet:

| Candidate outcome | Independently useful? | Public/durable contract? | Failure model changes? | Independently testable/revertible? | Owning boundary | Decision |
|---|---:|---:|---:|---:|---|---|
| `<outcome>` | Yes/No | Yes/No | Yes/No | Yes/No | `<boundary>` | Keep / Split / Reconnaissance |

Before grouping outcomes, inventory the affected observable paths. Depending on the work, include:

- success and ordinary miss;
- dependency unavailable/integrity failure;
- stale or superseded state;
- retry/replay/idempotency;
- save/reload/migration;
- identity/alias/rebind behavior;
- concurrent/interleaved operations;
- operator/dogfood paths.

Group outcomes only when one merge-ready invariant can govern every claimed path. Split when a second outcome is independently useful, independently revertible, independently consumable, or creates another public/durable contract.

Unresolved architecture is reconnaissance/design work, not permission for an implementation agent to guess.

## 3. Allocate lanes before dispatch

For each candidate slice, write down:

```text
flow/workstream
branch
worktree or equivalent isolated checkout
base revision
expected §4 write lease
runtime/state resources that can collide
predecessor/dependency
```

Compare active lanes before dispatch.

### Safe parallelism

Two lanes may proceed when:

- their expected write leases do not overlap;
- neither depends on the other's unmerged result;
- shared runtime/state resources are isolated, namespaced, copied safely, or intentionally serialized;
- one merge cannot invalidate the other's invariant without detection.

### Collision response

If two lanes need the same write path or unsafe shared state, choose explicitly:

1. split a seam so ownership becomes disjoint;
2. serialize the slices;
3. transfer the contested path to one lane and remove it from the other;
4. re-brief both slices if the dependency changed.

Do not let merge conflicts make this decision after both agents have already done the work.

Central routers, registries, lockfiles, root configuration, active state-authority docs, and generated schemas deserve extra scrutiny even when there is no current overlap.

## 4. Dispatch-readiness gate

Do not author the final handoff until these answers are concrete:

- **Outcome:** What one independently useful capability exists afterward?
- **Invariant:** What one property governs every changed layer and observable path?
- **Remaining falsehood:** What named successor remains intentionally unimplemented?
- **Authority:** What exact base, predecessor, schema/fixture, and parent design govern the slice?
- **Observable paths:** Which success/failure/stale/retry/persistence/interleaving paths change?
- **Second-contract check:** Does the work introduce another durable format, identifier, API, event, or operator workflow?
- **Write lease:** Can every expected changed path be named, with only a precisely bounded discovery exception if needed?
- **Parallel ownership:** Does §4 overlap another active lane? What runtime/state resources are shared?
- **Contract semantics:** Are applicable identity, state/fallback, persistence/replay, predecessor mapping, and commit-point questions resolved?
- **Proof:** Does each material invariant clause have evidence at its owning boundary?
- **Stop conditions:** Does the worker know when to stop rather than absorb adjacent work?
- **State-sync set:** Which mutable workstream authorities are expected to change after merge?

Any unresolved answer means split, reconnaissance, or design resolution—not dispatch.

## 5. Write the HANDOFF

Copy the canonical template and fill §1–§9. The handoff is a **slice payload**, not a tutorial.

It should contain only what changes from slice to slice:

- mission + merge-ready invariant + pre-dispatch critique;
- exact authority/base/predecessor/successor and state-sync set;
- affected observable paths and adversarial sequences;
- §4 write lease;
- explicit exclusions/collision boundaries;
- only the contract matrices that apply;
- evidence ledger and exact commands/manual scenarios;
- required review handback;
- slice-specific acceptance rubric and stop conditions.

Do not copy universal vocabulary, flow definitions, nano-commit policy, review-cycle law, atomic-sync law, or the `review_external_pr.py` manual into each handoff. Those already have owners.

## 6. Dispatch

The worker receives the checked-in handoff and works only inside its authority.

At dispatch, the steward should know:

```text
exact handoff path
exact base revision
branch / checkout identity
flow/workstream
write lease
parallel lanes and collision hotspots
runtime/state ownership
named successor
```

A worker discovering a new required path/contract/observable workflow stops and reports the scope consequence. The steward decides whether bounded discovery covers it or the slice must be re-briefed/split.

## 7. Review by invariant, not file order

Review one exact PR head at a time.

A formal judgment against one distinct head SHA is one **Review Cycle**. Count cycles; do not cap them.

For each cycle:

1. identify exact PR/branch/head SHA and handoff;
2. verify changed paths against §4 before interpreting behavior;
3. restate mission/invariant/named successor;
4. trace every governed observable path and adversarial sequence;
5. inspect for hidden second contracts or scope growth;
6. verify applicable state/identity/persistence/predecessor semantics;
7. rerun §7 evidence at the owning boundary;
8. compare baseline/head when a required gate already fails;
9. inspect nano commits as the implementation/fix story;
10. issue every material finding needed to reach merge, not merely the first one noticed.

Each finding states:

```text
failure or missing proof
affected observable path
owning boundary
specific fix or evidence required
```

### Review provenance

Separate:

- author-local result;
- independently rerun result;
- CI result;
- manual/dogfood observation;
- operator waiver.

Do not collapse them into "tests green."

## 8. Re-review from the finding ledger

After fixes, start with prior findings:

| Prior finding | Claimed fix | Owning files/tests | Closed? | New consequence? |
|---|---|---|---:|---|
| `<finding>` | `<claim>` | `<paths/proof>` | Yes/No | `<result>` |

Check the new delta first, then re-evaluate the **complete invariant**. A fix is closed only when the failure sequence is gone, not when the reviewer sees the requested line change.

New consequences become new findings/evidence requirements. The next formal judgment against the changed head increments the review-cycle count once.

## 9. Polish before approval

When all findings appear closed, make one deliberate polish pass before final approval:

- contradictory terminology or ownership;
- duplicated concepts that now have a canonical owner;
- stale comments/temporary compatibility language;
- names that encode old architecture;
- avoidable complexity introduced during fix loops;
- missing deletion of replacement paths;
- unclear failure/error wording;
- test names/evidence that no longer describe the final invariant.

Polish must remain inside the slice. A nice adjacent product improvement is still a successor.

## 10. Merge and close the cycle

After approval, merge using the external-agent runbook or the appropriate repo tool.

Then perform the handoff's **state-authority sync set** as one guarded transaction. Prefer one commit/small PR. If tooling writes files sequentially, do not dispatch a dependent slice or call the cycle closed while the set is partial.

Re-read:

- exact `main` head;
- every intended state authority;
- completion/review-cycle record;
- next action.

Architecture/contracts change only when their claims changed.

## 11. Learn, then select the next slice

Review-cycle counts are telemetry, not a target.

After close, ask:

- Which finding classes repeated?
- Was the failure visible during pre-dispatch critique?
- Did §7 test the wrong boundary?
- Did parallel ownership need human intervention?
- Did the handoff carry universal text that belongs upstream?
- Did the reviewer repeatedly copy or reconstruct something a tool should supply?

General lessons move upward only when they generalize:

```text
slice-specific → next handoff
workstream-specific → plan/checklist/decision
repo-wide invariant → AGENTS/rule
mechanical repetition → script/tool
```

Then re-anchor before dispatching the next dependent slice.

## Fast steward test

A healthy process lets a fresh steward answer these without chat history:

1. What is true on `main`?
2. What one capability is next?
3. What remains false afterward?
4. Which paths/state does its lane own?
5. Which other lanes can proceed safely?
6. What exact evidence proves merge readiness?
7. What would force a split?
8. How many review cycles did the predecessor need, and what did they teach us?
9. Which state-authority documents must change after merge?

If the answers require reverse-engineering old PR descriptions or copying a giant process prompt into the handoff, the process layer is carrying the wrong responsibility.
