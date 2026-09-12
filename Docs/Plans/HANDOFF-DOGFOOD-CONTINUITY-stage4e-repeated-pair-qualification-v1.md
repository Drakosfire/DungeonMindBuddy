# HANDOFF — DOGFOOD-CONTINUITY: Stage 4E repeated extraction-pair qualification

**Created:** 2026-09-12  
**Status:** DONE — PR #707 MERGED; LIVE REPEATED RUN PASS
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4e-repeated-pair-qualification-v1.md`  
**Conversation/workstream:** `C1/C2 demo-readiness / Stage 4 WOW recovery / ingestion-quality experiment program`  
**Flow / owner:** `DOGFOOD-CONTINUITY` / repeated Extraction Lab qualification  
**Direction:** DESIGN → CODE → REVIEW  
**Base revision:** `4af440b2cc4102972ad6212590885248e58375c1` (main after PR #706 merge)  
**Branch:** `dogfood-continuity/stage4e-repeated-pair-qualification-impl`
**PR title:** `DOGFOOD-CONTINUITY: qualify extraction variance across repeated pairs`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Product sequence: [`Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`](../Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md). Benchmark authority: [`Docs/Design/DESIGN-benchmark-philosophy-and-goals.md`](../Design/DESIGN-benchmark-philosophy-and-goals.md). Execution predecessor: [`HANDOFF-DOGFOOD-CONTINUITY-stage4d-isolated-experiment-pair-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-stage4d-isolated-experiment-pair-v1.md).

## §0 Program position and sequencing correction

PR #706 / Stage 4D / P0b1 merged at `4af440b2cc4102972ad6212590885248e58375c1`, accepted head `97df142cfee328c689a32ced19cfe2a9755f1b98`, after 2 review cycles. It established one bounded, exact, dry-run-by-default baseline/candidate execution pair with fresh isolated stores/caches, observed execution provenance, Extraction Lab scoring, PR #705 comparison, and fail-closed receipts.

The earlier P0b2 label bundled too many independent capabilities: repetitions, aggregation, resume, budget policy, and asynchronous lifecycle. Split it now.

```text
P0a   trustworthy cross-contract comparison              DONE — PR #705
P0b1  one bounded isolated baseline/candidate pair       DONE — PR #706
LIVE  one-source paid Stage 4D smoke                     DONE — 2026-09-12
P0b2a repeated-pair qualification + variance summary     DONE — PR #707
P0b2b resumable/budget-aware lifecycle                   later
P0b2c async OpenAI Batch/event-driven execution          later if justified
P1    representative development-cohort characterization
P2    bounded extraction ablations, evidence-selected
P3    frozen validation + qualitative qualification
P4    full-corpus rehearsal into disposable authorities
P5    governed durable source adoption / World publication
P6    baseline-vs-final analysis and remaining gaps
```

PR #707 merged at `4227f97da35e384e995263d5c6a62d9711333488` with accepted head `4ca2c12c3ad15e6e6c18b0fab8fb5acb2a76ebcc` after 2 formal review cycles. Its exact-merge three-repetition Session 23 run passed on 2026-09-12: 3/3 pairs completed, all comparisons were comparable, identity stayed pinned, observed models were consistently `gpt-5.3-codex`, and total cost was `$2.7019`. This qualifies P0 operation, not extraction quality or Stage 4 WOW.

### Why this split

The next unanswered question is not yet “how do we schedule many experiments?” It is:

> If the same bounded pair is run repeatedly with fresh isolated caches, how much do its benchmark outcomes, anchor failures, cost, and runtime vary?

Without that answer, automated ranking or broad orchestration can overreact to stochastic noise. This slice makes repeated evidence interpretable before adding resumability, larger cohorts, or asynchronous scheduling.

---

## §1 Pre-dispatch gate — Stage 4D live smoke is mandatory

**Do not implement this slice until the Stage 4D post-merge paid smoke has been performed against the exact PR #706 merge SHA.** PR #706 explicitly made that smoke the gate before P0b2 work.

