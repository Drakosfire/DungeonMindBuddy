---
# Contract generation this handoff was authored against. Copies keep the value;
# do not bump by hand. Changes: templates/CHANGELOG.md.
template_version: "2.0"
template_updated: "2026-07-25"

# Literal Markdown the worker MUST paste as the PR body and keep current.
pr_body_template: |
  ## Outcome
  {{TODO: copy §1 Mission exactly}}

  ## Merge-ready invariant
  {{TODO: copy §1 Invariant exactly}}

  ## Evidence required to merge
  | Guarantee | Owning boundary | Required evidence | Result |
  |---|---|---|---|
  | {{TODO: copy each material §7 guarantee}} | {{TODO}} | {{TODO: command/scenario + evidence class}} | {{TODO: pass/fail/not run + provenance}} |

  ## Scope and explicit deferrals
  {{TODO: base/head, §4 paths actually changed, paths outside §4, named successors still false}}

  ## Evidence produced
  ### Automated
  {{TODO}}
  ### Adversarial
  {{TODO}}
  ### Regression
  {{TODO}}
  ### Manual / dogfood
  {{TODO}}

  ## Gaps, waivers, and stop conditions
  {{TODO: none, or missing evidence + operator waiver + stop condition}}
---

# HANDOFF — {{TODO: one implementation capability}}

**Created:** {{TODO: YYYY-MM-DD}}.
**Status:** ACTIVE — dispatch exactly one capability.
**Canonical handoff path:** `{{TODO: repository path}}`

## Operating model

External agents are lossy executors: they see this document, not your chat history.
Design stays with the author; the worker implements the contract.

| Rule | Meaning |
|---|---|
| One capability | One independently useful outcome. Neighbors deferred by name. |
| Contract over recipe | Specify inputs, outputs, failure, and proof — not a file tour. |
| Allowlist is the interface | Only §4 paths may change. Adjacent “cleanup” is scope creep. |
| Prove at the owning boundary | Helper tests do not prove service/workflow/UI guarantees. |
| Evidence over narrative | “Tests passed” is not a merge contract. |
| Stop > improvise | Broken invariant, missing proof, or path outside §4 → stop and report. |

**Dispatch gate** — all must be true before launch:

- [ ] One independently useful mission remains
- [ ] One invariant governs every claimed observable path
- [ ] §7 names owning proof for every material claim
- [ ] §4 expected paths known (or bounded discovery filled)
- [ ] Required §6 matrices resolved or marked `Not applicable — <reason>`
- [ ] Pre-dispatch critique below survives skepticism

Do not compress, omit, or rewrite this handoff. The PR body uses the frontmatter skeleton and stays a truthful merge contract; it does not replace this file.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Capability** | One coherent behavior/contract: usable, dependable, testable, or revertible. |
| **Independently useful** | Valuable even if neighboring work never ships. |
| **Public/durable contract** | Persisted format, ID, API, event, schema, file shape, or caller-facing type that outlives one call stack. |
| **Observable path** | Externally visible route: success, miss, error, retry, persistence, operator. |
| **Owning boundary** | Layer where a guarantee becomes true (and must be proved): serializer, store, service, route, component, workflow, CLI. |
| **Invariant** | Single property every changed layer and observable path establishes or proves. |
| **Evidence ledger** | Map: invariant clause → owning boundary → required proof → result → provenance → stop condition. |
| **Stop condition** | Fact that invalidates slice boundaries or required proof; report before continuing. |

## §1 Mission and merge-ready invariant

One sentence. One outcome. “And” may not join separate outcomes.

```text
<caller or user> can <single capability> so that <value>.
```

**Merge-ready invariant:** `<one sentence: identity, revision, authority, durable/local state, observable paths, safe mismatch>`

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed path? | `<yes, or split/reconnaissance>` |
| Adversarial sequence most likely to falsify it? | `<ordered steps>` |
| Would §7 detect that failure? | `<why / why not>` |
| Easiest under-tested owning boundary? | `<boundary>` |
| Fact that forces stop or split? | `<stop condition>` |

Do not dispatch until this table survives critique.

## §2 Context, authority, and boundaries

| Field | Content |
|---|---|
| Parent authority | `<architecture, decision, tracker, or issue>` |
| Repository rules | `<dispatch, security, language, review>` |
| Base revision | `<immutable SHA>` |
| Predecessor contract | `<merged PR, schema/type, fixture, or none>` |
| Exact input consumed | `<artifact, payload, event, store revision, caller contract>` |
| Named successor | `<deferred capability>` |
| What remains false | `<behavior this slice does not deliver>` |
| Explicit non-goals | `<policy, API, UI, migration, cleanup, diagnostics>` |

