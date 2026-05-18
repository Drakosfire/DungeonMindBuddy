# PR53 Packet Quality Metrics Report

```json
{
  "schema": "dmb_pr53_packet_quality_summary_v1",
  "by_mode": {
    "prior_only": {
      "total_rows": 3,
      "average_admitted_count": 43.333333333333336,
      "average_rendered_tokens": 1676.0,
      "average_unknown_lane_ratio": 0.0,
      "support_burial_count": 0,
      "prior_only_support_leakage_count": 0,
      "known_gaps_not_near_top_count": 0,
      "eval_source_leakage_count": 0,
      "navigation_only_evidence_risk_count": 0,
      "average_llm_usability_score": 4.0,
      "worst_rows_by_flags": [
        {
          "question_id": "q01_who_are_the_npcs_the_players_encountered",
          "question_number": 1,
          "flag_count": 1,
          "flags": [
            "high_admitted_count"
          ]
        },
        {
          "question_id": "q03_how_far_away_is_mirathorn_at_this_point",
          "question_number": 3,
          "flag_count": 1,
          "flags": [
            "high_admitted_count"
          ]
        },
        {
          "question_id": "q05_there_is_a_gigantic_tree_growing_in_hemp",
          "question_number": 5,
          "flag_count": 1,
          "flags": [
            "high_admitted_count"
          ]
        }
      ]
    },
    "prior_plus_support_content_only": {
      "total_rows": 3,
      "average_admitted_count": 38.0,
      "average_rendered_tokens": 1528.0,
      "average_unknown_lane_ratio": 0.0,
      "support_burial_count": 1,
      "prior_only_support_leakage_count": 0,
      "known_gaps_not_near_top_count": 0,
      "eval_source_leakage_count": 0,
      "navigation_only_evidence_risk_count": 0,
      "average_llm_usability_score": 4.0,
      "worst_rows_by_flags": [
        {
          "question_id": "q01_who_are_the_npcs_the_players_encountered",
          "question_number": 1,
          "flag_count": 1,
          "flags": [
            "high_admitted_count"
          ]
        },
        {
          "question_id": "q03_how_far_away_is_mirathorn_at_this_point",
          "question_number": 3,
          "flag_count": 1,
          "flags": [
            "high_admitted_count"
          ]
        },
        {
          "question_id": "q05_there_is_a_gigantic_tree_growing_in_hemp",
          "question_number": 5,
          "flag_count": 1,
          "flags": [
            "support_buried_after_rank_20"
          ]
        }
      ]
    },
    "prior_plus_support_content_plus_lexical_hints": {
      "total_rows": 3,
      "average_admitted_count": 38.0,
      "average_rendered_tokens": 1582.6666666666667,
      "average_unknown_lane_ratio": 0.0,
      "support_burial_count": 1,
      "prior_only_support_leakage_count": 0,
      "known_gaps_not_near_top_count": 0,
      "eval_source_leakage_count": 0,
      "navigation_only_evidence_risk_count": 0,
      "average_llm_usability_score": 4.0,
      "worst_rows_by_flags": [
        {
          "question_id": "q01_who_are_the_npcs_the_players_encountered",
          "question_number": 1,
          "flag_count": 1,
          "flags": [
            "high_admitted_count"
          ]
        },
        {
          "question_id": "q03_how_far_away_is_mirathorn_at_this_point",
          "question_number": 3,
          "flag_count": 1,
          "flags": [
            "high_admitted_count"
          ]
        },
        {
          "question_id": "q05_there_is_a_gigantic_tree_growing_in_hemp",
          "question_number": 5,
          "flag_count": 1,
          "flags": [
            "support_buried_after_rank_20"
          ]
        }
      ]
    }
  }
}
```
