# HANDOFF — Phase 6: Batch Report Overhaul

**Status:** COMPLETED
**Completed:** 2026-04-03
**Verified:** 213 passed, 2 skipped; ruff clean on `tools/batch_ingest_corpus.py`

---

## What was implemented

### `_aggregate_batch_report()` (batch_ingest_corpus.py)

- Reads `logs/model_calls.jsonl` and filters to rows whose `run_id` is in the batch — includes both base-pass `run_id`s from `summary["results"]` and `escalated_run_id`s from `escalation_runs`.
- Aggregates `entity_extraction` and `fact_extraction` stages: tokens, `api_calls`, `duration_ms`, local `cache_hits`/`cache_misses`, recap `event_records_count`/`claims_count`.
- **Files:** total, succeeded (has `run_id`), failed, skipped (0), zero_output (completed with all deltas 0).
- **entity_class_distribution:** For each result path, loads `stage_entities.json` from `_latest_completed_run_for_path` (post-escalation artifacts used). Classes use `"missing"` when `entity_class` is absent.
- **Cost:** `_PRICING_PER_1M` with prefix-matched tiers (`gpt-4o-mini`, `gpt-4o`, `gpt-4.1-mini`, `gpt-4.1-nano`). Dominant model from non-empty `model_name` rows. Billable input = uncached_input + cached_tokens; `without_caching_cost_usd` assumes full input at list price. Models with no matching prefix get cost fields = 0.
- **cache_rate:** `cached_tokens / input_tokens` when `input_tokens > 0`.
- Writes `logs/batch_report.json` right after `batch_ingest_summary.json`.
- `_print_batch_report_table()` prints a stdout box table.

### `_compute_escalation_metrics()` update

- `other_rate` / `other_count` now count entities whose `entity_class` is `"other"` or `"unknown"` (explicit values only; missing class → `"missing"`, does not count toward `other_rate`).
- `other_missing_facets` uses `entity_class == "other"` and still requires empty `semantic_facets`.

### Backward compatibility

- `batch_ingest_summary.json` is unchanged.
- `batch_report.json` is additive (new file alongside existing summary).

### Pricing note

For models not in `_PRICING_PER_1M` (e.g., `gpt-5.4-nano`), cost fields are 0 until a matching prefix row is added to the dict.
