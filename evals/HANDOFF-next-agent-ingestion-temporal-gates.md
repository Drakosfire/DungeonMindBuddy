# Handoff: Ingestion Quality, Manual Gold, Entity Tags, Temporal Gates

**Date:** 2026-04-02 (updated, temporal split)  
**Repo:** `DungeonMindBuddy` (`/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy`)  
**Branch:** `main` (very dirty working tree: large corpus + ingestion pipeline edits are intentionally uncommitted)  
**Audience:** Next agent continuing ingestion quality, benchmarks, or narrative provenance work.

---

## 0. Verification (run first)

```bash
cd /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy
uv run pytest tests/ -q                                    # expect 159 passed, 2 skipped
uv run python evals/llm_ingestion_slice/run_slice.py        # expect exit 0 (all gates pass)
```

If either fails, stop and investigate before changing code. The green baseline is the contract.

**Last re-verified during handoff review:** both commands returned exit `0`; pytest reported `159 passed, 2 skipped`.

---

## 1. What shipped (recent commits on `main`)

### 1.1 Entity extraction prompt size (major)

**Problem:** Every extraction call sent the full store's known entities (~130k tokens) versus ~150 chars of actual evidence text.

**Fix in** `src/ingestion/entity_extractor.py`:

- **`_relevant_known_entities()`** (lines 412-432) — substring-matches `display_name.lower()` against evidence text; skips names shorter than 3 chars; caps aliases per entity to `_MAX_ALIASES_IN_PROMPT = 3` (shortest first).
- **`_PROMPT_ID`** (line 19) = `"phase_b_pass1_entity_extraction_v2_entity_tags"` — bumped so stale caches from the old (bloated) prompt are not reused.

### 1.2 Merge alias snowball cap

**`src/store.py`** line 30: `_MAX_ALIASES_PER_ENTITY = 20`. On entity merge (`add_entities`, lines 202-236), aliases from both sides are unioned, sorted by length ascending, then truncated to 20.

### 1.3 Entity name hygiene filters

**`src/ingestion/entity_extractor.py`** — `_is_plausible_entity_name()` (lines 519-574):

- Rejects pronouns (he/she/it/they/etc.)
- Rejects display names > 60 chars (`_MAX_ENTITY_NAME_LENGTH`)
- Rejects names not found as substring in source text
- Rejects single-token low-signal words
- Extra rules for `entity_type == "other"` (short tokens, connector-only, no uppercase)

**Tests:** `tests/ingestion/test_entity_extractor_filters.py` — parametrized pronoun rejection, length boundary (60 pass / 61 fail), relevant-known-entities filtering with alias cap, case-insensitive matching, short display name skip.

### 1.4 `entity_tags` on entities

**Purpose:** Keep `entity_type` enum small (npc/location/faction/item/other); use tags for facets (deity, patron, etc.).

**Data flow across files:**

| Step | File (line) | What happens |
|------|-------------|--------------|
| Schema | `schemas/v0.1/entity.schema.json` (lines 79-81) | Optional `entity_tags`: string array, unique items |
| Normalize | `src/contracts/entity_tags.py` (lines 10-28) | `normalize_entity_tags(raw, *, max_tags=12)`: lowercase, strip non-`[a-z0-9_]`, dedupe, cap |
| Extract | `src/ingestion/entity_extractor.py` | `ExtractedEntity.entity_tags: list[str] = []` (Pydantic model, line ~190); prompt requests `entity_tags` for `other` type |
| Merge | `src/store.py` (lines 202-236) | Union of tags → `normalize_entity_tags(..., max_tags=20)` (`_MAX_ENTITY_TAGS_MERGED = 20`) |
| Deterministic slice | `src/ingestion/event_sourced_slice.py` (line 323) | Built entities get `"entity_tags": []` (no tags in slice catalog) |
| Context display | `src/agent/context_formatter.py` (lines 79-84) | `== Entity: Name (type) [tag1, tag2] ==` header when tags present |
| Example | `schemas/v0.1/examples/entity.example.json` | Includes `entity_tags` |

