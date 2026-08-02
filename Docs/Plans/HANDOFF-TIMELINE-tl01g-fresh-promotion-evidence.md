---
pr_body_template: |
  ## Handoff pointer
  - Conversation: `TL01G Fresh Promotion Evidence`
  - Flow / agent: `TIMELINE`
  - Direction: DESIGN → CODE
  - Handoff: `Docs/Plans/HANDOFF-TIMELINE-tl01g-fresh-promotion-evidence.md`
  - Branch: `timeline/tl01g-fresh-promotion-evidence`
  - PR mode: **this PR is the implementation PR; do not open a second PR**

  ## Execution pointer
  - Initial branch base: `4811741eb3f784171c3f9840a3b0f0ad345470e1`
  - Required implementation base: current `origin/main` after an explicit rebase, recorded before fixture work
  - Frozen control/candidate: `tl01f-v1` / `tl01g-v1`
  - Fresh promotion pair: holdout V14 / adversarial V12
  - Provider budget: one six-lane × three-repetition matrix, maximum **18 attempts**, no retry

  ## Verification pointer
  - Base/head: TODO in this PR after implementation rebase
  - Cohort seal / provider execution SHA: TODO
  - Changed paths: §4 allowlist only
  - Verification and decision: TODO from §7 evidence ledger

  The checked-in handoff, cumulative diff, nano commits, sealed cohort bytes,
  provider manifests, aggregate, and independently rerun verification are the
  review contract. The PR description is transport metadata only.
---

# HANDOFF — TIMELINE: Fresh TL01G Promotion Evidence

**Created:** 2026-08-02.  
**Status:** ACTIVE — design handoff and implementation remain in this same open PR.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-TIMELINE-tl01g-fresh-promotion-evidence.md`  
**Conversation name:** `TL01G Fresh Promotion Evidence`  
**Flow / agent:** `TIMELINE`  
**Handoff direction:** `DESIGN → CODE`  
**Design agent:** GPT-5.6 Thinking, DungeonBuddy project conversation  
**Code agent:** TIMELINE code agent operating on this PR branch  
**PR title:** `TIMELINE: produce fresh TL01G promotion evidence`  
**Branch:** `timeline/tl01g-fresh-promotion-evidence`  
**Initial branch base:** `4811741eb3f784171c3f9840a3b0f0ad345470e1`  
**Predecessor merge:** PR #486, merge `27e67981f78c4901deff8919ca525b5a4ab585ae`

> **Same-PR execution gate:** This open PR is the sole implementation surface for
> this capability. Do not merge it as handoff-only work. Do not open a sibling or
> successor implementation PR. Do not switch to, merge from, or cherry-pick an old
> TL01 branch. Rebase this branch onto current `origin/main`, create a fresh local
> clone/worktree from this branch, and push every implementation, evidence, and
> review-response nano commit back to this PR.
>
> **Dispatch gate:** No fixture authoring or provider execution may begin until the
> branch/worktree reset in §0 is complete, the exact rebased base SHA is recorded in
> the PR, the frozen identities in §2 are independently verified, and the invariant
> and evidence ledger below survive review.
>
> This checked-in handoff is the complete authority. Once implementation begins,
> the worker must not compress, omit, replace, or rewrite it. A review-directed
> re-brief must be a discrete handoff commit made before any provider call.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Capability** | A coherent behavior or contract that creates one outcome someone can use, depend on, test, or revert. |
| **Promotion evidence** | A sealed, independent, provenance-bound control/candidate matrix capable of supporting a roadmap decision. |
| **Fresh cohort** | A never-observed fixture family whose semantic propositions, exact source spans, vocabulary, and adversarial templates pass the independence gates before provider execution. |
| **Seal commit** | The immutable full Git SHA containing final prompt-independent fixture, gold, source, audit, and test bytes before any provider call. |
| **Provider execution SHA** | One clean full Git SHA recorded by every run manifest in the live matrix. It must contain the seal commit and remain reachable in this PR history. |
| **Observable path** | A success, integrity failure, provider failure, model failure, grounding failure, replay attempt, or roadmap decision produced by this experiment. |
| **Owning boundary** | The layer where a guarantee becomes true and therefore must be proved: cohort fixture, test guard, calibration workflow, aggregate, report, or Git history. |
| **Evidence ledger** | The §7 mapping from each invariant clause to its owning proof, produced result, provenance, and merge-blocking stop condition. |
| **Stop condition** | A fact that invalidates this experiment or requires a different capability; it must be reported rather than absorbed through scope expansion. |

## Agent flow and nano-commit contract

Use the `TIMELINE` flow. Keep the entire capability in this PR and branch.

Required nano-commit story:

1. `docs(timeline): add fresh tl01g promotion handoff` — already opened by the design agent.
2. `test(timeline): define v14 and adversarial v12 integrity gates` — tests only; no provider calls.
3. `test(timeline): seal fresh v14 and adversarial v12 cohorts` — final fixture/gold/source/audit bytes plus green pre-live tests.
4. `eval(timeline): record frozen tl01g promotion matrix` — aggregate/report only after the one authorized live execution.
5. Review-response nano commits, each addressing one named finding without changing observed cohort bytes.

Do not squash, amend, force-push, or rebase after the first provider attempt. The
provider execution SHA must remain reachable and independently inspectable.

## §0 Workspace reset, branch retirement, and current-main rebase

### Old work is closed, not inherited

The following PRs/branches are historical inputs only:

| PR / branch | State and required treatment |
|---|---|
| PR #465 · `docs/tl01g-handoff` | Closed unmerged. Delete stale local/remote working branch after confirming no unpublished operator work; never merge or cherry-pick it. |
| PR #489 · `docs/tl01-grounding-path-recovery-handoff` | Closed unmerged. Delete stale local/remote working branch; never merge or cherry-pick it. |
| PR #468 · `feat/tl01g-resolution-proof-abstention-gate` | Merged. Treat `main` as authority; delete stale working branch/worktree rather than continuing it. |
| PR #486 · `agent/tl01-grounding-path-recovery-jumpstart` | Merged. Treat `main` as authority; delete stale working branch/worktree rather than continuing it. |

Branch deletion is housekeeping, not a repository diff. Before coding:

```bash
git fetch --prune origin

