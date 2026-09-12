# HANDOFF — DOGFOOD-CONTINUITY: Stage 4H campaign-memory baseline characterization

**Created:** 2026-09-12  
**Status:** IMPLEMENTED — PAID CHARACTERIZATION REQUIRED ON EXACT HEAD
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4h-campaign-memory-baseline-characterization-v1.md`  
**Conversation/workstream:** `C1/C2 demo-readiness / Stage 4 WOW recovery / ingestion-quality experiment program`  
**Flow / owner:** `DOGFOOD-CONTINUITY` / campaign-memory baseline characterization  
**Direction:** DESIGN → CODE → PAID CHARACTERIZATION → REVIEW  
**Base revision:** `0aa77bf791efa00cb51f45f3c7acd273ac3f351f` (main after PR #709 merge)  
**Branch:** `dogfood-continuity/stage4h-campaign-memory-baseline-characterization-impl`
**PR title:** `DOGFOOD-CONTINUITY: establish the Sol campaign-memory baseline`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Product sequence: [`Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`](../Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md). Predecessors: [`HANDOFF-DOGFOOD-CONTINUITY-stage4f-campaign-memory-development-benchmark-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-stage4f-campaign-memory-development-benchmark-v1.md) and [`HANDOFF-DOGFOOD-CONTINUITY-stage4g-campaign-memory-temporal-intent-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-stage4g-campaign-memory-temporal-intent-v1.md).

---

## §0 Where the program is now

```text
P0a    trustworthy cross-contract comparison              DONE — PR #705
P0b1   bounded isolated A/B execution                     DONE — PR #706
P0b2a  repeated-run variability qualification             DONE — PR #707
P1a    campaign-memory entity/fact benchmark              DONE — PR #708
P1a.1  identity + temporal requirement intent             DONE — PR #709
P1b    gold-backed Sol baseline characterization          ← THIS PR
P2     first evidence-selected correction                 later
P3     candidate qualification                            later
P4     full-corpus disposable rehearsal                   later
P5     governed durable publication                       later
```

PR #709 merged at `0aa77bf791efa00cb51f45f3c7acd273ac3f351f`, accepted head `236ea6c5d1486ccf7012ed6b1ea8f33f4b3af457`, after 2 formal review cycles.

The frozen campaign-memory authorities are now sufficient to ask a real question of the current ingestion pipeline:

```text
Stage 4F benchmark
  benchmark_id: c2-mireward-campaign-memory-dev-v1
  exact sources: 7
  entity anchors: 6
  fact anchors: 5
  identity expectations: 2 (explicitly unscored)
  corpus fingerprint:
    925ad24a54d888e2f1d3673919d126767b39cdeaf885c07057bfb5da346ba8c1
  gold fingerprint:
    de072c175cc00a1dc7ed672cdaca317ee0f8cb381a8186e9cfc53a5885a4cd23

Stage 4G temporal overlay
  temporal expectations: 7 (explicitly unscored)
  temporal intent fingerprint:
    ed3596e4fd7d75029534c19e5017f4905840347356bf5323b30c365f906c56c4
```

Current Buddy production model policy on the base resolves:

```text
structured_generation → fast_smart → gpt-5.3-codex
```

The current batch ingester's default evidence-unit batch size is `5`. P1b pins that value explicitly rather than relying on an implicit default.

Stage 4 remains **HOLD**. No extraction improvement, identity coalescence, temporal scoring, DungeonMind temporal representation, APP-STATE publication, or World publication has been accepted.

---

## §1 Mission and merge-ready invariant

**Mission:** Execute the unchanged ingestion prompts and extraction contracts with an explicit `gpt-5.6-sol` experiment override three times over the exact frozen seven-source campaign-memory benchmark using fresh isolated stores/caches, score the existing entity/fact anchors, expose run-to-run stability and failure buckets, and generate inspectable but explicitly unscored identity/temporal witness packets so the next engineering change can be selected from evidence.

**Merge-ready invariant:** On one exact review head, three cold-cache repetitions ingest exactly the Stage 4F seven-source cohort with explicit `gpt-5.6-sol` model identity and batch size `5`; all three reproduce identical repository/source/gold/temporal/model-policy/model execution identity; each produces a qualified Extraction Lab bundle for `campaign_memory_development`; a deterministic qualification artifact reports scored entity/fact recall, per-anchor stability/failure buckets, count and updated Sol cost/runtime/token telemetry; an unscored witness artifact exposes the actual store representation relevant to all Stage 4F identity and Stage 4G temporal requirements; and the PR handback truthfully records the result without changing prompts, scoring, benchmark authority, production model-policy selection, DungeonMind, APP-STATE, or World publication behavior.

### Success is characterization, not a high score

A baseline with poor recall can **PASS this PR**.

This PR succeeds when current behavior is reproducible and diagnosable. It does **not** require:

```text
minimum entity recall
minimum fact recall
identity coalescence success
temporal representation success
improvement over any predecessor run
```

Do not tune the system to make this baseline look better.

---

## §2 Why this is not another A/B experiment

Do not route P1b through the Stage 4D/4E pair runner.

That contract intentionally requires:

```text
1–3 sources
exactly baseline + candidate
```

P1b requires:

```text
exactly 7 frozen sources
one explicit Sol configuration
3 repetitions
```

Duplicating the same configuration into baseline/candidate would produce six paid runs, manufacture meaningless deltas, and obscure the question we are now asking.

P1b is a **characterization runner**, not a comparison runner.

Reuse these existing owning contracts directly:

```text
tools/batch_ingest_corpus.py
extraction_lab/run_extraction_lab.py
extraction_lab/campaign_memory_benchmark.py
extraction_lab/campaign_memory_temporal_intent.py
MODEL_POLICY.json
```

Do not change predecessor pair/repeat semantics merely to force this shape through them.

---

## §3 Frozen execution contract

The characterization is the current pipeline, not a candidate.

Required execution:

```text
surface: campaign_memory_development
sources: exactly the 7 sources from Stage 4F benchmark.json
entity/fact gold: exactly the paths owned by Stage 4F benchmark.json
temporal intent: exact Stage 4G sidecar
mode: flex
repetitions: 3
cache policy: isolated / fresh store each repetition
batch size: 5
OpenAI Batch API: false
resume: false
force: false
auto-escalate: false
production model policy mutation: forbidden
```

Repetition order is fixed:

```text
rep-001
rep-002
rep-003
```

Each repetition receives a new absent root and therefore a new local cache.

No retry-on-quality behavior. No automatic rerun of failed anchors. No prompt/model/taxonomy fallback.

The frozen cohort includes four documents whose legacy frontmatter predates the
current strict metadata schema. Paid characterization therefore uses the explicit
`--normalize-legacy-frontmatter` compatibility path. It projects World documents
onto current evergreen World metadata and ignores unsupported descriptive keys,
without modifying source bytes. The default ingest path remains strict, and the
batch report records that normalization was enabled.

### Model identity

At preflight resolve the Buddy-owned `structured_generation` model from `MODEL_POLICY.json` and pin the policy bytes.

For every repetition, read actual entity/fact model IDs from `logs/model_calls.jsonl`.

Fail characterization if:

- a required stage has no observed model;
- a stage has multiple observed models within one repetition;
- observed entity/fact stage model identity changes across repetitions;
- model-policy bytes change during execution.

Record the resolved policy model and actual observed stage models separately. Do not silently substitute one for the other.

---

## §4 Public manifest contract

Create a strict manifest schema owned by this slice.

Recommended operator manifest:

```json
{
  "schema": "dmb_campaign_memory_baseline_characterization_v1",
  "experiment_id": "stage4h-c2-mireward-current-baseline",
  "repository_sha": "<EXACT REVIEW HEAD SHA>",
  "model_id": "gpt-5.6-sol",
  "benchmark": "evals/campaign_memory_development/benchmark.json",
  "temporal_intent": "evals/campaign_memory_development/temporal_expectations.json",
  "pins": {
    "benchmark_id": "c2-mireward-campaign-memory-dev-v1",
    "corpus_fingerprint": "925ad24a54d888e2f1d3673919d126767b39cdeaf885c07057bfb5da346ba8c1",
    "gold_fingerprint": "de072c175cc00a1dc7ed672cdaca317ee0f8cb381a8186e9cfc53a5885a4cd23",
    "temporal_intent_fingerprint": "ed3596e4fd7d75029534c19e5017f4905840347356bf5323b30c365f906c56c4"
  },
  "execution": {
    "mode": "flex",
    "cache_policy": "isolated",
    "repetitions": 3,
    "batch_size": 5
  }
}
```

All fields are strict; unknown fields fail closed.

The operator manifest may live outside the repository so `repository_sha` can pin the final implementation head without a self-referential commit problem.

### Manifest loading

The loader must:

1. require the exact repository SHA;
2. resolve benchmark and temporal paths inside the repository;
3. call `validate_campaign_memory_benchmark(...)`;
4. call `validate_campaign_memory_temporal_intent(...)`;
5. require all four explicit fingerprint/ID pins above;
6. derive source locators and gold paths from Stage 4F benchmark authority rather than duplicating them in the P1b manifest;
7. require exactly 7 unique Markdown source files;
8. reject managed `_dungeonbuddy` storage as a source;
9. preserve a SHA-256 of the operator manifest bytes in the receipt.

---

## §5 CLI and dry-run behavior

Preferred CLI:

```bash
uv run python -m extraction_lab.run_campaign_memory_baseline \
  --manifest /tmp/stage4h-baseline.json \
  --out-dir /tmp/stage4h-baseline-run
```

Default behavior is **dry-run and inert**.

Paid execution requires explicit:

```bash
... --execute
```

Dry-run must:

- perform structural/benchmark/temporal preflight;
- resolve and display exact repository SHA, source cohort, fingerprints, batch size, repetitions, policy SHA, and resolved policy model;
- report the six forbidden batch modes/flags as false;
- make zero API calls;
- create no output root.

`--execute` requires:

- exact repository SHA match;
- clean worktree;
- absent output root;
- `OPENAI_API_KEY` present;
- valid frozen benchmark + temporal overlay;
- unchanged model policy.

Place the execution output outside the repository or under an already-ignored path so creating artifacts does not dirty the worktree.

---

## §6 Pinning and TOCTOU rules

P1b inherits the fail-closed provenance standard established in Stage 4D.

At execution start capture/pin:

```text
repository SHA
worktree cleanliness
operator manifest SHA-256
all 7 source byte SHA-256 values
benchmark.json bytes
gold/entity_anchors.json bytes
gold/fact_anchors.json bytes
temporal_expectations.json bytes
MODEL_POLICY.json bytes
benchmark ID/corpus/gold fingerprints
temporal intent fingerprint
```

Revalidate relevant state at least:

```text
before rep-001
post-ingest / pre-score rep-001
post-score rep-001
before rep-002
post-ingest / pre-score rep-002
post-score rep-002
before rep-003
post-ingest / pre-score rep-003
post-score rep-003
before qualification
```

Any drift fails the overall characterization and prevents a completed qualification claim.

Do not continue later repetitions after a failed repetition or provenance failure.

Partial artifacts remain available for diagnosis but the parent receipt status is `failed`, never `completed`.

---

## §7 Per-repetition execution

For each repetition create:

```text
<out>/rep-001/
  source_paths.txt
  stdout.log
  store/
  extraction_lab/
  witness.json

<out>/rep-002/
...

<out>/rep-003/
...
```

Invoke the existing batch ingester over the benchmark-derived exact source list with only the configuration relevant to this slice:

```text
--store <fresh store>
--corpus-root <Stage 4F corpus root>
--paths-file <exact seven-source file>
--batch-size 5
```

Do **not** pass:

```text
--force
--resume
--use-batch-api
--auto-escalate
--escalate-world
--limit
```

Require the batch report to show exactly 7 succeeded, 0 failed, 0 skipped.

Then run existing Extraction Lab scoring with:

```text
surface = campaign_memory_development
entity anchors = Stage 4F benchmark authority
fact anchors = Stage 4F benchmark authority
corpus source root = Stage 4F corpus root
pipeline code SHA = exact execution SHA
batch size = 5
observed entity/fact models = actual model-call log values
```

Require Extraction Lab's benchmark contract to reproduce the Stage 4F corpus/gold fingerprints before that repetition qualifies.

---

## §8 Scored qualification output

Create one deterministic qualification artifact, recommended schema:

```text
dmb_campaign_memory_baseline_qualification_v1
```

It must report **descriptive characterization only**.

### Aggregate scored metrics

For each of:

```text
entity_anchor_recall
fact_anchor_recall
total_entity_count
total_fact_count
```

report:

```text
values[3]
mean
min
max
population standard deviation
```

Counts are diagnostic; they are not quality rewards.

### Per-anchor stability

For every one of the 6 entity anchors and 5 fact anchors report:

```text
anchor_id
pass_count / 3
pass_rate
fail_bucket counts
per-repetition result
```

A descriptive stability label is allowed:

```text
stable_pass   = 3/3 pass
stable_fail   = 0/3 pass
unstable      = 1/3 or 2/3 pass
```

This label is descriptive only. Do not create a composite quality score.

### Telemetry

Across repetitions report values + mean/min/max/pstdev + total where appropriate for:

```text
estimated cost USD
elapsed seconds
input tokens
output tokens
cached tokens
API calls
```

Also record actual entity/fact model IDs and per-repetition entity/fact counts.

### Required limitations

The report must state at least:

- three repetitions are a small descriptive sample;
- all repetitions use isolated cold local caches;
- this is one seven-source development cohort, not whole-corpus validation;
- identity and temporal requirements are intentionally not scored;
- no confidence interval, significance test, winner, readiness score, or promotion claim is made.

---

## §9 Unscored identity + temporal witness packet

P1b must make the unscored requirements **inspectable**, not silently ignore them and not pretend to score them.

Create deterministic `witness.json` for each repetition plus an aggregate witness index.

### Identity witnesses

For each Stage 4F identity expectation record:

```text
expectation_id
anchor_ids
for each anchor:
  anchor resolution result
  resolved entity ID if present
  resolved display name/class if present
  full resolved entity payload if available
```

Do **not** emit:

```text
identity_pass = true/false
identity_score
identity_recall
```

If two anchors resolve to the same ID, the artifact may show those IDs; it must not convert that observation into a formal benchmark score in this slice.

### Temporal witnesses

For all seven Stage 4G expectations record:

```text
expectation_id
subject anchor
fact anchor or null
kind / persistence / truth window / evidence intent
subject anchor resolution
resolved subject entity payload if present
linked fact anchor resolution if present
matched fact payload if a linked fact passed
all current-store facts whose subject is the resolved subject entity
```

For requirement-only temporal expectations, preserve `fact_anchor = null` and expose relevant subject facts without inventing a synthetic fact score.

The witness packet must not infer start/end semantics from store ordering, timestamps, or source order.

Its job is to answer:

> What did the current store actually give a human reviewer to work with?

---

## §10 Required paid characterization gate on the review head

Unlike the infrastructure-building predecessor PRs, Stage 4H must return **real characterization evidence before merge**.

After implementation is believed review-ready:

1. commit all executable/config/test changes;
2. create an operator manifest pinning that exact head SHA;
3. run dry-run and inspect the plan;
4. run exactly one paid three-repetition characterization with `--execute`;
5. do not commit any code/config/corpus/model-policy change after the paid run unless willing to rerun the full characterization;
6. update the PR body/comment with a sanitized Characterization Record. Updating PR metadata does not change the head SHA.

If review requires a new implementation commit, the prior paid characterization becomes historical evidence only and must be rerun on the new exact review head before merge-ready disposition.

### Characterization Record

The PR handback must include:

```text
operator/date
exact execution/review head SHA
operator manifest SHA-256
receipt status
benchmark ID + corpus/gold fingerprints
temporal intent fingerprint
model-policy SHA
resolved policy model
observed entity/fact model IDs
3/3 repetition completion
entity anchor recall values
fact anchor recall values
per-anchor 3-run stability table
failure bucket summary
entity/fact count summary
total cost + runtime + token/API telemetry
identity witness table for both identity expectations
temporal witness table for all seven temporal expectations
explicit authority-mutation check
```

The sanitized PR record is the durable review artifact. Raw run artifacts must be retained by the operator through review but do not need to be committed.

### Human witness review

The identity table should show the actual resolved IDs/names for each repetition and a concise human note such as:

```text
same observed entity
different observed entities
one/both unresolved
ambiguous from current artifact
```

These notes are **qualitative observations**, not scored benchmark results.

For each temporal expectation, the reviewer records:

```text
what current store representation is visible
whether the requirement is inspectable from that representation
what information is flattened/missing/contradictory, if any
```

Do not force a numeric temporal score.

---

## §11 Merge gates

Merge readiness requires:

```text
3/3 repetitions completed
all execution identity pins stable
all three benchmark contracts qualified
same observed stage-model identity across repetitions
qualification artifact generated
11 scored anchors reported individually
identity witness packet covers both identity expectations
temporal witness packet covers all seven temporal expectations
sanitized Characterization Record posted for exact review head
no authority mutation
no tuning or candidate behavior introduced
```

**No minimum recall threshold exists.**

A low-quality but trustworthy baseline is merge-ready if all characterization gates pass.

A high-quality run with provenance drift, incomplete repetitions, or uninspectable results is not merge-ready.

---

## §12 Files in scope — write lease

Preferred implementation lease:

| Action | Path | Purpose |
|---|---|---|
| Create | `extraction_lab/campaign_memory_baseline_manifest.py` | Strict P1b operator manifest + frozen authority loading. |
| Create | `extraction_lab/run_campaign_memory_baseline.py` | Dry-run/paid three-repetition Sol/Flex execution + fail-closed receipt. |
| Create | `extraction_lab/flex_cost_projection.py` | Dated Flex price snapshot and same-workload/full-corpus projections. |
| Create | `extraction_lab/campaign_memory_baseline_qualification.py` | Scored descriptive aggregation + unscored witness assembly/report. |
| Create | `tests/extraction_lab/test_campaign_memory_baseline_manifest.py` | Manifest/pin/source-authority failures. |
| Create | `tests/extraction_lab/test_run_campaign_memory_baseline.py` | Execution, drift, fail-fast, cold-store and exact-command witnesses. |
| Create | `tests/extraction_lab/test_campaign_memory_baseline_qualification.py` | Metric/stability/telemetry and unscored witness regressions. |
| Create | `tests/extraction_lab/test_flex_cost_projection.py` | Flex rates, arithmetic, and projection-assumption regressions. |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4g-campaign-memory-temporal-intent-v1.md` | Backward-looking #709 merge/PASS only. |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | Record #709 done and Stage 4H current. |
| Modify | `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` | Record P1a.1 complete; P1b active; Stage 4 remains NOT DONE. |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4h-campaign-memory-baseline-characterization-v1.md` | Implementation/review handback only. |
| Modify | `src/ingestion/entity_extractor.py` | Honor the explicit experiment-only model override before policy resolution. |
| Modify | `src/ingestion/fact_extractor.py` | Honor the same explicit experiment-only model override. |
| Modify | `tools/batch_ingest_corpus.py` | Accept the explicit model argument without mutating production model policy; retain/update Sol cost telemetry. |
| Modify | `src/cli.py` | Accept the explicit legacy-frontmatter normalization flag and pass it to chunking. |
| Modify | `src/ingestion/frontmatter.py` | Provide an opt-in, schema-validated projection of legacy metadata without changing source bytes. |
| Modify | `src/ingestion/chunker.py` | Apply the same explicit normalization while preserving body line anchors. |
| Modify | `tests/ingestion/test_frontmatter.py` | Prove strict-by-default behavior and bounded legacy projection. |
| Modify | `tests/test_model_policy_authority.py` | Prove shared explicit override and unchanged default policy behavior. |
| Modify | `src/agent/planner_pricing.py` | Correct Sol promotional standard rates from supplied pricing authority. |
| Modify | `tests/test_planner_pricing.py` | Lock the corrected Sol standard rates. |

### Expected no-change paths

Do not modify:

```text
evals/campaign_memory_development/benchmark.json
evals/campaign_memory_development/gold/entity_anchors.json
evals/campaign_memory_development/gold/fact_anchors.json
evals/campaign_memory_development/temporal_expectations.json
extraction_lab/campaign_memory_benchmark.py
extraction_lab/campaign_memory_temporal_intent.py
extraction_lab/anchor_schema.py
extraction_lab/anchor_resolver.py
extraction_lab/run_extraction_lab.py
extraction_lab/pair_experiment_manifest.py
extraction_lab/run_pair_experiment.py
extraction_lab/repeat_experiment_manifest.py
extraction_lab/run_repeat_experiment.py
extraction_lab/repeat_experiment_qualification.py
extraction_lab/compare_experiment_runs.py
MODEL_POLICY.json
src/ingestion/entity_extractor.py (except the model override named above)
src/ingestion/fact_extractor.py (except the model override named above)
src/ingestion/** (except `frontmatter.py` and `chunker.py` named above)
corpus/eldyrwild-markdown/**
apps/**
```

A small amount of local orchestration duplication is preferable to silently changing predecessor A/B semantics in this slice.

If implementation discovers that a shared execution primitive must be extracted from Stage 4D/4E to implement P1b safely, stop and re-brief rather than widening the write lease.

---

## §13 Required deterministic tests before paid execution

At minimum prove:

```text
dry-run makes zero paid calls and creates no output root
wrong repository SHA fails
unclean worktree fails
missing API key fails execute
existing output root fails
benchmark ID/corpus/gold pin drift fails
temporal fingerprint drift fails
source byte drift fails
entity gold drift fails
fact gold drift fails
temporal sidecar byte drift fails
model-policy drift fails
exact benchmark source count != 7 fails
rep roots are distinct and fresh
exact batch command uses paths-file + batch-size 5 only
forbidden force/resume/batch-api/escalation flags never appear
batch report not 7 succeeded / 0 failed / 0 skipped fails
missing/ambiguous observed entity or fact model fails
observed stage-model identity drift across repetitions fails
post-ingest input mutation fails before scoring
post-score mutation fails before next repetition/qualification
rep-002 failure prevents rep-003 and completed qualification
all three qualified reps produce aggregate metrics
per-anchor 3/3, 0/3, and mixed stability are reported correctly
identity witness records IDs without pass/fail scoring
temporal witness records linked + requirement-only cases without temporal scoring
path/order normalization is deterministic where artifact identity requires it
```

Required commands:

```bash
uv run pytest tests/extraction_lab/ -q

uv run ruff check \
  extraction_lab/campaign_memory_baseline_manifest.py \
  extraction_lab/run_campaign_memory_baseline.py \
  extraction_lab/campaign_memory_baseline_qualification.py \
  tests/extraction_lab/test_campaign_memory_baseline_manifest.py \
  tests/extraction_lab/test_run_campaign_memory_baseline.py \
  tests/extraction_lab/test_campaign_memory_baseline_qualification.py

uv run python -m extraction_lab.run_campaign_memory_baseline \
  --manifest <operator-manifest> \
  --out-dir <fresh-output-root>

git diff --check
git diff --name-only 0aa77bf791efa00cb51f45f3c7acd273ac3f351f...HEAD
```

Run deterministic tests and dry-run before authorizing the paid characterization.

---

## §14 State-authority sync

Backward-looking sync in this implementation PR may record only facts already true before Stage 4H implementation:

- PR #709 merged at `0aa77bf791efa00cb51f45f3c7acd273ac3f351f`;
- accepted #709 head `236ea6c5d1486ccf7012ed6b1ea8f33f4b3af457`;
- #709 required 2 formal review cycles;
- Stage 4F entity/fact + identity benchmark authority exists;
- Stage 4G temporal requirements authority exists;
- identity and temporal requirements remain unscored;
- no extraction improvement has been accepted;
- Stage 4 WOW remains HOLD;
- P2 tuning/correction, P3 qualification, P4 full-corpus rehearsal, and publication remain false.

Do **not** mark Stage 4H/P1b complete in state authority before merge.

The paid Characterization Record in the PR discussion is evidence for review, not permission to pre-complete the roadmap.

---

## §15 Decision produced by this slice

P1b exists to choose the next capability.

After reviewing the scored and unscored evidence, classify the dominant next problem as one or more of:

```text
A. entity/fact recovery
B. stochastic instability
C. identity fragmentation / coalescence
D. temporal flattening / contradiction
E. provenance or observability insufficiency
F. operational cost/runtime burden
```

Do not automatically choose `A` merely because this is called an ingestion experiment.

Preferred successor behavior:

```text
A dominates → one bounded extraction ablation
B dominates → stochastic/model/prompt stability investigation
C dominates → identity measurement/representation slice
D dominates → temporal measurement/representation slice
E dominates → observability/provenance slice
F dominates → execution/batch/cost slice
```

If scored recovery is already strong and identity/temporal artifacts are sufficiently inspectable, the next slice may be **qualification/readiness for full-corpus rehearsal rather than a tuning PR**.

This is the evidence-based fast path toward P4.

---

## Stop conditions

Stop and report rather than broadening if:

- #708 or #709 fingerprints do not reproduce on the exact base;
- the seven-source benchmark cannot be executed through the existing batch ingester without changing ingestion semantics;
- current Extraction Lab cannot score `campaign_memory_development` without changing shared anchor/scorer behavior;
- generating the witness packet requires inventing identity or temporal scoring semantics;
- implementation requires changing prompts, models, taxonomy, model policy, source corpus, or benchmark gold;
- implementation requires modifying pair/repeat experiment semantics;
- implementation requires a production DungeonMind, APP-STATE, or World schema/storage change;
- a second independently useful capability appears;
- paid execution reveals provenance drift or non-reproducible execution identity.

Report:

```text
Stop condition:
Invariant clause affected:
Why Stage 4H cannot absorb it:
Required evidence missing:
Affected paths/authority:
Proposed successor/re-brief:
State-authority update needed:
```

---

## §16 Paid characterization findings and successor recommendations

### Evidence identity

The completed paid characterization is pinned to implementation head:

```text
6a61b63dca555d3d70cac3e38eb3e48c6fc690da
```

Durable sanitized record:

```text
https://github.com/Drakosfire/DungeonMindBuddy/pull/710#issuecomment-5649023090
```

The three-repetition run completed over the exact seven-source cohort with
`gpt-5.6-sol`, Flex, batch size 5, isolated stores/caches, and explicit legacy
frontmatter normalization. Frozen source bytes and benchmark fingerprints did
not change. The production model policy remained `gpt-5.3-codex`.

This section is interpretation of that evidence. It does not alter the frozen
gold, retroactively change the paid execution, or claim that identity and
temporal requirements were formally scored.

### Measured result

```text
entity recall: [1.0, 1.0, 1.0]
fact recall:   [0.6, 0.6, 0.6]

stable entity PASS: 6 / 6
stable fact PASS:   3 / 5
stable fact FAIL:   2 / 5
```

Stable fact passes:

- Brin Holloway is a cook from Edge;
- Brin leads the refugees/evacuees;
- Orik Tane is Mireward's mayor.

Stable fact failures, both `keyword_mismatch`:

- Karsemine learns that the tripod creature is weak to fire;
- Mireward is under active siege/refugee pressure.

Operational evidence:

```text
wall time:       2005.393 seconds (33m 25.4s)
per-run time:    723.243 / 649.475 / 625.308 seconds
API calls:       84 per run / 252 total
input tokens:    751,933 total
output tokens:   750,827 total
Flex cost:       $2.8586 / $2.6461 / $2.7358
total cost:      $8.2405
mean run cost:   $2.7468
```

Counts varied while benchmark outcomes remained stable:

```text
entities: 128 / 121 / 128
facts:    850 / 825 / 824
```

This is useful descriptive stability, not evidence that every extracted record
is deterministic.

### Finding A — decisive knowledge is summarized away

The source explicitly says that Hunter's Mark revealed the tripod creature was
resistant to poison and **weak to fire**. All three runs preserved only a fact
equivalent to:

```text
Karsemine used Hunter's Mark to learn its weaknesses and resistances.
```

The extractor noticed the correct event but discarded its table-useful answer.
This is lossy abstraction rather than wholesale retrieval or entity failure.

Mireward shows the same failure shape. The stores contain nearby facts such as
the refugee crush disrupting the town, northern arrivals filling haylofts, and
the north breaking against Mireward, but do not preserve the direct operational
statement `under siege` / `siege pressure` / `meat-monster flank` required by
the gold intent.

**Classification:** `A. entity/fact recovery`, specifically preservation of
discovery payloads and direct operational truths.

**Recommended bounded successor:** require extraction to retain the answer or
payload of discoveries, conclusions, vulnerabilities, immunities, revelations,
and current threats—not merely that a character learned or experienced them.
Evaluate the candidate against both stable failures while protecting the three
currently passing facts.

### Finding B — ordinary entity recall masks identity fragmentation

Both Orik/Orric entity anchors pass independently, but the unscored witness
shows different entity IDs in every repetition:

```text
Session 23: Orik Tane
reference:  Orric Tane / Mayor Orric Tane
result:     two actors in 3 / 3 repetitions
```

Brin provides the positive control: recap Brin and reference Brin resolved to
one entity within every repetition. Exact/same-name reconciliation works here;
spelling-tolerant cross-source reconciliation does not.

Entity ID strings also vary between repetitions—for example
`ent_brin_holloway` versus `brin_holloway`. Within-run identity can be coherent
while cross-run identifier generation remains unstable.

**Classification:** `C. identity fragmentation / coalescence`.

**Recommended bounded successor:** make the existing identity expectations
executable before attempting a broad identity fix. Then test a narrow alias or
spelling-drift candidate against Orik/Orric, with Brin as the non-regression
control. Do not infer success from independent entity-anchor recall.

### Finding C — source authority is not yet safe for automatic publication

The Mireward scaffold describes itself as non-canon until promoted, while its
legacy metadata says `canon_layer: world`. The explicit compatibility projection
allows the frozen source to be measured, but the disposable store consequently
contains scaffold-derived facts with `CANON` truth state.

This is acceptable only as disclosed disposable experiment behavior. It is not
a safe contract for automatic durable World publication. Document metadata and
prose-level authority disagree, and the present pipeline does not represent that
disagreement faithfully.

**Classification:** `E. provenance or observability insufficiency`, with a
governance consequence.

**Recommended boundary:** automatic full-corpus extraction may target disposable
stores; exact digest-bound source adoption may later be automated; semantic World
facts, merges, aliases, and relationships must not be silently promoted while
authority conflicts remain unresolved.

### Finding D — cost is affordable, but the whole-corpus projection is crude

The mean measured Sol/Flex seven-source workload projects linearly to about
`$170.30` for 434 Markdown files. The same price-only projection reports roughly:

```text
GPT-5.6 Luna Flex:  $10.07
GPT-5.6 Terra Flex: $100.67
GPT-5.6 Sol Flex:   $170.30
```

These are planning estimates, not model-quality or budget guarantees. The
Mireward scaffold contributed 76 of 130 evidence units, so scaling by file count
assumes an unusually large average file. Applying alternate model prices to
Sol's token volume also assumes identical token behavior across models.

**Classification:** `F. operational cost/runtime burden` is not currently the
dominant blocker, but projection quality needs improvement before a full-corpus
budget is approved.

**Recommended bounded successor:** inventory corpus bytes, evidence units, and
expected prompt batches without model calls; project from those workload units
rather than file count. Treat Luna/Terra estimates as price-equivalent scenarios
until small paid ablations measure their actual token volume and quality.

### Recommended ordering

```text
1. Preserve decisive discovery/threat payloads in extraction.
2. Make cross-source identity expectations executable.
3. Test narrow Orik/Orric spelling-tolerant reconciliation.
4. Resolve source-authority semantics before durable full-corpus publication.
5. Replace file-count cost projection with corpus workload inventory.
6. Only then qualify model/cost alternatives and rehearse full-corpus ingestion.
```

The dominant immediate issue is not that Sol failed to notice the relevant
material. It repeatedly found the correct entities and nearby facts, then
abstracted away the part a GM needs at the table. That makes a narrow extraction
ablation the best first correction, while identity measurement should follow
closely because better facts alone cannot connect Orik to Orric's reference
history.