### 1.5 Manual extraction + temporal gold

**File:** `evals/llm_ingestion_slice/gold/manual_entity_extraction_gold.json` (schema_version `1.1`)

**Structure:**
- `corpus_gaps[]` — documents known mismatches (Longmont General Notes session/source_class vs deterministic slice).
- `temporal_provenance` — documents the inheritance chain:
  - `fact_extractor_source`: points at `_build_fact_record` (lines 341-388 of `fact_extractor.py`).
  - `inheritance.asserted_in_session`: `evidence.document_session` → fallback `evidence.inferred_session` → coerce to `int` or `None`.
  - `inheritance.sequence_index_within_session`: `evidence.source_order_index` → coerce to `int` or `None`.
  - `deterministic_slice_evidence_gold[]` — six `evu_*` entries with exact expected temporal values for derived facts.
- `sources[].segments[]` — per-segment expected entities (with `entity_tags` where applicable), `aligns_with_slice_evidence_id`, `expected_evidence_temporal`, `expected_fact_temporal`.

**Tests:** `tests/evals/test_manual_entity_extraction_gold.py` — validates structure, manifest path match, temporal table consistency with aligned segments.

### 1.6 Narrative temporal tick gates

**The rule:** Any fact whose `evidence_ids` reference campaign-layer evidence (`canon_layer == "campaign"`) must have at least one of `asserted_in_session` or `sequence_index_within_session` non-null. World-only facts are exempt.

**Implementation across three surfaces:**

| Surface | File | Function / gate name | Lines |
|---------|------|---------------------|-------|
| Contract | `src/contracts/temporal_tick_gate.py` | `campaign_temporal_tick_violations(evidence_units, facts) -> list[str]` | 8-52 (full file, 53 lines) |
| CLI ingest | `src/cli.py` | gate `stage_campaign_narrative_temporal_tick` inside `_build_ingest_gate_report()` | 150-158 |
| Eval harness | `evals/llm_ingestion_slice/run_slice.py` | `_gate_temporal_narrative_tick()` → `Gate T - narrative temporal tick` | 327-338 |

**Gate ordering in eval harness** (`main()` in `run_slice.py`):
1. Gate A (source layer integrity)
2. Gate V (extraction viability)
3. Gate T (temporal tick) — **new**
4. Gate TC (campaign temporal consistency) — **new**
5. Gate TW (sequence-only temporal warning, non-blocking) — **new**
6. **Only if A, V, T, and TC all pass:** Gate B, Gate C, Gate D

**Gate ordering in CLI ingest** (`_build_ingest_gate_report` in `src/cli.py`):
1. `stage_chunk_build_non_empty`
2. `stage_chunk_layer_integrity` (world has no campaign_id, campaign has campaign_id)
3. `stage_chunk_schema` (JSON schema validation)
4. `stage_entity_extraction_non_empty`
5. `stage_entity_schema`
6. `stage_fact_extraction_non_empty`
7. `stage_fact_schema`
8. `stage_campaign_narrative_temporal_tick`
9. `stage_campaign_temporal_consistency`
10. `stage_campaign_temporal_quality_warning` (non-blocking by design: `pass=True`, emits warnings/metrics)

All gates must pass for `overall_pass = True`; if any fail, the CLI aborts before updating the store.

**Test coverage for temporal tick:**

| Test file | Key tests |
|-----------|-----------|
| `tests/contracts/test_temporal_tick_gate.py` | `test_world_sourced_fact_may_have_null_tick`, `test_campaign_fact_requires_session_or_sequence`, `test_campaign_fact_passes_with_session_only`, `test_campaign_fact_passes_with_sequence_only`, `test_missing_evidence_id_surfaces_error` |
| `tests/test_cli.py` | Temporal fail/pass integration through `_build_ingest_gate_report` |
| `tests/evals/test_llm_ingestion_slice.py` | `test_llm_ingestion_slice_main_passes_and_writes_artifacts` (Gate T/TC/TW pass on green run); `test_main_fails_fast_when_viability_fails` (verifies B/C/D are skipped when blocking pre-checks fail) |

