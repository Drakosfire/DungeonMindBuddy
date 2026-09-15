# Steward Cycle — Design, Dispatch, Review, and Re-anchor One Slice

**Status:** ACTIVE PROCESS REFERENCE  
**Use for:** a design/review steward selecting and carrying one implementation capability through merge and state synchronization.  
**Foundational law:** [`AGENTS.md`](../../AGENTS.md)  
**External PR mechanics:** [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md)  
**Slice template:** [`.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md`](../../.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md)

This document owns **steward judgment**: what to read, how to decompose work, when parallel lanes are safe, what belongs in one handoff, how to make that handoff durable, how to activate/dispatch it, how to review findings, and when the next slice may be dispatched.

It does not redefine repository law from `AGENTS.md`, provide the exact GitHub command runbook, or carry facts that belong in one slice's HANDOFF.

## Cycle

```text
RE-ANCHOR
  ↓
DECOMPOSE
  ↓
DESIGN ONE SLICE
  ↓
LAND HANDOFF ON MAIN
  ↓
BLOCKED? ── yes → wait for gate → RE-ANCHOR / ACTIVATE
  ↓ no / activated
ALLOCATE IMPLEMENTATION LANE
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

A checked-in `BLOCKED` handoff is a durable design artifact, not an implementation lane. Its §4 paths are not leased until the handoff becomes `ACTIVE`.

## 1. Re-anchor

Before selecting work, establish current state from repository authority rather than chat history.

Read only the sources needed for the current workstream, in precedence order:

1. architecture/decision/contracts that own the behavior;
2. active roadmap/tracker/plan/checklist/status documents that actually claim current sequence or progress;
3. exact `main` and predecessor state;
4. current open PRs/ACTIVE handoffs/parallel lanes that can collide;
5. checked-in BLOCKED handoffs that may become future successors but hold no lease yet;
6. attached/project-source context only after mapping it to repository authority;
7. historical handoffs/reports only as evidence.

Then state an explicit hypothesis:

```text
main is at <sha>
<predecessor> is actually true
<current state authorities> agree / disagree
<active lane A> owns <writes/runtime state>
<active lane B> owns <writes/runtime state>
<blocked successor C> awaits <activation gate>
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

## 3. Plan lane allocation before dispatch

Before the handoff is active, plan the likely implementation lane without creating it. Write down:

```text
flow/workstream
candidate branch name
candidate worktree/equivalent isolation
expected §4 write lease
runtime/state resources that can collide
predecessor/dependency
activation gate if any
```

Do not create/reserve an implementation lane merely because a BLOCKED handoff exists. Actual lane allocation occurs only after the handoff is ACTIVE.

### Safe parallelism

Two active lanes may proceed when:

- their expected write leases do not overlap;
- neither depends on the other's unmerged result;
- shared runtime/state resources are isolated, namespaced, copied safely, or intentionally serialized;
- one merge cannot invalidate the other's invariant without detection.

BLOCKED handoffs are inspected as future sequencing/design context, not as lease owners.

### Collision response

If two active lanes need the same write path or unsafe shared state, choose explicitly:

1. split a seam so ownership becomes disjoint;
2. serialize the slices;
3. transfer the contested path to one lane and remove it from the other;
4. re-brief both slices if the dependency changed.

Do not let merge conflicts make this decision after both agents have already done the work.

Central routers, registries, lockfiles, root configuration, active state-authority docs, and generated schemas deserve extra scrutiny even when there is no current overlap.

### Mechanical preflight

After the candidate HANDOFF is checked in, use the read-only preflight helper to replace manual copy/paste reconciliation:

```bash
uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-<FLOW>-<slug>.md
```

When reviewing an open PR, optionally include explicit review-cycle metadata:

```bash
uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-<FLOW>-<slug>.md \
  --pr <N>
```

Use `--local-only` when GitHub discovery is intentionally unavailable. The JSON snapshot reports candidate write lease, local worktrees, active top-level handoffs, open PR path overlap when available, base relation, declared runtime/state ownership, and explicitly labelled review-cycle judgments.

`pass` means no observed mechanical conflict. `warn` means the steward still has an incomplete or changed fact to judge (for example `main` advanced or GitHub discovery was unavailable). `block` means the candidate is not ACTIVE, has a concrete write-lease overlap, or has an invalid/empty candidate lease.

The command never decides whether an activation gate is semantically satisfied, whether a base change invalidates the slice, transfers ownership, authors a handoff, or mutates Git/GitHub. A clean snapshot is evidence for dispatch readiness, not a substitute for the steward's invariant/dependency judgment.

## 4. Handoff-readiness and activation gate

Author the handoff when the **design contract** is concrete. Do not confuse unresolved activation facts with unresolved design.

Before a handoff may become `ACTIVE`, these answers must be concrete:

- **Outcome:** What one independently useful capability exists afterward?
- **Invariant:** What one property governs every changed layer and observable path?
- **Remaining falsehood:** What named successor remains intentionally unimplemented?
- **Authority:** What design-time base, schema/fixture, parent design, and known predecessor state govern the slice?
- **Activation gate:** Which predecessor review/merge/operator fact must become true before dispatch, or `none` if immediately dispatchable?
- **Observable paths:** Which success/failure/stale/retry/persistence/interleaving paths change?
- **Second-contract check:** Does the work introduce another durable format, identifier, API, event, or operator workflow?
- **Write lease:** Can every expected changed path be named, with only a precisely bounded discovery exception if needed?
- **Parallel ownership:** Once ACTIVE, would §4 overlap another active lane? What runtime/state resources are shared?
- **Contract semantics:** Are applicable identity, state/fallback, persistence/replay, predecessor mapping, and commit-point questions resolved?
- **Proof:** Does each material invariant clause have evidence at its owning boundary?
- **Stop conditions:** Does the future worker know when to stop rather than absorb adjacent work?
- **State-sync set:** Which mutable workstream authorities are expected to change after merge?

If the mission/invariant/contract itself is unresolved, split, reconnaissance, or design resolution is required. If only a prerequisite fact is unresolved, write and land the handoff as `BLOCKED` with that explicit activation gate rather than leaving the authority in chat or an uncommitted worktree.

## 5. Write and land the HANDOFF

Copy the canonical template and fill §1–§9. The handoff is a **slice payload**, not a tutorial.

The designing steward owns the handoff until it is durably present on `main`. The default sequence is:

```text
author against current authority
→ record design-time authority snapshot
→ set Status: BLOCKED or ACTIVE truthfully
→ land the handoff on main
→ re-read main and the checked-in handoff
```

When an activation prerequisite is unresolved:

- use `Status: BLOCKED`;
- name the exact activation gate;
- record the creation/design authority snapshot;
- do not create the implementation branch;
- do not treat §4 as an active write lease;
- do not ask the future code worker to commit or activate its own authority document.

When the gate later becomes true, the steward re-anchors and makes a narrow activation sync: record the newly knowable predecessor/review/merge/current-main facts, change `BLOCKED → ACTIVE`, verify the mission/invariant/execution semantics did not drift, then allocate the implementation lane. If satisfying the gate changes the design materially, stop and re-review/rewrite the design rather than calling it metadata activation.

The handoff should contain only what changes from slice to slice:

- mission + merge-ready invariant + pre-dispatch critique;
- exact design authority/predecessor/successor, activation gate, and state-sync set;
- affected observable paths and adversarial sequences;
- §4 write lease;
- explicit exclusions/collision boundaries;
- only the contract matrices that apply;
- evidence ledger and exact commands/manual scenarios;
- required review handback;
- slice-specific acceptance rubric and stop conditions.

Do not copy universal vocabulary, flow definitions, nano-commit policy, review-cycle law, atomic-sync law, or the `review_external_pr.py` manual into each handoff. Those already have owners.

## 6. Activate, allocate, and dispatch

Dispatch requires an already checked-in `ACTIVE` handoff.

A BLOCKED handoff is never handed to an implementation worker as authority to begin code. Once the activation gate is satisfied and the handoff is ACTIVE, allocate the branch/worktree from the re-anchored current integration state and give the worker the checked-in handoff.

At dispatch, the steward should know:

```text
exact checked-in handoff path
Status: ACTIVE
activation gate satisfied
exact implementation branch base
branch / checkout identity
flow/workstream
write lease
parallel lanes and collision hotspots
runtime/state ownership
named successor
```

The implementation agent consumes this authority. It does not create, land, activate, or materially redesign its own implementation handoff unless the assigned slice is explicitly a design/architecture slice.

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

A successor handoff may already exist on `main` as BLOCKED. Merging its predecessor does not automatically dispatch it; the steward must re-anchor, activate it truthfully, and only then allocate the successor lane.

## 11. Learn, then select the next slice

Review-cycle counts are telemetry, not a target.

After close, ask:

- Which finding classes repeated?
- Was the failure visible during pre-dispatch critique?
- Did §7 test the wrong boundary?
- Did parallel ownership need human intervention?
- Did the handoff carry universal text that belongs upstream?
- Did the reviewer repeatedly copy or reconstruct something a tool should supply?
- Did the process accidentally make an implementation worker responsible for creating or activating its own authority document?

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
3. Is its handoff already durably checked in, and is it BLOCKED or ACTIVE?
4. If BLOCKED, what exact activation gate remains false?
5. What remains false afterward?
6. Which paths/state does its ACTIVE lane own?
7. Which other lanes can proceed safely?
8. What exact evidence proves merge readiness?
9. What would force a split?
10. How many review cycles did the predecessor need, and what did they teach us?
11. Which state-authority documents must change after merge?

If the answers require reverse-engineering old PR descriptions, recovering an uncommitted handoff from a temporary checkout, asking a code worker to land its own authority, or copying a giant process prompt into the handoff, the process layer is carrying the wrong responsibility.
