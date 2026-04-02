# Handoff: Gold Scoring, Threshold Policy, and Commit Hygiene

**Date:** 2026-04-02  
**Repo:** `DungeonMindBuddy` (`/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy`)  
**Branch:** `main` — 153 modified files, 22 untracked files. Not pushed.  
**Audience:** Next agent picking up commit packaging or follow-on LLM ingest scoring policy.

---

## 0. Verify baseline

```bash
cd /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy
uv run pytest tests/ -q                                 # 168 passed, 2 skipped
uv run python evals/llm_ingestion_slice/run_slice.py     # exit 0, all gates pass
```

Current gate report (deterministic slice):

| Gate | Status | Key metric |
|------|--------|------------|
| A - source/layer integrity | PASS | |
| V - extraction viability | PASS | entity_density=0.667, dup_ratio=0.0 |
| T - narrative temporal tick | PASS | |
| TC - campaign temporal consistency | PASS | |
| TW - sequence-only warning | PASS | sequence_only_ratio=0.0 |
| B - event contract integrity | PASS | |
| C - hybrid correctness | PASS | |
| D - workflow state progression | PASS | deltas: 2+2 |
| **G - gold scoring** | **PASS** | core_recall=0.3, temporal=1.0, catalog=1.0, negatives=0, eval_mode=deterministic_slice |

---

## 1. What exists now

### Gold scoring pipeline (fully implemented)

| File | Role |
|------|------|
| `evals/llm_ingestion_slice/score_gold.py` | Standalone scorer — loads gold + stage artifacts, computes entity recall/precision at 3 tiers, temporal field accuracy, catalog entity recall, negative-example violations. CLI with `--artifacts-dir`, `--min-*` thresholds, `--run-slice-first`. |
| `evals/llm_ingestion_slice/run_slice.py` | Gate G (`_gate_g_gold_scoring`) calls `score_gold.score()` inline after gates B/C/D. Writes `gold_score.json`. |
| `tests/evals/test_score_gold.py` | 7 tests: integration against deterministic slice, exact/alias/substring entity matching, negative detection, temporal pass/mismatch. |
| `evals/llm_ingestion_slice/gold/manual_entity_extraction_gold.json` | Human-authored gold (schema v1.1): 13 segments across 2 sources, ~30 expected entities, 6 temporal expectations, 4 catalog entities, 8 negative examples. |

### How scoring works

**Entity matching** (`_entity_match_score`): strength 3 = exact name/alias hit, 2 = gold suggested-alias hit, 1 = substring containment. Best-match greedy assignment, no stage entity used twice.

**Tiers**: `core` (must-have entities), `core_supporting`, `all` (includes `optional`). Recall, precision, and F1 computed per tier.

**Temporal accuracy**: For segments with `aligns_with_slice_evidence_id` + `expected_fact_temporal`, finds facts by evidence_id, checks `asserted_in_session` and `sequence_index_within_session` field-by-field.

**Catalog recall**: Scores the 4 deterministic-slice catalog entities separately from the full gold set.

**Negative check**: Verifies none of 8 forbidden strings (`"his"`, `"her"`, `"the players"`, etc.) appear as `display_name` in stage entities.

### Current thresholds in `run_slice.py` (line 33)

```python
GOLD_SCORE_THRESHOLDS = {
    "min_core_recall": 0.10,
    "min_temporal_accuracy": 0.75,
    "min_catalog_recall": 0.50,
}
```

### Observed deterministic-slice metrics

| Metric | Value | Current threshold |
|--------|-------|-------------------|
| `core_recall` | 0.30 | 0.10 |
| `temporal_field_accuracy` | 1.00 | 0.75 |
| `catalog_recall` | 1.00 | 0.50 |
| `negative_violations` | 0 | 0 |

---

## 2. Work item status

### Item 1: Tighten Gate G thresholds

**Status:** Completed on 2026-04-02.

**Implemented:**

- `min_temporal_accuracy`: raised from `0.75` to `1.0`.
- `min_catalog_recall`: raised from `0.50` to `1.0`.
- `min_core_recall`: kept at `0.10` for deterministic slice.

**Where:** `GOLD_SCORE_THRESHOLDS` in `evals/llm_ingestion_slice/run_slice.py`; expectations aligned in `tests/evals/test_score_gold.py`.

**Verification:** `uv run pytest tests/ -q` and `uv run python evals/llm_ingestion_slice/run_slice.py` both pass.

### Item 2: Add eval mode flag to scorer output

**Status:** Completed on 2026-04-02.

**Implemented:** Added explicit mode labeling so scorer outputs are unambiguous across deterministic slice vs full ingest.

```json
{
  "eval_mode": "deterministic_slice",
  ...
}
```

**Where:**

- Added `eval_mode` parameter to `score_gold.score()` and `score_gold.main()` in `evals/llm_ingestion_slice/score_gold.py`.
- Added CLI flag `--eval-mode` (default `full_ingest`).
- Gate G in `evals/llm_ingestion_slice/run_slice.py` now passes `eval_mode="deterministic_slice"`.
- `gold_score.json` now includes:

```json
{
  "eval_mode": "deterministic_slice",
  ...
}
```

**Why this matters:** Core recall of 0.3 is expected for deterministic slice but would be a failure for full ingest. Mode field enables policy by evaluation context.

### Item 3: Commit the working tree

**Status:** Still open (not executed in this pass).

**What:** Large dirty tree needs commit packaging across logical boundaries. This remains the largest immediate task.

**Logical commit boundaries:**