# Inspect before destructive cleanup; the operator explicitly authorized retiring
# these old Timeline working branches. Do not delete a branch with unique unpublished work.
git worktree list
git branch --contains 27e67981f78c4901deff8919ca525b5a4ab585ae

# Remove clean stale worktrees, then delete stale local branches.
# Delete corresponding remote branches only after verifying their PR is closed/merged.
```

If permissions prevent remote deletion, record that limitation in the PR. It does
not authorize reuse of the branch.

### Fresh copy and rebase

Do not reuse a dirty TL01G or grounding-path directory. Create a fresh clone or
worktree for `timeline/tl01g-fresh-promotion-evidence`, then:

```bash
git fetch --prune origin
git switch timeline/tl01g-fresh-promotion-evidence
git rebase origin/main
git status --short
git rev-parse HEAD
git rev-parse origin/main
git merge-base --is-ancestor origin/main HEAD
```

Required result before fixture work:

```text
worktree: clean
origin/main: ancestor of HEAD
old TL01 branches: not merged/cherry-picked into this branch
exact rebased origin/main SHA: recorded in the PR handback
```

If `main` moves again before the cohort seal, rebase again and rerun every pre-live
proof. After the first provider attempt, do **not** rebase or rewrite history; if a
late `main` update is required, use a history-preserving merge only after the
provider evidence is safely committed and explicitly record it.

## §1 Mission and merge-ready invariant

**Mission:** The Timeline steward can obtain one trustworthy fresh promotion
judgment for frozen `tl01g-v1` against holdout V14 and adversarial V12 so the
roadmap can advance to broader shadow use or name the demonstrated successor.

**Merge-ready invariant:** From one clean provider execution SHA descended from
current `main`, byte-frozen `tl01f-v1` and `tl01g-v1` use unchanged packet and
renderer identities across one sealed, independent six-lane/three-repetition
matrix; all cohort, evidence, Gate E3, value-grounding, and provenance checks pass
before calls, every failed or missing observation remains explicit, and the same
PR emits exactly one truthful roadmap disposition without mutating observed gold,
changing graph authority, or opening another implementation PR.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Cohort construction, sealing, provider execution, aggregation, and recommendation all serve one outcome: a trustworthy promotion judgment for the existing frozen candidate. |
| What adversarial sequence is most likely to falsify it? | Author a superficially novel cohort that replays old proposition structures or contains defective temporal gold → run provider calls → discover the defect → patch the observed fixture and call the rerun promotion evidence. This handoff blocks that sequence through cumulative semantic/span/template guards, positive Gate E3/value audits, immutable seal identity, no live retry, and no post-observation fixture edits. |
| Would §7 detect that failure? | **Yes.** The explicit V14/V12 tests must pass before the seal; the live command verifies the seal commit; diff inspection proves fixture bytes do not change after the provider execution SHA; the report must retire rather than repair any post-observation defect. |
| Which owning boundary is easiest to under-test? | Freshness and gold faithfulness: exact source-span disjointness, proposition-template overlap after entity scrubbing, positive start/end boundary narration for the selected proposition, and temporal-value grounding rather than related-future-event grounding. |
| What fact forces a stop or split? | Any need to modify `tl01g-v1`, packet/renderer, schema, calibration runner, thresholds, graph/kernel code, or prior observed cohorts; inability to create a genuinely independent V14/V12; a gold/audit defect found after the first provider call; or provider execution that cannot produce the complete bounded matrix. |

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Reports/REPORT-tl01g-resolution-proof-abstention-gate.md`; `Docs/Reports/REPORT-tl01g-grounding-path-recovery.md`; merged PRs #468 and #486 |
| Repository rules | `AGENTS.md`; `.cursor/rules/external-agent-pr-loop.mdc`; `.cursor/skills/external-agent-pr-loop/SKILL.md` |
| Initial branch base | `4811741eb3f784171c3f9840a3b0f0ad345470e1` |
| Required implementation base | Exact current `origin/main` after the §0 rebase; record full SHA before fixture work |
| Predecessor contract | `GROUNDING_PATH_READY` on shared clean SHA `46158038c8f29c1b6fbaba70039a71bb5cf6f063`; frozen prompt/packet/renderer identities below |
| Exact input consumed | Existing TL01 development control/candidate cases, newly authored V14/Adv V12 paired cases, owned evidence spans, current calibration workflow, model `gpt-5.4-mini` |
| Named successor on success | Broader-shadow acceptance/cutover design for the temporal producer; not implemented here |
| Named successor on prompt-specific failure | A separately designed `tl01h-v1` prompt iteration grounded only in the fresh observed defect |
| Named successor on textual-only failure | A separately designed textual-normalization/grounding-policy capability; no semantic relaxation here |
| What remains false | Temporal annotations are not authoritative graph assertions; no producer cutover, timeline query, event nodes, participant roles, projection, API, or UI is delivered |
| Explicit non-goals | Prompt edits; packet/renderer/schema/threshold/runner changes; prior cohort edits; graph writes; Kernel changes; product UI; retries; second PR |

### Frozen predecessor identities

