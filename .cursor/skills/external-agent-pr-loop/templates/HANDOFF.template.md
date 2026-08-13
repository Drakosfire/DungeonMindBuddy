---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: {{TODO}}
  - Flow: {{TODO}}
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: {{TODO: checked-in path}}
  - Branch / PR: {{TODO: optional transport metadata}}

  ## Verification pointer
  - Base/head: {{TODO}}
  - Changed paths: {{TODO}}
  - Verification: {{TODO: exact result pointer}}

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — {{TODO: one implementation capability}}

**Created:** {{TODO: YYYY-MM-DD}}  
**Status:** ACTIVE — one implementation capability  
**Canonical handoff path:** `{{TODO}}`  
**Conversation/workstream:** `{{TODO}}`  
**Flow / owner:** `{{TODO}}`  
**Direction:** DESIGN → CODE → REVIEW  
**Base revision:** `{{TODO: immutable SHA/revision}}`  
**PR title:** `{{TODO: FLOW: short capability}}`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`../SKILL.md`](../SKILL.md).

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
| Base revision | `<immutable SHA/revision>` |
| Predecessor contract | `<merged PR / schema / fixture / none>` |
| Exact input consumed | `<artifact / payload / event / store revision / caller contract>` |
| Named successor | `<capability intentionally deferred>` |
| What remains false | `<specific behavior not delivered>` |
| Explicit non-goals | `<bounded exclusions>` |
| Branch / isolated checkout | `<branch + worktree/equivalent>` |
| Parallel lanes / collision hotspots | `<active lanes or none; shared files/runtime/state>` |
| Runtime/state ownership | `<isolated root / namespace / shared serialized resource / not applicable>` |
| State-authority sync set after merge | `<PLAN/CHECKLIST/HANDOFF/ROADMAP/tracker/status/index paths as applicable, or handoff-only>` |

Read the exact predecessor/implementation seam/tests required by this slice before changing code. If base, authority, predecessor shape, lane ownership, or invariant differs materially, stop and report the consequence.

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

Every expected changed path must be expressible here.

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

A required path outside this lease/exception is a stop report. If another active lane owns it, do not edit it before the steward resolves ownership.

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
git diff --name-only <base>...HEAD
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
2. §1 mission/invariant disposition;
3. §7 required vs produced evidence + provenance;
4. nano-commit/fix story;
5. base/head and actual changed paths vs §4;
6. baseline failures/waivers;
7. paths outside §4 (`none` or stop report);
8. stop conditions and resolution;
9. named successor still false;
10. prior finding ledger on re-review.

## §9 Acceptance rubric

- [ ] Exactly one independently useful capability from §1 is delivered and proved by §7.
- [ ] The §1 invariant holds across every claimed §3 path/adversarial sequence.
- [ ] Exact PR/head, evidence provenance, and review-cycle number are recorded.
- [ ] No second public/durable contract or operator workflow was silently introduced.
- [ ] Applicable §6 state/identity/persistence/predecessor semantics hold.
- [ ] Actual changed paths stay inside §4 / bounded discovery.
- [ ] Baseline failures and waivers are truthful.
- [ ] Parallel write/runtime ownership did not drift silently.
- [ ] Named successor remains unimplemented/unclaimed.

## Stop conditions

Stop and report instead of expanding when any of these appears:

- second independently useful outcome or public/durable contract;
- invariant cannot govern every claimed path;
- owning-boundary evidence cannot be produced;
- unresolved state/identity/persistence/replay/compatibility semantics;
- predecessor differs materially from the authoritative fixture/schema;
- required path outside §4 or another lane's write lease;
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