### 1.7 Fact temporal inheritance (how ticks get onto facts)

**`src/ingestion/fact_extractor.py`** — `_build_fact_record()` (lines 341-388):

```
356:    inferred_session = evidence_unit.get("document_session")
357:    if inferred_session is None:
358:        inferred_session = evidence_unit.get("inferred_session")
359:    try:
360:        asserted_in_session = int(inferred_session) if inferred_session is not None else None
363:    source_order = evidence_unit.get("source_order_index")
365:        sequence_index = int(source_order) if source_order is not None else None
```

The LLM does **not** produce temporal fields. They are copied from the evidence unit at fact-record construction time. If the evidence unit lacks `document_session`, `inferred_session`, and `source_order_index`, the fact will have both ticks null — and the temporal tick gate will reject it for campaign-layer evidence.

### 1.8 Gap 1 investigation results (campaign metadata coverage)

Gap 1 was investigated empirically on 2026-04-01.

**Findings:**
- Campaign files scanned: `70`
- Campaign files with `session: null`: `30`
- Chunking failures: `0`
- Evidence units missing `source_order_index`: `0`
- Campaign facts missing both temporal ticks in ingest artifacts: `0`
- Runs with temporal tick gate failures in sampled artifacts: `0`

**Conclusion:** Gate T is **not** currently a broad ingest blocker for normal CLI/batch paths, because chunking consistently populates `source_order_index`. The remaining issue is temporal **quality** (many facts anchored by sequence only, without explicit session).

### 1.9 New temporal clash handling (implemented 2026-04-01)

To handle temporal edge cases where a fact references campaign evidence with conflicting session provenance:

- **New contract function** in `src/contracts/temporal_tick_gate.py`:
  - `campaign_temporal_consistency_violations(evidence_units, facts) -> list[str]`
  - Fails when one fact references campaign evidence from multiple sessions.
  - Fails when `fact.asserted_in_session` conflicts with evidence-derived sessions.

- **New blocking CLI gate** in `src/cli.py`:
  - `stage_campaign_temporal_consistency`
  - Included in `overall_pass`; ingest aborts before store write on failure.

- **New blocking eval gate** in `evals/llm_ingestion_slice/run_slice.py`:
  - `Gate TC - campaign temporal consistency`
  - Must pass alongside A/V/T before B/C/D run.

- **New non-blocking warning gate/metric**:
  - CLI: `stage_campaign_temporal_quality_warning`
  - Eval: `Gate TW - sequence-only temporal warning`
  - Reports `campaign_fact_count`, `asserted_session_count`, `sequence_only_count`, `missing_tick_count`, `missing_evidence_links`, `sequence_only_ratio`.
  - Always pass; used for quality SLO visibility without stopping ingest.

- **Tests added/updated**:
  - `tests/contracts/test_temporal_tick_gate.py`: consistency violations + quality summary coverage.
  - `tests/test_cli.py`: gate report includes consistency fail path and warning metrics.
  - `tests/evals/test_llm_ingestion_slice.py`: asserts Gate TC/Gate TW presence and pass on green run.

**Verification run (2026-04-01):**
```bash
uv run pytest tests/contracts/test_temporal_tick_gate.py tests/test_cli.py tests/evals/test_llm_ingestion_slice.py -q
# 31 passed
```

### 1.10 Document temporal metadata schema v0.2 + corpus-wide frontmatter rewrite (implemented 2026-04-02)

**Goal:** replace ambiguous `session: null` meaning with explicit temporal semantics on all docs.

**Schema and contract changes:**
- `schemas/v0.1/document_metadata.schema.json` upgraded from v0.1 to **v0.2**.
- New required field: `temporal_scope` with enum:
  - `session_specific`
  - `campaign_stateful`
  - `evergreen`
