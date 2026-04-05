# Handoff: Entity Taxonomy, Profile Dispatch, Recap Lane, and Eval Instrumentation

**Date:** 2026-04-02  
**Repo:** `DungeonMindBuddy` (`/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy`)  
**Branch:** `main`  
**Status:** Phases A–C implemented and covered by tests. Optional corpus re-ingest and downstream consumers remain.

**Audience:** Anyone continuing ingestion, evals, or retrieval work on entities, events, and claims.

---

## 0. Verify baseline

```bash
cd /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy
uv run pytest tests/ -q                                 # expect: 208 passed, 2 skipped
uv run python evals/llm_ingestion_slice/run_slice.py    # expect: exit 0, gates pass (when run)
```

---

## 1. Problem statement (why this exists)

A full 130-file corpus ingest produced 7,667 entities. **27.1% were `entity_type=other`** — a catch-all with weak retrieval value. Escalating from `gpt-5.4-mini` to `gpt-5.4` made taxonomy quality **worse** (`other_rate` 36.9% → 42.5%), so the bottleneck was taxonomy and prompt design, not raw model strength.

**Direction:** Separate ontology (`entity_class`, `subtype_facets`), narrative/document tags, explicit `decision=exclude`, authority weighting, and **source-profile-specific** extraction behavior. Session recaps additionally emit **event records** and **claims**.

See `evals/RESEARCH-entity-taxonomy-design.md` and `evals/AUTO_ESCALATION_FULL_CORPUS_REPORT.md` for research and escalation artifacts.

---

## 2. Historical corpus metrics (pre-rework reference)

These tables describe the **old** `entity_type` / `entity_kind` world. They remain useful when comparing re-ingests or interpreting older store snapshots.

### 2.1 Type and kind distribution (7,667 entities)

| entity_type | Count | % |
|-------------|------:|----:|
| other | 2,075 | 27.1% |
| item | 1,799 | 23.5% |
| npc | 1,731 | 22.6% |
| location | 1,635 | 21.3% |
| faction | 427 | 5.6% |

| entity_kind | Count | % |
|-------------|------:|----:|
| object | 1,859 | 24.2% |
| actor | 1,637 | 21.4% |
| place | 1,614 | 21.1% |
| concept | 1,275 | 16.6% |
| group | 572 | 7.5% |
| event | 379 | 4.9% |
| document_anchor | 323 | 4.2% |
| unknown | 8 | 0.1% |

### 2.2 “Other” breakdown (failure categories)

| Category | Count | % of others | Examples |
|----------|------:|:-----------:|---------|
| Named concepts (legitimate but mistyped) | 1,197 | 57.7% | Festival of Expansion, Song of Shattering |
| Document structure | 409 | 19.7% | Executive DM Summary, Running the Location |
| Generic words | 253 | 12.2% | light, water, roots, smoke |
| D&D spells | 106 | 5.1% | Detect Magic, Mage Hand |
| D&D skills | 99 | 4.8% | Insight, Arcana, Persuasion |
| Mechanics text | 11 | 0.5% | Dexterity save (DC 12) |

### 2.3 Escalation lesson

On 40 files escalated mini → full: `other_rate` improved 9, worsened 30, unchanged 1; throughput rose but taxonomy degraded.

**Conclusion:** Clear enums, prompt rules, and profile dispatch matter more than “stronger model” alone.

---

## 3. What is implemented now (executive summary)

