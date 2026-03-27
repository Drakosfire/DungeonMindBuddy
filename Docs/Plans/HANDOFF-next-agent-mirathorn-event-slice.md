# Handoff: Mirathorn Event-Sourced Slice

## Update (2026-03-27)

### What Changed Since Prior Handoff

- Phase D (`ingest` + `ask`) is now implemented and empirically passing.
  - Gate run: `uv run python evals/mirathorn_vertical_slice/eval_synthesis.py`
  - Latest result: `OVERALL: PASS`
- Corpus markdown was generated from source docs and relocated to:
  - `corpus/eldyrwild-markdown/`
- Legacy corpus tree under `Docs/Eldyrwild and Campaign Context/` is now treated as source/binary-heavy location.
- Synthesis and extraction runtime now includes:
  - async model-call path for synthesis
  - async-capable OpenAI adapters for entity/fact extraction
  - structured JSONL run records (`<store>/logs/*.jsonl`)
  - verbose per-stage/per-unit logging
  - fail-fast/early-exit behavior in CLI/eval when critical stages fail
- Environment/model policy resolution now supports central workspace roots:
  - `.env.development` fallback to `/home/drakosfire/Projects/DungeonOverMind/.env.development`
  - `MODEL_POLICY.json` fallback to `/home/drakosfire/Projects/DungeonOverMind/MODEL_POLICY.json`

### Execution Verification Snapshot (2026-03-27)

- End-to-end verification executed in `DungeonMindBuddy` with no code edits required.
- Commands run:
  - `uv run ruff check .` -> pass
  - `uv run pytest tests/ --maxfail=1` -> `65 passed, 2 skipped`
  - `uv run python evals/llm_ingestion_slice/run_slice.py` -> completed successfully and regenerated eval artifacts
- Current gates from `evals/llm_ingestion_slice/output/current/report.md`:
  - `OVERALL: PASS`
  - `Gate A: PASS`
  - `Gate V: PASS` (`entity_density=0.3333`, `duplicate_fact_ratio=0.0`, `conflict_volume_band=1`)
  - `Gate B: PASS`
  - `Gate C: PASS`
  - `Gate D: PASS` (`instantiation_to_zero_tick=2`, `zero_tick_to_live_state=2`)
- Runtime outputs under `evals/llm_ingestion_slice/output/current/` were refreshed and remain untracked artifacts.

### Completed In This Session (Extraction Viability Gates)

- Added deterministic pre-projection viability gate (`Gate V`) in `evals/llm_ingestion_slice/run_slice.py`.
  - Metrics:
    - `entity_density = len(unique_entity_ids) / len(evidence_units)`
    - `duplicate_fact_ratio = (total_facts - unique_fact_keys) / total_facts`
    - `conflict_volume_band = len(conflicts)`
  - Duplicate fact canonical key:
    - `(subject_entity_id, attribute, normalized_or_label)` where `normalized_or_label` prefers `value.normalized` then `value.label`.
- Added threshold config at:
  - `evals/llm_ingestion_slice/viability_thresholds.json`
  - Values:
    - `min_entity_density: 0.20`
    - `max_duplicate_fact_ratio: 0.35`
    - `min_conflicts: 1`
    - `max_conflicts: 12`
- Added fail-fast gate sequencing:
  - Run `Gate A` + `Gate V` first.
  - If `Gate V` fails, skip Gate B/C/D and return non-zero.
  - Always emit machine-readable and human-readable diagnostics:
    - `evals/llm_ingestion_slice/output/current/gate_report.json`
    - `evals/llm_ingestion_slice/output/current/report.md`
- Added tests in `tests/evals/test_llm_ingestion_slice.py`:
  - viable pass case
  - zero entities failure
  - zero facts failure
  - high duplicate fact ratio failure
  - conflict count outside band failure
  - fail-fast `main()` behavior that confirms Gate B/C/D are skipped on viability failure
