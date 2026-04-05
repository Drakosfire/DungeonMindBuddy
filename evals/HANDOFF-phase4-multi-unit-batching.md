# HANDOFF — Phase 4: Multi-Unit Batching

**Status:** COMPLETED
**Completed:** 2026-04-03
**Verified:** 213 passed, 2 skipped; ruff clean on touched files

---

## What was implemented

### Behavior

- `run_entity_extraction` / `run_fact_extraction` accept `batch_size` with default `1`, so existing callers and stubs keep the old one-call-per-unit behavior.
- `ingest` CLI adds `--batch-size` (default 5) and forwards to both extractors. Invalid values (< 1) fail with a clear error.
- `tools/batch_ingest_corpus.py` adds `--batch-size` (default 5) and appends it to every `ingest` / `ingest --force` line.
- Session recap entity units are still one API call each (different schema: `RecapExtractionResult`). Only standard entity units are multi-batched.
- Cache: still one JSON file per evidence unit (`_cache_key` unchanged); batched responses are split and written per unit.
- Mismatch handling: missing `evidence_id`s in a batch are logged; those units get empty entities/facts so the run does not crash.

### Code changes

| Area | Changes |
|---|---|
| `entity_extractor.py` | `UnitEntityResult`, `BatchedEntityExtractionResult`, `_build_batched_entity_user_prompt`, `extract_entities_batched` on sync/async clients, `extract_entities_batch(..., batch_size=1)` with cache-first pass + batched uncached standard units |
| `fact_extractor.py` | `UnitFactResult`, `BatchedFactExtractionResult`, `_prompt_entities_for_unit`, `_build_batched_fact_user_prompt`, `extract_facts_batched` on sync/async clients, same batching pattern with per-section entity lists |
| `cli.py` | `--batch-size`, validation, `extraction_batch_size` on ingest run events |
| Tests | Batched-call tests for entity + fact paths; CLI batch-size validation and wiring assertions |

### Key contracts for downstream phases

```python
# Client batched methods (entity)
openai_client.extract_entities_batched(
    model=model_id,
    system_prompt=system_prompt,
    user_prompt=batched_user_prompt,
    prompt_id=_PROMPT_ID,
) -> dict[str, Any]  # includes _usage

# Client batched methods (fact)
openai_client.extract_facts_batched(
    model=model_id,
    system_prompt=system_prompt,
    user_prompt=batched_user_prompt,
    prompt_id=_PROMPT_ID,
) -> dict[str, Any]  # includes _usage

# Batch functions accept batch_size
run_entity_extraction(..., batch_size=5) -> {"entities", "usage", "cache_hits", "cache_misses"}
run_fact_extraction(..., batch_size=5) -> {"facts", "usage", "cache_hits", "cache_misses", "scoped_prompts"}
```

### Backward compatibility

- `--batch-size 1` restores pre-Phase-4 behavior (one API call per unit).
- Default `batch_size=1` on the Python API means tests and programmatic callers are unaffected unless they opt in.