Read in order before editing code:

1. `<architecture / decision>`
2. `<tracker or issue state>`
3. `<predecessor contract / fixture>`
4. `<implementation seam>`
5. `<existing owning tests>`

Stop and report if base moved, authorities conflict, predecessor shape differs, or the invariant cannot hold.

## §3 Observable-path and adversarial-sequence inventory

Required for user-facing, multi-entry, stateful, persistence, concurrent, partially durable, or multi-source work.
Otherwise: `Not applicable — <one-sentence reason>`.

| Path | Current | Required | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| `<entry / interaction>` | `<today>` | `<after slice>` | Yes / No | `<layer>` |

Inventory success, ordinary miss, error/unavailable, stale context, retry/replay, save/reload, traversal, operator paths as relevant. `No` → split or remove the row from the mission.

Stateful / concurrent / cross-surface / navigation / commit work — enumerate ordered failure sequences:

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| `<step 1 → step 2 → failure/interleaving>` | `<truthful state, blocked mutation, or recovery>` | `<§7 row>` |

## §4 Files in scope (allowlist)

Every changed path must appear here, including this handoff and any tracker/plan doc the slice updates. The expected focused `git diff --stat` must be expressible from this table.

| Action | Path | Purpose: how this establishes or proves §1 |
|---|---|---|
| Create / Modify / Delete | `{{TODO: relative/path}}` | `{{TODO}}` |

**Bounded discovery exception:** `Not applicable — <reason>` or:

```text
Directory:
Maximum additional paths:
Allowed path kinds:
Decision rule for including one:
```

No unrestricted globs (`src/**`). Need another path → stop and report; do not add silently.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why not this slice |
|---|---|
| `{{TODO}}` | `{{TODO: successor ownership, collision risk, or separate invariant}}` |

Proximity is not authorization. Search, notes, classifications, management controls, persistence, reports, or panels are product capabilities unless §1 names them.

## §6 Implementation contract and conditional matrices

Behavior, not a code recipe.

```text
Input:
  <types, artifacts, exact predecessor authority>

Output:
  <public result, durable artifact, or observable state>

Invariant:
  <same as §1>

Failure behavior:
  <named failure> → <stable result, unresolved state, or blocked transition>

Replay / idempotency:
  same input →
  changed input →
  retry after partial failure →

Trust boundary:
  Verifies:
  Records or trusts without proving:
```

Irreversible or partially durable work:

```text
Commit point:
Before commit:
After commit:
Truthful result after a post-commit failure:
```

Each matrix: fill when applicable, else `Not applicable — <one-sentence reason>`. Never omit silently.

### A. State and fallback matrix

Required when multiple states, dependencies, sources, or sibling paths exist.

| Observable path | Loading | Exact success | Ordinary miss | Dependency unavailable | Integrity / contract failure | Stale / superseded | Retry / replay |
|---|---|---|---|---|---|---|---|
| `<path>` | `<defer / fail / fallback>` | `<primary source>` | `<unresolved / named fallback>` | `<behavior>` | `<fail closed / behavior>` | `<behavior>` | `<allowed conditions>` |

Name every fallback. Audit sibling paths on the same trust boundary.

### B. Identity matrix

Required when IDs, labels, aliases, normalization, merge, rename, deletion, or rebinding affect resolution.

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Exact ID | `<rule>` | `<rule>` | Yes / No: `<source>` |
| Alias / label | `<unique-only / prohibited / other>` | `<rule>` | Yes / No |
| Normalized key | `<rule or prohibited>` | `<rule>` | Yes / No |
| Rename / deletion / rebind | `<stable identity>` | `<rule>` | Yes / No |

Prefer unique durable identity. Prohibit silent first-win and display-label substitution for durable IDs.

### C. Persistence and replay matrix

Required when data survives restart, save/reload, retries, replay, compatibility, or migration.

| Operation | Durable representation | Round-trip guarantee | Duplicate / replay | Compatibility / migration | Rollback / reversion |
|---|---|---|---|---|---|
| `<write / load / replay>` | `<format / revision>` | `<exact property>` | `<rule>` | `<rule>` | `<rule>` |

A new persisted format or durable ID is not incidental. If independently useful or revertible from §1, stop and propose a successor slice.

### D. Predecessor-to-consumer mapping

Required when adapting an existing API, event, schema, file, fixture, or error payload.

**Grounding source:** `<exact captured fixture | canonical schema/type | field-level mapping>`

