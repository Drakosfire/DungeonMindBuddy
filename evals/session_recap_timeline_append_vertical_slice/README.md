# Session recap → timeline append (Stage-2 vertical slice)

**What this slice grades:** After Stage-1 has committed `Session 20 - Recap.md`, the planner performs a **new turn** (no recap-write skill): read the recap + NPC `timeline.md`, then **two-phase** `append_timeline_row` only.

- **Spec:** [Docs/Plans/EXPERIMENT-Session-Recap-Timeline-Append-Benchmark.md](../../Docs/Plans/EXPERIMENT-Session-Recap-Timeline-Append-Benchmark.md)
- **Gate ledger:** [Docs/Plans/STATUS-Session-Recap-Timeline-Append-Benchmark.md](../../Docs/Plans/STATUS-Session-Recap-Timeline-Append-Benchmark.md)
- **Stage-1 artifact pinned in:** `gold/Session 20 - Recap.md` (byte snapshot of `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md` at slice creation time; canonical reference path documented in `gold/step0_pre_state_manifest.json`).

Stage-1 ingest code under `evals/session_recap_ingest_vertical_slice/` is **not** imported by this slice (shared surface: live corpus copy + `append_timeline_row` in `corpus_writer.py`).

---

## Pre-state corpus

Copies `corpus/eldyrwild-markdown`, removes any Lysandra `timeline.md` row for session **20**, then overwrites the recap path from `gold/Session 20 - Recap.md`.

```bash
uv run python -m evals.session_recap_timeline_append_vertical_slice.step1_timeline_append_run --print-root
```

---

## Offline tests

```bash
uv run pytest tests/test_timeline_append_grader.py tests/test_timeline_append_pre_state.py -q
```

---

## Live cohort

```bash
export OPENAI_API_KEY=…   # or repo .env
export DUNGEONMIND_PLANNER_ALLOW_WRITES=1
PLANNER_REVIEW_MODE=summary uv run python -m \
  evals.session_recap_timeline_append_vertical_slice.step1_timeline_append_run \
  --n 3 --model gpt-5.4-mini
```

Artifacts: `artifacts/runs/<YYYY-MM-DD>/timeline_append--*.{md,json}` and `artifacts/last_timeline_append_run.{md,json}`.

Optional: `TIMELINE_APPEND_RUNS_ROOT` to override the runs directory.

---

## Grading (summary)

- **Hybrid row rubric:** session cell `**20**`; recap cell backticked path ending in `Session 20 - Recap.md` (full corpus-relative path allowed); beat cell non-empty with regex anchors (Lysandra + recap context keyword).
- **Tool rubric:** `append_timeline_row` preview→commit with successful commit; no `write_corpus_file`; no `assemble_recap_draft` / `build_recap_write_payload`.

See the EXPERIMENT doc for normative gate IDs.
