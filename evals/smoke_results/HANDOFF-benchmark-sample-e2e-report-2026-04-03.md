# Benchmark-Sample E2E Smoke Report (2026-04-03)

## Scope and Intent

This report captures the benchmark-sample smoke execution requested in `evals/HANDOFF-e2e-smoke-and-quality-validation.md`, using the prepared Mirathorn-related sample (not full corpus), plus follow-up code changes made during execution.

## Sample Identification (Verified Before Running)

The handoff's default `--limit N` strategy on `corpus/eldyrwild-markdown` is **not** benchmark-safe because it picks lexical-first files, not the benchmark slice.

Prepared benchmark sample was identified from:

- `evals/mirathorn_vertical_slice/output/council_room_ingest_scope.json`

Unique source set (5 files):

- `Elderwyld/Cities and Towns/Mirathorn/City Council Building/The Council Room.md`
- `Elderwyld/Cities and Towns/Mirathorn/City Council Building/Battle with The Wolf and Aftermath.md`
- `Elderwyld/Cities and Towns/Mirathorn/City Council Building/The Emergency Council Meeting.md`
- `Elderwyld/Cities and Towns/Mirathorn/City Council Building/The City Council.md`
- `Longmont Campaign/Campaign 1/Longmont Campaign General Notes.md`

To make this deterministic, this session added:

- `evals/mirathorn_vertical_slice/benchmark_corpus_paths.txt`
- `tools/batch_ingest_corpus.py --paths-file` support

---

## Run Log and Outcomes

### Run A - 5-file benchmark sample (first attempt, failed environment)

Store: `out/stores/smoke_benchmark_slice`

Command path was correct (`--paths-file .../benchmark_corpus_paths.txt`), but run failed due DNS resolution errors in the constrained execution environment:

- `httpcore.ConnectError: [Errno -3] Temporary failure in name resolution`
- `openai.APIConnectionError: Connection error.`

Result:

- files: 5 total, 0 succeeded, 5 failed
- api_calls: 0
- tokens: 0

### Run B - 1-file interactive smoke (successful)

Store: `out/stores/smoke_benchmark_slice_one`

Result (from model logs):

- files: 1 succeeded
- evidence units: 10
- entities: 7
- facts: 27
- api_calls: 4 (2 entity + 2 fact)
- tokens: 9,717 input / 5,869 output / 0 cached
- model time: 20,999 ms (~21.0s)
- model: `gpt-5.4-nano`

Batching comparison:

- naive expected calls ~= `2 * evidence_units = 20`
- actual calls = 4
- reduction: 80% fewer calls (5.0x lower)

### Run C - 1-file incremental re-run (successful skip)

Store: `out/stores/smoke_benchmark_slice_one`

Result:

- files: 1 skipped (unchanged)
- api_calls: 0
- tokens: 0
- elapsed wall time: ~0.6s

### Run D - 4-file benchmark subset smoke (successful)

Store: `out/stores/smoke_benchmark_cache4`

(Used first 4 benchmark files; excluded large Longmont General Notes file for runtime control.)

Result (from model logs):

- files: 4 succeeded
- evidence units: 202
- entities: 91
- facts: 514
- api_calls: 133 (91 entity + 42 fact)
- tokens: 276,132 input / 115,832 output / 3,584 cached
- cache rate (OpenAI prefix): ~1.30%
- estimated cost: ~$0.20
- model time: 170,850 ms (~170.8s)
- model: `gpt-5.4-nano`

Batching comparison:

- naive expected calls ~= `2 * evidence_units = 404`
- actual calls = 133
- reduction: ~~67.1% fewer calls (~~3.04x lower)

Observed warnings during this run (pre-fix):

- batched response alignment warnings where returned `evidence_id` differed from expected by small string mutations (e.g., extra character suffix), causing missing/unexpected ID warnings.

### Run E - 4-file incremental re-run (successful skip)

Store: `out/stores/smoke_benchmark_cache4`

Result:

- files: 4 skipped (unchanged)
- api_calls: 0
- tokens: 0
- elapsed wall time: sub-second

### Run F - Recap lane validation (Session 17)

Store: `out/stores/smoke_recap_session2`
Input: `Session 17 - Recap.md`

Result:

- evidence units: 15
- entities: 30
- facts: 83
- event_records: 0
- claims: 0
- entity stage usage: 24,192 input / 11,146 output, 15 API calls
- fact stage usage: 9,492 input / 7,581 output, 3 API calls

Status vs handoff Run 6 criteria:

- `event_records_count > 0`: **FAIL** (0)
- `claims_count > 0`: **FAIL** (0)
- non-empty `event_records.json`: **FAIL** (empty)
- non-empty `claims.json`: **FAIL** (empty)

### Run G - Post-fix live validation (2 files)

Store: `out/stores/smoke_placeholder_2`
Purpose: validate new placeholder/index-based batched mapping in real API calls.

