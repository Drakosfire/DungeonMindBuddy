# PR46 Packet Quality Report

Topline verdict: packet quality is measurable and deterministic; benchmark pass/fail unchanged.

## prior_only
- Q1: score=3, flags=high_admitted_count,high_unknown_lane_ratio, unknown_lane_ratio=1.0, support_burial_depth=None, support_token_share=0.0
- Q3: score=3, flags=high_admitted_count,high_unknown_lane_ratio, unknown_lane_ratio=1.0, support_burial_depth=None, support_token_share=0.0
- Q5: score=3, flags=high_admitted_count,high_unknown_lane_ratio, unknown_lane_ratio=1.0, support_burial_depth=None, support_token_share=0.0

## prior_plus_support_content_only
- Q1: score=3, flags=high_admitted_count,high_unknown_lane_ratio, unknown_lane_ratio=1.0, support_burial_depth=None, support_token_share=0.0
- Q3: score=3, flags=high_admitted_count,high_unknown_lane_ratio, unknown_lane_ratio=1.0, support_burial_depth=None, support_token_share=0.0
- Q5: score=2, flags=high_admitted_count,high_unknown_lane_ratio,support_buried_after_rank_20, unknown_lane_ratio=0.8864, support_burial_depth=36, support_token_share=0.2393

## prior_plus_support_content_plus_lexical_hints
- Q1: score=3, flags=high_admitted_count,high_unknown_lane_ratio, unknown_lane_ratio=1.0, support_burial_depth=None, support_token_share=0.0
- Q3: score=3, flags=high_admitted_count,high_unknown_lane_ratio, unknown_lane_ratio=1.0, support_burial_depth=None, support_token_share=0.0
- Q5: score=2, flags=high_admitted_count,high_unknown_lane_ratio,support_buried_after_rank_20, unknown_lane_ratio=0.907, support_burial_depth=26, support_token_share=0.2446

## PR47-target baseline metrics
- Reduce unknown_lane_ratio.
- Reduce support_burial_depth where support is expected.
- Increase support_token_share for support-driven prompts.
- Preserve required-group hits and current pass/fail behavior.