| Area | Behavior |
|------|----------|
| **Taxonomy** | `entity_class` ∈ {actor, group, place, object, event, concept}; `decision` ∈ {entity, exclude} with `exclude_reason`; separate `subtype_facets`, `narrative_tags`, `document_tags`; `authority` and `source_profile` on extraction. |
| **Legacy** | `entity_type` / `entity_kind` / `semantic_facets` still accepted on `ExtractedEntity` for old cache/prompts; pipeline normalizes toward new fields. |
| **Phase A: Profile dispatch** | `_resolve_source_profile(unit)` maps evidence metadata → profile string; `_build_prompt()` prepends `_WORLDBUILDING_PREFIX` or `_SESSION_RECAP_PREFIX` (other profiles currently fall back to worldbuilding prefix). Cache key includes `source_profile`. `_PROMPT_ID` = `phase_b_pass1_entity_extraction_v5_profiled_dispatch`. |
| **Phase B: Recap pipeline** | `session_recap` units use `_build_recap_prompt()` + `_call_recap_extractor()` with `RecapExtractionResult` (`entities`, `event_records`, `claims`). Optional `recap_artifacts` dict collects lists for callers. `FactStore` persists `event_records.json` and `claims.json` with schema validation. |
| **Phase C: Eval instrumentation** | `excluded_candidates.json` under cache root (append-only across runs in a session). `extraction_method` ∈ {llm, heuristic} on entities. `score_gold.py` adds `concept_event_confusion` and `exclude_path_metrics`; loads `excluded_candidates.json` when present. |
| **Heuristic path** | `_heuristic_extract_entities` sets `extraction_method="heuristic"`; class inferred via `_infer_entity_class`. |

---

## 4. Source profile resolution (Phase A)

**Function:** `src/ingestion/entity_extractor.py` → `_resolve_source_profile(unit)`

| Condition | Profile |
|-----------|---------|
| `source_class == "observed_session_recap"` | `session_recap` |
| `canon_layer == "world"` | `worldbuilding` |
| `source_class in ("planning_document", "seed_reference")` | `worldbuilding` |
| `source_class == "ledger_or_dossier"` | `npc_dossier` |
| Default | `worldbuilding` |

**Prompt prefixes:** `_PROFILE_PREFIXES` currently keys only `worldbuilding` and `session_recap`. Resolved profiles `npc_dossier`, `item_card`, etc. use the **worldbuilding** prefix until dedicated strings are added.

**Cache:** `_cache_key(unit, model_id, source_profile)` hashes `text | _PROMPT_ID | model_id | source_profile`. Changing prompt or profile resolution requires bumping `_PROMPT_ID` (or recap `_RECAP_PROMPT_ID`) if you rely on cache correctness.

**Recap prompt ID:** `_RECAP_PROMPT_ID = "recap_extraction_v1"` (used by `_call_recap_extractor`).

---

## 5. Recap extraction and persistence (Phase B)

### 5.1 Models

**File:** `src/ingestion/recap_models.py`

- `EventRecord` — `event_class`, `time_scope`, `certainty`, optional `event_name`, `participants`, `location`, `outcomes`
- `ClaimRecord` — `subject`, `predicate`, `object`, `claim_type`, `speaker_or_source`, `certainty`
- `RecapExtractionResult` — `entities`, `event_records`, `claims`

### 5.2 Batch API

**Functions:** `extract_entities_batch(...)`, `run_entity_extraction(...)`

- Optional `recap_artifacts: dict[str, list[dict[str, Any]]] | None`. When provided and profile is `session_recap`, keys `event_records` and `claims` are extended with serialized recap outputs (entities still flow through the normal entity path).

### 5.3 Store

**File:** `src/store.py`

- `load()` / `save()` read/write `event_records.json`, `claims.json` beside other store JSON.
- `add_event_records(records)` — validates against `event_record.schema.json`
- `add_claims(claims)` — validates against `claim.schema.json`

### 5.4 JSON schemas

- `schemas/v0.1/event_record.schema.json`
- `schemas/v0.1/claim.schema.json`
- `schemas/v0.1/entity.schema.json` includes `extraction_method` enum `llm` | `heuristic`

---

## 6. Excluded candidates and scoring (Phase C)

### 6.1 `excluded_candidates.json`

Written under the **cache root** used for extraction (same tree as per-unit cache files): path `.../excluded_candidates.json`.

Each run **appends** to the file after loading existing content. Entries include LLM `decision=exclude` rows and heuristic filter rejects (fields such as `display_name`, `exclude_reason`, `source_profile`, `extraction_method`, provenance hints — see `extract_entities_batch` implementation for the exact shape).

### 6.2 Gold scorer extensions

**File:** `evals/llm_ingestion_slice/score_gold.py`

- `_concept_event_confusion` — mismatches where gold vs stage disagree on treating a span as `event` vs `concept` (by normalized name keys).
- `_exclude_path_metrics` — counts excluded candidates, reasons, heuristic vs llm, and false-positive style signals vs gold non-entities when data allows.
- `main()` loads `artifacts_dir / "excluded_candidates.json"` when present and passes into `score()`.

