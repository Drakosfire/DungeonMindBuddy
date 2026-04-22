# Session Events Extraction Vertical Slice

**Stage A of the two-stage session-events → timeline-append architecture.**

This benchmark tests whether a model can read a session recap and extract a complete, structured list of `event_record`-shaped JSON objects covering all meaningful beats in the session. Stage B (appending timeline rows from those events) is unbuilt and out of scope for this slice.

## Layout

```
evals/session_events_extraction_vertical_slice/
  __init__.py
  README.md                         ← this file
  step1_session_events_run.py       ← runner (CLI entry point)
  grader.py                         ← gate logic + telemetry
  session_events_run_report.py      ← per-run + cohort artifact writers
  gold/
    session_events_session20.json   ← gold scenario (curated from Session 20 recap)
  artifacts/
    .gitignore
    last_session_events_run.{md,json}  ← legacy symlinks (latest run)
    runs/
      YYYY-MM-DD/
        session_events--*--PASS--.md
        session_events--*--PASS--.json
        session_events_summary--*--N*.{md,json}
tests/
  test_session_events_grader.py     ← offline grader tests (no network)
```

## Recap path strategy

The Session 20 recap is **not** duplicated into this slice's `gold/` directory. The runner reads it directly from the canonical corpus path:

```
corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md
```

relative to the repo root. The `DUNGEONMIND_CORPUS_ROOT` env var can override the corpus root if needed.

## How to run

```bash
# Single run
uv run python -m evals.session_events_extraction_vertical_slice.step1_session_events_run --n 1 --model gpt-5.4-mini

# Cohort of 5
uv run python -m evals.session_events_extraction_vertical_slice.step1_session_events_run --n 5 --model gpt-5.4-mini

# Dry run (no artifacts written)
uv run python -m evals.session_events_extraction_vertical_slice.step1_session_events_run --n 1 --no-writes
```

## Gates

| Gate | Description | Threshold |
|------|-------------|-----------|
| **SE1** | Every parsed event validates against `event_record.schema.json`. Fail closed. | Hard fail on any violation |
| **SE2** | Event count is within `[min_event_count, max_event_count]` (gold: 10–25). | Hard bounds |
| **SE3** | Every slug in `must_cover_participants` appears in at least one event's `participants[]`. | All required |
| **SE4** | Every class in `must_cover_event_classes` appears in at least one event's `event_class`. | All required |
| **SE5** | For each `expected_events[i]`, at least one model event matches (same `event_class` + participant overlap + text overlap on name/outcomes). Coverage ratio reported in telemetry. | Soft fail when ratio < 0.5 |

SE5 is deliberately permissive at launch. The threshold is documented at `_SE5_PASS_THRESHOLD = 0.5` in `grader.py` and will be raised once we have cohort data.

## Gold curation (Session 20)

Gold events were hand-curated by reading `Session 20 - Recap.md` directly. The gold contains 16 `expected_events` covering:

- **combat**: red gnat swarm battle
- **social_conflict**: Stacey warehouse confrontation; Bonogo knife threat; Marla vs Bonogo confrontation; Caelynn de-escalation
- **conversation**: party reports to Stafl; mayor denies Lysandra; Sara/Lysandra rockie-talkie call; Caelynn reports tainted meat to Sara; Ephanna announces departure
- **discovery**: fortification fires drive forest retreat; Lysandra found with cult eyes and tower blueprint
- **travel**: Karsemine tracks Lysandra; group reaches wagon camp
- **ritual**: Caelynn administers antidote tea to Lysandra
- **investigation**: Stafl finds tainted meat; Karsemine rounds up horses and spots approaching storm

## Telemetry exposed

Each run report includes:

```json
{
  "event_count": <int>,
  "participants_seen": ["bonogo", "caelynn", ...],
  "event_classes_seen": ["combat", "conversation", ...],
  "expected_event_coverage_ratio": 0.75,
  "unmatched_expected_event_indices": [3, 11]
}
```

## Offline tests

```bash
uv run pytest tests/test_session_events_grader.py -q
```

## Future work

1. **Stage B handoff**: `step2_timeline_from_events_run.py` (not built). Whether Stage B re-reads the recap or consumes only event records is an open empirical question — do not bake in an answer here.

2. **`FactStore.add_event_records()` persistence**: The runner validates events against the JSON schema but does not call `FactStore.add_event_records()`. Persistence is intentionally deferred until Stage A pass rates are acceptable.

3. **SE5 threshold lift**: Start at 0.5. After first passing cohort, raise to 0.65 or 0.75. Document iterations here.

4. **Out-of-scope improvements noticed while reading**:
   - `src/ingestion/fact_extractor.py`: `_usage_dict_from_openai_response` is defined in `entity_extractor.py` and re-imported by `fact_extractor.py`; should be centralized in `src/llm/api_client.py` — not touched per scope rules.
   - `evals/session_recap_timeline_pass_vertical_slice/grader.py`: TP4 is referenced in some comments but was removed in Iteration 6; dead code cleanup opportunity — not touched.
