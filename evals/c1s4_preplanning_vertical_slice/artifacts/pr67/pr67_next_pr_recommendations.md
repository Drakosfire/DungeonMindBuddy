# PR67 next PR recommendations

## Tier A miss root causes

- `strict_gold_lane_mismatch`: 3

## Q3 prior-distance probe (mirathorn + week)

- **prior_only**: failure_stage=no_session_evidence session_evidence_ref=None admitted_lane_ref=None
- **prior_plus_support_content_only**: failure_stage=no_session_evidence session_evidence_ref=None admitted_lane_ref=None
- **prior_plus_support_content_plus_lexical_hints**: failure_stage=no_session_evidence session_evidence_ref=None admitted_lane_ref=None

## Recommended follow-ups

1. If Q3 `failure_stage=admission` persists after route-event preservation, inspect lane budgets for `prior_campaign_memory`.
2. Q5 passes strict gold in support modes after visibility-contract gold realignment (not retrieval improvement); Hempholm campaign hub remains excluded.
3. Keep legacy `top_k=9` labeled as preview/scoring shim only (`grading_surface_labels`).
