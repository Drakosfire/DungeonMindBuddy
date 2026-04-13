# Lysandra statblock vertical slice (benchmark scaffolding)

**Planner alignment:** Buddy’s canonical “which documents?” path is the **Responses tool loop** (`read_corpus_file` + `tool_trace` in `run_planning_turn_detailed`, `src/agent/planner.py`). This slice should **prefer gates on that trace**; keyword scoring here is a **baseline**, not the definition of retrieval—see design doc “Planner alignment — one line”.

- **Gate status (signpost):** [`GATES.md`](GATES.md) · [`gold/step0_status.json`](gold/step0_status.json) · [`gold/step1_status.json`](gold/step1_status.json) · [`gold/planner_step1_status.json`](gold/planner_step1_status.json) — **Steps 0–1 done** (Step 1 = Lane A trace + Lane B keyword); Step 2 next.
- **Design:** `Docs/Plans/DESIGN-lysandra-statblock-vertical-slice-benchmark.md`
- **Corpus survey:** `SURVEY-captain_lysandra_corpus.md`
- **Gold:** `gold/corpus_policy.json`, `gold/step0_environment.json`
- **Step 0 implementation:** `step0_corpus_environment.py` — `run_step0_gates()`
- **Step 1 Lane A:** `step1_planner_trace.py` — `run_planner_step1_turn()` → `PlannerStep1Run` (includes `detail.usage_rounds` per API completion); CLI prints review + enables `dmb.planner` INFO telemetry; loads `OPENAI_API_KEY` from `.env` via `src.bootstrap_env` · `gold/planner_step1_directed.json` (path-steered smoke) and `gold/planner_step1_autonomous.json` (human-style ask; default via `LYSANDRA_PLANNER_STEP1_SCENARIO`) · `tests/test_lysandra_vertical_slice_planner_step1.py`
- **Step 1 Lane B:** `step1_retrieval.py` — `run_step1_keyword_scan_and_gates()`
- **Tests:** `tests/test_lysandra_vertical_slice_step0.py`, `tests/test_lysandra_vertical_slice_step1.py`, `tests/test_lysandra_vertical_slice_planner_step1.py`

Refresh fingerprint in `gold/step0_environment.json` after corpus edits (see survey §6).
