# Handoff: Phase 5 - Batch Pipeline Transition Stability

**Date:** 2026-04-04  
**Status:** IN PROGRESS  
**Priority:** HIGH  
**Owner lane:** `tools/corpus_batch.py` transition path (`entity_complete -> fact_submitted`)

---

## 1) Mission

Stabilize the corpus batch transition so `--poll` can reliably advance from `entity_complete` to `fact_submitted` on constrained local machines (laptop-class resources), without UI/system lockups.

This phase is strictly about operational reliability and observability in the local transition path.

---

## 2) Current State (What Is Already True)

- Entity transition has been reworked to chunked/observable behavior.
- Progress logs show full entity transition can complete on full-corpus runs.
- Manifest can still remain stuck at `stage: entity_complete` with `fact_batch: null` after process termination.
- Most likely remaining hotspot is fact-prep memory pressure in the local transition path.

Recent observed pattern:

- Chunk build completes (`4164` units from `130` files).
- Entity transition reaches `4164/4164` and reports completion.
- Process terminates before `Fact batch submitted`.

---

## 3) Problem Statement

`--poll` still has a high-risk local segment after entity completion. Even with chunked entity transition, the process may terminate before fact batch submission due to heavy local computation and memory usage in fact-prep.

This blocks:

- Finalization of `batch_api_full_corpus`
- Extraction Lab full-corpus calibration (Phase 6)
- Readiness/generalization proving work (Phase 7)

---

## 4) Scope and Non-Goals

### In scope

- `tools/corpus_batch.py` transition behavior and telemetry
- Fact-prep memory profile and request-building approach
- Reliability of stage advancement and manifest mutation
- Safe operating defaults for constrained environments

### Out of scope

- Extraction Lab scoring semantics
- Anchor tuning/threshold policy changes
- Prompt/schema/taxonomy redesign
- Cross-repo retrieval/refactor work

---

## 5) Primary Blocker

Fact-prep remains too heavy at full-corpus scale. Phase-5 success depends on reducing peak local memory behavior and proving stage advancement reliability under safe settings.

---

## 6) Strict Exit Criteria (Must All Pass)

1. **Stage advancement reliability**
  - From `entity_complete`, `--poll` consistently reaches `fact_submitted`.
  - Manifest reflects non-null `fact_batch` with valid `request_count`.
2. **Machine stability**
  - No Cursor/UI/system lock during transition on laptop-safe profile.
3. **Bounded phase behavior**
  - Phase-level telemetry shows bounded memory behavior and clear per-step timing through fact-prep.
4. **Reproducibility**
  - At least two consecutive runs on same manifest/store profile produce same stage outcome (`fact_submitted`) without manual intervention.
5. **Functional benchmark continuity**
  - After transition succeeds and store is finalized, a benchmark/probe run must prove outputs are usable:
    - Extraction Lab run completes on finalized store.
    - Anchor resolution metrics are emitted (`entity_anchor_recall`, `fact_anchor_recall`, `unresolved_core_anchors`).
    - Regression assert executes (with baseline or explicit `no_baseline_for_surface` warning path).

---

## 7) Required Investigation and Evidence

For every validation run, capture:

- Exact command line
- Start/end timestamps
- Final manifest stage
- Whether `fact_batch` was created
- Telemetry snapshot:
  - units processed
  - chunk size/pause
  - per-phase elapsed
  - RSS MiB
  - request/manifest artifact sizes
- Failure mode details (if any):
  - last 50 transition log lines
  - process exit behavior
  - whether manifest mutated before failure
- Post-transition benchmark evidence:
  - finalized store path
  - Extraction Lab run id and artifact path
  - aggregate metrics snapshot
  - regression assertion result (`pass/fail`, warnings/failures)

No claim of success without command evidence.

---

## 8) Safe Operating Profile (Default)

Use this profile unless explicitly testing limits:

- `--transition-unit-chunk-size 180`
- `--transition-chunk-pause-ms 100`
- `--poll-interval 30`
- optional process niceness: `nice -n 10`

Command shape:

```bash
env PYTHONPATH=. nice -n 10 uv run python tools/corpus_batch.py \
  --poll out/stores/batch_api_full_corpus/logs/corpus_batch/corpus_batch_manifest.json \
  --poll-interval 30 \
  --transition-unit-chunk-size 180 \
  --transition-chunk-pause-ms 100
```

If transition is unstable, reduce chunk size before changing anything else:

- first fallback: `--transition-unit-chunk-size 120`
- second fallback: `--transition-unit-chunk-size 80`

---

## 9) Execution Checklist for Next Agent

1. Confirm manifest status:
  - `PYTHONPATH=. uv run python tools/corpus_batch.py --status <manifest>`
2. Run transition diagnostics first (if needed):
  - `--transition-debug --debug-step fact` with ramping `--debug-unit-limit`
3. Run `--poll` with laptop-safe profile
4. Verify manifest moved to `fact_submitted`
5. Record telemetry and artifact sizes
6. Repeat once to confirm reliability
7. If failure persists:
  - reduce chunk size (120 then 80) while keeping pause at 100ms
  - preserve evidence; do not hand-wave
8. If `fact_submitted` and later `ready` are reached:
  - run `--complete`
  - run Extraction Lab on finalized store
  - run regression assert and record metrics

---

## 10) Benchmark Proof Loop (Required)

This phase is not complete until it proves the stabilized transition produces benchmark-usable outputs.

### Step A: finalize store once ready

```bash
PYTHONPATH=. uv run python tools/corpus_batch.py \
  --complete out/stores/batch_api_full_corpus/logs/corpus_batch/corpus_batch_manifest.json
```

### Step B: run Extraction Lab on finalized store

```bash
RUN_ID="phase5_probe_$(date -u +%Y%m%dT%H%M%SZ)"
uv run python -m extraction_lab.run_extraction_lab \
  --surface core_extraction \
  --store out/stores/batch_api_full_corpus \
  --out-dir out/extraction_lab \
  --run-id "$RUN_ID"
```

### Step C: run regression assertion

```bash
uv run python -m extraction_lab.assert_regression \
  --surface core_extraction \
  --current "out/extraction_lab/$RUN_ID/aggregate_metrics.json" \
  --baseline out/extraction_lab/baselines/core_extraction/current/aggregate_metrics.json \
  --thresholds extraction_lab/regression_thresholds.json
```

If no baseline exists yet, run without `--baseline` and record the expected `no_baseline_for_surface` warning.

### Required reported fields

- `run_id`
- `entity_anchor_recall`
- `fact_anchor_recall`
- `unresolved_core_anchors`
- regression assertion `pass`
- regression `warnings` and `failures`

---

## 11) Definition of Done for Phase 5

Phase 5 is done when:

- local transition from `entity_complete` to `fact_submitted` is repeatedly successful and stable under constrained-machine profile,
- evidence-backed telemetry shows bounded transition behavior,
- and the benchmark proof loop demonstrates finalized output can be consumed by Extraction Lab and regression assertion path.

At that point, hand off to Phase 6 for full-corpus Extraction Lab calibration.