Report keys include `concept_event_confusion` and `exclude_path_metrics`.

---

## 7. Taxonomy contract and extraction model

### 7.1 Contract module

**File:** `src/contracts/entity_taxonomy.py`

- `EntityClass`, `SourceProfile`, `Authority`, `ExcludeReason` literals
- `ALLOWED_SUBTYPE_FACETS`, `ALLOWED_NARRATIVE_TAGS`, `ALLOWED_DOCUMENT_TAGS`
- `EntityKind` alias → `EntityClass`; `ALLOWED_SEMANTIC_FACETS` alias → subtype facets
- `normalize_semantic_facets()` — controlled tokens + `domain:*` extensions

### 7.2 `ExtractedEntity` (high level)

**File:** `src/ingestion/entity_extractor.py`

Primary fields: `decision`, `exclude_reason`, `entity_class`, `display_name`, `aliases`, `subtype_facets`, `narrative_tags`, `document_tags`, `source_profile`, `authority`, `confidence`, `span_text`, `extraction_method`, `is_new`, plus legacy `entity_type`, `entity_kind`, `entity_tags`, `semantic_facets`.

### 7.3 Hygiene and mechanics filtering

Same module: `_is_plausible_entity_name`, `_DND_SKILLS`, `_DND_SPELLS`, `_MECHANICS_PATTERNS`, expanded `_LOW_SIGNAL_SINGLE_TOKENS`, junk lists, `other`-style rules coordinated with `decision=exclude` prompt policy.

---

## 8. Tests to read before changing behavior

| File | Focus |
|------|--------|
| `tests/ingestion/test_entity_extractor_filters.py` | `_resolve_source_profile`, profile-specific prompt text, filters |
| `tests/ingestion/test_recap_models.py` | Recap models, recap prompt, batch collection, schema, `FactStore` event/claim persistence |
| `tests/evals/test_score_gold.py` | Concept/event confusion, exclude metrics, excluded file wiring |
| `tests/test_entity_extractor.py`, `tests/test_store.py`, … | Integration with store and extraction |

---

## 9. Optional / not done in Phases A–C

1. **Dedicated prompt prefixes** for `npc_dossier`, `item_card`, `encounter_table`, `cultural_event_doc` (currently default to worldbuilding prefix text).
2. **3-file corpus verification** — re-ingest and compare `entity_class` distribution vs historical `other_rate` (target discussed: `other_rate`-equivalent pollution low; modern metric is exclude rate + class balance).
3. **Downstream consumers** — retrieval, context formatter, and UI may need to surface `event_records` and `claims` alongside entities.
4. **Batch ingest / CLI** — ensure orchestration passes `recap_artifacts` and calls `add_event_records` / `add_claims` when wiring full pipeline (verify call sites if not already connected).

---

## 10. Key file index

| Area | Path |
|------|------|
| Extraction + prompts + batch | `src/ingestion/entity_extractor.py` |
| Recap Pydantic models | `src/ingestion/recap_models.py` |
| Taxonomy literals + facet allowlists | `src/contracts/entity_taxonomy.py` |
| Entity tag normalization | `src/contracts/entity_tags.py` |
| Store + event/claim persistence | `src/store.py` |
| Entity / event / claim schemas | `schemas/v0.1/entity.schema.json`, `event_record.schema.json`, `claim.schema.json` |
| Deterministic slice entities | `src/ingestion/event_sourced_slice.py` |
| Context formatting | `src/agent/context_formatter.py` |
| Gold data | `evals/llm_ingestion_slice/gold/manual_entity_extraction_gold.json` |
| Gold scorer | `evals/llm_ingestion_slice/score_gold.py` |
| Slice harness | `evals/llm_ingestion_slice/run_slice.py` |
| Model policy (parent repo) | `/home/drakosfire/Projects/DungeonOverMind/MODEL_POLICY.json` |
| Research brief | `evals/RESEARCH-entity-taxonomy-design.md` |
| Escalation report | `evals/AUTO_ESCALATION_FULL_CORPUS_REPORT.md` |
| Batch ingest | `tools/batch_ingest_corpus.py` |