- Verification evidence:
  - `uv run ruff check evals/llm_ingestion_slice/run_slice.py tests/evals/test_llm_ingestion_slice.py` -> pass
  - `uv run pytest tests/evals/test_llm_ingestion_slice.py -q` -> `9 passed`
  - `uv run python evals/llm_ingestion_slice/run_slice.py` -> pass; Gate V metrics+thresholds present in output report

## Mission

Continue implementation of the Mirathorn event-sourced vertical slice from the locked plan:

- `Docs/Plans/mirathorn_event-sourced_slice_8eab1beb.plan.md`

Primary objective: prove the GM workflow state progression (`instantiation -> planning/zero-tick -> live`) using event-sourced ingestion and strict canon-layer behavior.

## Focused Handoff: Extraction Viability Gates (Do This First)

Status: DONE

### Objective

Add deterministic viability gates before event projection so the slice fails fast when extraction quality is too low to trust.

### Why This Is Blocking

- Current slice runner can pass using scaffolded artifacts even when extraction quality drifts.
- We need minimum extraction viability guarantees before `facts -> events -> projections`.
- This preserves hard-gate semantics and prevents false positives in downstream Gate B/C/D.

### Required Metrics (Deterministic)

1. **`entity_density`**
   - Formula: `len(unique_entity_ids) / len(evidence_units)`
   - Fail when:
     - `len(evidence_units) == 0`, or
     - `len(unique_entity_ids) == 0`, or
     - `entity_density < min_entity_density`
2. **`duplicate_fact_ratio`**
   - Use a canonical key per fact:
     - `(subject_entity_id, attribute, normalized_or_label)`
   - Formula: `(total_facts - unique_fact_keys) / total_facts`
   - Fail when:
     - `total_facts == 0`, or
     - `duplicate_fact_ratio > max_duplicate_fact_ratio`
3. **`conflict_volume_band`**
   - Formula: `len(conflicts)`
   - Fail when:
     - `conflicts < min_conflicts`, or
     - `conflicts > max_conflicts`

### Fail-Fast Contract

- Add a pre-projection viability stage in `evals/llm_ingestion_slice/run_slice.py`.
- If viability fails:
  - stop immediately (do not run projection/hybrid/workflow gates),
  - write machine-readable failure details to `output/current/gate_report.json`,
  - return non-zero exit code,
  - include clear reason(s) in `output/current/report.md`.

### Suggested Config Shape

- Add deterministic threshold config at:
  - `evals/llm_ingestion_slice/viability_thresholds.json`
- Suggested initial values for Milestone-1:
  - `min_entity_density`: `0.20`
  - `max_duplicate_fact_ratio`: `0.35`
  - `min_conflicts`: `1`
  - `max_conflicts`: `12`

### Implementation Targets

- `evals/llm_ingestion_slice/run_slice.py`
  - add viability metric computation
  - add fail-fast gate before projection gates
  - include metric snapshot in `gate_report.json`
- `tests/evals/test_llm_ingestion_slice.py`
  - add pass test for viable run
  - add failure tests for:
    - zero entities
    - zero facts
    - high duplicate ratio
    - conflict count outside band
- Optional helper (if cleaner):
  - `src/ingestion/extraction_viability.py`

### Acceptance Criteria

- Slice run fails immediately when viability checks fail.
- Failure is deterministic and reproducible for same inputs/config.
- `gate_report.json` contains:
  - computed metrics
  - thresholds
  - explicit fail reasons
- Existing hard gates (A/B/C/D) remain strict and unchanged when viability passes.

### Verification Commands

- `uv run ruff check evals/llm_ingestion_slice/run_slice.py tests/evals/test_llm_ingestion_slice.py`
- `uv run pytest tests/evals/test_llm_ingestion_slice.py -q`
- `uv run python evals/llm_ingestion_slice/run_slice.py`

### Commit Guidance

- Keep this as a single focused commit:
  - `feat(evals): add deterministic extraction viability gates with fail-fast behavior`

## Current State

