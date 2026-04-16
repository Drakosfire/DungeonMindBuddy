# Agent benchmark — run artifacts

`step1_planner_trace.py` (CLI: `uv run python evals/lysandra_vertical_slice/step1_planner_trace.py`)
uses **`upgrade_prose`** when `LYSANDRA_PLANNER_STEP1_SCENARIO` is unset. Each run writes:

- **`runs/YYYY-MM-DD/step1--<scenario>--<model>--PASS|FAIL--1turn|2turn--<UTC-timestamp>.md`** — dated, named report (same body as stdout review: usage, tool trace, final answer, Step 2 block when configured).
- **`last_planner_step1_run.md`** — mirror of the latest run for quick reopen.

`runs/` and `last_*.md` are gitignored. Optional **`LYSANDRA_PLANNER_STEP1_RUNS_ROOT`**: absolute directory for dated folders instead of `<slice>/artifacts/runs`.

`LYSANDRA_PLANNER_FINAL_OUT=/path.md` writes **final answer only** (separate from the full report).
