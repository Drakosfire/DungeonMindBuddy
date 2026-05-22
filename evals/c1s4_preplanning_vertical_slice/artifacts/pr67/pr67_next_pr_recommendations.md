# PR67 next PR recommendations

## Tier A miss root causes

- `strict_gold_lane_mismatch`: 3

## Q3 prior-distance probe (mirathorn + week)

- **prior_only**: merged_rank=14 admitted_rank=8 failure_stage=render
- **prior_plus_support_content_only**: merged_rank=19 admitted_rank=9 failure_stage=render
- **prior_plus_support_content_plus_lexical_hints**: merged_rank=21 admitted_rank=9 failure_stage=render

## Recommended follow-ups

1. If Q3 `failure_stage=admission` persists after route-event preservation, inspect lane budgets for `prior_campaign_memory`.
2. Q5 should pass strict gold in support modes after visibility-contract gold realignment; do not admit Hempholm campaign hub.
3. Keep legacy `top_k=9` labeled as preview/scoring shim only (`grading_surface_labels`).
