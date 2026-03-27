# Handoff: Mirathorn Event-Sourced Slice

## Mission

Continue implementation of the Mirathorn event-sourced vertical slice from the locked plan:

- `Docs/Plans/mirathorn_event-sourced_slice_8eab1beb.plan.md`

Primary objective: prove the GM workflow state progression (`instantiation -> planning/zero-tick -> live`) using event-sourced ingestion and strict canon-layer behavior.

## Current State

- Plan is finalized and updated with current status.
- Locked source documents:
  - `Docs/Eldyrwild and Campaign Context/Elderwyld/Cities and Towns/Mirathorn/The City of Mirathorn.docx`
  - `Docs/Eldyrwild and Campaign Context/Longmont Campaign/Campaign 1/Longmont Campaign General Notes.docx`
- World baseline anchor to seed instantiation:
  - `Approach to Mirathorn` section in `The City of Mirathorn.docx`
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

1. Lock and fingerprint the two source docs for reproducibility.
2. Create Milestone-1 gold artifact pack under `evals/llm_ingestion_slice/`:
   - `slice_manifest.json`
   - `gold/evidence_units.json`
   - `gold/events.json`
   - `gold/facts.json`
   - `gold/conflicts.json`
   - `gold/canon_decisions.json`
   - `gold/projection_instantiation.json`
   - `gold/projection_zero_tick.json`
   - `gold/projection_live_state.json`
3. Implement event-first ingestion loop in `src/ingestion/` that outputs schema-valid records with provenance.
4. Implement projection runner checkpoints:
   - instantiation
   - zero-tick
   - live-state
5. Implement hard-gate evaluator:
   - source/layer integrity
   - event contract integrity
   - hybrid correctness
   - workflow state progression
6. Add tests for success and failure paths.
7. Run verification commands and emit machine-readable pass/fail artifacts.

## Acceptance Gates

- Gate A: source and layer integrity passes
- Gate B: event schema and ordering integrity passes
- Gate C: hybrid correctness passes (exact core fields + conflict behavior)
- Gate D: instantiation/zero-tick/live progression pass with auditable deltas

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