Required smoke shape:

```text
repository SHA:
  4af440b2cc4102972ad6212590885248e58375c1

source:
  Longmont Campaign/Campaign 2/Session Recaps/Session 23 - Mireward Gate.md

surface:
  core_extraction

baseline:
  batch_size = 5
candidate:
  batch_size = 4

execution:
  realtime
  repetitions = 1
  isolated caches
  unchanged Buddy MODEL_POLICY
```

Before implementation begins, amend this handoff with a **Smoke Gate Record** containing:

```text
operator/date
exact merge SHA
pair manifest SHA-256
experiment receipt path or durable evidence pointer
receipt status
comparison comparable=true/false
observed entity/fact model IDs
actual total token/cost/runtime telemetry
whether APP-STATE, DungeonMind, corpus, gold, MODEL_POLICY remained unchanged
failure classification if not successful
```

Dispatch rules:

- orchestration/receipt/provenance failure → **STOP**; repair Stage 4D instead of implementing Stage 4E;
- comparator non-comparable → **STOP**; repair benchmark provenance instead;
- ingestion crash common to the pair → classify that blocker first;
- poor extraction quality with a completed/comparable receipt → **does not block Stage 4E**; that is exactly the evidence this program is meant to characterize;
- completed/comparable smoke with trustworthy telemetry → Stage 4E may dispatch.

### Smoke Gate Record

**PASS — 2026-09-12, operator: Codex with explicit user authorization.**

- exact PR #706 merge SHA: `4af440b2cc4102972ad6212590885248e58375c1`
- pair manifest SHA-256: `e8721e6833a81e051ed17b31d60f27f7c5e30110a82e0babf2f4667d844d08d9`
- execution receipt path at smoke time: `/tmp/dmb-stage4d-live-smoke-20260912/experiment_receipt.json`; the raw temporary receipt was not retained, and this checked-in, sanitized Smoke Gate Record is explicitly the accepted durable evidence artifact for dispatch/review
- receipt `completed`; comparison `comparable=true`
- observed entity/fact model, both variants: `gpt-5.3-codex`
- actual pair telemetry: 79,720 input tokens; 57,119 output tokens; 44,800 cached tokens; 33 API calls; `$0.8686`; 99.15 seconds summed variant runtime
- baseline: `$0.4298`, 53.194 seconds; candidate: `$0.4388`, 45.956 seconds
- clean pinned worktree remained at the exact merge SHA; source, entity gold, fact gold, and `MODEL_POLICY.json` post-run hashes matched their receipt pins; APP-STATE and DungeonMind were not invoked or mutated
- classification: orchestration/provenance PASS. Poor anchor quality is intentionally not a machinery failure and makes no claim that either batch size is better.

---

## §2 Mission and merge-ready invariant

**Mission:** An operator can repeat one already-valid Stage 4D pair experiment a small fixed number of times with fresh isolated stores/caches and receive one deterministic experiment-level qualification artifact that shows run-to-run variability in benchmark metrics, anchor outcomes, cost, and runtime without collapsing the evidence into a winner or promotion decision.

**Merge-ready invariant:** Every repetition consumes the exact same Stage 4D pair-manifest bytes and pinned repository/source/gold/policy identity, executes through the existing Stage 4D runner into a fresh non-overlapping output root, and must itself finish `completed` with PR #705 `comparable=true`. The repeated experiment is `completed` only when **all** requested repetitions qualify and the cross-repetition execution identity remains consistent. Aggregates are descriptive only: per-run values plus mean/min/max/population-standard-deviation and anchor stability counts. Any failed/non-comparable/drifted repetition makes the repeated experiment non-success and never produces a winner/READY/promotion claim.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every changed layer? | Yes. Manifest, repeated execution, cross-run qualification, aggregation, report, and receipt all serve “repeat the exact same pair and describe variability truthfully.” |
| Most likely adversarial sequence | rep 1 qualifies → rep 2 observes a different model or benchmark identity → rep 3 would still be expensive → aggregator averages incompatible runs and looks authoritative. |
| Will §8 detect that failure? | Yes. Tests must inject benchmark/model drift in rep 2, prove fail-fast before rep 3, preserve rep 1, and prohibit a completed aggregate. |
| Easiest boundary to under-test | Anchor-level stability. Aggregate recall can look stable while different anchors flip pass/fail between runs. |
| Fact that forces stop/split | Need for resume, continue-after-failure, larger than Stage 4D's 1–3 source cohort, async Batch jobs, model/prompt mutation, or budget scheduling. Those are successors. |

