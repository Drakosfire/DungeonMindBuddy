# HANDOFF — Phase 8: OpenAI Batch API

**Status:** COMPLETED
**Completed:** 2026-04-03
**Verified:** 215 passed, 2 skipped; ruff clean on touched files

---

## Design decision

`known_entities` must follow the store per file (same as normal corpus ingest), so the flow is **per file**: chunk → entity batch job → fill caches → `run_entity_extraction` (cache-only) → fact batch job → fill caches → `run_fact_extraction` (cache-only) → gates + store. This matches interactive semantics and still uses Batch pricing for the actual model work.

---

## What was implemented

### `src/ingestion/openai_batch_pipeline.py` (new module)

- Builds `/v1/responses` bodies (via `type_to_text_format_param`), writes JSONL, `files.create` + `batches.create`, polls, downloads output/error JSONL.
- `extract_response_body_from_batch_line` / `extract_output_text_from_responses_body` — parse Batch API result lines.

### Entity extractor (`entity_extractor.py`)

- `prepare_entity_batch_requests()` — skips cache hits; recap units → one request each (`RecapExtractionResult`); standard units → `entity_batch_{NNNN}` with `BatchedEntityExtractionResult`.
- `apply_entity_batch_outputs_to_cache()` — writes per-unit cache files from batch results.

### Fact extractor (`fact_extractor.py`)

- `prepare_fact_batch_requests()` — same cache/skip rules as the live path; `fact_batch_{NNNN}` lines with `BatchedFactExtractionResult`.
- `apply_fact_batch_outputs_to_cache()` — writes per-unit cache files from batch results.

### CLI (`src/cli.py`)

- `ingest ... --use-openai-batch-api` — runs the two batch jobs, writes `<store>/logs/openai_batch/<run_id>/` (requests JSONL, output JSONL, manifests), logs `model_calls` with `openai_batch: true` and batch usage.

### Batch tool (`tools/batch_ingest_corpus.py`)

- `--use-batch-api` appends `--use-openai-batch-api` to each `ingest` / `ingest --force` line (including escalation).
- Summary includes `use_openai_batch_api`.

### Batch report (`batch_report.json` / stdout table)

- If any included `model_calls` row has `openai_batch`, `estimated_cost_usd` is multiplied by 0.5 and fields `openai_batch_discount_applied`, `openai_batch_pricing_multiplier`, `estimated_cost_before_openai_batch_usd` are set.
- Printed report adds `(×0.5 OpenAI Batch pricing)`.

---

## Usage

```bash
# Batch API corpus run (3 files)
uv run python tools/batch_ingest_corpus.py \
  --store out/stores/my_store --use-batch-api --limit 3

# Single file via CLI
uv run python -m src.cli
# then: ingest /path/to/file.md --use-openai-batch-api
```

---

## Operational notes

- End-to-end behavior depends on live Batch output shape. If OpenAI changes the batch result line format, adjust `extract_response_body_from_batch_line` / `extract_output_text_from_responses_body` in `openai_batch_pipeline.py`.
- A small corpus run with `--limit 1` is the right first check with a real API key.
- Cache files are written per evidence unit after batch completion, so subsequent non-batch runs benefit from the warm cache.

---

## Cost impact (all phases combined)

| Phase | Mechanism | Savings |
|---|---|---|
| 3 | Prompt prefix caching | ~90% off cached input tokens |
| 4 | Multi-unit batching | 5–10x fewer API calls |
| 8 | OpenAI Batch API | 50% off total cost |
| **Combined** | | **~5–10% of original baseline cost** |
