---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: {{TODO}}
  - Flow: {{TODO}}
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: {{TODO: path + pinned ref/commit}}
  - Branch / PR: {{TODO: optional transport metadata; none while BLOCKED}}
  - PR topology: {{TODO: serial | stacked | parallel-independent}}

  ## Verification pointer
  - Design authority / head: {{TODO}}
  - Changed paths: {{TODO}}
  - Verification: {{TODO: exact result pointer}}

  The pinned ACTIVE handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — {{TODO: one implementation capability}}

**Created:** {{TODO: YYYY-MM-DD}}
**Status:** {{TODO: BLOCKED — <activation gate> | ACTIVE — one implementation capability}}
**Handoff locator:** `{{TODO: path + pinned ref/commit}}`
**Conversation/workstream:** `{{TODO}}`
**Flow / owner:** `{{TODO}}`
**Direction:** DESIGN → CODE → REVIEW
**Design authority base:** `{{TODO: exact main SHA/revision used to design this handoff}}`
**Activation gate:** {{TODO: `none — satisfied` or exact predecessor/review/merge/operator condition}}
**Dispatch base rule:** re-anchor current integration state after the activation gate is satisfied; the handoff itself may be on any durable pinned ref. Record the exact implementation branch base at dispatch/review.
**PR topology:** `{{TODO: serial (default) | stacked | parallel-independent}}`
**PR authorization:** `{{TODO: exactly which implementation PR this worker may open/update without asking; normally “open/update this one assigned PR only; no successor/repair PRs”}}`
**PR title:** `{{TODO: FLOW: short capability}}`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

> Handoff lifecycle: the designing steward makes this file durably addressable and pins its exact ref/commit before dispatch. It does not have to be on `main`. `BLOCKED` means design authority only—no implementation lane and no active §4 lease. The steward changes `BLOCKED → ACTIVE` only after re-anchoring and verifying the activation gate. The implementation worker consumes the exact pinned ACTIVE handoff and does not materially redesign its own authority document.

> PR authorization rule: once this handoff is ACTIVE, the worker should open the **one assigned implementation PR** without asking the user for another confirmation. That convenience does not let the worker choose PR topology or open successor/repair/cleanup PRs. Unless this handoff explicitly says `stacked` or `parallel-independent` and names the relationship, a newly discovered next defect is a stop/handback to the steward.

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
| What PR topology is authorized, and why is it safe? | `<serial by default; or exact stacked/parallel rationale>` |
| Fact that forces stop/split | `<stop condition>` |

## §2 Context, authority, lane, and PR topology

| Field | Required content |
|---|---|
| Parent authority | `<architecture / decision / tracker / issue>` |
| Design authority base | `<immutable SHA/revision used to design the slice>` |
| Activation gate | `<none/satisfied, or exact prerequisite that keeps this handoff BLOCKED>` |
| Dispatch base rule | `fresh current integration state after activation; exact branch base recorded at dispatch/review; handoff location is independent` |
| Predecessor contract | `<merged PR / schema / fixture / none; if unmerged, name exact gate>` |
| Exact input consumed | `<artifact / payload / event / store revision / caller contract>` |
| Named successor | `<capability intentionally deferred>` |
| What remains false | `<specific behavior not delivered>` |
| Explicit non-goals | `<bounded exclusions>` |
| PR topology | `<serial (default) / stacked / parallel-independent>` |
| Authorized PR action | `<open/update exactly this assigned PR without asking; no additional PRs unless explicitly authorized here>` |
| Open implementation PRs in workstream at dispatch | `<none / exact PR list>` |
| Stack parent + merge/rebase order | `<not applicable, or exact parent PR/head and required order>` |
| Branch / isolated checkout | `<none while BLOCKED; exact branch + worktree/equivalent after ACTIVE>` |
| Parallel lanes / collision hotspots | `<active lanes or none; BLOCKED handoffs are not lease owners>` |
| Runtime/state ownership | `<isolated root / namespace / shared serialized resource / not applicable>` |
| State-authority sync set after merge | `<PLAN/CHECKLIST/HANDOFF/ROADMAP/tracker/status/index paths as applicable, or handoff-only>` |

Read the exact predecessor/implementation seam/tests required by this slice before changing code. If design authority, activation gate, predecessor shape, PR topology, lane ownership, or invariant differs materially, stop and report the consequence.

### PR topology semantics

Use exactly one:

```text
serial
  default
  this worker owns one PR
  no dependent/successor PR opens until predecessor merge + sync + re-anchor

stacked
  only when this handoff names an exact unmerged parent PR/head
  this worker owns one child PR in that declared stack
  merge/rebase order is part of the handoff contract

parallel-independent
  only when this handoff proves no unmerged behavioral dependency
  write/runtime/state ownership is disjoint or deliberately isolated
```

A user instruction such as “don’t ask before opening the PR” means: open the PR explicitly assigned above without ceremony once ACTIVE. It does **not** mean “open whatever additional PR seems useful.”

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

Also out of scope unless §2 explicitly authorizes otherwise: opening a second implementation PR, spawning a repair PR from dogfood, or creating a successor lane while this PR/predecessor is still open.

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
3. declared PR topology, open PRs at dispatch, and whether topology remained truthful;
4. §1 mission/invariant disposition;
5. §7 required vs produced evidence + provenance;
6. nano-commit/fix story;
7. base/head and actual changed paths vs §4;
8. baseline failures/waivers;
9. paths outside §4 (`none` or stop report);
10. stop conditions and resolution;
11. named successor still false;
12. prior finding ledger on re-review.

## §9 Acceptance rubric

- [ ] This handoff was durably pinned by the steward before implementation dispatch and was ACTIVE/authorized at dispatch.
- [ ] PR topology was explicit and honored; the worker opened/updated only the PR(s) this handoff actually authorized.
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
- observed open-PR shape differs from the declared PR topology;
- a newly discovered successor/repair would require opening another PR not explicitly authorized by §2;
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
PR topology consequence:
Why current mission cannot absorb it:
Required evidence now missing:
Affected paths/ownership layers:
Proposed successor or re-brief:
State-authority update needed:
```
