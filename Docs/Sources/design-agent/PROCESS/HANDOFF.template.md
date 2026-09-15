---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: {{TODO}}
  - Flow: {{TODO}}
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: {{TODO: checked-in path}}
  - Branch / PR: {{TODO: optional transport metadata; none while BLOCKED}}

  ## Verification pointer
  - Design authority / head: {{TODO}}
  - Changed paths: {{TODO}}
  - Verification: {{TODO: exact result pointer}}

  The checked-in ACTIVE handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — {{TODO: one implementation capability}}

**Created:** {{TODO: YYYY-MM-DD}}  
**Status:** {{TODO: BLOCKED — <activation gate> | ACTIVE — one implementation capability}}  
**Canonical handoff path:** `{{TODO}}`  
**Conversation/workstream:** `{{TODO}}`  
**Flow / owner:** `{{TODO}}`  
**Direction:** DESIGN → CODE → REVIEW  
**Design authority base:** `{{TODO: exact main SHA/revision used to design this handoff}}`  
**Activation gate:** {{TODO: `none — satisfied` or exact predecessor/review/merge/operator condition}}  
**Dispatch base rule:** fresh current `main` containing this checked-in handoff after the activation gate is satisfied; record the exact implementation branch base at dispatch/review rather than trying to self-reference it inside this main commit.  
**PR title:** `{{TODO: FLOW: short capability}}`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

> Handoff lifecycle: the designing steward lands this file on `main`. `BLOCKED` means durable design authority only—no implementation lane and no active §4 lease. The steward changes `BLOCKED → ACTIVE` only after re-anchoring and verifying the activation gate. The implementation worker consumes the already-checked-in ACTIVE handoff and does not create or activate its own authority document.

## §1 Mission and merge-ready invariant

**Mission:** `<caller/user> can <one independently useful capability> so that <value>.`

**Merge-ready invariant:** `<one property governing every changed layer and observable path, including exact identity/revision/authority/state and safe mismatch behavior>`

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | `<yes or split/reconnaissance>` |
| Most likely adversarial sequence | `<ordered sequence>` |
| Will §7 actually detect that failure? | `<why>` |
| Easiest owning boundary to under-test | `<boundary>` |
| Fact that forces stop/split | `<stop condition>` |

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | `<architecture / decision / tracker / issue>` |
| Design authority base | `<immutable SHA/revision used to design the slice>` |
| Activation gate | `<none/satisfied, or exact prerequisite that keeps this handoff BLOCKED>` |
| Dispatch base rule | `fresh current main containing this handoff after activation; exact branch base recorded at dispatch/review` |
| Predecessor contract | `<merged PR / schema / fixture / none; if unmerged, name exact gate>` |
| Exact input consumed | `<artifact / payload / event / store revision / caller contract>` |
| Named successor | `<capability intentionally deferred>` |
| What remains false | `<specific behavior not delivered>` |
| Explicit non-goals | `<bounded exclusions>` |
| Branch / isolated checkout | `<none while BLOCKED; exact branch + worktree/equivalent after ACTIVE>` |
| Parallel lanes / collision hotspots | `<active lanes or none; BLOCKED handoffs are not lease owners>` |
| Runtime/state ownership | `<isolated root / namespace / shared serialized resource / not applicable>` |
| State-authority sync set after merge | `<PLAN/CHECKLIST/HANDOFF/ROADMAP/tracker/status/index paths as applicable, or handoff-only>` |

Read the exact predecessor/implementation seam/tests required by this slice before changing code. If design authority, activation gate, predecessor shape, lane ownership, or invariant differs materially, stop and report the consequence.

## §3 Observable paths and adversarial sequences

`Not applicable — <reason>` or:

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| `<entry/success/failure/retry/persistence path>` | `<today>` | `<after>` | Yes/No | `<layer>` |

For stateful/concurrent/navigation/commit work, include the sequences that could falsify §1:

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| `<step → step → failure/interleaving>` | `<truthful state / blocked mutation / recovery>` | `<proof row>` |

A `No` in the invariant column is a split signal unless that path leaves the mission.

## §4 Files in scope — write lease

Every expected changed path must be expressible here. This table becomes an exclusive expected write lease only when `Status: ACTIVE`; while BLOCKED it is prospective scope, not reserved ownership.

| Action | Path | Purpose |
|---|---|---|
| Create / Modify / Delete | `{{TODO: relative/path}}` | `{{TODO: how it establishes/proves §1}}` |

**Bounded discovery exception:** `Not applicable — <reason>` or:

```text
Directory:
Maximum additional paths:
Allowed path kinds:
Decision rule:
```

Once ACTIVE, a required path outside this lease/exception is a stop report. If another active lane owns it, do not edit it before the steward resolves ownership.