- New optional lineage fields:
  - `origin_session`
  - `last_updated_session`
- Contract enforcement:
  - `session_specific` requires `session`.
  - `campaign_stateful`/`evergreen` require `session: null`.
  - `canon_layer=world` requires `temporal_scope=evergreen`, all session lineage fields null.

**Parser/inference updates:**
- `src/ingestion/frontmatter.py`
  - `DocumentMetadata` now includes `temporal_scope`, `origin_session`, `last_updated_session`.
  - `to_dict`, parse, and render all include new fields.
- `src/ingestion/frontmatter_inference.py`
  - heuristic inference now emits new temporal fields.
  - OpenAI inference prompt/schema updated to request new temporal fields.

**Corpus rewrite:**
- All files under `corpus/eldyrwild-markdown/` were rewritten to the new frontmatter shape.
- Sweep result:
  - `SCANNED 130`
  - `CHANGED 130`
- Post-rewrite validation:
  - all `130` corpus markdown files parse and validate against `document_metadata.schema.json` with **0 failures**.

**Related test and eval updates:**
- Updated tests with embedded frontmatter blocks to include v0.2 temporal fields:
  - `tests/ingestion/test_frontmatter.py`
  - `tests/test_chunker.py`
  - `tests/test_cli.py`
- Updated `evals/llm_ingestion_slice/slice_manifest.json` source SHA256 entries because corpus frontmatter rewrites changed source file fingerprints.

**Verification (2026-04-02):**
```bash
uv run pytest tests/ -q
# 159 passed, 2 skipped
```

### 1.11 Structural vs narrative temporal split in quality metrics (implemented 2026-04-02)

**Problem addressed:** `sequence_index_within_session` was being interpreted as narrative temporal anchoring even for sessionless docs (`campaign_stateful` / `evergreen`), inflating sequence-only warnings with structural ordering.

**What changed:**
- `campaign_temporal_quality_summary()` in `src/contracts/temporal_tick_gate.py` now separates:
  - **Session-specific campaign facts** (narrative temporal quality bucket)
  - **Sessionless campaign facts** (structural-only provenance bucket)
- `sequence_only_ratio` now uses denominator:
  - `session_specific_fact_count` (not all campaign facts)
- New metrics for explicit split:
  - `session_specific_fact_count`
  - `sessionless_fact_count`
  - `sessionless_structural_only_count`
  - `sessionless_missing_tick_count`
  - `sessionless_asserted_session_count`
- Warning semantics changed:
  - sequence-only warning applies to **session-specific** facts only.

**How session-specific vs sessionless is determined:**
1. Prefer evidence `document_temporal_scope` when present.
2. Fallback to `source_class` heuristic:
   - session-specific: `observed_session_recap`, `planning_document`
   - sessionless: `seed_reference`, `ledger_or_dossier`, `other`

**Evidence metadata propagation updates:**
- `src/ingestion/chunker.py` now stamps evidence units with:
  - `document_temporal_scope`
  - `document_origin_session`
  - `document_last_updated_session`
- `schemas/v0.1/evidence_unit.schema.json` now includes those fields (optional).
- `src/ingestion/event_sourced_slice.py` seeds now populate these fields for deterministic eval payloads.

**Why this matters:**
- Structural document order is preserved.
- Narrative temporal quality signal is no longer polluted by sessionless references.
- Gate TW becomes a more faithful indicator of true session-anchoring debt.

**Verification (2026-04-02):**
```bash
uv run pytest tests/ -q
# 159 passed, 2 skipped
```

---

## 2. Nano experiment snapshot (for context, not action)

Store `dungeonbuddy_store_nano_full/` is gitignored. Key numbers:

| Metric | Value |
|--------|-------|
| Corpus files ingested | 17 / 130 (13%) |
| Entities | 1,835 (43% typed as "other") |
| Facts | 5,532 |
| Temporal fill (`asserted_in_session` non-null) | 6.4% of facts |
| Entity name hygiene issues found | 31 names > 60 chars, pronouns as entities |

The hygiene filters (1.3) now block the pronoun/long-name problems. The 43% "other" rate is a model-quality issue (nano under-classifies).

---

## 3. Intentional gaps / next-agent work

### Gap 1 (reframed): Temporal quality hardening under v0.2 metadata model

Gap 1 investigation is complete. Gate T blocking risk was lower than expected for normal ingest paths because `source_order_index` is consistently present.

**What remains:**
1. Reduce sequence-only temporal anchoring for **session-specific** docs (`session_specific_fact_count` bucket).
2. Track both:
   - `sequence_only_ratio` (session-specific only)
   - `sessionless_structural_only_count` (separate structural provenance context)
3. Set policy thresholds and optionally promote session-specific threshold breaches to blocking later.

### Gap 2: No automated recall/precision scoring against manual gold

The file `evals/llm_ingestion_slice/gold/manual_entity_extraction_gold.json` has per-segment expected entities, but no runner joins `stage_entities.json` / `stage_facts.json` to it for automated scoring.

**To build this:** Write a script that:
1. Loads gold segments and their `expected_entities` / `expected_fact_temporal`
2. Loads `stage_entities.json` and `stage_facts.json` from an ingest run
3. Computes recall (expected entities found) and precision (entities found that are in gold)
4. For temporal: checks that campaign facts carry the expected `asserted_in_session` and `sequence_index_within_session`

### Gap 3: Cache invalidation

Entity extractor caches are keyed partly by `_PROMPT_ID`. The current ID is `phase_b_pass1_entity_extraction_v2_entity_tags`. If you change the prompt, bump `_PROMPT_ID` or clear `.cache/` under the store directory. Relying on the new ID usually suffices, but a full cache clear is safer for A/B comparisons.

### Gap 4: `observed_at` / validity fields not gate-enforced

The fact schema has `observed_at`, `valid_from`, `valid_until` fields. The temporal tick gate only checks `asserted_in_session` and `sequence_index_within_session`. The other fields are aspirational and not populated by any current code path.

### Gap 5: MODEL_POLICY.json nano vs. quality

`MODEL_POLICY.json` at repo root (`/home/drakosfire/Projects/DungeonOverMind/MODEL_POLICY.json`) routes `structured_generation` → `cheapest` → `gpt-5.4-nano`. The 43% "other" entity-type rate and other quality issues in the nano experiment have not been re-benchmarked against a higher-tier model. Next step would be an A/B comparison on 3 representative files.

---

## 4. Key paths (quick index with line numbers)

