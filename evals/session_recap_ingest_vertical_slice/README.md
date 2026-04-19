# Session recap ingest vertical slice (Scope-B scaffold)

Benchmark design: [Docs/Plans/EXPERIMENT-Session-Recap-Ingest-Benchmark.md](../../Docs/Plans/EXPERIMENT-Session-Recap-Ingest-Benchmark.md).

## Scope-A (fast, no LLM)

Mechanical recap ingest is tested in-repo:

```bash
uv run pytest tests/test_session_20_scope_a_gold.py tests/test_recap_ingest_helpers.py -q
```

## Scope-B (live planner)

1. **Step 0 — environment:** `step0_corpus_environment.run_step0_gates()` checks corpus fingerprint (`gold/step0_environment.json`) and `OPENAI_API_KEY` (or `SESSION_RECAP_INGEST_SKIP_SERVICE_GATE=1` for CI-only smoke).

2. **Pre-state corpus:** `step0_pre_state.build_pre_state_corpus()` copies `corpus/eldyrwild-markdown` to a temp directory and applies `gold/step0_pre_state_manifest.json` (removes Session 20 recap, Mossford NPC dirs, Lysandra row 20, trailing prep blockquote).

3. **Run planner (step 1):** `step1_recap_ingest_run.py` builds the pre-state corpus (unless `--live-corpus`), loads `fixtures/session_20_raw_notes.txt`, prepends the **recap-write** skill body from `.cursor/skills/recap-write/SKILL.md`, and runs one `run_planning_turn_detailed` with **`include_write_tools` + `allow_corpus_writes`** so `write_corpus_file` / `append_timeline_row` match production. Sets `DUNGEONMIND_PLANNER_ALLOW_WRITES=1` by default.

   ```bash
   export OPENAI_API_KEY=...
   uv run python -m evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run
   ```

   Flags: `--print-root` (only materialize tmp corpus path), `--live-corpus` (skip manifest; uses repo corpus), `--tmp-parent DIR` (fixed parent for the copy), `--model ID`, `--no-writes` (dry policy / debugging).

4. **Grade:** `step2_grade_against_gold.py` and extended tool-trace checks are still TODO (fixture `final.require` in `gold/scope_b_session_20.json` is empty so step 1 gates stay permissive until graders land).

5. **Unsure queue:** `step3_unsure_queue_grading.py` implements regex/count grading against `gold/scope_b_session_20_unsure_queue.json` for local unit-style checks once planner output is available.

6. **C3 chaos:** Documented in `step4_chaos_two_phase.py`; behavior is asserted in `tests/test_corpus_writer.py`.

## Artifacts

Dated run logs should land under `artifacts/runs/` (mirrors other vertical slices).

## Fixture

`fixtures/session_20_raw_notes.txt` is a copy of repo-root `Session 20 Recap.txt`.