1. **Corpus frontmatter v0.2 rewrite** (~130 modified corpus files under `corpus/eldyrwild-markdown/`)
   - All corpus markdown files got `temporal_scope`, `origin_session`, `last_updated_session` fields
   - `schemas/v0.1/document_metadata.schema.json` upgraded to v0.2
   - `src/ingestion/frontmatter.py` + `src/ingestion/frontmatter_inference.py` updated
   - `evals/llm_ingestion_slice/slice_manifest.json` SHA256 entries updated
   - Tests: `tests/ingestion/test_frontmatter.py`, `tests/test_chunker.py`

2. **Entity extraction hardening** (entity_extractor, store, entity_tags, filters)
   - `src/ingestion/entity_extractor.py` — prompt narrowing, hygiene filters
   - `src/store.py` — alias cap, tag merge
   - `src/contracts/entity_tags.py` (new)
   - `schemas/v0.1/entity.schema.json` + example
   - `src/agent/context_formatter.py`
   - Tests: `tests/ingestion/test_entity_extractor_filters.py`, `tests/test_store.py`, `tests/test_context_formatter.py`, `tests/test_fact_extractor.py`

3. **Temporal gates** (tick, consistency, quality warning)
   - `src/contracts/temporal_tick_gate.py` (new)
   - `src/cli.py` — 3 new ingest gates
   - `src/ingestion/event_sourced_slice.py` — temporal metadata on seeds, entity seeding fix
   - `src/ingestion/chunker.py` — temporal metadata propagation
   - `schemas/v0.1/evidence_unit.schema.json`
   - Tests: `tests/contracts/test_temporal_tick_gate.py` (new), `tests/test_cli.py`

4. **Gold scoring** (score_gold, Gate G, gold JSON)
   - `evals/llm_ingestion_slice/score_gold.py` (new)
   - `evals/llm_ingestion_slice/run_slice.py` — Gate G integration
   - `evals/llm_ingestion_slice/gold/manual_entity_extraction_gold.json` (new)
   - Tests: `tests/evals/test_score_gold.py` (new), `tests/evals/test_manual_entity_extraction_gold.py` (new), `tests/evals/test_llm_ingestion_slice.py`

5. **Docs and handoffs** (optional / separate)
   - `Docs/Design/SCHEMA-document-temporal-metadata-v0.2.md` (new)
   - `report/REPORT-current-status.md`
   - Handoff files

**Files to NOT commit:**
- `.cursor/agents/*.md` — local agent briefs, not project code
- `evals/mirathorn_vertical_slice/output/council_room_*.json` — investigation artifacts
- `evals/mirathorn_vertical_slice/output/q_wolf_status_trace*.json` — investigation artifacts
- `evals/mirathorn_vertical_slice/output/post_play_delta_investigation.md` — investigation notes

### Item 4: Regression tests for two fixed failure modes

**Status:** Completed on 2026-04-02.

**What:** During gold scoring implementation, two bugs in `event_sourced_slice.py` were found and fixed:

1. **Planning facts lost `asserted_in_session`**: Facts derived from campaign evidence with `inferred_session=6` were getting `asserted_in_session=null` because fact-building in the slice didn't copy session from evidence.
2. **State-change entity subjects missing from `stage_entities`**: Entities referenced as fact subjects but not appearing in evidence text via substring matching were excluded from the entity list.

Both are fixed and now covered by targeted regression tests:

- `test_campaign_planning_facts_copy_asserted_session_from_evidence()`
- `test_all_fact_subject_entities_exist_in_stage_entities()`

**Where:** Added to `tests/evals/test_llm_ingestion_slice.py`.

---

## 2.1 Verification evidence from this pass

```bash
uv run pytest tests/ -q
# 168 passed, 2 skipped

uv run python evals/llm_ingestion_slice/run_slice.py
# exit 0
```

Gate G metrics after threshold hardening:

- `core_recall=0.3` (threshold `0.1`)
- `temporal_field_accuracy=1.0` (threshold `1.0`)
- `catalog_recall=1.0` (threshold `1.0`)
- `negative_violations=0`

---

## 3. Key file index

| Area | Path |
|------|------|
| Gold scorer | `evals/llm_ingestion_slice/score_gold.py` |
| Gold contract | `evals/llm_ingestion_slice/gold/manual_entity_extraction_gold.json` |
| Gate G in harness | `evals/llm_ingestion_slice/run_slice.py` → `_gate_g_gold_scoring()`, `GOLD_SCORE_THRESHOLDS` |
| Scorer tests | `tests/evals/test_score_gold.py` |
| Gold structure tests | `tests/evals/test_manual_entity_extraction_gold.py` |
| Harness tests | `tests/evals/test_llm_ingestion_slice.py` |
| Temporal contracts | `src/contracts/temporal_tick_gate.py` |
| Entity tags contract | `src/contracts/entity_tags.py` |
| CLI ingest gates | `src/cli.py` → `_build_ingest_gate_report()` |
| Deterministic slice | `src/ingestion/event_sourced_slice.py` |
| Entity extractor | `src/ingestion/entity_extractor.py` |
| Fact temporal copy | `src/ingestion/fact_extractor.py` → `_build_fact_record()` |
| Frontmatter parser | `src/ingestion/frontmatter.py` |
| Document metadata schema | `schemas/v0.1/document_metadata.schema.json` (v0.2) |
| Entity schema | `schemas/v0.1/entity.schema.json` |
| Evidence schema | `schemas/v0.1/evidence_unit.schema.json` |
| Status report | `report/REPORT-current-status.md` |
