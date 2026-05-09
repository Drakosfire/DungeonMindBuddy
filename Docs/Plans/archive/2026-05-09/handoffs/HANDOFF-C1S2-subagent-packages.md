# HANDOFF — C1S2 Subagent task packages

Parent plan: C1S2 breadcrumb retrieval slice (contracts in `evals/sentence_routing_retrieval_falsification/C1S2_BENCHMARK_CONTRACTS.md`). Use each block as a single `Task` brief: mission, allowlist, out-of-scope, verification command, report footer (`git diff --stat` scoped).

## Handoff A — Breadcrumb artifact + sentinels (mostly done)

- **Mission:** Keep `manual_labels/Session 2 - Finishing the Job.breadcrumbed.md` aligned with normalization (`?` / newline joint rules) and `gold/breadcrumb_tagging_sentinels_c1s2.json` passing.
- **Files in scope:** `manual_labels/Session 2 - Finishing the Job.breadcrumbed.md`, `gold/breadcrumb_tagging_sentinels_c1s2.json`, optional `breadcrumb_tagging_variant_runner` cohort artifacts under `artifacts/runs/`.
- **Out of scope:** Gold natural queries, candidate builder, runner.
- **Verify:** `uv run python -c "from pathlib import Path; from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import normalize_breadcrumb_artifact; normalize_breadcrumb_artifact(artifact_text=Path('evals/sentence_routing_retrieval_falsification/manual_labels/Session 2 - Finishing the Job.breadcrumbed.md').read_text(), corpus_root=Path('corpus/eldyrwild-markdown'))"` and `score_artifact` with C1S2 sentinels.

## Handoff B — Candidate builder

- **Mission:** Extend `c1s2_query_candidate_build.py` heuristics (categories, natural questions) without reading gold.
- **Files in scope:** `c1s2_query_candidate_build.py`, `tests/test_c1s2_query_candidate_build.py`.
- **Out of scope:** `gold/breadcrumb_query_natural_c1s2_v1.json`, `breadcrumb_query_run.py`.
- **Verify:** `uv run pytest tests/test_c1s2_query_candidate_build.py`.

## Handoff C — Candidate canvas emitter

- **Mission:** Adjust `c1s2_query_candidate_canvas_emit.py` / `canvases/c1s2-breadcrumb-query-candidate-review.canvas.tsx` UX only (component-shaped review).
- **Files in scope:** `c1s2_query_candidate_canvas_emit.py`, `canvases/c1s2-breadcrumb-query-candidate-review.canvas.tsx`, `tests/test_c1s2_query_candidate_canvas_emit.py`.
- **Out of scope:** Benchmark gold, C1S1 canvas.
- **Verify:** `uv run pytest tests/test_c1s2_query_candidate_canvas_emit.py`.

## Handoff D — Gold + offline / live harness

- **Mission:** Tune `gold/breadcrumb_query_natural_c1s2_v1.json` after human review; run **three identical live** `breadcrumb_query_run` cohorts; refresh benchmark canvas from real reports (not offline stub).
- **Files in scope:** `gold/breadcrumb_query_natural_c1s2_v1.json`, `artifacts/runs/<date>/breadcrumb_query_natural_c1s2_report*.json`, `c1s2_offline_benchmark_report_build.py` (only if adjusting offline stub shape).
- **Out of scope:** `src/prompts/*`, Session 20 gold.
- **Verify:** README commands; `uv run pytest tests/test_c1s2_gold_retrieval_contract.py`; three live reports with `scenario_estimated_cost_usd` recorded.

## Handoff E — Runner + C1S2 benchmark canvas wiring

- **Mission:** Regression-test `breadcrumb_query_run.py` C1S2 canvas refresh flags; keep C1S1 behavior unchanged.
- **Files in scope:** `breadcrumb_query_run.py`, `c1s2_benchmark_canvas_emit.py`, `canvases/c1s2-breadcrumb-query-benchmark-review.canvas.tsx`, `tests/test_breadcrumb_query_run_canvas_integration.py`, `tests/test_c1s2_benchmark_canvas_emit.py`.
- **Out of scope:** C1S1 emitter logic changes.
- **Verify:** `uv run pytest tests/test_breadcrumb_query_run_canvas_integration.py tests/test_c1s2_benchmark_canvas_emit.py`.