---

## §3 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | Stage 4 WOW HOLD from PR #704; comparison authority PR #705; bounded pair execution PR #706. |
| Base revision | `4af440b2cc4102972ad6212590885248e58375c1` |
| Completed predecessor | PR #706 merged; accepted head `97df142cfee328c689a32ced19cfe2a9755f1b98`; 2 review cycles; live paid smoke still pending at design time. |
| Exact predecessor consumed | `extraction_lab.pair_experiment_manifest.load_pair_experiment_manifest`; `extraction_lab.run_pair_experiment.run_pair_experiment`; Stage 4D `experiment_receipt.json`; PR #705 `comparison.json`. |
| Exact input consumed | One repeat-experiment manifest pointing at one immutable Stage 4D pair manifest. |
| Named successor | P0b2b resumable/budget-aware repeated-experiment lifecycle. |
| What remains false | No resume; no continue-on-failure; no async Batch; no 10–20 document cohort; no prompt/model/taxonomy A/B; no automatic winner; no holdout qualification; no publication. |
| Explicit non-goals | No changes to ingestion prompts, taxonomy, gold, corpus, `MODEL_POLICY.json`, APP-STATE, DungeonMind, Stage 4 UI, or PR #705 comparison semantics. |
| Branch / isolated checkout | `dogfood-continuity/stage4e-repeated-pair-qualification-v1` from exact base above. Implementation only after §1 smoke gate is satisfied. |
| Runtime/state ownership | Operator-selected fresh repeat root; each repetition owns a fresh Stage 4D subroot and therefore fresh baseline/candidate stores and `.cache` trees. |
| Parallel lanes / collision hotspots | `extraction_lab/**`, `tests/extraction_lab/**`, roadmap/steward files. Do not change `tools/batch_ingest_corpus.py`, `src/ingestion/**`, or model policy. |
| State-authority sync after implementation | Record #706 merged/PASS + exact smoke disposition; set Stage 4E/P0b2a current. Stage 4/WOW remains HOLD. |

### Existing machinery to reuse

Do not duplicate or weaken:

- Stage 4D pair manifest validation;
- Stage 4D exact pinning and drift checks;
- Stage 4D dry-run/`--execute` safety;
- Stage 4D fresh store/cache semantics;
- Extraction Lab scoring;
- PR #705 cross-contract comparator.

Stage 4E is a thin repeated-experiment layer above one accepted Stage 4D pair.

---

## §4 Public operator contract

### Repeat manifest v1

Create a new wrapper schema rather than changing the Stage 4D pair schema:

```json
{
  "schema": "dmb_extraction_repeat_experiment_v1",
  "experiment_id": "stage4e-s23-variance",
  "pair_manifest": "./stage4d-s23-pair.json",
  "repetitions": 3
}
```

Required semantics:

- `schema` exactly `dmb_extraction_repeat_experiment_v1`;
- `experiment_id` non-empty;
- `pair_manifest` resolves to one readable Stage 4D `dmb_extraction_pair_experiment_v1` manifest;
- pair manifest bytes are hashed once and remain unchanged for the repeated experiment;
- pair manifest must itself validate through the existing Stage 4D loader;
- `repetitions` is bounded to **2 or 3** for P0b2a;
- pair manifest retains Stage 4D's own 1–3 source cap and isolated/realtime/one-pair semantics;
- unknown fields fail closed.

