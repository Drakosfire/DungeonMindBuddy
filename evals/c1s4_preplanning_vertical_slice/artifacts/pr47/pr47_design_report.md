# PR47 Design Report

## What changed
- Deterministic query feature extraction and lane planning are now attached to each Step2 row.
- Lane-budgeted admission is the default and enforces support exclusion in prior_only.

## What improved
- Packet quality metrics are now computed and populated per row (unknown lane ratio, support burial depth, support token share, usability flags/score).
- Lane plan artifact now contains concrete query_features/lane_plan objects for Q1/Q3/Q5 across modes.

## Metric deltas vs PR46
- Q5 support modes are compared against recorded PR46 baselines in `pr47_packet_quality_delta_vs_pr46.json`.
- Rows without explicit PR46 baselines are retained with explanatory notes to avoid hiding data.

## Stability checks
- Expected-context pass/fail behavior remains green for Q1/Q3/Q5 across all modes.
- Forbidden violations remain 0 and known-gap recall remains intact.

## Caveats
- Lane admission preserves candidate rank order after selection; therefore salience improvement can come from better inclusion and rendered section grouping, not necessarily lower global admitted rank in all cases.