| Identity | Required exact value |
|---|---|
| Control prompt | `tl01f-v1` |
| Control SHA256 | `7a9d27c3a9980893f18757d7a5fe0612cf67f9aad8dfd2ccb20f9e3c667b7143` |
| Candidate prompt | `tl01g-v1` |
| Candidate SHA256 | `3af1e470e304008d2490ba73e1a53628519c211bb54e17a10cd4c694beae9013` |
| Packet | `tl01c-packet-v1` |
| Renderer | `render_temporal_shadow_user_content_v2` |
| Model | `gpt-5.4-mini` |
| Prior live-smoke budget | 4/4 exhausted; do not edit or reuse its ledger |
| Prior V8–V13 / Adv V6–V11 | Retired observed regression only; never promotion authority |

`GROUNDING_PATH_READY` proves the shared smoke path can reach ordinary comparison.
It does **not** promote `tl01g-v1`, validate prior cohorts, or authorize changing the
exact grounding policy.

### Authority read order

Before changing files, read:

1. This handoff.
2. `Docs/Reports/REPORT-tl01g-grounding-path-recovery.md`.
3. `Docs/Reports/REPORT-tl01g-resolution-proof-abstention-gate.md`.
4. `tests/test_temporal_shadow_extraction_tl01g.py`.
5. `evals/graph_memory_layer/temporal_shadow_prompt_calibration.py`.
6. `tests/test_temporal_shadow_prompt_calibration.py`.
7. Existing V13/Adv V11 fixtures as defects to avoid, not templates to copy.

If any current-main contract differs materially from this mapping, stop and report
before implementation.

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Branch pickup | Old TL01 branches remain visible | Fresh worktree from this PR branch, rebased onto current main; old branches not imported | Yes | Git history / PR |
| V14 authoring | No fresh promotion holdout exists | New canonical holdout with genuinely new propositions and exact source spans, paired F/G cases, explicit gold audit | Yes | V14 fixture + tests |
| Adv V12 authoring | No fresh adversarial successor exists | New synthetic adversarial cohort with source and proposition-template novelty, paired F/G cases, explicit gold audit | Yes | Adv V12 fixture + tests |
| Pre-live integrity | Auto-discovery guards exist for versions above cutoffs | Explicit V14/V12 tests make every required freshness, Gate E3, value, pairing, and identity proof non-skippable | Yes | TL01G test suite |
| Seal | Prior observed cohorts have retired seals | One final commit freezes V14/V12/test bytes before any provider call | Yes | Git commit / seal verification |
| Live promotion | No authoritative TL01G promotion matrix exists | One exact 18-attempt matrix from one clean SHA; no retry | Yes | Calibration workflow |
| Provider unavailable | Prior runs could become misleading zero metrics | Failed attempts remain failures; comparison metrics remain unobserved; disposition is incomplete, not safe | Yes | manifests / aggregate / report |
| Shared grounding collapse | PR486 smoke is healthy, full cohort remains untested | If both lanes fail shared stages, do not call it candidate prompt failure | Yes | aggregate classification |
| Candidate semantic failure | No fresh isolated result exists | If control is evaluable and candidate uniquely fails semantic/temporal gates, report `ITERATE_PROMPT` | Yes | aggregate + report |
| Textual-only failure | Exact copying may remain a separate limitation | If semantics are correct and only textual copy/grounding blocks, report textual-normalization successor; do not mutate prompt or matcher | Yes | aggregate + report |
| Ready result | No current promotion authority | Report readiness only when all §6/§7 gates are observed and green | Yes | aggregate + report |
| Post-observation defect | Past cohorts were patched/retired after defects | Never patch or rerun; retire the fresh matrix as invalid/incomplete and stop | Yes | diff history / report |

### Ordered failure sequences

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| Old branch checkout → cherry-pick prior TL01 work → author V14 | Reject pickup; reset to fresh branch/current main | §7 branch ancestry and changed-path proof |
| Main advances → fixture authoring continues on stale base | Rebase before seal and rerun pre-live suite | §7 base/seal provenance |
| V14 reuses old semantic proposition or span | Fail before provider execution | Explicit V14 fingerprint tests |
| Adv V12 noun-swaps an old adversarial skeleton | Fail Jaccard/proposition-template gate before provider execution | Explicit Adv V12 novelty tests |
| Gold marks resulting state as boundary without transition narration | Fail positive Gate E3 audit before provider execution | Explicit start/end boundary tests |
| Gold uses rescheduled time as postponement occurrence | Fail proposition-first value audit before provider execution | Explicit postponement/value test |
| Provider attempt fails without response ID | Attempt still counts; manifest records failure; no retry | Matrix count/report inspection |
| Candidate and control both fail shared grounding | `PROMOTION_EVIDENCE_INCOMPLETE`, never isolated prompt verdict | Aggregate/report precedence |
| Provider results observed → gold defect discovered | No fixture edit or rerun; stop report and retire evidence | Git diff after provider SHA |
| Evidence committed → branch rebased/force-pushed | Prohibited; provider SHA must remain reachable | Git ancestry check |

## §4 Files in scope (allowlist)