---

## 11. Design constraints (still apply)

1. **Re-ingest over migration** — old store rows can be replaced by a full ingest; prefer additive schema changes when possible.
2. **Cache invalidation** — bump `_PROMPT_ID` / `_RECAP_PROMPT_ID` when prompt semantics change; `source_profile` is already in the entity cache key.
3. **Model band** — prompts should remain clear for smaller structured models as well as larger ones.
4. **Facet gates** — unknown subtype facets (outside allowlist and not `domain:*`) are dropped in normalization; update `ALLOWED_*` when expanding vocabulary.

---

## 12. Canonical taxonomy spec (reference)

Principle: **ontology is shared, extraction behavior is profile-specific, truth is authority-scoped.**

### 12.1 Core extraction decision shape

```json
{
  "decision": "entity | exclude",
  "entity_class": "actor | group | place | object | event | concept",
  "subtype_facets": ["..."],
  "source_profile": "...",
  "authority": "...",
  "confidence": 0.0
}
```

- `entity` — durable, retrievable campaign-world referent  
- `exclude` — do not persist in entity graph  

### 12.2 Entity classes

- `actor`, `group`, `place`, `object`, `event`, `concept`  
- No persisted `other`, `document_anchor`, or `unknown` **class** (excludes use `decision=exclude`).

### 12.3 Exclusion reasons

`generic_noun | descriptive_phrase | document_structure | game_mechanic | sentence_fragment | temporal_connector | underspecified_collective`

### 12.4 Facet lanes

- **subtype_facets** — ontology detail  
- **narrative_tags** — story function  
- **document_tags** — authoring structure  

### 12.5 Authority

`canon_reference | planning_note | play_record | rumor_or_belief | mechanic_reference`

### 12.6 Source profiles

`worldbuilding | session_recap | npc_dossier | item_card | encounter_table | cultural_event_doc`

### 12.7 Session recap outputs

Beyond entities: `event_records[]`, `claims[]` — shapes implemented in `recap_models.py` and JSON schemas.

---

## 13. Implementation-ready enum sketch (spec; code uses literals)

The codebase uses `Literal` types and Pydantic models rather than `enum.Enum` for these. The following remains a readable spec mirror.

```python
# Conceptual only — see entity_taxonomy.py and recap_models.py for truth.

class ExtractionDecision(str, Enum):
    ENTITY = "entity"
    EXCLUDE = "exclude"

class EntityClass(str, Enum):
    ACTOR = "actor"
    GROUP = "group"
    PLACE = "place"
    OBJECT = "object"
    EVENT = "event"
    CONCEPT = "concept"

class ExcludeReason(str, Enum):
    GENERIC_NOUN = "generic_noun"
    DESCRIPTIVE_PHRASE = "descriptive_phrase"
    DOCUMENT_STRUCTURE = "document_structure"
    GAME_MECHANIC = "game_mechanic"
    SENTENCE_FRAGMENT = "sentence_fragment"
    TEMPORAL_CONNECTOR = "temporal_connector"
    UNDERSPECIFIED_COLLECTIVE = "underspecified_collective"

class SourceProfile(str, Enum):
    WORLDBUILDING = "worldbuilding"
    SESSION_RECAP = "session_recap"
    NPC_DOSSIER = "npc_dossier"
    ITEM_CARD = "item_card"
    ENCOUNTER_TABLE = "encounter_table"
    CULTURAL_EVENT_DOC = "cultural_event_doc"

class Authority(str, Enum):
    CANON_REFERENCE = "canon_reference"
    PLANNING_NOTE = "planning_note"
    PLAY_RECORD = "play_record"
    RUMOR_OR_BELIEF = "rumor_or_belief"
    MECHANIC_REFERENCE = "mechanic_reference"
```

### 13.1 Migration mapping (legacy → new)

```text
npc → actor
location → place
faction → group
item → object
other + kind=event → event
other + kind=concept → concept
other + kind=document_anchor → exclude/document_structure
other + generic noun pattern → exclude/generic_noun
```

Replace over time: `entity_type` + `entity_kind` + single mixed `semantic_facets` → `entity_class` + `subtype_facets` + `narrative_tags` + `document_tags` + `authority` + `source_profile`.
