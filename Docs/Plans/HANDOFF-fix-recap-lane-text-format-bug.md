# Handoff: Fix Recap Lane `text_format` Bug

**Date:** 2026-04-03  
**Priority:** HIGH  
**Estimated Effort:** Small (surgical client change + test)  
**Precondition:** Read this file, then read referenced code before writing anything.

---

## 1) Problem Statement

Recap ingestion produces **0 `event_records` and 0 `claims`** despite correct routing, prompts, models, and downstream plumbing. The smoke report (`evals/smoke_results/HANDOFF-benchmark-sample-e2e-report-2026-04-03.md`, Run F) confirmed this on a Session 17 recap file.

### Root Cause

`_call_recap_extractor()` calls the standard `extract_entities()` client method, which hardcodes `text_format=EntityExtractionResult`. That Pydantic schema only has an `entities` field. The OpenAI structured-output parser constrains the response to that schema, so `event_records` and `claims` are never returned — even though the recap *prompt* asks for them. When the result is then validated as `RecapExtractionResult`, the missing fields default to empty lists.

The **Batch API path** already does this correctly — it passes `text_format=RecapExtractionResult` when building batch requests for recap units. The bug is only on the **live/interactive (sync + async) ingest path**.

---

## 2) File Locations (read all before writing)


| File                                   | Lines     | Role                                                                                                                                                       |
| -------------------------------------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/ingestion/entity_extractor.py`    | 335–361   | `OpenAIResponsesEntityClient.extract_entities` — sync client, hardcodes `EntityExtractionResult` (line 351)                                                |
| `src/ingestion/entity_extractor.py`    | 405–431   | `AsyncOpenAIResponsesEntityClient.extract_entities` — async client, hardcodes `EntityExtractionResult` (line 421)                                          |
| `src/ingestion/entity_extractor.py`    | 916–949   | `_call_recap_extractor` — calls `extract_entities()` and validates result as `RecapExtractionResult` (line 949)                                            |
| `src/ingestion/entity_extractor.py`    | 1536–1541 | Batch path — correctly uses `text_format=RecapExtractionResult` (line 1540)                                                                                |
| `src/ingestion/recap_models.py`        | 1–43      | `RecapExtractionResult`, `EventRecord`, `ClaimRecord` models                                                                                               |
| `tests/ingestion/test_recap_models.py` | 137–188   | `TestStubRecapClient` — uses a stub that returns all three fields; proves downstream plumbing works but does **not** guard the real client's `text_format` |


---

## 3) Fix Strategy

The fix needs the client to use `RecapExtractionResult` as the `text_format` when called from a recap context. There are two clean approaches — pick one:

### Option A: Add `extract_recap()` method to both clients (recommended)

Add a dedicated method to `OpenAIResponsesEntityClient` and `AsyncOpenAIResponsesEntityClient` that mirrors `extract_entities()` but uses `text_format=RecapExtractionResult`. Then update `_call_recap_extractor` to call it.

**Pattern source:** `extract_entities_batched()` (lines 363–387 sync, 433–457 async) already demonstrates the pattern — same method body with a different `text_format`.

```python
# In OpenAIResponsesEntityClient (sync):
def extract_recap(
    self,
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    evidence_unit: dict[str, Any],
    known_entities: list[dict[str, Any]],
    prompt_id: str,
) -> dict[str, Any]:
    from src.ingestion.recap_models import RecapExtractionResult

    response = self._client.responses.parse(
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        text_format=RecapExtractionResult,
    )
    parsed = getattr(response, "output_parsed", None)
    if parsed is None:
        raise ValueError("OpenAI response parse did not return output_parsed.")
    if isinstance(parsed, RecapExtractionResult):
        result = parsed.model_dump()
    else:
        result = RecapExtractionResult.model_validate(parsed).model_dump()
    result["_usage"] = _usage_dict_from_openai_response(response)
    return result
```

Duplicate for `AsyncOpenAIResponsesEntityClient` with `async def` / `await`.

Then in `_call_recap_extractor` (line 935–948), change:

```python
# Before:
if not hasattr(openai_client, "extract_entities"):
    raise ValueError(...)
payload = openai_client.extract_entities(...)

# After:
extract_fn_name = "extract_recap" if hasattr(openai_client, "extract_recap") else "extract_entities"
extract_fn = getattr(openai_client, extract_fn_name)
payload = extract_fn(...)
```

The fallback to `extract_entities` preserves backward compatibility with stubs that only implement `extract_entities`.

### Option B: Pass `prompt_id` as dispatch signal (lighter, less clean)

In `extract_entities()`, check if `prompt_id` starts with `"recap_"` and conditionally switch `text_format`. This avoids a new method but couples prompt naming to output schema selection.

**Recommendation:** Option A. It's explicit, follows existing patterns, and doesn't add conditional logic inside the hot path.

---

## 4) Test Changes

### 4a: Update `TestStubRecapClient` to cover the real path

The current stub test proves the downstream wiring but does not guard the `text_format` choice. Add a test that uses a **mock SDK client** (not a stub) to verify that `extract_recap()` is called with `RecapExtractionResult`:

```python
def test_recap_client_uses_recap_schema(self) -> None:
    """Verify the real client method passes RecapExtractionResult as text_format."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from src.ingestion.recap_models import RecapExtractionResult

    mock_response = MagicMock()
    mock_response.output_parsed = RecapExtractionResult(
        entities=[],
        event_records=[EventRecord(event_class="combat", time_scope="scene", certainty="observed")],
        claims=[],
    )
    mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)

    mock_sdk = MagicMock()
    mock_sdk.responses.parse.return_value = mock_response

    client = OpenAIResponsesEntityClient(sdk_client=mock_sdk)
    result = client.extract_recap(
        model="test",
        system_prompt="test",
        user_prompt="test",
        evidence_unit={},
        known_entities=[],
        prompt_id="recap_extraction_v2_prompt_cache",
    )
    # Verify text_format was RecapExtractionResult
    call_kwargs = mock_sdk.responses.parse.call_args[1]
    assert call_kwargs["text_format"] is RecapExtractionResult
    assert len(result.get("event_records", [])) == 1
```

### 4b: Add integration-style test with `_call_recap_extractor`

Ensure the full flow from `_call_recap_extractor` → client → `RecapExtractionResult` produces non-empty `event_records`/`claims` when the mock returns them.

---

## 5) Verification

After implementing, run:

```bash
uv run pytest tests/ingestion/test_recap_models.py tests/test_entity_extractor.py -v
uv run ruff check src/ingestion/entity_extractor.py
```

If API access is available, re-run the smoke Run F:

```bash
uv run python tools/batch_ingest_corpus.py \
    --store out/stores/smoke_recap_retest \
    --source "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session 17 - Recap.md"
```

**Success criteria:**

- `event_records > 0`
- `claims > 0`
- Existing entity extraction tests still pass (31 tests)

---

## 6) Scope Boundary

This handoff fixes **only** the `text_format` bug on the live client path. It does NOT:

- Change recap prompts or models
- Add new recap-specific filtering or post-processing
- Modify the Batch API path (already correct)
- Address quality drift (separate handoff)

