# HANDOFF — Phase 5: Enriched Model Calls Logging

**Status:** COMPLETED
**Completed:** 2026-04-03 (model_name item; event_records_count/claims_count done in Phase 2)
**Verified:** 45 passed (test_cli, test_entity_extractor, test_fact_extractor); lints clean

---

## What was implemented across Phases 1, 2, and 5

All model_calls enrichment is now complete. Here is the cumulative state:

### Phase 1 added:
- `usage`: nested dict `{input_tokens, output_tokens, cached_tokens, api_calls}`
- `cache_hits`, `cache_misses`
- `scoped_prompts` (fact extraction only)

### Phase 2 added:
- `event_records_count`, `claims_count` (entity extraction only)

### Phase 5 added:
- `model_name` — `extract_entities_batch()` and `extract_facts_batch()` now return `"model_name": model_id`. CLI records it via `.get("model_name", "")` for backward compatibility (mocked tests produce `""`).

---

## Final model_calls.jsonl schema (per entry)

```json
{
  "run_id": "uuid",
  "timestamp": "ISO8601",
  "stage": "entity_extraction | fact_extraction",
  "duration_ms": 12345,
  "input_units": 34,
  "output_entities": 42,
  "model_role": "structured_generation",
  "model_name": "gpt-4o-mini-2024-07-18",
  "usage": {
    "input_tokens": 45000,
    "output_tokens": 3200,
    "cached_tokens": 0,
    "api_calls": 34
  },
  "cache_hits": 12,
  "cache_misses": 22,
  "event_records_count": 0,
  "claims_count": 0,
  "scoped_prompts": 34
}
```

Note for Phase 6 (batch report): `usage` is a nested dict — access via `entry["usage"]["input_tokens"]` etc. `model_name` may be `""` in test/mock contexts.
