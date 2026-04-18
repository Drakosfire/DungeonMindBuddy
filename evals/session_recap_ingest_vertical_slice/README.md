# Session recap ingest vertical slice (Scope-B scaffold)

Benchmark design: [Docs/Plans/EXPERIMENT-Session-Recap-Ingest-Benchmark.md](../../Docs/Plans/EXPERIMENT-Session-Recap-Ingest-Benchmark.md).

## Scope-A (fast, no LLM)

Mechanical recap ingest is tested in-repo:

```bash
uv run pytest tests/test_session_20_scope_a_gold.py tests/test_recap_ingest_helpers.py -q
```

## Scope-B (live planner — scaffold)

1. **Step 0 — environment:** `step0_corpus_environment.run_step0_gates()` checks corpus fingerprint (`gold/step0_environment.json`) and `OPENAI_API_KEY` (or `SESSION_RECAP_INGEST_SKIP_SERVICE_GATE=1` for CI-only smoke).

2. **Pre-state corpus:** `step0_pre_state.build_pre_state_corpus()` copies `corpus/eldyrwild-markdown` to a temp directory and applies `gold/step0_pre_state_manifest.json` (removes Session 20 recap, Mossford NPC dirs, Lysandra row 20, trailing prep blockquote).

3. **Run planner:** `step1_recap_ingest_run.py` currently only supports `--print-root` to emit a tmp corpus path. Full wiring should call `evals.planner_slice.live_eval` like `evals/npc_voice_vertical_slice/`.

4. **Grade:** `step2_grade_against_gold.py` and extended tool-trace checks are TODO.

5. **Unsure queue:** `step3_unsure_queue_grading.py` implements regex/count grading against `gold/scope_b_session_20_unsure_queue.json` for local unit-style checks once planner output is available.

6. **C3 chaos:** Documented in `step4_chaos_two_phase.py`; behavior is asserted in `tests/test_corpus_writer.py`.

## Artifacts

Dated run logs should land under `artifacts/runs/` (mirrors other vertical slices).

## Fixture

`fixtures/session_20_raw_notes.txt` is a copy of repo-root `Session 20 Recap.txt`.