Every changed path must be listed here or admitted by the two bounded source-file
exceptions below.

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-TIMELINE-tl01g-fresh-promotion-evidence.md` | Complete authority for this same-PR implementation |
| Modify | `tests/test_temporal_shadow_extraction_tl01g.py` | Add explicit, non-skippable V14/Adv V12 identity, freshness, pairing, audit, Gate E3, and value-grounding proofs |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_holdout_v14/README.md` | State fresh promotion role, seal protocol, and no-post-observation-edit rule |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_holdout_v14/GOLD-AUDIT.md` | Bind every assertion to proposition, status, lane, value, source phrase, refs, and Gate rationale |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_holdout_v14/base-contribution.json` | Fresh canonical assertions and owned evidence refs |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_holdout_v14/gold-overlay.json` | Human-reviewed temporal gold |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_holdout_v14/temporal-case-tl01f.json` | Frozen control case |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_holdout_v14/temporal-case-tl01g.json` | Frozen candidate case, byte-equivalent except identity fields |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_adversarial_v12/README.md` | State fresh synthetic adversarial role, seal protocol, and novelty requirements |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_adversarial_v12/GOLD-AUDIT.md` | Bind every adversarial assertion to expected abstention/resolution and evidence rationale |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_adversarial_v12/base-contribution.json` | Fresh synthetic assertions and owned evidence refs |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_adversarial_v12/gold-overlay.json` | Human-reviewed adversarial temporal gold |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_adversarial_v12/temporal-case-tl01f.json` | Frozen control adversarial case |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_adversarial_v12/temporal-case-tl01g.json` | Frozen candidate adversarial case |
| Modify if required | `.gitignore` | Unignore only the V14 promotion aggregate path below; no broader artifact exposure |
| Create | `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion-v14/calibration/aggregate.json` | Durable exact aggregate; prior promotion aggregate remains untouched |
| Create | `Docs/Reports/REPORT-tl01g-v14-fresh-promotion-evidence.md` | Durable provenance, result matrix, decision precedence, and roadmap disposition |

### Bounded discovery exception 1 — V14 source artifacts

```text
Directory: evals/graph_memory_layer/examples/temporal_shadow_holdout_v14/sources/
Maximum additional paths: 12
Allowed path kinds: UTF-8 Markdown files only
Decision rule: include only a source artifact directly referenced by at least one
               V14 evidence registry entry; every file must be named in GOLD-AUDIT.md.
```

### Bounded discovery exception 2 — Adv V12 source artifacts

```text
Directory: evals/graph_memory_layer/examples/temporal_shadow_adversarial_v12/sources/
Maximum additional paths: 10
Allowed path kinds: UTF-8 Markdown files only
Decision rule: include only a synthetic source artifact directly referenced by at
               least one Adv V12 evidence registry entry; every file must be named
               in GOLD-AUDIT.md.
