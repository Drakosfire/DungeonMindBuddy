# HANDOFF — Phase 2: Recap Lane Wiring

**Status:** COMPLETED
**Completed:** 2026-04-03
**Verified:** 13 passed (test_cli.py); lints clean on src/cli.py

---

## Goal

The recap extraction pipeline is fully implemented (`_call_recap_extractor`, `RecapExtractionResult`, `extract_entities_batch` with `recap_artifacts`) and the store can persist event records and claims (`store.add_event_records`, `store.add_claims`). But `cli.py` `_cmd_ingest()` never passes `recap_artifacts` to `run_entity_extraction()` and never calls `store.add_event_records()` / `store.add_claims()`. Fix the ~10-line wiring gap.

---

## File Locations

| File | Lines | What to change |
|---|---|---|
| `src/cli.py` | 590–600 | Pass `recap_artifacts` to `run_entity_extraction()` |
| `src/cli.py` | 700–717 | After store persistence, also persist event_records/claims |
| `src/cli.py` | 601–612 | Add recap counts to model_calls log entry |

---

## Current Code (cli.py line 590–599, after Phase 1)

```python
entity_client = AsyncOpenAIResponsesEntityClient(api_key=api_key)
t1 = time.perf_counter()
entity_result = run_entity_extraction(
    evidence_units,
    known_entities=self.store.list_entities(),
    concurrency=parsed.entity_concurrency,
    cache_dir=cache_dir,
    openai_client=entity_client,
    allow_heuristic_fallback=False,
)
entities = entity_result["entities"]
entity_usage = entity_result["usage"]
```

Phase 1 dict unpacking is already in place. No `recap_artifacts` parameter yet.

---

## Changes

### 1. Create recap_artifacts dict before entity extraction (before line 590)

```python
recap_artifacts: dict[str, list[dict[str, Any]]] = {
    "event_records": [],
    "claims": [],
}
```

### 2. Pass to run_entity_extraction (line 592)

Add the `recap_artifacts` kwarg to the existing call:

```python
entity_result = run_entity_extraction(
    evidence_units,
    known_entities=self.store.list_entities(),
    concurrency=parsed.entity_concurrency,
    cache_dir=cache_dir,
    openai_client=entity_client,
    allow_heuristic_fallback=False,
    recap_artifacts=recap_artifacts,  # NEW
)
```

### 3. Persist event_records and claims after store persistence

After `self.store.add_facts(facts)` (currently around line 714), add:

```python
if recap_artifacts["event_records"]:
    self.store.add_event_records(recap_artifacts["event_records"])
if recap_artifacts["claims"]:
    self.store.add_claims(recap_artifacts["claims"])
```

### 4. Add counts to completion log

Update the print statement to include event_records/claims counts:

```python
print(
    "  Stored. Total: "
    f"{len(self.store.entities)} entities, "
    f"{len(self.store.facts)} facts, "
    f"{len(recap_artifacts['event_records'])} event_records, "
    f"{len(recap_artifacts['claims'])} claims"
)
```

### 5. Add counts to entity extraction model_calls log entry (line 603–617)

In the existing `_record_event("model_calls", {...})` dict for entity_extraction, add:

```python
"event_records_count": len(recap_artifacts["event_records"]),
"claims_count": len(recap_artifacts["claims"]),
```

---

## Verification

- [ ] `uv run pytest tests/test_cli.py` passes
- [ ] Linter clean on `src/cli.py`
- [ ] Ingest a session_recap file and confirm event_records/claims appear in store (manual spot check)
- [ ] Ingest a non-recap file and confirm 0 event_records/claims (no crash, no noise)