Do **not** add repeated-experiment copies of corpus paths, gold paths, variants, model policy, or repository SHA. The Stage 4D pair manifest remains the single source of truth for the pair being repeated.

### CLI

Preferred entrypoint:

```bash
uv run python -m extraction_lab.run_repeat_experiment \
  --manifest <REPEAT_MANIFEST.json> \
  --out-dir <FRESH_REPEAT_ROOT>
```

Default behavior is inert:

```text
validate repeat manifest
load + validate referenced Stage 4D pair manifest
verify current repo/pair preconditions using Stage 4D dry-run path
print normalized repeated execution plan
perform zero model calls
create no repeat output root
```

Paid execution requires explicit:

```bash
uv run python -m extraction_lab.run_repeat_experiment \
  --manifest <REPEAT_MANIFEST.json> \
  --out-dir <FRESH_REPEAT_ROOT> \
  --execute
```

No environment variable may silently turn dry-run into execution.

### Fixed execution order

P0b2a uses:

```text
rep-001: baseline → candidate
rep-002: baseline → candidate
rep-003: baseline → candidate
```

Do not add randomization/alternating order in this slice. Record fixed order as a known limitation. If later evidence suggests temporal/order effects, that becomes a bounded successor rather than silent complexity here.

---

## §5 Execution semantics

### Fresh independent repetitions

For each repetition:

```text
<repeat-root>/rep-001/
  <complete Stage 4D experiment root>
<repeat-root>/rep-002/
  <complete Stage 4D experiment root>
<repeat-root>/rep-003/
  <complete Stage 4D experiment root>
```

Each repetition must call the existing Stage 4D `run_pair_experiment(...)` contract with:

- the exact same pair-manifest path and bytes;
- `execute=True` only when the top-level command received `--execute`;
- a fresh, absent per-repetition output root;
- the same current repository checkout;
- no store/cache reuse between repetitions.

Because Stage 4D creates fresh baseline/candidate stores, P0b2a naturally produces isolated caches across both variants **and** across repetitions.

### Fail-fast rule

P0b2a is deliberately fail-fast.

If repetition N fails, is non-comparable, or violates cross-repetition identity:

- preserve all completed prior repetition artifacts;
- mark the repeated experiment `failed`;
- mark repetition N failed with exact child failure evidence;
- do not start repetition N+1;
- do not call a partial experiment “qualified”;
- partial descriptive values may be retained under an explicitly `partial` section, but must not be emitted in the same fields used by a completed qualification artifact.

Continue-on-failure and resume are P0b2b.

### Cross-repetition qualification

After each child Stage 4D receipt completes, verify:

1. child receipt schema/status are expected and `status=completed`;
2. child comparison has `comparable=true`;
3. child pair-manifest SHA equals the repeat experiment's pinned pair-manifest SHA;
4. repository SHA is identical across repetitions;
5. corpus/source locators and source-byte fingerprints are identical;
6. entity/fact gold fingerprints are identical;
7. model-policy fingerprint is identical;
8. surface is identical;
9. baseline observed entity/fact model IDs match baseline observed IDs from repetition 1;
10. candidate observed entity/fact model IDs match candidate observed IDs from repetition 1;
11. benchmark corpus and gold fingerprints for each side are identical across repetitions.

Do not require identical store hashes, extracted entity/fact counts, benchmark scores, anchor outcomes, token counts, cost, or runtime; those are the stochastic quantities being measured.

If an identity field above changes, fail with an explicit reason such as:

```text
repeat_pair_manifest_changed
repeat_repository_identity_mismatch
repeat_source_identity_mismatch
repeat_gold_identity_mismatch
repeat_model_policy_mismatch
repeat_observed_model_mismatch
repeat_benchmark_identity_mismatch
```

---

## §6 Repeated qualification artifact

Write:

```text
<repeat-root>/repeat_receipt.json
<repeat-root>/qualification.json
<repeat-root>/report.md
```