```

No other discovery exception exists. If another file is required, stop and request a
re-brief before changing it.

## §5 Files and capabilities explicitly out of scope

| Path / capability | Why this slice must not touch or claim it |
|---|---|
| `src/graph_memory/temporal_shadow_extraction.py` | `tl01f-v1` and `tl01g-v1` are byte-frozen; prompt, packet, renderer, client, and grounding changes would destroy experiment isolation |
| `evals/graph_memory_layer/temporal_shadow_prompt_calibration.py` | Runner, thresholds, decision logic, provenance, and reaggregate semantics are predecessor contracts, not this capability |
| `tests/test_temporal_shadow_prompt_calibration.py` | Existing runner contract should be consumed unchanged; a required runner fix is a stop/split |
| `evals/.../temporal_shadow_holdout_v8` through `v13` | Observed/retired evidence; immutable |
| `evals/.../temporal_shadow_adversarial_v6` through `v11` | Observed/retired evidence; immutable |
| Existing `tl01g/promotion/calibration/aggregate.json` | Retained V13/Adv V11 diagnostic evidence; do not overwrite |
| PR486 smoke fixture or budget ledger | 4/4 exhausted diagnostic budget and evidence remain immutable |
| `src/graph_memory/kernel/**`, contribution/publication paths | No graph authority or producer cutover in TL01 evaluation |
| Timeline API, projection, event nodes, participant roles, UI | Separate product capabilities after temporal producer acceptance |
| `tl01h-v1` or any prompt revision | A new prompt requires fresh observed prompt-specific evidence and a separate handoff |
| Fuzzy/semantic phrase matching or normalization | Separate policy capability; no hidden relaxation of exact grounding |
| Any second PR or branch for this implementation | Operator explicitly requires the handoff and implementation to remain in this PR |

## §6 Implementation contract and conditional matrices

```text
Input:
  current-main TL01 calibration contracts
  frozen tl01f-v1 / tl01g-v1
  existing paired development cases
  newly authored fresh V14 / Adv V12 paired cases
  exact owned evidence spans and human-reviewed gold

Output:
  one sealed 18-attempt aggregate at promotion-v14/calibration/aggregate.json
  one report selecting exactly one roadmap disposition

Invariant:
  §1 merge-ready invariant, unchanged

Failure behavior:
  pre-live integrity failure        → no provider calls; repair before seal
  provider/infrastructure failure   → count attempt, no retry, PROMOTION_EVIDENCE_INCOMPLETE
  shared control/candidate failure  → PROMOTION_EVIDENCE_INCOMPLETE
  candidate semantic failure        → ITERATE_PROMPT
  textual-only exact-copy failure   → ADVANCE_TO_TEXTUAL_NORMALIZATION
  all promotion gates observed/green→ PROMPT_READY_FOR_BROADER_SHADOW
  post-observation cohort defect     → retire as invalid/incomplete; no patch, no rerun

Replay / idempotency:
  deterministic tests               → repeat freely before seal
  same live matrix                   → execute once only
  --reaggregate-only                → allowed only from the exact complete on-disk
                                      manifest set and performs zero provider calls
  changed fixture after observation → prohibited; successor cohort required

Trust boundary:
  Verifies: exact identities, paired bytes, cohort novelty, evidence ownership,
            gold/audit binding, Gate E3/value rules, seals, run matrix, provider SHA,
            aggregate metrics and failures
  Records without proving: provider semantic quality and natural-language rationale
  Rejects: stale/mutated cohorts, missing metrics presented as zero, shared failure
           presented as prompt failure, aliases/fallback evidence, post-hoc gold repair
```

### Commit point

```text
Commit point: first live provider attempt in the authorized calibration command
Before commit: cohort/test bytes may be corrected; no provider output exists
After commit: V14/Adv V12 fixture, gold, audit, case, and test bytes are immutable
Truthful post-commit failure: preserve manifests, consume the attempt, report incomplete
                               evidence, and do not retry or patch the cohort
```

### Provider-call budget

This is a new bounded promotion budget, separate from the exhausted PR486 smoke ledger.

```text
baseline development:  3 attempts
candidate development: 3 attempts
baseline holdout V14:   3 attempts
candidate holdout V14:  3 attempts
baseline Adv V12:       3 attempts
candidate Adv V12:      3 attempts
maximum total:         18 attempts
retries:                0
```

Every attempted provider call counts even when it returns no response ID. The live
command may be invoked once. An interrupted or partially failed matrix is not rerun in
this PR; it yields `PROMOTION_EVIDENCE_INCOMPLETE` unless the exact complete manifest
set already exists and only `--reaggregate-only` is needed.

### A. State and fallback matrix

| Observable path | Initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Stale/superseded | Retry/replay |
|---|---|---|---|---|---|---|---|
| Branch/base | Fetch + rebase current main | Clean fresh branch and recorded SHA | N/A | Git unavailable → stop | Old branch ancestry/import → reset/stop | Main moves before seal → rebase | Repeat before seal |
| V14/Adv V12 load | Parse exact files/refs | Paired F/G cases and owned spans validate | Missing ref/path → fail closed | Source file unavailable → fail | Digest/range/gold/audit mismatch → fail | Version ≤ cutoff → not fresh | Deterministic only |
| Freshness | Build cumulative prior pools | Semantic/span/template/source gates all pass | Any overlap is a failure | Prior corpus unavailable → stop | Non-numeric/missing version → fail closed | Prior cohorts remain immutable | Recompute before seal |
| Gate E3/value audit | Inspect every resolved boundary/value | Positive proposition-specific boundary and value proof | No proof → unresolved/NA gold or fail | Evidence unavailable → fail | Resulting-state/related-event substitution → fail | Old defective gold is regression only | Before seal only |
| Seal | Commit final fixture/test bytes | Full SHA recorded; clean worktree | N/A | Git unavailable → stop | Dirty/untracked input → stop | Main moved → rebase then reseal | New seal before calls only |
| Live matrix | Exact single command | 18 manifests and aggregate | Model abstention/miss is observed result | Provider error → incomplete | Seal/provenance mismatch → no calls or stop | Wrong SHA/case → fail closed | No live retry |
| Aggregate | Runner/reaggregate validates disk | Exact matrix, full provider SHA, metrics/failures preserved | Missing metric remains null/unobserved | Missing manifest → incomplete | Matrix mismatch/ambiguous manifests → fail | Old aggregate untouched | Reaggregate only, no calls |
| Report | Read exact aggregate/manifests | One precedence-based disposition | N/A | Evidence incomplete → incomplete | Contradiction → block merge | Superseded result remains history | No reinterpretation without evidence |

No fallback to prior cohorts, prior aggregates, label text, another evidence ref, source
filename, another prompt, latest run, or copied provider output is permitted.

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Prompt | Exact versions and frozen SHA256 values in §2 | Stop before provider | No |
| Packet/renderer | Exact `tl01c-packet-v1` and V2 renderer | Stop | No |
| Case pair | Same fixture bytes/IDs except `case_id` and `prompt_version` | Stop | No |
| Assertion | Exact assertion ID from base contribution | Stop | No |
| Evidence | Exact owned ref, path, digest, line range, normalized span hash | Stop | No |
| Cohort version | Exact numeric V14 / V12 above retired cutoffs | Stop | No |
| Semantic freshness | Exact semantic assertion fingerprints disjoint from cumulative prior pool | Stop | No |
| Span freshness | Exact normalized span SHA256 disjoint from cumulative prior pool | Stop | No |
| Proposition novelty | Entity-scrubbed label+predicate Jaccard `< 0.40` vs every prior and earlier fresh successor | Stop | No |
| Adversarial source novelty | Source/template Jaccard `< 0.40` plus proposition novelty | Stop | No |
| Seal | Full lowercase 40-character SHA containing exact fixture bytes | Stop | No |
| Provider execution | One clean full SHA across all manifests; seal is ancestor | Incomplete/stop | No |
| Provider response | Exact ID when supplied; missing remains missing | Record attempt without invention | No |
| Rename/rebind | Prohibited after seal | Stop | No |

First-win matching, aliases, normalized-label identity, and evidence substitution are
prohibited.

### C. Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay behavior | Compatibility/migration | Rollback/reversion |
|---|---|---|---|---|---|
| V14/Adv V12 fixtures | Checked-in JSON/Markdown + Git blobs | Exact case/base/gold/evidence bytes verified at seal/provider SHA | Never duplicate observed cohort under same version | Current schemas only; no migration | Revert before provider calls only |
| Cohort seal | Full Git commit SHA | All referenced bytes resolve identically | A new pre-live seal supersedes earlier draft seal | No abbreviated/ref seals | Reset before calls only |
| Per-run outcomes | Local `run-manifest.json` or `failure-manifest.json` | One unambiguous outcome per lane/cohort/repetition | Live replay prohibited | Existing schema | Preserve after attempts |
| Aggregate | New checked-in `promotion-v14/calibration/aggregate.json` | Exact matrix and provider SHA reconstruct from local manifests | `--reaggregate-only` may rewrite equivalent aggregate without calls | Existing aggregate schema | Revert artifact commit; observed source remains reportable |
| Report | Checked-in Markdown | Faithfully names SHA, IDs, counts, null/unobserved fields, and decision | Amend only for review accuracy, not new evidence | No machine-loader contract | Revert report commit |
| Handoff | This checked-in file | Same PR/branch remains authority | No replacement PR/handoff | No migration | Re-brief before calls only |
| Branch history | Git commits in this PR | Seal/provider SHA remain reachable | No rebase/force-push after calls | History-preserving merge only if late main update required | Revert commits, never rewrite observed SHA |

No new public schema or runtime identifier is introduced.

### D. Predecessor-to-consumer mapping

**Grounding sources:** frozen prompt registry, paired TL01 cases, current calibration
runner/schema, TL01G integrity tests, PR468 report, PR486 grounding report.

| Predecessor field/outcome | Real shape / optionality | This slice behavior | Transformation | Proof |
|---|---|---|---|---|
| `tl01f-v1` / `tl01g-v1` | Exact registry versions + SHA256 | Control/candidate identities | None | Frozen-hash tests |
| packet/renderer identity | Exact constants/callable | Same rendered payload path | None | Registry/render equality tests |
| `GROUNDING_PATH_READY` | Four EVALUABLE smoke lanes on one clean SHA | Satisfies shared-path prerequisite only | No promotion inference | PR486 report + grounding tests |
| development F/G cases | Existing paired cases | Baseline/candidate development lanes | None | Pair-equivalence validation |
| V14/Adv V12 cases | New F/G paired files | Holdout/adversarial lanes | Prompt identity only | Explicit new tests |
| `provider_response_id` | Optional string in manifests | Record exact value when present | None | Aggregate/report inspection |
| failure counts | Nullable/unobserved where runs fail | Preserve null/unobserved; never sum as observed zero | Existing aggregation | Aggregate tests/inspection |
| `CalibrationDecision` | Existing machine decision | Input to human precedence, never sole authority | Bounded mapping below | Report rubric |
| retired V13/Adv V11 | Immutable regression evidence | Excluded from promotion authority | None | Diff/allowlist scan |

### Roadmap disposition precedence

The report must select exactly one:

1. **`PROMOTION_EVIDENCE_INCOMPLETE`** when seals, integrity, provenance, provider
   availability, exact run matrix, or shared control/candidate evaluability is not
   established. Missing metrics are not safety evidence.
2. **`ADVANCE_TO_TEXTUAL_NORMALIZATION`** when control and candidate temporal
   semantics/values/statuses are otherwise correct and the only demonstrated blocker
   is exact textual phrase/copy grounding. Do not relax the matcher in this PR.
3. **`ITERATE_PROMPT`** when the fresh matrix isolates candidate-specific semantic,
   status, lane, temporal-value, source-time licensing, or unsafe over-resolution
   defects. Name the observed rows and leave `tl01h-v1` unimplemented.
4. **`PROMPT_READY_FOR_BROADER_SHADOW`** only when all readiness conditions below
   are observed and green.

Readiness requires, at minimum:

- exact frozen identities and verified seals;
- all six lane/cohort cells present at three repetitions;
- one clean provider execution SHA and comparison metrics observed;
- machine decision `PROMPT_READY`;
- candidate `unsafe_over_resolution == 0`;
- candidate `wrong_temporal_value == 0`;
- candidate source leakage, evidence-selection mismatch, foreign-evidence attempts,
  grounding failures, model-output failures, contract failures, and evidence failures
  all equal zero;
- required development/holdout exact-match and status thresholds satisfied by the
  unchanged runner;
- no post-observation fixture/gold/audit/test mutation;
- report and aggregate agree exactly.

A control failure may still be useful regression evidence, but shared collapse or
missing comparison blocks promotion authority.

## §7 Evidence required to merge

### Evidence ledger

| Guarantee / invariant clause | Owning boundary | Evidence class | Command/scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Fresh branch from current main; old work not imported | Git/PR | provenance | §0 commands; `git log --first-parent`; `git diff --name-only` | Recorded current-main base; only this branch commits | Old branch merge/cherry-pick or stale base |
| Frozen F/G prompt identities unchanged | registry/tests | contract | focused TL01G tests | Exact hashes in §2 | Any hash or prompt-byte change |
| Packet/renderer unchanged and F/G payloads paired | extraction tests | contract | focused TL01G tests | Same packet/renderer/rendered content | Any mismatch |
| V14 semantic and exact span freshness | V14 fixture/tests | adversarial | explicit V14 fingerprint tests | Disjoint cumulative sets | Any overlap/missing span |
| V14 proposition novelty | V14 tests | adversarial | explicit Jaccard test | Every score `< 0.40` | Any score `>= 0.40` |
| Adv V12 source and proposition novelty | Adv fixture/tests | adversarial | explicit source + proposition Jaccard tests | Every score `< 0.40`; no old template replay | Any overlap/replay |
| Reserved vocabulary and anti-oracle separation | prompt/cohort tests | regression | focused TL01G tests | Prompt terms absent from cohorts and cohort terms absent from prompt/prior pools | Contamination |
| Paired case equivalence | calibration workflow/tests | contract | existing pair validator + focused tests | F/G differ only by case/prompt identity | Any other diff |
| GOLD-AUDIT binds every row | audit tests | contract | explicit audit↔fixture test | IDs/status/proposition/lane/value/phrase/refs match | Missing/stale audit row |
| Gate E3 positive boundary proof | V14 gold/evidence tests | adversarial | explicit start/end tests | Every non-null valid boundary has direction-compatible proposition-specific transition phrase and grounded value | Resulting-state/restatement or unrelated cue |
| Proposition-first value grounding | V14/Adv tests | adversarial | explicit value/postponement tests | Value temporally modifies selected proposition | Related event/reschedule time substituted |
| No live call before seal | Git history + manifests | provenance | inspect earliest provider SHA and seal ancestry | Seal commit precedes every manifest | Provider output before final seal |
| One clean exact provider SHA | calibration workflow | provenance | live command; reaggregate verification | Full 40-char SHA shared by all 18 manifests | Multiple/dirty/missing SHAs |
| Maximum 18 attempts, zero retry | run matrix/report | budget | inspect manifest directories and provider IDs | Exactly one outcome for each of 18 specs; no run-04 or second matrix | >18 attempts or rerun |
| Failures remain explicit | manifests/aggregate | failure injection/inspection | inspect aggregate run records | Null/unobserved metrics and failure diagnostics preserved | Failure totaled as observed zero |
| Prior observed cohorts and aggregate untouched | repository diff | regression | `git diff <base>...HEAD --` denylist | No bytes changed | Any prior-cohort/aggregate edit |
| One truthful disposition | report | acceptance | compare report to aggregate/manifests | Precedence applied exactly | Unsupported promotion/iteration claim |
| Same PR/branch used throughout | PR | process | PR commit history and changed paths | All nano commits in this PR; no sibling implementation PR | Work dispatched elsewhere |

### Required pre-live commands

Run from the fresh rebased worktree before authoring:

```bash
git fetch --prune origin
git rebase origin/main
git status --short
git rev-parse HEAD
git rev-parse origin/main
git merge-base --is-ancestor origin/main HEAD
```

After authoring V14/Adv V12 and explicit tests, but before the seal/provider call:

```bash
uv run pytest -q tests/test_temporal_shadow_extraction_tl01g.py
uv run pytest -q tests/test_temporal_shadow_prompt_calibration.py
uv run pytest -q tests/test_temporal_shadow_grounding_path.py
uv run pytest -q \
  tests/test_temporal_shadow_extraction.py \
  tests/test_temporal_shadow.py \
  tests/test_graph_kernel_temporal.py
uv run ruff check tests/test_temporal_shadow_extraction_tl01g.py
git diff --check
git status --short
```

The V14/V12-specific tests must execute and pass; they may not skip because the
cohort is absent. Record exact test counts and provenance.

### Seal protocol

When all pre-live tests are green:

```bash
git add \
  tests/test_temporal_shadow_extraction_tl01g.py \
  evals/graph_memory_layer/examples/temporal_shadow_holdout_v14 \
  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v12
git commit -m "test(timeline): seal fresh v14 and adversarial v12 cohorts"
git status --short
SEAL_SHA="$(git rev-parse HEAD)"
test "$(printf %s "$SEAL_SHA" | wc -c)" -eq 40
```

`SEAL_SHA` must be clean and must contain the exact current V14/V12/test bytes.
Immediately before live execution, rerun the focused TL01G and calibration tests from
that exact commit. If any file changes, create a new pre-live seal commit and rerun all
pre-live proofs. No provider call may exist yet.

### Authorized live command — invoke once

```bash
SEAL_SHA="$(git rev-parse HEAD)"

uv run python evals/graph_memory_layer/temporal_shadow_prompt_calibration.py \
  --development-case \
    evals/graph_memory_layer/examples/temporal_shadow_cohort/temporal-case-tl01f.json \
  --candidate-development-case \
    evals/graph_memory_layer/examples/temporal_shadow_cohort/temporal-case-tl01g.json \
  --holdout-case \
    evals/graph_memory_layer/examples/temporal_shadow_holdout_v14/temporal-case-tl01f.json \
  --candidate-holdout-case \
    evals/graph_memory_layer/examples/temporal_shadow_holdout_v14/temporal-case-tl01g.json \
  --baseline-adversarial-case \
    evals/graph_memory_layer/examples/temporal_shadow_adversarial_v12/temporal-case-tl01f.json \
  --adversarial-case \
    evals/graph_memory_layer/examples/temporal_shadow_adversarial_v12/temporal-case-tl01g.json \
  --model-id gpt-5.4-mini \
  --repetitions 3 \
  --experiment-role promotion \
  --output-dir \
    evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion-v14 \
  --holdout-seal-commit "$SEAL_SHA" \
  --adversarial-seal-commit "$SEAL_SHA"
```

Expected maximum: **18 provider attempts**. Do not invoke this command again.
Do not print or commit API keys. Use the repository-root environment loading contract.

If every exact manifest exists but only aggregate construction failed, the following
zero-provider operation is permitted once after fixing no code/fixture files:

```bash
# Same arguments as above, plus:
--reaggregate-only
```

If the manifest set is partial, ambiguous, or includes another execution SHA, stop.

### Post-live verification

```bash
uv run pytest -q tests/test_temporal_shadow_extraction_tl01g.py
uv run pytest -q tests/test_temporal_shadow_prompt_calibration.py
uv run pytest -q tests/test_temporal_shadow_grounding_path.py
uv run ruff check tests/test_temporal_shadow_extraction_tl01g.py
git diff --check

git diff --name-only <REBASED_BASE_SHA>...HEAD
git diff --stat <REBASED_BASE_SHA>...HEAD -- \
  Docs/Plans/HANDOFF-TIMELINE-tl01g-fresh-promotion-evidence.md \
  tests/test_temporal_shadow_extraction_tl01g.py \
  evals/graph_memory_layer/examples/temporal_shadow_holdout_v14 \
  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v12 \
  evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion-v14/calibration/aggregate.json \
  Docs/Reports/REPORT-tl01g-v14-fresh-promotion-evidence.md \
  .gitignore

git merge-base --is-ancestor "$SEAL_SHA" HEAD
```

Inspect and record:

- exact 18 lane/cohort/repetition outcomes;
- exact provider attempt count and every available response ID;
- full provider execution SHA set, expected singleton;
- prompt hashes, packet, renderer, model, seal SHAs, case digests, calibration ID;
- candidate and control success/failure counts by cohort;
- unsafe over-resolution, wrong value, wrong lane/status, leakage, evidence,
  grounding, model-output, contract, and provider failure totals;
- which metrics are null/unobserved;
- machine decision and human precedence result;
- confirmation that V14/V12 bytes did not change after the first provider attempt.

### Minimal live proof

```text
Existing surface used: temporal prompt calibration CLI
Smallest realistic scenario: one complete paired development/V14/AdvV12 matrix,
                             three repetitions, both control and candidate
Expected observation: exact sealed manifests and one aggregate supporting a bounded
                      roadmap disposition
Evidence captured: aggregate.json, local run/failure manifests, report, full Git SHAs,
                   provider response IDs when available
```

This is an evaluation workflow, not a product UI or graph publication surface.

### Baseline failure protocol

Any required command failing on the rebased base must be rerun on base and head. Record
whether the branch adds failures. A baseline failure does not become green through
wording; an explicit operator waiver is required if it remains an acceptance gate.

## §8 Required review handback

The code agent must return:

1. Exact PR URL, branch, and reviewed head SHA.
2. Confirmation that no second implementation PR or branch was opened.
3. Initial base `4811741…`, exact rebased `origin/main` base, seal SHA, provider execution SHA, and final head.
4. Old working branches/worktrees retired, or exact permission/unique-work reason one could not be deleted.
5. §1 mission and invariant copied exactly.
6. Nano-commit list and discrete story for each commit.
7. Actual changed paths and focused diff stat against the rebased base.
8. Complete §7 evidence ledger with exact results and provenance.
9. Exact pre-live and post-live command outputs.
10. Provider attempt count, response IDs when present, and proof of no retry.
11. Full six-lane × three-repetition outcome table.
12. Aggregate identity and every decision diagnostic, including null/unobserved metrics.
13. Confirmation that all prior cohorts, old aggregate, frozen prompts, packet, renderer, runner, thresholds, and graph code are unchanged.
14. Confirmation that V14/Adv V12/test bytes did not change after the first provider attempt.
15. Exactly one roadmap disposition with precedence reasoning.
16. Baseline failures, waivers, stop conditions, and paths outside §4; use `none` when none exist.
17. Named successor that remains unimplemented.

## §9 Acceptance rubric

The reviewer accepts only when every applicable item is true:

- [ ] This PR, and no other PR, contains the complete handoff, implementation, evidence, and review-response history.
- [ ] The implementation began from a fresh worktree and a rebase onto current main; no old TL01 branch was imported.
- [ ] Old working branches were retired or a precise permission/unique-work exception is documented.
- [ ] Exactly one capability was delivered: trustworthy fresh promotion evidence for frozen `tl01g-v1`.
- [ ] Frozen prompt hashes, packet, renderer, runner, thresholds, and graph authority remain unchanged.
- [ ] V14 and Adv V12 pass explicit paired-case, semantic, span, vocabulary, source-template, proposition-template, audit-binding, Gate E3, and value-grounding tests before provider execution.
- [ ] The seal commit is a clean full SHA, contains all final cohort/test bytes, and is an ancestor of the provider execution SHA and final head.
- [ ] The authorized live command ran at most once and consumed no more than 18 attempts.
- [ ] Every expected run has exactly one manifest; every failed attempt remains explicit and is not totaled as observed safety.
- [ ] The aggregate uses one full provider execution SHA and the exact six-lane/three-repetition matrix.
- [ ] Prior observed cohorts and the V13/Adv V11 aggregate are byte-unchanged.
- [ ] No fixture/gold/audit/test byte changed after the first provider attempt.
- [ ] The report agrees with the aggregate and applies the §6 disposition precedence exactly.
- [ ] `PROMPT_READY_FOR_BROADER_SHADOW` is claimed only if every readiness requirement is observed and green.
- [ ] No second public/durable contract, prompt version, cohort retry, product surface, or graph write was introduced.
- [ ] Every §7 command has an exact produced result and provenance, or an explicit operator waiver.
- [ ] No path outside §4 changed.
- [ ] The named successor remains false and unimplemented.

## Stop conditions

Stop and report rather than expanding if any of the following occurs:

- current `main` cannot be cleanly rebased before fixture authoring;
- an old branch contains unique work the operator has not reviewed for salvage;
- another active TL01G promotion PR or V14/Adv V12 cohort appears;
- a required path falls outside §4 or the bounded source exceptions;
- frozen prompt, packet, renderer, schema, runner, threshold, or graph changes appear necessary;
- V14/Adv V12 cannot pass semantic/span/template independence without weakening gates;
- Gate E3 or temporal-value gold cannot be positively defended from owned evidence;
- a source or gold defect is discovered after the first provider attempt;
- provider execution exceeds 18 attempts, is retried, uses multiple SHAs, or leaves an ambiguous/partial matrix;
- comparison metrics are unobserved and a report attempts to treat them as zero/safe;
- control and candidate share a failing stage but the report attempts an isolated candidate verdict;
- branch history is rebased, squashed, amended, or force-pushed after provider observation;
- implementation moves to another PR or branch;
- evidence cannot support exactly one disposition under §6 precedence.

Use this stop report shape:

```text
Stop condition:
Why the current mission cannot absorb it:
Invariant clause affected:
Required evidence now missing:
New public/durable contract discovered:
Affected observable paths or ownership layers:
Provider attempts already consumed:
Cohort/provider SHAs involved:
Proposed successor slice:
Tracker/roadmap or operator decision needed:
```