## §5 Explicitly out of scope / collision boundary

| Path | Why this slice must not touch or claim it |
|---|---|
| `{{TODO: path/glob}}` | `{{TODO: successor ownership / parallel lease / separate invariant}}` |

## §6 Implementation contract

```text
Input:
  <exact types/artifacts/predecessor authority>

Output:
  <public result/durable artifact/observable state>

Invariant:
  <same §1 invariant>

Failure behavior:
  <named failure> → <stable result / unresolved state / blocked transition>

Replay / idempotency:
  same input →
  changed input →
  retry after partial failure →

Trust boundary:
  Verifies:
  Records/trusts without proving:
```

For irreversible or partially durable work:

```text
Commit point:
Before commit:
After commit:
Truthful result after post-commit failure:
```

Include only the matrices that apply; otherwise write `Not applicable — <reason>`.

### A. State / fallback matrix

| Observable path | Loading/init | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Stale/superseded | Retry/replay |
|---|---|---|---|---|---|---|---|
| `<path>` | `<behavior>` | `<source/result>` | `<behavior>` | `<behavior>` | `<behavior>` | `<behavior>` | `<rule>` |

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Exact ID | `<rule>` | `<rule>` | Yes/No |
| Alias/label | `<rule>` | `<rule>` | Yes/No |
| Normalized key | `<rule/prohibited>` | `<rule>` | Yes/No |
| Rename/delete/rebind | `<stable identity rule>` | `<rule>` | Yes/No |

### C. Persistence / replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility/migration | Rollback/reversion |
|---|---|---|---|---|---|
| `<write/load/replay>` | `<format/revision>` | `<property>` | `<rule>` | `<rule>` | `<rule>` |

### D. Predecessor → consumer mapping

**Grounding source:** `<captured fixture / canonical schema/type / exact field mapping>`

| Predecessor field/outcome | Real shape/optionality | Consumer behavior | Transformation | Proof |
|---|---|---|---|---|
| `<field>` | `<type/nullability/error shape>` | `<destination>` | `<mapping>` | `<fixture/test>` |

## §7 Evidence required to merge

Every material invariant clause needs proof at its owning boundary.

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| `<guarantee>` | `<store/service/route/component/workflow/CLI/...>` | `<contract/adversarial/regression/manual/dogfood>` | `<exact command/scenario>` | `<observable result>` | `<merge blocker>` |

Exact verification commands:

```bash
<focused owning-boundary test>
<contract / round-trip / failure-injection test as applicable>
<repository regression/build/lint command as applicable>
git diff --check
git diff --name-only <dispatch-base>...HEAD
```

### Minimal live / dogfood proof

`Not applicable — <reason>` or:

```text
Existing surface:
Smallest realistic scenario:
Expected observation:
Evidence captured:
```

### Baseline failure handling

`Not applicable — no required baseline failure` or record the same command on base and head, whether head adds failures, and any explicit operator waiver.

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR/branch/head SHA;
2. exact implementation branch base used at dispatch;
3. §1 mission/invariant disposition;
4. §7 required vs produced evidence + provenance;
5. nano-commit/fix story;
6. base/head and actual changed paths vs §4;
7. baseline failures/waivers;
8. paths outside §4 (`none` or stop report);
9. stop conditions and resolution;
10. named successor still false;
11. prior finding ledger on re-review.

## §9 Acceptance rubric

- [ ] This handoff was checked in by the steward before implementation dispatch and was ACTIVE at dispatch.
- [ ] Exactly one independently useful capability from §1 is delivered and proved by §7.
- [ ] The §1 invariant holds across every claimed §3 path/adversarial sequence.
- [ ] Exact implementation base, PR/head, evidence provenance, and review-cycle number are recorded.
- [ ] No second public/durable contract or operator workflow was silently introduced.
- [ ] Applicable §6 state/identity/persistence/predecessor semantics hold.
- [ ] Actual changed paths stay inside §4 / bounded discovery.
- [ ] Baseline failures and waivers are truthful.
- [ ] Parallel write/runtime ownership did not drift silently.
- [ ] Named successor remains unimplemented/unclaimed.

## Stop conditions

Stop and report instead of expanding when any of these appears:

- this handoff is still BLOCKED or its activation gate is not truthfully satisfied;
- second independently useful outcome or public/durable contract;
- invariant cannot govern every claimed path;
- owning-boundary evidence cannot be produced;
- unresolved state/identity/persistence/replay/compatibility semantics;
- predecessor differs materially from the authoritative fixture/schema;
- required path outside §4 or another active lane's write lease;
- unsafe shared runtime/state collision;
- irreversible operation outside the declared commit model;
- repository/architecture conflict;
- baseline/head gate requiring an unapproved waiver.

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
