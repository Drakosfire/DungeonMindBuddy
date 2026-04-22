# HANDOFF — Phase 1: Token Usage Capture

**Status:** COMPLETED
**Completed:** 2026-04-03
**Verified:** 210 passed, 2 skipped; lints clean

---

## What was implemented

### Core infrastructure (entity_extractor.py)

- `UsageStats` dataclass at line 25: `input_tokens`, `output_tokens`, `cached_tokens`, `api_calls`, with `merge()` and `to_dict()`.
- `_usage_dict_from_openai_response()` at line 42: reads `response.usage` including `input_tokens_details.cached_tokens`.
- Exported from `src/ingestion/__init__.py`.

### Entity extraction

- `OpenAIResponsesEntityClient` / `AsyncOpenAIResponsesEntityClient`: `extract_entities()` returns dict with `_usage` key.
- `_call_extractor` / `_call_recap_extractor`: strip `_usage` before Pydantic validation, return `(result, usage_dict)` tuple.
- `extract_entities_batch()` / `run_entity_extraction()`: return `{"entities", "usage", "cache_hits", "cache_misses"}`.

### Fact extraction

- Same `_usage` pattern on sync/async `extract_facts`.
- `extract_facts_batch()` / `run_fact_extraction()`: return `{"facts", "usage", "cache_hits", "cache_misses", "scoped_prompts"}`.
- `fact_extractor` imports `UsageStats` and `_usage_dict_from_openai_response` from `entity_extractor` (no new shared module).

### CLI & telemetry

- `_cmd_ingest()` unpacks `entity_result["entities"]` / `fact_result["facts"]` and records `usage`, `cache_hits/misses`, and `scoped_prompts` (facts) on `model_calls` events.

### Tests

- Updated: `test_entity_extractor.py`, `test_fact_extractor.py`, `test_cli.py`, `test_recap_models.py`, `test_score_gold.py`, and eval scripts under `evals/mirathorn_vertical_slice/`.
- Added: `test_usage_accumulates_across_units` (entities) and `test_usage_accumulates_across_fact_units` (facts).
- Extended OpenAI adapter tests to assert `_usage` from fake response objects.
- `test_entity_extractor_filters.py` had no mocked clients — no changes needed.

---

## Key contracts for downstream phases

Downstream phases depend on these return shapes:

```python
# Entity extraction (run_entity_extraction / extract_entities_batch)
entity_result = {
    "entities": list[dict],
    "usage": {"input_tokens": int, "output_tokens": int, "cached_tokens": int, "api_calls": int},
    "cache_hits": int,
    "cache_misses": int,
}

# Fact extraction (run_fact_extraction / extract_facts_batch)
fact_result = {
    "facts": list[dict],
    "usage": {"input_tokens": int, "output_tokens": int, "cached_tokens": int, "api_calls": int},
    "cache_hits": int,
    "cache_misses": int,
    "scoped_prompts": int,
}

# UsageStats (importable from src.ingestion.entity_extractor or src.ingestion)
from src.ingestion import UsageStats
```