### `repeat_receipt.json`

Minimum semantic content:

```text
schema: dmb_extraction_repeat_receipt_v1
experiment_id
repeat_manifest_sha256
pair_manifest_path
pair_manifest_sha256
status: running | failed | completed
started_at / completed_at
requested_repetitions
completed_repetitions
repository_sha
source/gold/model-policy identity summary
fixed execution order
repetitions:
  - index
    status
    child_root
    child_receipt_path
    child_receipt_sha256
    comparable
    failure if any
failure if any
qualification_path if completed
```

### `qualification.json`

Only write/finalize the completed qualification section when every requested repetition qualifies.

Schema concept:

```text
schema: dmb_extraction_repeat_qualification_v1
repetition_count
benchmark_identity
execution_identity
metrics:
  <metric_name>:
    baseline: {values, mean, min, max, pstdev}
    candidate: {values, mean, min, max, pstdev}
    delta: {values, mean, min, max, pstdev, positive_count, zero_count, negative_count}
anchors:
  entity:
    <anchor_id>:
      baseline_pass_count
      baseline_pass_rate
      candidate_pass_count
      candidate_pass_rate
      transition_counts: {improved, regressed, unchanged}
      baseline_fail_bucket_counts
      candidate_fail_bucket_counts
  fact:
    same
telemetry:
  baseline:
    cost_usd: {values, total, mean, min, max}
    elapsed_seconds: {values, total, mean, min, max}
    input_tokens/output_tokens/cached_tokens/api_calls: same useful summaries
  candidate:
    same
pair_total:
    cost_usd total/mean
    elapsed_seconds total/mean
limitations:
  fixed baseline→candidate order
  small N descriptive only
  isolated/cold local caches
```

### Statistics contract

Use deterministic descriptive statistics only:

- exact per-repetition values;
- arithmetic mean;
- minimum;
- maximum;
- population standard deviation (`pstdev`), with no inferential significance claim;
- sign counts for metric deltas.

Do not emit:

- p-values;
- confidence intervals pretending N=2/3 is sufficient;
- “statistically significant”;
- “winner”;
- `READY`;
- candidate promotion;
- a weighted composite quality score.

### Metric authority

Aggregate only the metric fields already emitted by PR #705's comparison artifact unless the benchmark authority is separately amended:

```text
entity_anchor_recall
fact_anchor_recall
unresolved_core_anchors
total_entity_count
total_fact_count
```

Do not invent new quality metrics inside the repeated-run orchestration layer.

### Anchor authority

Aggregate the PR #705 `anchor_transitions` plus each underlying Extraction Lab result row. The important output is stability, not merely net recall.

Examples the artifact should make obvious:

```text
brin_identity:
  baseline pass 1/3
  candidate pass 3/3
  transitions: improved=2 unchanged=1 regressed=0

orrik_mayor_fact:
  baseline pass 2/3
  candidate pass 2/3
  transitions: improved=1 regressed=1 unchanged=1
```

The second example is not a candidate win; it is unstable evidence.

---

## §7 Cost and execution safety

P0b2a does not yet implement dynamic budget scheduling. Safety comes from hard bounding:

- 1–3 source files inherited from Stage 4D;
- exactly two variants inherited from Stage 4D;
- 2–3 repetitions only;
- synchronous realtime only;
- dry-run by default;
- explicit `--execute` required;
- fail-fast on first failed repetition;
- no automatic retry.

The dry-run plan must state the maximum planned work explicitly:

```text
repetitions
variant runs = repetitions * 2
source ingestions = repetitions * 2 * source_count
cache policy = isolated
```

It should also display the Stage 4D smoke's actual cost/runtime as operator context **only if the smoke record has been supplied as durable input**. Do not fabricate a future cost estimate from it unless a separate estimation contract is designed.

Budget ceilings and resume belong to P0b2b, after we see actual repeated-run costs.

---

