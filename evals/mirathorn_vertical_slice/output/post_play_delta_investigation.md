# Post-Play Delta Investigation (Council Room)

## Purpose

Consolidate investigation evidence for why post-play deltas are weak despite successful ingestion.

## Existing Artifacts (Already Generated)

- `evals/mirathorn_vertical_slice/output/council_room_question_set.json`
- `evals/mirathorn_vertical_slice/output/council_room_question_set.md`
- `evals/mirathorn_vertical_slice/output/phase_d_context.txt`
- `evals/mirathorn_vertical_slice/output/phase_d_answer.txt`
- `evals/mirathorn_vertical_slice/output/phase_d_summary.json`
- `evals/mirathorn_vertical_slice/output/phase_d_store/logs/ask_runs.jsonl`
- `evals/mirathorn_vertical_slice/output/phase_d_store/logs/ingest_runs.jsonl`

## Benchmark Outcome Snapshot

- `pass_updated`: 1
- `fail_stale`: 1
- `fail_incomplete`: 3
- `fail_error`: 0

Interpretation: ingestion succeeded, but answer generation does not consistently reflect post-play updates.

## Root-Cause Findings

### 1) Scope gating excluded campaign OBSERVED facts in benchmark run

- The question-set runner invoked `ask` without campaign scope.
- Without `--campaign longmont-c1`, projection excludes campaign-layer facts by design.

Evidence:
- `none` scope: 3/5 answers claimed "no OBSERVED facts"
- `--campaign longmont-c1`: 0/5 answers claimed "no OBSERVED facts"

### 2) Temporal provenance is missing in extracted campaign facts

- Campaign facts currently have:
  - `asserted_in_session = None`
  - `sequence_index_within_session = None`
- Selection then degenerates to non-temporal tie-break behavior.

Evidence:
- campaign facts: 1944
- `asserted_in_session_non_null`: 0
- `sequence_non_null`: 0

### 3) Selected fact can be wrong "current" state even when better OBSERVED facts exist

Example (`ent_the_wolf` / `physical_condition`):
- OBSERVED candidates include:
  - "receives a killing blow (dies)"
  - "oily sheen in eyes fades"
- Selected fact:
  - "Invisible"

This produces "partial/stale" answers despite correct evidence being present in store.

### 4) Truth-state visibility is blurred in context passed to synthesis

- Context formatter maps campaign layer to `CAMPAIGN` label, not explicit `OBSERVED` / `PREP`.
- Synthesis prompt asks model to distinguish `CANON`/`PREP`/`OBSERVED`, but context does not carry those labels directly.

### 5) Store noise and repeated ingest increase conflict pressure

- Store is append-oriented; repeated ingests accumulate duplicates/conflicts.
- Current duplicate pressure:
  - `facts_total`: 4982
  - `duplicate_fact_instances`: 1238
  - `duplicate_ratio`: 0.2485

Projection metrics:
- no campaign: `open_conflicts=374`, `projected_entities=353`
- with campaign: `open_conflicts=642`, `projected_entities=718`

### 6) Entity quality issues likely contaminate downstream behavior

Example:
- `ent_the_wolf` alias list includes unrelated names/pronouns, indicating over-merge/entity contamination risk.

## Confirmed Ingestion Coverage (Requested Sources)

Ingested into `phase_d_store`:
- `Battle with The Wolf and Aftermath.md`
- `The Emergency Council Meeting.md`
- `The City Council.md`
- `Longmont Campaign General Notes.md` (campaign `longmont-c1`)

## What Is Proven vs Not Proven

- Proven:
  - Source docs were ingested.
  - Campaign scope materially changes retrieval behavior.
  - Temporal metadata is missing from campaign facts.
  - Selection can pick suboptimal "current" observed fact.
- Not yet proven:
  - Quantified contribution split between selection policy vs entity contamination vs synthesis behavior for each failed question.

## Next Investigation Actions

1. Run the same 5-question set with explicit `--campaign longmont-c1` and rescore.
2. For each failed question, trace:
   - expected fact(s),
   - all candidate facts,
   - selected fact,
   - mismatch reason (`scope`, `timeline`, `selection`, `entity_merge`, `synthesis`).
3. Add temporal extraction fields from session headers and verify selection changes.
4. Re-run multi-pass sampling to measure drift after temporal provenance is added.