- Plan is finalized and updated with current status.
- Locked source references for slice work now have markdown equivalents in:
  - `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/The City of Mirathorn.md`
  - `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Longmont Campaign General Notes.md`
- World baseline anchor to seed instantiation:
  - `Approach to Mirathorn` section in `The City of Mirathorn` source
- Rules corpus policy for Milestone 1:
  - reference metadata only (not first-class graph nodes)
- Product direction:
  - no backward compatibility requirement; build and fix forward

## Non-Negotiables

- Preserve canon-layer semantics:
  - world evidence: `canon_layer=world`, `campaign_id=null`
  - campaign evidence: `canon_layer=campaign`, `campaign_id=<campaign>`
- Event-sourced change tracking is required (do not shortcut directly to facts-only behavior).
- Hard gates remain hard. No soft-pass language and no threshold downgrades.

## Execution Order (Do This Next)

1. [DONE] Lock and fingerprint the two markdown source artifacts for reproducibility.
2. [DONE] Create Milestone-1 gold artifact pack under `evals/llm_ingestion_slice/`:
   - `slice_manifest.json`
   - `gold/evidence_units.json`
   - `gold/events.json`
   - `gold/facts.json`
   - `gold/conflicts.json`
   - `gold/canon_decisions.json`
   - `gold/projection_instantiation.json`
   - `gold/projection_zero_tick.json`
   - `gold/projection_live_state.json`
3. [DONE] Implement event-first ingestion loop in `src/ingestion/` that outputs schema-valid records with provenance.
4. [DONE] Implement projection runner checkpoints:
   - instantiation
   - zero-tick
   - live-state
5. [DONE] Implement hard-gate evaluator:
   - source/layer integrity
   - event contract integrity
   - hybrid correctness
   - workflow state progression
   - extraction viability pre-gate (Gate V) with fail-fast behavior
6. [DONE] Add tests for success and failure paths.
7. [DONE] Run verification commands and emit machine-readable pass/fail artifacts.

## Proposed Next Steps (Recommended)

1. [PENDING] **Build `evals/llm_ingestion_slice/` scaffold first**
   - commit evaluator skeleton + fixture contracts before implementing ingestion event loop changes
   - keep hard-gate outputs machine-readable (`json`) plus human-readable summary
2. [PENDING] **Implement event-first ingestion with explicit stage artifacts**
   - persist stage outputs (`chunks`, `entities`, `facts`, `events`) to deterministic artifact paths for replay/debug
3. [PENDING] **Add projection delta reporter**
   - output field-level changes across `instantiation -> zero-tick -> live` checkpoints to make Gate D auditable
4. [PENDING] **Run blind replay on moved corpus path**
   - ensure all scripts use `corpus/eldyrwild-markdown` and no longer depend on legacy `Docs/...` paths
5. [PENDING] **Commit sequence**
   - commit A: eval scaffold + gold contracts
   - commit B: event ingestion loop + stage artifacts
   - commit C: hard gates + replay tests + projection deltas

## Acceptance Gates

- [DONE] Gate A: source and layer integrity passes
- [DONE] Gate V: extraction viability passes (entity density, duplicate fact ratio, conflict volume band)
- [DONE] Gate B: event schema and ordering integrity passes
- [DONE] Gate C: hybrid correctness passes (exact core fields + conflict behavior)
- [DONE] Gate D: instantiation/zero-tick/live progression pass with auditable deltas

Any red gate blocks progression.

## Verification Commands

- `uv run ruff check .`
- `uv run pytest tests/ --maxfail=1`
- `uv run python evals/llm_ingestion_slice/run_slice.py`

## Notes for Next Agent

- Keep commits atomic:
  - commit 1: artifact pack + contracts
  - commit 2: ingestion loop
  - commit 3: runner + gates + tests
- If a provisional scaffold conflicts with plan intent, replace it rather than adapting it for compatibility.
- Keep all artifacts and reports reproducible and deterministic for the same inputs/config.
