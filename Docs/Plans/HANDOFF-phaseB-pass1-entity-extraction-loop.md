# Handoff: Phase B — Pass 1 Entity Extraction Loop

## Read First

- `Docs/Design/DESIGN-layered-canon-vertical-slice.md` — canonical design and current decisions
- `src/store.py` — Phase A JSON persistence + projection delegation
- `src/ingestion/docx_converter.py` — docx/markdown normalization and heading fallback logic
- `src/ingestion/chunker.py` — deterministic chunking pipeline and evidence-unit emission
- `evals/mirathorn_vertical_slice/eval_chunker.py` — Phase A chunking gate script

## Current State (Verified)

Phase A is implemented and committed. Foundation is in place for automated ingestion.

Recent commits:
- `7237253` — Phase A implementation + design updates
- `3d97383` — Step 2/3 fixtures, runners, and projection artifacts

Implemented files:
- `src/store.py`
- `src/ingestion/__init__.py`
- `src/ingestion/docx_converter.py`
- `src/ingestion/chunker.py`
- `tests/test_store.py`
- `tests/test_docx_converter.py`
- `tests/test_chunker.py`
- `evals/mirathorn_vertical_slice/eval_chunker.py`

Validation status:
- `uv run pytest` => all tests passing
- `uv run ruff check ...` => clean
- `uv run python evals/mirathorn_vertical_slice/eval_chunker.py` => PASS

## Scope for This Handoff

Implement **Phase B only**: Pass 1 entity extraction loop on top of Phase A.

Do **not** implement Pass 2 fact extraction in this handoff.

## Objective

Take chunked evidence units and extract a high-recall entity set using an LLM loop patterned after RulesIngestion `enrich_units_batch` style orchestration (concurrency + structured outputs + cache), then persist entities through `FactStore`.

## Deliverables

Create:
- `src/ingestion/entity_extractor.py`
- `evals/mirathorn_vertical_slice/gold/gold_entities.json`
- `evals/mirathorn_vertical_slice/eval_entity_recall.py`
- `tests/test_entity_extractor.py`

Update:
- `src/ingestion/__init__.py` (exports)

Optional helper if needed:
- `src/ingestion/models.py` for Pydantic response models (if extractor file becomes too large)

## Required Behavior

### 1) Entity extraction contract

Input:
- list of evidence units (from `chunk_document`)
- optional known entities for ID reuse

Output:
- extracted entity records valid against `schemas/v0.1/entity.schema.json`

Entity record expectations:
- `entity_id`
- `entity_type` (`npc | location | faction | item | other`)
- `display_name`
- `aliases` (list)
- `entity_status` default `provisional`
- `source_mention_ids` can be deterministic placeholders for now (for schema compliance)

### 2) Loop shape

Use an async batch loop with bounded concurrency:
- one LLM call per evidence unit
- structured output parsing (Pydantic model)
- deterministic cache key from `(chunk content fingerprint + prompt id + model id)`
- cache on disk under `store_dir` or eval output subtree

### 3) ID policy

For new entities:
- deterministic slug form: `ent_<snake_case_display_name>`
- sanitize to schema-safe `idString` pattern

For matches against known entities:
- reuse existing `entity_id`

### 4) Recall-first post-processing

After per-chunk extraction:
- merge duplicates case-insensitively by display/aliases (can reuse `FactStore.add_entities`)
- keep broad recall; do not aggressively prune borderline entities in Phase B

## Suggested API

`src/ingestion/entity_extractor.py`:

```python
class ExtractedEntity(BaseModel): ...
class EntityExtractionResult(BaseModel): ...

async def extract_entities_batch(
    evidence_units: list[dict[str, Any]],
    *,
    known_entities: list[dict[str, Any]] | None = None,
    model: str | None = None,
    concurrency: int = 8,
    cache_dir: Path | None = None,
    openai_client: Any | None = None,
) -> list[dict[str, Any]]:
    ...
```

Sync wrapper for CLI/evals:

```python
def run_entity_extraction(... ) -> list[dict[str, Any]]:
    return asyncio.run(extract_entities_batch(...))
```

