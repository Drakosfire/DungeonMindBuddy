# DungeonMindBuddy Status Report

Date: 2026-03-29

## 1) Current Status

Mirathorn event-sourced vertical slice is implemented and passing end-to-end with hard gates enforced. The GM workflow progression is proven through deterministic projection checkpoints (`instantiation`, `zero_tick`, `live_state`).

A full-corpus nano-model ingest experiment (`dungeonbuddy_store_nano_full/`) completed 17/130 corpus files. Extraction quality issues surfaced (see §6).

## 2) Completed Scope

### Phase A-C Foundations (complete)

- Docx/markdown ingestion, chunking, entity extraction, and fact extraction are implemented and tested.
- Canon-layer contracts and reducer behavior remain stable.
- Frontmatter schema, session split for play docs, and corpus-wide validation (130 files) are in place.

### Phase D Synthesis + CLI (complete)

- `src/agent/synthesis.py`
- `src/agent/context_formatter.py`
- `src/cli.py`
- `src/__main__.py`
- Phase D artifacts committed: `phase_d_context.txt`, `phase_d_answer.txt`, `phase_d_summary.json`

Runtime behavior includes async synthesis/model call paths, structured JSONL run logs, and fail-fast handling in CLI/eval flows for critical failures.

### Event-Sourced Slice + Gate Pack (complete)

- `src/ingestion/event_sourced_slice.py` builds deterministic artifacts:
  - `evidence_units`, `entities`, `events`, `facts`, `conflicts`, `canon_decisions`
  - projections at `instantiation`/`zero_tick`/`live_state`
- `evals/llm_ingestion_slice/run_slice.py` enforces hard gates A/V/B/C/D.
- Gold pack and manifest are locked under `evals/llm_ingestion_slice/`.

### Cost Knob (wired, under evaluation)

- `MODEL_POLICY.json` routes `structured_generation` → `cheapest` (gpt-5.4-nano).
- `dungeonbuddy_store_nano_full/` is the experiment store (gitignored, 33MB).

## 3) Extraction Viability Hardening (Gate V)

Gate V is implemented as a deterministic pre-projection viability check.

- Metrics: `entity_density`, `duplicate_fact_ratio`, `conflict_volume_band`
- Threshold config: `evals/llm_ingestion_slice/viability_thresholds.json`
- Fail-fast contract: non-viable extraction (including zero entities or zero facts) fails the run before event projection.

## 4) Nano Experiment Snapshot

Store: `dungeonbuddy_store_nano_full/` (gitignored)

| Metric | Value |
|---|---|
| Corpus files ingested | 17 / 130 (13%) |
| Entities | 1,835 |
| Facts | 5,532 |
| Evidence units | ~966 (23,691 lines) |
| Conflicts (open) | ~801 |
| Canon decisions | 0 |
| Ingest runs (started/completed) | 18 / 17 |

### Known Quality Issues

- **Entity type distribution**: 43% classified as "other" (788/1,835). Suggests nano model under-classifies.
- **Pronoun entities**: Entities like "his", "her" were created as NPCs (now blocked by pronoun filter).
- **Sentence-fragment entities**: 31 entities with names >60 chars (now blocked by length filter).
- **Temporal fill**: `asserted_in_session` non-null on 6.4% of facts; `observed_at` is 0% (expected — only 1 campaign doc ingested).
- **Layer/canon_status**: Facts do not carry `layer` or `canon_status` fields; these are derived at projection time from evidence unit provenance. This is architecturally correct but not obvious from fact inspection.

## 5) Verification Snapshot (Latest)

Latest full verification run:

- `uv run ruff check .` → PASS
- `uv run pytest tests/ --maxfail=1` → PASS (`131 passed, 2 skipped`)

Current gate outcomes from `evals/llm_ingestion_slice/output/current/report.md`:

- OVERALL: PASS
- Gate A: PASS
- Gate V: PASS (`entity_density=0.3333`, `duplicate_fact_ratio=0.0`, `conflict_volume_band=1`)
- Gate B: PASS
- Gate C: PASS
- Gate D: PASS (`instantiation_to_zero_tick=2`, `zero_tick_to_live_state=2`)

Phase D synthesis gates (from `phase_d_summary.json`):

- D1: PASS (evidence=1115, entities=798, facts=5470)
- D2: PASS (mentions_mirathorn=True, attributes_hit=5)
- D3: PASS (entity_header, provenance, conflicts present)
- D4: PASS (sequence_ok, no missing files/keys)

## 6) Git/Execution State

- Entity extraction filter hardened: pronoun rejection + max-length (60 char) filter added.
- Runtime artifacts under `evals/llm_ingestion_slice/output/current/` are regenerated during verification and remain untracked by design.
- `dungeonbuddy_store_nano_full/` is gitignored.
- Uncommitted eval artifacts: `council_room_*.json`, `q_wolf_status_trace*.json`, `post_play_delta_investigation.md` in `evals/mirathorn_vertical_slice/output/`.

## 7) Recommended Next Focus

1. **Decide nano vs. mid-tier model**: Run A/B comparison on 3 files (nano vs fast_smart) to measure extraction precision/recall before ingesting remaining 113 files.
2. **Close nano experiment**: Script reporting entities/facts/conflicts, temporal fill rate, and entity-type quality metrics.
3. **Fix campaign summary misclassification**: `# _Campaign Summary_ Mirathorn Post-Cultist Battle_.md` ingested as `world/seed_reference` but contains campaign-layer content.
4. **Commit hygiene**: Decide on uncommitted eval artifacts (commit vs. gitignore).
5. **Expand temporal coverage**: Ingest Longmont Campaign files to populate `asserted_in_session` / `observed_at` and validate temporal end-to-end.
6. **Phase F / blind set**: Pick a held-out anchor for GM-review evaluation without pipeline changes mid-eval.