| Area | Path | Key location |
|------|------|--------------|
| Temporal contracts | `src/contracts/temporal_tick_gate.py` | `campaign_temporal_tick_violations()`, `campaign_temporal_consistency_violations()`, `campaign_temporal_quality_summary()` |
| Document metadata schema | `schemas/v0.1/document_metadata.schema.json` | v0.2 fields: `temporal_scope`, `origin_session`, `last_updated_session` |
| Evidence schema | `schemas/v0.1/evidence_unit.schema.json` | Optional evidence-level metadata: `document_temporal_scope`, `document_origin_session`, `document_last_updated_session` |
| Frontmatter parser | `src/ingestion/frontmatter.py` | `DocumentMetadata` + parse/render support for v0.2 temporal fields |
| Frontmatter inference | `src/ingestion/frontmatter_inference.py` | heuristic/LLM inference outputs v0.2 temporal fields |
| Chunker metadata propagation | `src/ingestion/chunker.py` | frontmatter temporal metadata copied onto evidence units |
| Temporal gate tests | `tests/contracts/test_temporal_tick_gate.py` | Tick + consistency + quality summary coverage |
| CLI ingest gates | `src/cli.py` | `_build_ingest_gate_report()` with `stage_campaign_narrative_temporal_tick`, `stage_campaign_temporal_consistency`, `stage_campaign_temporal_quality_warning` |
| Eval harness gates | `evals/llm_ingestion_slice/run_slice.py` | `Gate T`, `Gate TC`, `Gate TW`; B/C/D run only after A/V/T/TC pass |
| Fact temporal copy | `src/ingestion/fact_extractor.py` | `_build_fact_record()` lines 341-388; temporal inheritance at 356-367 |
| Entity tags normalize | `src/contracts/entity_tags.py` | `normalize_entity_tags()` lines 10-28 (full file: 29 lines) |
| Entity name filters | `src/ingestion/entity_extractor.py` | `_is_plausible_entity_name()` lines 519-574; `_relevant_known_entities()` lines 412-432 |
| Entity filter tests | `tests/ingestion/test_entity_extractor_filters.py` | Pronoun, length, relevant-known-entities tests |
| Manual gold | `evals/llm_ingestion_slice/gold/manual_entity_extraction_gold.json` | schema_version 1.1; `temporal_provenance` section; `deterministic_slice_evidence_gold` array |
| Gold structure tests | `tests/evals/test_manual_entity_extraction_gold.py` | Structure, manifest path match, temporal table consistency |
| Deterministic slice seeds | `src/ingestion/event_sourced_slice.py` | `_EVIDENCE_SEEDS` lines 48-139 (6 seeds); `_build_entities` line 323 → `entity_tags: []` |
| Entity schema | `schemas/v0.1/entity.schema.json` | `entity_tags` at lines 79-81; `entity_type` enum at lines 57-65 |
| Context formatter | `src/agent/context_formatter.py` | Entity header with tags at lines 79-84 |
| Store merge logic | `src/store.py` | Alias cap `_MAX_ALIASES_PER_ENTITY = 20` line 30; tag merge `_MAX_ENTITY_TAGS_MERGED = 20` line 31; merge in `add_entities` lines 202-236 |
| Status report | `report/REPORT-current-status.md` | Current counts, nano experiment notes |
| Batch ingest tool | `tools/batch_ingest_corpus.py` | Script for running corpus-wide ingest |
| Corpus frontmatter tool | `tools/corpus_split_and_frontmatter.py` | Session splitting + frontmatter annotation |
| Temporal schema design doc | `Docs/Design/SCHEMA-document-temporal-metadata-v0.2.md` | Forward-only temporal metadata contract and examples |
| Design doc | `Docs/Design/DESIGN-ingestion-pipeline-architecture-and-refactor-assessment.md` | Architecture overview and refactor assessment |

---

## 5. Git state

Current branch relation:
```
main...origin/main
```

Recent commits (newest first):
```
dce456d chore(cursor): remove BMAD skills from repo
1e37324 chore: ignore nano batch store; track ingestion pipeline design doc
5a1962b chore(tools): add corpus batch ingest and frontmatter helpers
2abb60b feat(cli): extend ingestion CLI and expand test coverage
```

**Untracked highlights (optional to commit):**
- `.cursor/agents/*.md` — local agent briefs
- `evals/mirathorn_vertical_slice/output/council_room_*.json` — council-room investigation artifacts
- `evals/mirathorn_vertical_slice/output/q_wolf_status_trace*.json` — wolf trace artifacts
- `evals/mirathorn_vertical_slice/output/post_play_delta_investigation.md` — investigation notes
- `evals/llm_ingestion_slice/gold/manual_entity_extraction_gold.json` — **manual gold (should be committed)**
- `evals/HANDOFF-next-agent-ingestion-temporal-gates.md` — this file

**Working tree magnitude (captured in this handoff update):**
- `modified=153`, `untracked=20`
- Modified set includes:
  - corpus frontmatter/session docs (`corpus/eldyrwild-markdown/**`)
  - ingestion contracts and pipeline (`src/contracts/**`, `src/ingestion/**`, `src/cli.py`)
  - schemas/tests/evals (`schemas/**`, `tests/**`, `evals/**`)

