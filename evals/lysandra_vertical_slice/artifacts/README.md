# Agent benchmark — default benchmark artifact

`step1_planner_trace.py` (CLI entrypoint: `uv run python evals/lysandra_vertical_slice/step1_planner_trace.py`)
uses the **default benchmark** **`upgrade_prose`** (natural power-rise ask) when `LYSANDRA_PLANNER_STEP1_SCENARIO` is unset, and always writes **`last_planner_step1_run.md`** here (full human-readable review: usage, tool trace, final answer, Step 2 benchmark block when configured). The file is gitignored; open it locally after each run.

Override the artifact path with `LYSANDRA_PLANNER_FINAL_OUT=/some/other/path.md`.
