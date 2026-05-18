# PR56 Step 2C Lane-Aware Failure Analysis

## Scope
Q1/Q3/Q5 across three retrieval modes using PR55 lane-aware gold. Analysis-only (no retrieval/admission/gold tuning).

## Commands Run
- `uv run python evals/c1s4_preplanning_vertical_slice/step2c_expected_context_benchmark.py --all-modes --output-json /tmp/c1s4_pr56_lane_aware_step2c_multimode_report.json`
- `uv run python evals/c1s4_preplanning_vertical_slice/analyze_lane_aware_failures.py --input-json /tmp/c1s4_pr56_lane_aware_step2c_multimode_report.json --output-dir evals/c1s4_preplanning_vertical_slice/artifacts/pr56`

## Summary Counts
- Total classified missing required groups: 23
- Counts by failure class: {'retrieval_miss': 23}
- Counts by mode: {'prior_only': {'retrieval_miss': 7}, 'prior_plus_support_content_only': {'retrieval_miss': 8}, 'prior_plus_support_content_plus_lexical_hints': {'retrieval_miss': 8}}

## Failure Taxonomy
Primary observed class is `retrieval_miss` for all missing groups in Q1/Q3/Q5. No candidate/admitted evidence was surfaced for those groups in the benchmark report.

## Q1 Analysis
All required groups (`pippa_character_continuity`, `bubbles_character_continuity`, `grishna_character_continuity`, `stone_bridge_location_support_context`) are retrieval misses in all modes.

## Q3 Analysis
`mirathorn_distance_estimate_from_play` and `stone_bridge_location_context` are retrieval misses in all modes. Known-gap expectation itself still hits in benchmark row-level metrics, but required lane-aware groups remain missing.

## Q5 Analysis
- prior_only: `hempholm_location_context` retrieval miss.
- support-enabled modes: both `hempholm_location_context` and `hempholm_tree_support_context` retrieval miss.

## Lane Visibility
Rendered packet sections exist structurally, but with empty content (`(none)`) in failed rows; this indicates visibility scaffolding without evidence population.

## Invalid Evidence Rejections
No navigation-only/anchor-only lane-aware rejection cases were observed for Q1/Q3/Q5 in this rerun.

## Retrieval vs Admission vs Rendering
For all classified misses, evidence did not reach candidate context; therefore misses are retrieval-stage, not admission-stage or rendering-stage.

## Recommendations
1. retrieval_indexing: verify indexing/population for session memory, npc_hub, and location_hub artifacts used by Q1/Q3/Q5 requirements.
2. retrieval_indexing: audit route/path expansion and source-module coverage for Mirathorn/Stone Bridge/Hempholm artifacts.
3. admission_budgeting/rendering_or_provenance: defer changes until retrieval is producing non-empty candidate context for these questions.

## Non-goals / Deferred Work
No ranking, budget, corpus, renderer semantics, or gold definition changes were implemented in PR56.


## Step 2D invocation note
Direct script execution can fail import resolution in this environment; module invocation works: `uv run python -m evals.c1s4_preplanning_vertical_slice.step2d_expected_context_canvas_emit --help`.