## §8 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `extraction_lab/repeat_experiment_manifest.py` | Strict wrapper manifest referencing one immutable Stage 4D pair manifest; 2–3 repetition bound. |
| Create | `extraction_lab/run_repeat_experiment.py` | Dry-run/execute repeated orchestration, child receipt qualification, fail-fast state machine, final receipt. |
| Create | `extraction_lab/repeat_experiment_qualification.py` | Deterministic metric/anchor/telemetry aggregation + report rendering. |
| Create | `tests/extraction_lab/test_repeat_experiment_manifest.py` | Schema/path/repetition/unknown-field/pair-manifest validation. |
| Create | `tests/extraction_lab/test_run_repeat_experiment.py` | Inert default, fresh roots, child execution, drift/failure/fail-fast, receipt behavior. |
| Create | `tests/extraction_lab/test_repeat_experiment_qualification.py` | Exact descriptive-statistics, anchor stability, telemetry totals, no-winner tests. |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4d-isolated-experiment-pair-v1.md` | Backward-looking #706 merge/PASS + live smoke record only. |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | Record #706 + smoke; set Stage 4E/P0b2a current; Stage 4 remains NOT DONE. |
| Modify | `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` | Record #706 + smoke and repeated-qualification lane; no Stage 4 completion. |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4e-repeated-pair-qualification-v1.md` | Implementation/review evidence and exact disposition. |

**Expected no-change predecessor paths:**

- `extraction_lab/pair_experiment_manifest.py`
- `extraction_lab/run_pair_experiment.py`
- `extraction_lab/compare_experiment_runs.py`
- `extraction_lab/run_extraction_lab.py`
- `extraction_lab/benchmark_contract.py`
- `tools/batch_ingest_corpus.py`
- `MODEL_POLICY.json`
- `src/ingestion/**`

If implementation requires changing Stage 4D or PR #705 semantics, stop and re-brief rather than silently broadening this PR.

**Bounded discovery exception:**

```text
Directory: tests/fixtures/extraction_lab/
Maximum additional paths: 4
Allowed: tiny repeat manifest / child receipt / comparison fixtures only
Decision rule: prefer tmp-path generated fixtures unless committed fixtures make the contract materially clearer
```

---

## §9 Explicitly out of scope / collision boundary

| Area | Why excluded |
|---|---|
| P0b1 runner behavior changes | Accepted predecessor; this slice composes it. |
| resume in same repeat root | P0b2b. |
| continue after failed repetition | P0b2b policy. |
| dynamic budget ceiling / cost stop | P0b2b after real repeated costs are known. |
| OpenAI Batch submit/poll/complete | P0b2c if justified. |
| event-driven scheduler/daemon | P0b2c/later. |
| random/alternating variant order | Separate response to observed order effects, if needed. |
| >3 repetitions | Not needed to prove the first variance contract. |
| >3 corpus sources | P1 representative development cohort. |
| development/holdout split | P1/P3. |
| prompt/model/taxonomy mutation | P2 ablation slices. |
| composite score / automatic winner | Explicitly prohibited. |
| gold edits | Separate benchmark-authority work. |
| APP-STATE / World publication | P4/P5. |
| C2S23 adoption/UI repair | Separate continuity/product lane. |

---

## §10 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Owning boundary |
|---|---|---|---|
| repeated dry-run | manual repetition planning | normalized plan, zero child execution | repeat runner |
| independent repetitions | operator reruns Stage 4D manually | exact 2–3 fresh child pair roots | repeat runner |
| repeated identity | manually inferred | pair/repo/source/gold/policy/model/benchmark identity qualified explicitly | repeat qualifier |
| variance | no program artifact | exact per-run values + descriptive stats | qualification |
| anchor stability | one pair transition only | per-anchor pass rates + transition/fail-bucket counts across reps | qualification |
| telemetry | per-pair only | per-side and pair total cost/runtime/token summaries | qualification |
| repetition failure | manual interpretation | fail-fast parent receipt, preserve prior reps, no completed qualification | repeat state machine |

