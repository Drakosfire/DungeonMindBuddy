# Stage C NPC Candidate Identification — Vertical Slice

**Position in the events-first pipeline:** Stage A (events extraction) → **Stage C (this slice)** → Stage D (entity resolution) + Stage E (per-NPC artifact updates).

Stage A produces `event_record`-shaped JSON with `participants[]` and `referenced_slugs[]`. Stage C reads that JSON plus the per-campaign NPC registry (`<campaign>/_npc_registry.json`) and a PC negative list, and classifies every distinct non-PC entity into one of three buckets:

- **`tracked_npcs_active[]`** — entities matched against the registry positive-list (by slug, display_name, or alias). Feed into **Stage E** (per-NPC hub/timeline updates).
- **`new_npc_candidates[]`** — named entities the model believes deserve a registry record. Feed into the **GM review queue** for promotion to `candidate` → `tracked`.
- **`unresolved_descriptors[]`** — ambiguous descriptors (e.g. "the masked figure") that need **Stage D**'s harder entity-resolution work.

Mixing these buckets defeats the purpose — each downstream consumer cares about a different bucket. No corpus reads. No recap re-reads. All input is JSON, mirroring the discipline Stage B established.

## Layout

```
evals/stage_c_npc_candidates_vertical_slice/
  __init__.py
  README.md                              ← this file
  step1_stage_c_run.py                   ← runner (CLI entry point)
  grader.py                              ← NC1-NC5 gate logic + telemetry
  stage_c_run_report.py                  ← per-run + cohort artifact writers
  gold/
    stage_c_session20.json               ← Stage C gold (S20 — first cohort)
  fixtures/
    .gitignore                           ← allow stage_a_events_*.json; ignore everything else
    stage_a_events_session20.json        ← FROZEN Stage A events for deterministic Stage C testing
  artifacts/
    .gitignore
    last_stage_c_run.{md,json}           ← latest Stage C run
    runs/
      .gitkeep
      YYYY-MM-DD/
        stage_c--*.{md,json}             ← per-run artifacts (sidecar carries stage_c_output)
        stage_c_summary--*--N*.{md,json} ← cohort summary
tests/
  test_stage_c_grader.py                 ← offline grader unit tests (no network)
```

## Frozen Stage A events fixture

