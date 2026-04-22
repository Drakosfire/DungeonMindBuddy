# HANDOFF — Phase 3: Prompt Restructuring for OpenAI Prompt Caching

**Status:** COMPLETED
**Completed:** 2026-04-03
**Verified:** 210 passed, 2 skipped; ruff clean on both ingestion modules

---

## What was implemented

### Entity extraction (entity_extractor.py)

- `_build_entity_system_prompt()` — Static role, profile docs, ontology, excludes, authority, output rules, per-field `ExtractedEntity` notes (~4.4k chars, ~1,100 tokens est.).
- `_build_entity_user_prompt()` — Source profile, profile prefix, `known_entities` JSON, evidence text.
- `_build_recap_system_prompt()` / `_build_recap_user_prompt()` — Same split for the recap lane; recap system text ~4.3k chars (~1,077 tokens est.).
- `OpenAIResponsesEntityClient` / `AsyncOpenAIResponsesEntityClient` — `responses.parse` now uses `input=[system, user]` instead of a single user message.
- `_call_extractor` / `_call_recap_extractor` — Take a prebuilt `system_prompt`; user text from the new builders.
- `extract_entities_batch` — Builds `entity_system_prompt` and `recap_system_prompt` once and reuses for all units.
- IDs bumped: `_PROMPT_ID` → `phase_b_pass1_entity_extraction_v6_prompt_cache_split`, `_RECAP_PROMPT_ID` → `recap_extraction_v2_prompt_cache`.

### Fact extraction (fact_extractor.py)

- `_build_fact_system_prompt()` / `_build_fact_user_prompt()` — Same pattern; system block ~4.2k chars (~1,040 tokens est.).
- Clients and `_call_extractor` — Two-message input; batch loop uses one `fact_system_prompt` for all units.
- `_PROMPT_ID` → `phase_c_pass2_fact_extraction_v2_prompt_cache`.

### Tests

- `test_entity_extractor_filters.py` — Uses new builders (user vs system) instead of `_build_prompt`.
- `test_recap_models.py` — Asserts recap instructions on system text and `_SESSION_RECAP_PREFIX` on user text.
- `test_entity_extractor.py` / `test_fact_extractor.py` — Adapter tests assert two-turn input and pass `system_prompt` + `user_prompt`.

### Client signature contract for downstream phases

```python
# Entity client
openai_client.extract_entities(
    model=model_id,
    system_prompt=system_prompt,   # static, cacheable
    user_prompt=user_prompt,       # per-unit variable
    evidence_unit=unit,
    known_entities=known_entities,
    prompt_id=_PROMPT_ID,
)

# Fact client
openai_client.extract_facts(
    model=model_id,
    system_prompt=system_prompt,
    user_prompt=user_prompt,
    evidence_unit=unit,
    entities=entities,
    prompt_id=_PROMPT_ID,
)
```

### Cache invalidation

Bumped `_PROMPT_ID` / `_RECAP_PROMPT_ID` values force re-extraction on next corpus run. Existing file caches are stale and will be regenerated.

### Validation note

`tiktoken` is not in the env; token estimates are `len(chars) / 4`. All three system prompts are above ~1,000 tokens by that estimate, meeting the OpenAI 1,024-token prefix caching threshold. Actual `cached_tokens > 0` can be confirmed on first real corpus run via Phase 1 usage data.