Adversarial sequences:

| Sequence | Required safe outcome |
|---|---|
| dry-run → inspect plan | zero output/model calls; exact planned run count visible |
| rep1 success → rep2 child failure | parent failed; rep1 preserved; rep3 not started; no completed qualification |
| rep1 success → rep2 comparator non-comparable | same fail-fast behavior |
| rep1 success → rep2 observed model differs | fail `repeat_observed_model_mismatch`; rep3 not started |
| rep1 success → pair manifest bytes change before rep2 | fail before rep2 execution |
| all child pairs comparable but benchmark identity differs across reps | parent failed; no aggregation claim |
| all 3 qualify | completed parent + qualification + report, no winner |
| metrics stable but different anchors flip | anchor stability output reveals flips; aggregate recall alone is not allowed to hide them |

---

## §11 Evidence required to merge

| Guarantee | Owning boundary | Required proof | Stop condition |
|---|---|---|---|
| Stage 4D smoke prerequisite honored | handoff/state authority | recorded exact smoke result from §1 | no implementation without it |
| default is inert | CLI | subprocess/child-run spy | any child execution/output on default invocation |
| pair manifest remains single pair authority | manifest | wrapper loads existing Stage 4D schema; no duplicated config | copied/drifting pair fields |
| repetitions bounded | manifest | reject 1, 4+, booleans, unknowns | unbounded paid work |
| fresh isolation across reps | runner | 3-rep fake run → 6 distinct variant stores/caches | any reused root/cache |
| Stage 4D safety inherited | runner | child calls use existing `run_pair_experiment` | bypassing predecessor pinning |
| fail-fast | runner | rep2 failure witness | rep3 starts or parent looks complete |
| cross-rep identity | qualifier | model/benchmark/pair-manifest drift injections | drift averaged into qualification |
| exact descriptive stats | qualifier | hand-calculated fixture | wrong mean/min/max/pstdev/sign counts |
| anchor instability visible | qualifier | anchor flip fixture | only aggregate recall reported |
| cost/runtime totals truthful | qualifier | known telemetry fixtures | dropped/double-counted runs |
| no winner/composite | artifacts | serialized fixture assertions | winner/READY/promotion/weighted score |
| predecessor suites remain green | regression | full `tests/extraction_lab/` | new failures attributable to head |

Exact verification target:

```bash
uv run pytest tests/extraction_lab/ -q
uv run ruff check \
  extraction_lab/repeat_experiment_manifest.py \
  extraction_lab/run_repeat_experiment.py \
  extraction_lab/repeat_experiment_qualification.py \
  tests/extraction_lab/test_repeat_experiment_manifest.py \
  tests/extraction_lab/test_run_repeat_experiment.py \
  tests/extraction_lab/test_repeat_experiment_qualification.py

git diff --check
git diff --name-only 4af440b2cc4102972ad6212590885248e58375c1...HEAD
```

### Required deterministic end-to-end proof

Use fake Stage 4D child execution at the model boundary while preserving the real parent qualification logic:

```text
repeat manifest preflight
→ rep1 child pair completed/comparable
→ rep2 child pair completed/comparable
→ rep3 child pair completed/comparable
→ cross-repetition identity qualification
→ metric aggregation
→ anchor stability aggregation
→ telemetry aggregation
→ completed repeat receipt + qualification + report
```

Also prove:

```text
rep1 success
→ rep2 failure/drift
→ parent failed
→ rep1 preserved
→ rep3 absent
→ no completed qualification
```

No paid repeated experiment is required to merge this implementation PR. The live post-merge run is an operator gate.

---

## §12 Immediate post-merge experiment gate

After Stage 4E merges, run one real repeated experiment before building P0b2b/P1.

Recommended first run:

```text
pair manifest:
  same one-source Session 23 pair used by the Stage 4D smoke

repetitions:
  3

execution:
  realtime
  isolated caches
  fixed baseline→candidate order
```

Purpose:

- measure actual stochastic variability of the current extraction path;
- verify cost/runtime scaling from the one-pair smoke;
- learn whether anchor outcomes are stable enough that a 10–20 document development cohort will be interpretable;
- decide whether resume/budget mechanics are actually the next bottleneck.

A successful repeated run does **not** mean `batch_size=4` or `5` is superior. That parameter remains a harmless executor witness unless the evidence unexpectedly shows a real extraction difference.

### Decision after the first repeated run

Use evidence, not the old roadmap, to pick the next slice:

```text
If cost/runtime is the bottleneck:
  → P0b2b budget/resume lifecycle

If realtime execution is operationally awkward:
  → P0b2c async Batch/event-driven lifecycle

If variance is acceptably low and operations are fine:
  → P1 representative 10–20 document baseline characterization

If anchor instability is high:
  → investigate stochastic/extraction failure class before scaling cohort
```

This is the first point where the program is allowed to resequence itself from observed experiment behavior.

---

## §13 Required implementation/review handback

Record:

1. exact PR/branch/head/base and review cycle;
2. exact Stage 4D smoke gate evidence that authorized dispatch;
3. #706 merge SHA and accepted head;
4. repeat manifest schema and its exact pair-manifest reference semantics;
5. proof dry-run is inert;
6. exact repetition bound and fixed execution order;
7. proof each repetition uses fresh Stage 4D output/store/cache roots;
8. fail-fast evidence;
9. cross-repetition identity checks and drift witnesses;
10. exact metric aggregation formulas;
11. anchor pass-rate/transition/fail-bucket aggregation proof;
12. telemetry totals/means and provenance;
13. proof no winner/composite/promotion semantics exist;
14. full Extraction Lab test/Ruff/diff evidence;
15. actual changed paths vs §8;
16. backward-looking authority sync;
17. P0b2b/P0b2c/P1 remain false;
18. Stage 4 WOW remains HOLD.

---

## §14 Acceptance rubric

- [x] §1 live Stage 4D smoke gate is recorded and successful before implementation begins.
- [x] Exactly one independently useful capability is delivered: repeated qualification of one bounded Stage 4D pair.
- [x] Stage 4D remains the single pair execution authority.
- [x] Default invocation performs no paid execution.
- [x] Only 2–3 repetitions are permitted.
- [x] Every repetition has fresh non-overlapping Stage 4D roots/stores/caches.
- [x] All repetitions consume identical pair-manifest bytes and pinned benchmark/execution identity.
- [x] Parent completion requires every child pair completed + comparable.
- [x] Failure is fail-fast and preserves prior evidence without pretending qualification.
- [x] Metrics expose exact values + mean/min/max/pstdev and delta sign counts.
- [x] Anchor-level stability is visible across repetitions.
- [x] Cost/runtime/token telemetry is aggregated truthfully.
- [x] No composite score, winner, READY, promotion, significance claim, or publication is introduced.
- [x] Resume, budgets, async lifecycle, larger cohort, holdouts, tuning, and publication remain false.
- [x] Stage 4 WOW remains HOLD.

## Stop conditions

Stop and report rather than broadening if:

- Stage 4D paid smoke does not complete with trustworthy `comparable=true` evidence;
- repeated orchestration requires modifying Stage 4D pair execution semantics;
- reliable variance qualification requires >3 repetitions before the first real repeated run;
- identity cannot be proven consistently across child receipts;
- the batch/model API requires asynchronous lifecycle to complete even the bounded repeated run;
- operator safety requires a dynamic budget system before any 2–3 repetition run can be authorized;
- a representative cohort >3 sources is necessary to make the first variance artifact useful;
- a required production path falls outside §8;
- implementation begins adding ranking, tuning, holdouts, publication, or scheduler behavior.

Report:

```text
Stop condition:
Invariant clause affected:
Why Stage 4E cannot absorb it:
Required evidence missing:
Affected paths/authority:
Proposed successor/re-brief:
State-authority update needed:
```