| Predecessor field / outcome | Real shape and optionality | Consumer field / behavior | Transformation | Proof fixture/test |
|---|---|---|---|---|
| `<field>` | `<type, ID shape, nullability, error payload>` | `<destination>` | `<mapping>` | `<path/test>` |

Invented “close enough” fixture vocabulary is not proof.

## §7 Evidence required to merge

Every material invariant clause: exercise at its owning boundary; for stateful work, through the adversarial sequence that could falsify it. Lower-level coverage is useful, never sufficient for a higher-level claim.

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| `<guarantee>` | `<serializer/store/service/route/component/workflow/CLI>` | `<contract/adversarial/regression/manual/dogfood>` | `<exact command or scenario>` | `<observable result>` | `<result that blocks merge>` |

Run applicable commands. Record each one's exit status and the assertion-relevant output — not full logs.

```bash
<focused owning-boundary test>
<contract or exact round-trip test>
<integration / failure-injection test>
<repository-specific regression suite>
<repository-specific build, formatting, or lint>
git diff --check
git diff --stat <base>...HEAD -- <§4 paths>
git diff --name-only <base>...HEAD
```

### Minimal live / dogfood proof

`Not applicable — <reason>` or:

```text
Existing surface used:
Smallest realistic scenario:
Expected observation:
Evidence captured:
```

If proof needs new search, persistence, notes, classifications, management controls, reports, or a dedicated panel → stop for split review.

### Baseline failure protocol

If a required command already fails on base:

- cite the same command on base and head;
- state whether head adds failures;
- do not call the gate green;
- name the operator waiver if it remains an acceptance gate.

## §8 PR description and handback

Paste the frontmatter skeleton as the PR body and keep it current until merge.

| Field | Source | Rule |
|---|---|---|
| Outcome, merge-ready invariant | §1 | Verbatim — no paraphrase |
| Evidence ledger | §7 | Required proof beside produced result, per row |
| Provenance per result | — | `author-local` \| `rerun-local` \| `CI` \| `manual/dogfood` |
| Base and head | §2 + branch tip | Immutable SHAs |
| Changed paths | §4 | Focused diff stat, plus paths outside §4 (`none` or stop report) |
| Baseline failures | §7 protocol | base/head comparison; never a green claim |
| Waivers | operator | Explicit, or `none` |
| Stop conditions | Stop conditions | Encountered + resolution, or `none` |
| Deferrals | §2 successor | Named capability still false |
| Fidelity | this file | Confirm implemented with no compressed or omitted constraint |

Redact corpus prose and player names from anything posted to GitHub (`.cursor/rules/corpus-pii-and-llm-payloads.mdc`); cite paths, IDs, and metrics instead.

A generic “Summary / Test plan” body fails this section.

## §9 Acceptance rubric

Reviewer accepts only when every bullet is true. Behavioral bullets must name their §7 proof.

- [ ] Exactly one independently useful capability from §1 — proved by `<§7 proof>`
- [ ] Merge-ready invariant holds across §3 paths and adversarial sequences — proved by `<§7 proofs>`
- [ ] PR description restates the exact invariant and exposes a complete, truthful evidence ledger
- [ ] Every required proof has a produced result and provenance, or an explicit operator waiver
- [ ] No second public/durable contract introduced silently — proved by `<diff inspection + contract tests>`
- [ ] Applicable §6 matrices followed — proved by `<§7 proofs>`
- [ ] Real predecessor vocabulary and shapes used — proved by `<fixture / schema / mapping test>`
- [ ] No path outside §4 changed — proved by `<changed-path command>`
- [ ] Baseline failures reported truthfully; required waiver explicit — proved by `<base/head evidence>`
- [ ] Minimal live proof did not grow into an unacknowledged product surface — proved by `<scenario or N/A reason>`
- [ ] Named successor remains unimplemented and unclaimed

## Stop conditions

Stop and report rather than expand when implementation discovers:

- a second independently useful outcome
- a new public/durable contract not owned by §1
- an invariant that cannot govern every claimed path
- required evidence that cannot be produced at the owning boundary
- an untested adversarial sequence that can mutate or misreport state
- unresolved identity, state, fallback, persistence, replay, or compatibility semantics
- a predecessor contract that differs materially from the authoritative fixture/schema/mapping
- a required path outside §4 or its bounded discovery exception
- a new product/operator surface disguised as verification
- an irreversible operation outside the declared commit model
- a repository rule or architecture conflict
- a base/head failure that needs an operator waiver before acceptance

```text
Stop condition:
Why the current mission cannot absorb it:
Invariant clause affected:
Required evidence now missing:
New public/durable contract discovered:
Affected observable paths or ownership layers:
Proposed successor slice:
Tracker or authority update needed:
```