Result:

- files: 2 succeeded
- evidence units: 72
- entities: 37
- facts: 196
- api_calls: 79 (64 entity + 15 fact)
- tokens: 225K input / 44K output / 5K cached
- cache rate: 2.4%
- estimated cost: ~$0.10
- model time: 663.1s

Notable:

- run completed successfully with new `unit_index` mapping
- no `missing evidence_ids` / `unexpected evidence_ids` warnings surfaced in captured stdout for this run

---

## Comparison to Prior Benchmark Artifacts

### Against prior Mirathorn slice artifact (`council_room_ingest_scope.json`)

Prior unique-file totals in that artifact:

- 5 files: 858 entities / 2,907 facts
- 4 council files only: 303 entities / 969 facts

Current smoke (4-file subset, Run D):

- 91 entities / 514 facts

Delta vs prior 4-file artifact:

- entities: -212 (-70.0%)
- facts: -455 (-47.0%)

Interpretation:

- substantial extraction-profile shift exists versus prior artifact set (prompting + filtering + batching-era behavior differences)
- this is consistent with handoff risk note on quality drift and requires explicit quality review before treating as equivalent baseline

### Against handoff baseline tables (full corpus stores)

Handoff full baselines (130 files) remain reference points:

- `cheapest_full`: 1,759 entities / 22,548 facts / 3,867 evidence units
- `escalation_full_mini_to_54`: 2,779 / 21,964 / 5,299
- `nano_full`: 4,845 / 15,359 / 2,526

Current executions are sample-only smokes and not directly comparable at full-corpus scale.

---

## Code Changes Made During This Session

### 1) Deterministic benchmark-sample ingest selection

- `tools/batch_ingest_corpus.py`
  - added `--paths-file` support (one path per line, comments allowed)
  - allows deterministic ingestion of benchmark-prepared sample rather than lexical corpus prefix
- added manifest:
  - `evals/mirathorn_vertical_slice/benchmark_corpus_paths.txt`

### 2) Batched prompt/output alignment hardening (model no longer handles hash-like evidence IDs)

In response to ID-confusion risk, batched flows now use placeholder indices:

- `src/ingestion/entity_extractor.py`
- `src/ingestion/fact_extractor.py`

What changed:

- batched prompt sections now labeled `unit_index: 0..N-1`
- batched schema rows now return `unit_index` (int) instead of `evidence_id` (opaque hash-like string)
- runtime maps `unit_index` -> actual in-memory unit/order server-side
- single-unit fact prompt no longer prints evidence ID

Behavioral intent:

- keep opaque internal identifiers out of model-facing surface
- reduce response-key mutation errors and row assignment failures

### 3) Test updates and verification

Updated tests:

- `tests/test_entity_extractor.py`
- `tests/test_fact_extractor.py`

Validation:

- `uv run pytest tests/test_entity_extractor.py tests/test_fact_extractor.py -q`
- result: 31 passed

---

## Status vs Handoff Plan (Runs 1-7)

- Run 1 interactive smoke: **PARTIAL PASS** (executed on benchmark sample, with 1-file and 4-file successful slices)
- Run 2 incremental skip: **PASS**
- Run 3 OpenAI Batch API smoke: **NOT RUN**
- Run 4 prompt caching validation: **PARTIAL PASS** (`cached_tokens > 0` observed on 4-file and 2-file runs; 10-file target not run)
- Run 5 quality comparison (10 files): **NOT RUN**
- Run 6 recap lane event_records/claims: **FAIL**
- Run 7 full corpus optional: **NOT RUN (intentionally excluded)**

---

## Primary Risks / Open Items for Next Agent

1. **Recap lane regression remains unresolved**
  - recap extraction returns 0 event_records/claims for Session 17 despite recap profile routing.
2. **Quality drift vs prior Mirathorn artifacts is large**
  - especially entity count (-70% on 4-file subset vs prior artifact).
3. **OpenAI Batch API path still unverified in this smoke cycle**
  - discount-path and output-format assumptions not re-confirmed in this execution pass.
4. **Environment caveat**
  - constrained environment produced DNS failures; unrestricted network context was required to run live API calls reliably.

---

## Recommended Next Actions

1. **Recap lane deep-dive first**
  - inspect recap parser and persistence path from `RecapExtractionResult` -> `recap_artifacts` -> store write.
  - add a targeted failing test asserting non-zero event_records/claims for known recap snippet.
2. **Run handoff Run 3 (Batch API) on 1-file or 2-file benchmark subset**
  - confirm discount fields and output parsing.
3. **Run handoff Run 5 style quality comparison on 5-file benchmark sample**
  - compute class distribution and drift thresholds against prior `council_room_ingest_scope`/baseline expectations.
4. **If quality acceptable, scale to 10-file sample before any full-corpus run.**