Stage C is graded against a **checked-in, frozen** Stage A events fixture (`fixtures/stage_a_events_session20.json`) so Stage C runs are deterministic and Stage C iteration is decoupled from Stage A model variance. Stage A does not yet persist `parsed_events` to its standalone sidecars (open follow-up #4 in the Stage A README, captured in `Backlog.md`); when that lands, Stage C will be able to grade against ANY Stage A cohort artifact, not just hand-frozen fixtures.

## How to run

```bash
# Single run
uv run python -m evals.stage_c_npc_candidates_vertical_slice.step1_stage_c_run --n 1 --model gpt-5.4-mini

# Cohort of 5 (the canonical proving cohort for this slice)
uv run python -m evals.stage_c_npc_candidates_vertical_slice.step1_stage_c_run --n 5 --model gpt-5.4-mini

# Dry run (no artifacts written)
uv run python -m evals.stage_c_npc_candidates_vertical_slice.step1_stage_c_run --n 1 --no-writes
```

Cohort budget guard: stops if cumulative cost > $1.00 with 0 passes after 2+ runs; warns above $2.00.

## Gates

| Gate | Description | Threshold |
|------|-------------|-----------|
| **NC1** | Output JSON parses; three top-level arrays present; per-record fields typed correctly; `evidence_event_indices` are valid 0-indexed positions; `tracked_npcs_active[].slug` matches a real registry slug; all slugs match `^[a-z0-9_]+$`. | Hard fail on any violation |
| **NC2** | **PC negative-list cleanliness (HARD GATE)** — no PC slug or display_name/alias substring leaks into any of the three buckets. | Hard fail on any leak |
| **NC3** | **Registry positive-list recall (HARD GATE)** — every `tracked`/`background` registry slug that appears in events' `participants` ∪ `referenced_slugs` MUST appear in `tracked_npcs_active[].slug`. PLUS every gold `expected_tracked_active_minimum` slug must appear (alias-aware floor). | Hard fail on any miss |
| **NC4** | Every `new_npc_candidates[]` and `unresolved_descriptors[]` record cites at least one valid `evidence_event_indices[]` entry. | Hard fail per bare record |
| **NC5** | Total candidates ≤ `max_total_candidates` (gold default: 25). | Hard bound |

## Soft-bonus telemetry (NOT a gate)

`expected_new_candidates_should_include_at_least_one_of` in the gold lists slugs that *should* surface in `new_npc_candidates[].suggested_slug` if Stage A populated `referenced_slugs[]` with the right named entities. The grader emits `expected_new_candidate_coverage_hit: bool` in telemetry but does NOT fail any gate when missed — this is exploratory and doubles as a diagnostic for Stage A's referenced-slugs coverage of summary-only-named NPCs.

## Telemetry exposed

```json
{
  "tracked_active_count": 6,
  "new_candidates_count": 1,
  "unresolved_count": 0,
  "registry_recall_ratio": 1.0,
  "registry_active_slugs_in_events": ["captain_lysandra_ironveil", "sara_mirathorn_operator", "stuart", "thrin_branchborn"],
  "tracked_active_slugs_emitted": [...],
  "expected_tracked_active_missing": [],
  "expected_new_candidate_coverage_hit": true,
  "expected_new_candidate_coverage_terms": ["professor_tealeaf", "tealeaf"],
  "new_candidate_slugs_emitted": [...],
  "pc_leaks": [],
  "total_candidates": 1
}
```

## Offline tests

```bash
uv run pytest tests/test_stage_c_grader.py -v
```

19 tests covering NC1 (5), NC2 (3), NC3 (3), NC4 (2), NC5 (2), and top-level grader (4). Synthetic registry + synthetic events fixtures inline; no corpus dependency.

## Iteration history

- **2026-04-22** — Stage C proving slice landed. S20 N=5 cohort at `gpt-5.4-mini` is the first ever Stage C cohort; results recorded in the commit message and the corresponding cohort artifact under `artifacts/runs/`. Frozen Stage A events fixture: 20 events, includes participants for all 5 PCs + 5 tracked NPCs; `referenced_slugs[]` populated for `captain_lysandra_ironveil` and `stacey`. Tealeaf appears in event_name/outcomes but not in `referenced_slugs[]` — the soft-bonus telemetry signal will surface this as a Stage A coverage gap.

## Open follow-ups

1. **C1 triple (shipped 2026-04-22)** — `gold/stage_c_session{1,2,3}_c1.json` + `fixtures/stage_a_events_session{1,2,3}_c1.json` + `corpus/.../Campaign 1/_npc_registry.json` (Lysandra/Torbin + candidate seeds). N=5 cohorts recorded under `artifacts/runs/2026-04-22/`. Downstream Stage D gold/fixtures for the same sessions live in `evals/stage_d_entity_resolution_vertical_slice/` (including `stage_d_session2_c1.json` + `fixtures/stage_c_output_session2_c1.json` as of 2026-04-23).
2. **Stage A `parsed_events` sidecar persistence** — would let Stage C run against ANY Stage A cohort artifact instead of frozen fixtures. See `Backlog.md` entry tagged READY.
3. **Stage D v1+** — narrow LLM coreference for Kirfan-class unresolvables; see `evals/stage_d_entity_resolution_vertical_slice/README.md` and `Backlog.md` `[READY] Stage D — narrow LLM coreference pass`.
4. **Stage E (per-NPC artifact update)** — consumes `tracked_npcs_active[]`. Separate slice.