**Operator note:** do not "clean up" or reset this tree by default. Treat it as an intentional in-progress state tied to the temporal metadata + gate quality work described in Sections 1, 3, 7, and 8.

**Gitignored:** `dungeonbuddy_store_nano_full/` (33MB experiment store with `.cache/`)

---

## 6. Design stance

- **Narrow `entity_type` + `entity_tags`** avoids enum churn while keeping queryable facets. The `entity_type` enum is locked to 5 values: npc, location, faction, item, other. Tags handle everything else (deity, patron, etc.).
- **Temporal tick gate** encodes "campaign narrative must be anchored on the session/sequence timeline," not just schema-valid JSON.
- **Temporal consistency gate** prevents cross-session evidence clashes from silently passing as valid facts.
- **Temporal quality warning metric** intentionally does not block ingest; it exposes sequence-only anchoring debt so quality can be improved incrementally.
- **Fact temporal inheritance is from evidence, not LLM** — the LLM extracts semantic content; temporal positioning is derived from evidence metadata. Under v0.2, metadata quality depends on accurate `temporal_scope` + lineage fields and session values where applicable.
- **Manual gold** is the human contract for entities + temporal targets; CI only validates structure and internal consistency today. Automated recall/precision scoring is the primary gap.
- **Gate ordering is intentional** — A (source integrity), V (extraction viability), T (temporal tick), and TC (temporal consistency) are pre-checks. TW is informational only. B/C/D (projection gates) are expensive and only run if blocking pre-checks pass.

---

## 7. Clarifications captured in this thread

### 7.1 "Does this resolve Gap 1?"

**Status:** Partially resolved, with blocking risk removed and signal quality improved.

- **Resolved:** campaign facts with conflicting evidence sessions are now blocked by TC.
- **Resolved:** sequence-only warning signal now targets `session_specific` facts only.
- **Not yet resolved:** reducing actual sequence-only dependence in `session_specific` docs remains an ongoing quality objective.
- **Open policy call:** decide threshold(s) for when high `sequence_only_ratio` should become blocking for `session_specific` facts.

Practical read: Gap 1 is no longer a hidden ingest-failure risk; it is now a visible and bounded quality-hardening track.

### 7.2 What causes `sequence_only_ratio`

`sequence_only_ratio` rises when facts have:
- `sequence_index_within_session != null`
- `asserted_in_session == null`
- and they are classified as `session_specific`.

Main contributors:
1. Evidence lacks/loses session value (`document_session` and `inferred_session` absent or non-coercible).
2. Fact inherits structural index (`source_order_index`) from chunker, so it still has a sequence tick.
3. Dedup merges can preserve evidence links with mixed quality, where sequence survives but explicit session does not.

After the split, intentionally sessionless docs (`campaign_stateful`, `evergreen`) are tracked separately as structural-only and do **not** inflate `sequence_only_ratio`.

### 7.3 Why keep sequence for sessionless docs

Even for sessionless docs, structural sequencing remains useful:
- Stable provenance ordering inside a source document.
- Deterministic replay/debugging and diffing across ingest runs.
- Tie-break signal for retrieval/context packing when stronger temporal anchors are absent.

But it should be treated as **document structural order**, not narrative timeline. The current split codifies this distinction in quality metrics.

---

## 8. Immediate next actions (if continuing)

1. Add a small report script that prints TW split metrics over a selected corpus/sample ingest.
2. Establish target bands for:
   - `sequence_only_ratio` (`session_specific`)
   - `sessionless_structural_only_count` (monitoring only)
3. Prototype one stricter mode:
   - warning-only (current)
   - fail if `sequence_only_ratio` exceeds threshold for `session_specific` facts.
4. Implement automated gold scoring (Gap 2) so temporal/provenance quality changes can be measured alongside entity recall/precision.