## Evaluation Gate (Phase B)

Create a gold entity list for Mirathorn Set A:
- `evals/mirathorn_vertical_slice/gold/gold_entities.json`

Minimum contents must include at least:
- Mirathorn
- Lake Mirathorn
- Stormspire Peaks
- Lundayell Empire
- Festival of Expansion
- Shepherd's Flock
- key council/NPC names from the corpus docs

Create `evals/mirathorn_vertical_slice/eval_entity_recall.py`:
- run chunker on Mirathorn doc
- run Pass 1 extractor
- compute recall against gold list (case-insensitive name/alias matching)
- print metric and pass/fail

Target gate:
- recall >= 0.90 on Mirathorn gold entities

## Test Requirements

Add `tests/test_entity_extractor.py` with at least:

1. deterministic ID generation / normalization
2. dedup merge behavior on alias overlap
3. cache hit behavior (no second API call when cached)
4. schema validation of produced entity dicts

Keep tests runnable without real OpenAI calls via stubs/mocks.

## Model Selection Constraint

Follow `model-selection-policy.mdc`:
- use role-based mapping from `MODEL_POLICY.json`
- avoid hardcoded legacy model strings

For Phase B (NER/classification), use the "fast smart" tier per policy.

## Integration Path (Minimal)

For this handoff, integration only needs to prove pipeline viability:
1. `chunk_document(...)` -> evidence units
2. `run_entity_extraction(...)` -> entities
3. `FactStore.add_entities(...)` -> persistence and dedup

Do not wire CLI commands yet unless trivial and low-risk.

## Verification Commands

- `uv run ruff check src/ingestion/entity_extractor.py tests/test_entity_extractor.py evals/mirathorn_vertical_slice/eval_entity_recall.py`
- `uv run pytest tests/test_entity_extractor.py`
- `uv run pytest`
- `uv run python evals/mirathorn_vertical_slice/eval_entity_recall.py`

## Done Criteria

- Pass 1 extractor implemented with async batch + cache + structured outputs
- Mirathorn gold entity file added
- Recall eval script added and passing threshold (>= 0.90) on Set A
- New tests pass and full suite remains green
- No regressions to Phase A components

## Execution Update (2026-03-27)

Phase B Pass 1 is implemented and validated with a stricter gate than originally specified.

Implemented:
- `src/ingestion/entity_extractor.py`
  - async bounded-concurrency batch loop
  - deterministic cache key based on chunk fingerprint + prompt id + model id
  - schema-validated structured extraction output (`ExtractedEntity`, `EntityExtractionResult`)
  - OpenAI Responses adapter (`OpenAIResponsesEntityClient`) using `responses.parse` with Pydantic output parsing
  - deterministic ID generation + known-entity ID reuse
  - post-processing with `FactStore.add_entities(...)` dedup merge
  - additional low-signal filtering to reduce heading/title noise while preserving recall
- `evals/mirathorn_vertical_slice/gold/gold_entities.json`
- `evals/mirathorn_vertical_slice/eval_entity_recall.py`
  - loads `.env.development`
  - enforces OpenAI-backed path (`allow_heuristic_fallback=False`)
  - computes strict and loose recall
  - enforces density guardrail (`entities_per_unit <= 1.80`)
- `tests/test_entity_extractor.py` (cache behavior, ID normalization, dedup, schema validation, adapter parsing, fallback enforcement, junk filtering)
- `src/ingestion/__init__.py` exports updated

Verification:
- `uv run ruff check src/ingestion/entity_extractor.py tests/test_entity_extractor.py evals/mirathorn_vertical_slice/eval_entity_recall.py` => PASS
- `uv run pytest tests/test_entity_extractor.py` => PASS
- `uv run pytest` => PASS
- `uv run python evals/mirathorn_vertical_slice/eval_entity_recall.py` (OpenAI-backed strict gate) =>
  - Evidence units: 126
  - Extracted entities: 202
  - Entities per unit: 1.603 (max 1.80)
  - Strict recall: 1.000
  - Loose recall: 1.000
  - PASS: True
