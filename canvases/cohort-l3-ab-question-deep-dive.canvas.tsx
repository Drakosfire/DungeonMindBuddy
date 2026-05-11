import React from "react";

// BEGIN GENERATED COHORT_L3_QUESTION_DEEP_DIVE
const cohortL3QuestionDeepDiveGenerated = {
  "schema_id": "dmb_breadcrumb_query_cohort_l3_question_delta_v1",
  "cohort_manifest": "evals/sentence_routing_retrieval_falsification/cohorts/c1s1_to_c1s3_v1.json",
  "scenario_level_delta_path": "evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s1_to_c1s3_v1.json",
  "baseline_schema": "dmb_breadcrumb_query_cohort_summary_v2",
  "question_count": 44,
  "summary": {
    "regressed": 2,
    "improved": 0,
    "unchanged_pass": 42,
    "unchanged_fail": 0
  },
  "scenarios": [
    {
      "scenario_id": "c1s1",
      "question_count": 16,
      "baseline_pass_count": 16,
      "with_equivalence_pass_count": 15,
      "questions": [
        {
          "question_id": "c1s1_party_roster_origin",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Baergrom",
              "Bonogo",
              "Caelynn",
              "Ephanna",
              "Karsemine",
              "Stafl",
              "Stonebridge",
              "merchant"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Parties/party_merchant_guards",
                "matched": true
              },
              {
                "substring": "Campaign 1/PCs/karsemine",
                "matched": true
              },
              {
                "substring": "Campaign 1/PCs/baergrom",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0003-01",
                "score": 15,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:guard",
                  "lexical_token:merchant",
                  "lexical_token:stonebridge",
                  "route_token:guard",
                  "route_token:merchant",
                  "route_token:party",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0005-03",
                "score": 12,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:guard",
                  "route_token:merchant",
                  "route_token:party",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0009-03",
                "score": 10,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:group",
                  "route_token:guard",
                  "route_token:merchant",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 10,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:group",
                  "route_token:guard",
                  "route_token:merchant",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0009-01",
                "score": 9,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:guard",
                  "route_token:merchant",
                  "route_token:party"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Baergrom",
              "Bonogo",
              "Caelynn",
              "Ephanna",
              "Karsemine",
              "Stafl",
              "Stonebridge",
              "merchant"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Parties/party_merchant_guards",
                "matched": true
              },
              {
                "substring": "Campaign 1/PCs/karsemine",
                "matched": true
              },
              {
                "substring": "Campaign 1/PCs/baergrom",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0003-01",
                "score": 18,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:guard",
                  "lexical_token:merchant",
                  "lexical_token:stonebridge",
                  "route_token:guard",
                  "route_token:longmont",
                  "route_token:merchant",
                  "route_token:party",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0005-03",
                "score": 18,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:guard",
                  "route_token:longmont",
                  "route_token:merchant",
                  "route_token:npc",
                  "route_token:party",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0009-01",
                "score": 15,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:guard",
                  "route_token:longmont",
                  "route_token:merchant",
                  "route_token:npc",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0013-01",
                "score": 15,
                "line_start": 13,
                "line_end": 13,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:guard",
                  "route_token:longmont",
                  "route_token:merchant",
                  "route_token:npc",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0009-03",
                "score": 13,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:group",
                  "route_token:guard",
                  "route_token:longmont",
                  "route_token:merchant",
                  "route_token:party"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0013-01"
            ],
            "topk_units_swapped_out": [
              "u-L0011-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s1_party_classes_species",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Bard",
              "Bugbear",
              "Dwarf",
              "Fighter",
              "Kenku",
              "Ranger",
              "Rogue",
              "Sorcerer",
              "Tiefling",
              "Warlock"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/PCs/karsemine",
                "matched": true
              },
              {
                "substring": "Campaign 1/PCs/stafl",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0013-03",
                "score": 4,
                "line_start": 13,
                "line_end": 13,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:each",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0015-01",
                "score": 4,
                "line_start": 15,
                "line_end": 15,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:first",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0003-01",
                "score": 3,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0005-03",
                "score": 3,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0009-01",
                "score": 3,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:party"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Bard",
              "Bugbear",
              "Dwarf",
              "Fighter",
              "Kenku",
              "Ranger",
              "Rogue",
              "Sorcerer",
              "Tiefling",
              "Warlock"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/PCs/karsemine",
                "matched": true
              },
              {
                "substring": "Campaign 1/PCs/stafl",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0005-03",
                "score": 9,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0009-01",
                "score": 9,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0013-01",
                "score": 9,
                "line_start": 13,
                "line_end": 13,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0013-03",
                "score": 7,
                "line_start": 13,
                "line_end": 13,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:each",
                  "route_token:longmont",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0015-01",
                "score": 7,
                "line_start": 15,
                "line_end": 15,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:first",
                  "route_token:longmont",
                  "route_token:party"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0013-01"
            ],
            "topk_units_swapped_out": [
              "u-L0003-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s1_stonebridge_known_for",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Glowkindle",
              "Grishna",
              "Stonebridge",
              "job",
              "rats",
              "river"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Locations/stonebridge",
                "matched": true
              },
              {
                "substring": "Campaign 1/NPCs/grishna",
                "matched": true
              },
              {
                "substring": "Campaign 1/NPCs/glowkindle",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "meta-session-0001-locations",
                "score": 9,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:campaign",
                  "lexical_token:start",
                  "lexical_token:stonebridge",
                  "route_token:campaign",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 8,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/"
                ],
                "why_matched": [
                  "lexical_token:known",
                  "lexical_token:stonebridge",
                  "route_token:campaign",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0003-01",
                "score": 7,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:stonebridge",
                  "route_token:campaign",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0005-02",
                "score": 7,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "lexical_token:stonebridge",
                  "route_token:campaign",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0005-03",
                "score": 6,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:campaign",
                  "route_token:stonebridge"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Glowkindle",
              "Grishna",
              "Stonebridge",
              "job",
              "rats",
              "river"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Locations/stonebridge",
                "matched": true
              },
              {
                "substring": "Campaign 1/NPCs/grishna",
                "matched": true
              },
              {
                "substring": "Campaign 1/NPCs/glowkindle",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "meta-session-0001-locations",
                "score": 13,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:campaign",
                  "lexical_token:longmont",
                  "lexical_token:start",
                  "lexical_token:stonebridge",
                  "route_token:campaign",
                  "route_token:longmont",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0005-02",
                "score": 13,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "lexical_token:stonebridge",
                  "route_token:campaign",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0005-03",
                "score": 12,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:campaign",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 11,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/"
                ],
                "why_matched": [
                  "lexical_token:known",
                  "lexical_token:stonebridge",
                  "route_token:campaign",
                  "route_token:longmont",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0003-01",
                "score": 10,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:stonebridge",
                  "route_token:campaign",
                  "route_token:longmont",
                  "route_token:stonebridge"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [],
            "topk_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s1_glowkindle_job_source",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Glowkindle",
              "fermentation",
              "mercenaries",
              "rats"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/glowkindle",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/wizards_tower_brewing_company",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0005-03",
                "score": 4,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:help",
                  "lexical_token:job",
                  "lexical_token:need",
                  "lexical_token:posted"
                ]
              },
              {
                "unit_id": "u-L0013-04",
                "score": 1,
                "line_start": 13,
                "line_end": 13,
                "routes": [],
                "why_matched": [
                  "lexical_token:help"
                ]
              },
              {
                "unit_id": "u-L0015-01",
                "score": 1,
                "line_start": 15,
                "line_end": 15,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:first"
                ]
              },
              {
                "unit_id": "u-L0017-01",
                "score": 0,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0017-01"
                ]
              },
              {
                "unit_id": "u-L0017-02",
                "score": 0,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0017-02"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Glowkindle",
              "fermentation",
              "mercenaries",
              "rats"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/glowkindle",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/wizards_tower_brewing_company",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0005-03",
                "score": 10,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:help",
                  "lexical_token:job",
                  "lexical_token:need",
                  "lexical_token:posted",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0005-02",
                "score": 6,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 6,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0009-01",
                "score": 6,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0013-01",
                "score": 6,
                "line_start": 13,
                "line_end": 13,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0005-02",
              "u-L0007-01",
              "u-L0009-01",
              "u-L0013-01"
            ],
            "topk_units_swapped_out": [
              "u-L0013-04",
              "u-L0015-01",
              "u-L0017-01",
              "u-L0017-02"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s1_grishna_directions",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Grishna",
              "boulder",
              "brewing"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/grishna",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/rivers_edge_pub",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/wizards_tower_brewing_company",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0009-01",
                "score": 7,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:grishna",
                  "route_token:grishna",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0005-02",
                "score": 5,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "lexical_token:about",
                  "lexical_token:grishna",
                  "route_token:grishna"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 4,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:grishna",
                  "route_token:grishna"
                ]
              },
              {
                "unit_id": "u-L0013-01",
                "score": 4,
                "line_start": 13,
                "line_end": 13,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:about",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0003-01",
                "score": 3,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:party"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Grishna",
              "boulder",
              "brewing"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/grishna",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/rivers_edge_pub",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/wizards_tower_brewing_company",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0009-01",
                "score": 13,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:grishna",
                  "route_token:grishna",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0005-02",
                "score": 11,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "lexical_token:about",
                  "lexical_token:grishna",
                  "route_token:grishna",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 10,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:grishna",
                  "route_token:grishna",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0013-01",
                "score": 10,
                "line_start": 13,
                "line_end": 13,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:about",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0005-03",
                "score": 9,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:party"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0005-03"
            ],
            "topk_units_swapped_out": [
              "u-L0003-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s1_brewery_compass_direction",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Grishna",
              "brewing",
              "up river",
              "west"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/grishna",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/stonebridge",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/wizards_tower_brewing_company",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0005-02",
                "score": 8,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "lexical_token:grishna",
                  "lexical_token:stonebridge",
                  "route_token:grishna",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "meta-session-0001-locations",
                "score": 6,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:brewery",
                  "lexical_token:grishna",
                  "lexical_token:stonebridge",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0009-01",
                "score": 5,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:direction",
                  "lexical_token:grishna",
                  "route_token:grishna"
                ]
              },
              {
                "unit_id": "u-L0003-01",
                "score": 4,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:stonebridge",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 4,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/"
                ],
                "why_matched": [
                  "lexical_token:stonebridge",
                  "route_token:stonebridge"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "context_support_below_threshold",
              "semantic_verdict:fail_incomplete"
            ],
            "context_support_ratio": 0.5,
            "context_must_hits": [
              "Grishna",
              "brewing"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/grishna",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/stonebridge",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/wizards_tower_brewing_company",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0005-02",
                "score": 14,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "lexical_token:grishna",
                  "lexical_token:stonebridge",
                  "route_token:grishna",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0009-01",
                "score": 11,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:direction",
                  "lexical_token:grishna",
                  "route_token:grishna",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "meta-session-0001-locations",
                "score": 10,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:brewery",
                  "lexical_token:grishna",
                  "lexical_token:longmont",
                  "lexical_token:stonebridge",
                  "route_token:longmont",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 10,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:grishna",
                  "route_token:grishna",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0005-03",
                "score": 9,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:stonebridge"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "regressed",
            "support_ratio_delta": -0.5,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0005-03",
              "u-L0007-01"
            ],
            "topk_units_swapped_out": [
              "u-L0003-01",
              "u-L0005-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s1_bonogo_firkin",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Bonogo",
              "ale",
              "firkin",
              "gold"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/PCs/bonogo",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/rivers_edge_pub",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0003-01",
                "score": 4,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:bonogo",
                  "route_token:bonogo"
                ]
              },
              {
                "unit_id": "u-L0007-03",
                "score": 4,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:bonogo",
                  "route_token:bonogo"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 3,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "route_token:bonogo"
                ]
              },
              {
                "unit_id": "u-L0007-02",
                "score": 3,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "route_token:bonogo"
                ]
              },
              {
                "unit_id": "u-L0007-04",
                "score": 2,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:brewery",
                  "lexical_token:hike"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Bonogo",
              "ale",
              "firkin",
              "gold"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/PCs/bonogo",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/rivers_edge_pub",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0007-01",
                "score": 9,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "route_token:bonogo",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0003-01",
                "score": 7,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:bonogo",
                  "route_token:bonogo",
                  "route_token:longmont"
                ]
              },
              {
                "unit_id": "u-L0007-03",
                "score": 7,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:bonogo",
                  "route_token:bonogo",
                  "route_token:longmont"
                ]
              },
              {
                "unit_id": "u-L0005-02",
                "score": 6,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0005-03",
                "score": 6,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0005-02",
              "u-L0005-03"
            ],
            "topk_units_swapped_out": [
              "u-L0007-02",
              "u-L0007-04"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s1_route_to_brewery",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 0.6666666666666666,
            "context_must_hits": [
              "brewing",
              "trail"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Parties/party_merchant_guards",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/stonebridge",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/wizards_tower_brewing_company",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "meta-session-0001-locations",
                "score": 20,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:brewing",
                  "lexical_token:company",
                  "lexical_token:stonebridge",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:brewing",
                  "route_token:company",
                  "route_token:stonebridge",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 17,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:brewing",
                  "lexical_token:company",
                  "lexical_token:group",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:brewing",
                  "route_token:company",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 15,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:brewing",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:brewing",
                  "route_token:company",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0007-03",
                "score": 12,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "route_token:brewing",
                  "route_token:company",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0007-04",
                "score": 12,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "route_token:brewing",
                  "route_token:company",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "boulder",
              "brewing",
              "trail"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Parties/party_merchant_guards",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/stonebridge",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/wizards_tower_brewing_company",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "meta-session-0001-locations",
                "score": 24,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:brewing",
                  "lexical_token:company",
                  "lexical_token:longmont",
                  "lexical_token:stonebridge",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:brewing",
                  "route_token:company",
                  "route_token:longmont",
                  "route_token:stonebridge",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 21,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:brewing",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:brewing",
                  "route_token:company",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 20,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:brewing",
                  "lexical_token:company",
                  "lexical_token:group",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:brewing",
                  "route_token:company",
                  "route_token:longmont",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0007-03",
                "score": 15,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "route_token:brewing",
                  "route_token:company",
                  "route_token:longmont",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0007-04",
                "score": 15,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "route_token:brewing",
                  "route_token:company",
                  "route_token:longmont",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.3333,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [],
            "topk_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s1_stone_foot_landmark",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "foot"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Locations/wizards_tower_brewing_company",
                "matched": true
              },
              {
                "substring": "Campaign 1/Parties/party_merchant_guards",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0007-02",
                "score": 2,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:big",
                  "lexical_token:rock"
                ]
              },
              {
                "unit_id": "meta-session-0001-locations",
                "score": 1,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:brewery"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 1,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:way"
                ]
              },
              {
                "unit_id": "u-L0007-04",
                "score": 1,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:brewery"
                ]
              },
              {
                "unit_id": "u-L0009-04",
                "score": 1,
                "line_start": 9,
                "line_end": 9,
                "routes": [],
                "why_matched": [
                  "lexical_token:way"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "foot"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Locations/wizards_tower_brewing_company",
                "matched": true
              },
              {
                "substring": "Campaign 1/Parties/party_merchant_guards",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0007-01",
                "score": 7,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:way",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0005-02",
                "score": 6,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0005-03",
                "score": 6,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0009-01",
                "score": 6,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0013-01",
                "score": 6,
                "line_start": 13,
                "line_end": 13,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0005-02",
              "u-L0005-03",
              "u-L0009-01",
              "u-L0013-01"
            ],
            "topk_units_swapped_out": [
              "meta-session-0001-locations",
              "u-L0007-02",
              "u-L0007-04",
              "u-L0009-04"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s1_brewery_arrival",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "brewing",
              "bustling",
              "crystals",
              "gnomes"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Locations/wizards_tower_brewing_company",
                "matched": true
              },
              {
                "substring": "Campaign 1/NPCs/glowkindle",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0011-01",
                "score": 17,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:brewing",
                  "lexical_token:company",
                  "lexical_token:group",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:brewing",
                  "route_token:company",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "meta-session-0001-locations",
                "score": 16,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:brewing",
                  "lexical_token:company",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:brewing",
                  "route_token:company",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 15,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:brewing",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:brewing",
                  "route_token:company",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0007-03",
                "score": 12,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "route_token:brewing",
                  "route_token:company",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0007-04",
                "score": 12,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "route_token:brewing",
                  "route_token:company",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "brewing",
              "bustling",
              "crystals",
              "gnomes"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Locations/wizards_tower_brewing_company",
                "matched": true
              },
              {
                "substring": "Campaign 1/NPCs/glowkindle",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0007-01",
                "score": 21,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:brewing",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:brewing",
                  "route_token:company",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "meta-session-0001-locations",
                "score": 20,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:brewing",
                  "lexical_token:company",
                  "lexical_token:longmont",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:brewing",
                  "route_token:company",
                  "route_token:longmont",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 20,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:brewing",
                  "lexical_token:company",
                  "lexical_token:group",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:brewing",
                  "route_token:company",
                  "route_token:longmont",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0007-03",
                "score": 15,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "route_token:brewing",
                  "route_token:company",
                  "route_token:longmont",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0007-04",
                "score": 15,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "route_token:brewing",
                  "route_token:company",
                  "route_token:longmont",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [],
            "topk_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s1_glowkindle_offer",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "25",
              "Glowkindle",
              "gold",
              "rats"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/glowkindle",
                "matched": true
              },
              {
                "substring": "Campaign 1/Parties/party_merchant_guards",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0005-03",
                "score": 5,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:glowkindle",
                  "lexical_token:rats",
                  "route_token:glowkindle"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 4,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:glowkindle",
                  "route_token:glowkindle"
                ]
              },
              {
                "unit_id": "u-L0013-01",
                "score": 4,
                "line_start": 13,
                "line_end": 13,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:glowkindle",
                  "route_token:glowkindle"
                ]
              },
              {
                "unit_id": "u-L0005-02",
                "score": 3,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "route_token:glowkindle"
                ]
              },
              {
                "unit_id": "meta-session-0001-locations",
                "score": 2,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:clearing",
                  "lexical_token:glowkindle"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "25",
              "Glowkindle",
              "gold",
              "rats"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/glowkindle",
                "matched": true
              },
              {
                "substring": "Campaign 1/Parties/party_merchant_guards",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0005-03",
                "score": 11,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:glowkindle",
                  "lexical_token:rats",
                  "route_token:glowkindle",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 10,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:glowkindle",
                  "route_token:glowkindle",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0013-01",
                "score": 10,
                "line_start": 13,
                "line_end": 13,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:glowkindle",
                  "route_token:glowkindle",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0005-02",
                "score": 9,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "route_token:glowkindle",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "meta-session-0001-locations",
                "score": 6,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:clearing",
                  "lexical_token:glowkindle",
                  "lexical_token:longmont",
                  "route_token:longmont"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [],
            "topk_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s1_rat_incident_origin",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "cellar",
              "excavation",
              "rats",
              "wall"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/glowkindle",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/wizards_tower_brewing_company",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "meta-session-0001-locations",
                "score": 2,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:brewery",
                  "lexical_token:rat"
                ]
              },
              {
                "unit_id": "u-L0013-02",
                "score": 2,
                "line_start": 13,
                "line_end": 13,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:giant",
                  "lexical_token:rat"
                ]
              },
              {
                "unit_id": "u-L0005-03",
                "score": 1,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:rat"
                ]
              },
              {
                "unit_id": "u-L0007-04",
                "score": 1,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:brewery"
                ]
              },
              {
                "unit_id": "u-L0013-03",
                "score": 1,
                "line_start": 13,
                "line_end": 13,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:rat"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "cellar",
              "excavation",
              "rats",
              "wall"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/glowkindle",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/wizards_tower_brewing_company",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0005-03",
                "score": 7,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:rat",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "meta-session-0001-locations",
                "score": 6,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:brewery",
                  "lexical_token:longmont",
                  "lexical_token:rat",
                  "route_token:longmont"
                ]
              },
              {
                "unit_id": "u-L0005-02",
                "score": 6,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 6,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0009-01",
                "score": 6,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0005-02",
              "u-L0007-01",
              "u-L0009-01"
            ],
            "topk_units_swapped_out": [
              "u-L0007-04",
              "u-L0013-02",
              "u-L0013-03"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s1_first_combat_cost",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "blood",
              "cat owl",
              "harder",
              "potions"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Parties/party_merchant_guards",
                "matched": true
              },
              {
                "substring": "Campaign 1/PCs/karsemine",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0013-02",
                "score": 5,
                "line_start": 13,
                "line_end": 13,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:rats",
                  "lexical_token:rough",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0015-01",
                "score": 5,
                "line_start": 15,
                "line_end": 15,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:combat",
                  "lexical_token:first",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0005-03",
                "score": 4,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:rats",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0013-03",
                "score": 4,
                "line_start": 13,
                "line_end": 13,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:rats",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0003-01",
                "score": 3,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:party"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "blood",
              "cat owl",
              "harder",
              "potions"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Parties/party_merchant_guards",
                "matched": true
              },
              {
                "substring": "Campaign 1/PCs/karsemine",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0005-03",
                "score": 10,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:rats",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0009-01",
                "score": 9,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0013-01",
                "score": 9,
                "line_start": 13,
                "line_end": 13,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0013-02",
                "score": 8,
                "line_start": 13,
                "line_end": 13,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:rats",
                  "lexical_token:rough",
                  "route_token:longmont",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0015-01",
                "score": 8,
                "line_start": 15,
                "line_end": 15,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:combat",
                  "lexical_token:first",
                  "route_token:longmont",
                  "route_token:party"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0009-01",
              "u-L0013-01"
            ],
            "topk_units_swapped_out": [
              "u-L0003-01",
              "u-L0013-03"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s1_post_combat_exploration",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "alchemical",
              "hallway",
              "mosaic"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Parties/party_merchant_guards",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/wizards_tower_brewing_company",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0017-01",
                "score": 3,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:explore",
                  "lexical_token:free",
                  "lexical_token:team"
                ]
              },
              {
                "unit_id": "u-L0003-01",
                "score": 1,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:after"
                ]
              },
              {
                "unit_id": "u-L0009-01",
                "score": 1,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:were"
                ]
              },
              {
                "unit_id": "u-L0013-02",
                "score": 1,
                "line_start": 13,
                "line_end": 13,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:after"
                ]
              },
              {
                "unit_id": "u-L0013-03",
                "score": 1,
                "line_start": 13,
                "line_end": 13,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:team"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "alchemical",
              "hallway",
              "mosaic"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Parties/party_merchant_guards",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/wizards_tower_brewing_company",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0009-01",
                "score": 7,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:were",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0005-02",
                "score": 6,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0005-03",
                "score": 6,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 6,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0013-01",
                "score": 6,
                "line_start": 13,
                "line_end": 13,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0005-02",
              "u-L0005-03",
              "u-L0007-01",
              "u-L0013-01"
            ],
            "topk_units_swapped_out": [
              "u-L0003-01",
              "u-L0013-02",
              "u-L0013-03",
              "u-L0017-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s1_karsemine_spider_reveal",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Karsemine",
              "magma",
              "spider"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/PCs/karsemine",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/shatter_mages_tower",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0017-02",
                "score": 5,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/"
                ],
                "why_matched": [
                  "lexical_token:karsemine",
                  "lexical_token:room",
                  "route_token:karsemine"
                ]
              },
              {
                "unit_id": "u-L0003-01",
                "score": 4,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:karsemine",
                  "route_token:karsemine"
                ]
              },
              {
                "unit_id": "u-L0017-01",
                "score": 4,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:room",
                  "route_token:karsemine"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 1,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:while"
                ]
              },
              {
                "unit_id": "u-L0011-02",
                "score": 1,
                "line_start": 11,
                "line_end": 11,
                "routes": [],
                "why_matched": [
                  "lexical_token:room"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Karsemine",
              "magma",
              "spider"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/PCs/karsemine",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/shatter_mages_tower",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0017-02",
                "score": 8,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/"
                ],
                "why_matched": [
                  "lexical_token:karsemine",
                  "lexical_token:room",
                  "route_token:karsemine",
                  "route_token:longmont"
                ]
              },
              {
                "unit_id": "u-L0003-01",
                "score": 7,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:karsemine",
                  "route_token:karsemine",
                  "route_token:longmont"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 7,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:while",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-01",
                "score": 7,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:room",
                  "route_token:karsemine",
                  "route_token:longmont"
                ]
              },
              {
                "unit_id": "u-L0005-02",
                "score": 6,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0005-02"
            ],
            "topk_units_swapped_out": [
              "u-L0011-02"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s1_final_threat",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 0.6666666666666666,
            "context_must_hits": [
              "magma",
              "spider"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Locations/shatter_mages_tower",
                "matched": true
              },
              {
                "substring": "Campaign 1/PCs/karsemine",
                "matched": true
              }
            ],
            "hit_count": 10,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "meta-session-0001-locations",
                "score": 1,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:threat"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 0,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0005-01"
                ]
              },
              {
                "unit_id": "u-L0005-02",
                "score": 0,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0005-02"
                ]
              },
              {
                "unit_id": "u-L0005-03",
                "score": 0,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0005-03"
                ]
              },
              {
                "unit_id": "u-L0003-01",
                "score": 0,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0003-01"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 0.6666666666666666,
            "context_must_hits": [
              "magma",
              "spider"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Locations/shatter_mages_tower",
                "matched": true
              },
              {
                "substring": "Campaign 1/PCs/karsemine",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0005-02",
                "score": 6,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0005-03",
                "score": 6,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 6,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0009-01",
                "score": 6,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0013-01",
                "score": 6,
                "line_start": 13,
                "line_end": 13,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/",
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0007-01",
              "u-L0009-01",
              "u-L0013-01"
            ],
            "topk_units_swapped_out": [
              "meta-session-0001-locations",
              "u-L0003-01",
              "u-L0005-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        }
      ]
    },
    {
      "scenario_id": "c1s2",
      "question_count": 15,
      "baseline_pass_count": 15,
      "with_equivalence_pass_count": 15,
      "questions": [
        {
          "question_id": "c1s2_threat_inventory",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Centipede",
              "Spider",
              "mutate",
              "rats",
              "well"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Parties/party_merchant_guards",
                "matched": true
              },
              {
                "substring": "Campaign 1/NPCs/magma_spider",
                "matched": true
              },
              {
                "substring": "Campaign 1/NPCs/giant_centipede_well",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0003-02",
                "score": 4,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/",
                  "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
                ],
                "why_matched": [
                  "lexical_token:big",
                  "lexical_token:deal",
                  "lexical_token:rat",
                  "lexical_token:were"
                ]
              },
              {
                "unit_id": "u-L0009-01",
                "score": 3,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:clearing",
                  "lexical_token:rat"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 2,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:clearing"
                ]
              },
              {
                "unit_id": "u-L0011-02",
                "score": 1,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "lexical_token:say"
                ]
              },
              {
                "unit_id": "u-L0011-03",
                "score": 0,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0011-03"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Centipede",
              "Spider",
              "mutate",
              "rats",
              "well"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Parties/party_merchant_guards",
                "matched": true
              },
              {
                "substring": "Campaign 1/NPCs/magma_spider",
                "matched": true
              },
              {
                "substring": "Campaign 1/NPCs/giant_centipede_well",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0003-02",
                "score": 10,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/",
                  "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
                ],
                "why_matched": [
                  "lexical_token:big",
                  "lexical_token:deal",
                  "lexical_token:rat",
                  "lexical_token:were",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0011-02",
                "score": 7,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "lexical_token:say",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 6,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0009-01",
                "score": 6,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:clearing",
                  "lexical_token:rat",
                  "route_token:longmont"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 6,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0007-01",
              "u-L0011-01"
            ],
            "topk_units_swapped_out": [
              "u-L0005-01",
              "u-L0011-03"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s2_basement_clearing_payoff",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "alchemical",
              "gems",
              "healing",
              "potions",
              "wall",
              "well"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Locations/wizards_tower_brewing_company",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0005-01",
                "score": 11,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:basement",
                  "lexical_token:clearing",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "meta-session-0002-locations",
                "score": 10,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:basement",
                  "lexical_token:more",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0011-03",
                "score": 9,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:more",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0005-02",
                "score": 7,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:find",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0011-02",
                "score": 6,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "route_token:tower",
                  "route_token:wizard"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "alchemical",
              "gems",
              "healing",
              "potions",
              "wall",
              "well"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Locations/wizards_tower_brewing_company",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "meta-session-0002-locations",
                "score": 14,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:basement",
                  "lexical_token:longmont",
                  "lexical_token:more",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:longmont",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 14,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:basement",
                  "lexical_token:clearing",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:longmont",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0011-02",
                "score": 12,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0011-03",
                "score": 12,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:more",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:longmont",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0005-02",
                "score": 10,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:find",
                  "route_token:longmont",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [],
            "topk_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s2_glowkindle_stash_deal",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Glowkindle",
              "alchemy",
              "contract",
              "stash"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/glowkindle",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0007-01",
                "score": 5,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "lexical_token:glowkindle",
                  "lexical_token:negotiate",
                  "route_token:glowkindle"
                ]
              },
              {
                "unit_id": "u-L0009-01",
                "score": 4,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:about",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 4,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "lexical_token:glowkindle",
                  "route_token:glowkindle"
                ]
              },
              {
                "unit_id": "u-L0003-01",
                "score": 3,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0003-02",
                "score": 1,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/",
                  "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
                ],
                "why_matched": [
                  "lexical_token:about"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Glowkindle",
              "alchemy",
              "contract",
              "stash"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/glowkindle",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0007-01",
                "score": 11,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "lexical_token:glowkindle",
                  "lexical_token:negotiate",
                  "route_token:glowkindle",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 10,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "lexical_token:glowkindle",
                  "route_token:glowkindle",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0003-02",
                "score": 7,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/",
                  "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
                ],
                "why_matched": [
                  "lexical_token:about",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0009-01",
                "score": 7,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:about",
                  "route_token:longmont",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0003-01",
                "score": 6,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:party"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [],
            "topk_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s2_god_forsaken_scope",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "contract",
              "forsaken"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/glowkindle",
                "matched": true
              }
            ],
            "hit_count": 9,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0007-01",
                "score": 2,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "lexical_token:contract",
                  "lexical_token:original"
                ]
              },
              {
                "unit_id": "u-L0007-02",
                "score": 0,
                "line_start": 7,
                "line_end": 7,
                "routes": [],
                "why_matched": [
                  "expanded_adjacent:u-L0007-02"
                ]
              },
              {
                "unit_id": "u-L0009-01",
                "score": 0,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0009-01"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 0,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0005-01"
                ]
              },
              {
                "unit_id": "u-L0005-02",
                "score": 0,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0005-02"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "contract",
              "forsaken"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/glowkindle",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0007-01",
                "score": 8,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "lexical_token:contract",
                  "lexical_token:original",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0003-02",
                "score": 6,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/",
                  "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 6,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0011-02",
                "score": 6,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "meta-session-0002-locations",
                "score": 4,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:longmont",
                  "route_token:longmont"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "meta-session-0002-locations",
              "u-L0003-02",
              "u-L0011-01",
              "u-L0011-02"
            ],
            "topk_units_swapped_out": [
              "u-L0005-01",
              "u-L0005-02",
              "u-L0007-02",
              "u-L0009-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s2_pay_and_loot_summary",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "25",
              "gp",
              "loot"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Parties/party_merchant_guards",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0009-01",
                "score": 5,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:each",
                  "lexical_token:money",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0003-01",
                "score": 3,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 1,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:away"
                ]
              },
              {
                "unit_id": "u-L0007-02",
                "score": 1,
                "line_start": 7,
                "line_end": 7,
                "routes": [],
                "why_matched": [
                  "lexical_token:much"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 0,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0011-01"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "25",
              "gp",
              "loot"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Parties/party_merchant_guards",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0009-01",
                "score": 8,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:each",
                  "lexical_token:money",
                  "route_token:longmont",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0003-01",
                "score": 6,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0003-02",
                "score": 6,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/",
                  "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 6,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 6,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0003-02",
              "u-L0007-01"
            ],
            "topk_units_swapped_out": [
              "u-L0005-01",
              "u-L0007-02"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s2_party_commitment",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "stick together",
              "winds"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Parties/party_merchant_guards",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0009-01",
                "score": 5,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:about",
                  "lexical_token:after",
                  "lexical_token:decide",
                  "lexical_token:group",
                  "lexical_token:together"
                ]
              },
              {
                "unit_id": "u-L0003-02",
                "score": 1,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/",
                  "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
                ],
                "why_matched": [
                  "lexical_token:about"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 1,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:after"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 0,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0011-01"
                ]
              },
              {
                "unit_id": "u-L0011-02",
                "score": 0,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0011-02"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "stick together",
              "winds"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Parties/party_merchant_guards",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0009-01",
                "score": 8,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:about",
                  "lexical_token:after",
                  "lexical_token:decide",
                  "lexical_token:group",
                  "lexical_token:together",
                  "route_token:longmont"
                ]
              },
              {
                "unit_id": "u-L0003-02",
                "score": 7,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/",
                  "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
                ],
                "why_matched": [
                  "lexical_token:about",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 6,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 6,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0011-02",
                "score": 6,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0007-01"
            ],
            "topk_units_swapped_out": [
              "u-L0005-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s2_basement_lesson",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "basements",
              "dangers",
              "rats"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Parties/party_merchant_guards",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0009-01",
                "score": 7,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:basements",
                  "lexical_token:clearing",
                  "lexical_token:out",
                  "lexical_token:rats",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0003-01",
                "score": 3,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0003-02",
                "score": 2,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/",
                  "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
                ],
                "why_matched": [
                  "lexical_token:out",
                  "lexical_token:rats"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 1,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:clearing"
                ]
              },
              {
                "unit_id": "u-L0011-02",
                "score": 1,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "lexical_token:say"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "basements",
              "dangers",
              "rats"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Parties/party_merchant_guards",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0009-01",
                "score": 10,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:basements",
                  "lexical_token:clearing",
                  "lexical_token:out",
                  "lexical_token:rats",
                  "route_token:longmont",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0003-02",
                "score": 8,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/",
                  "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
                ],
                "why_matched": [
                  "lexical_token:out",
                  "lexical_token:rats",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0011-02",
                "score": 7,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "lexical_token:say",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0003-01",
                "score": 6,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:party"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 6,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0007-01"
            ],
            "topk_units_swapped_out": [
              "u-L0005-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s2_hook_more_work_glowkindle",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Glowkindle",
              "work"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/glowkindle",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0007-01",
                "score": 4,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "lexical_token:glowkindle",
                  "route_token:glowkindle"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 4,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "lexical_token:glowkindle",
                  "route_token:glowkindle"
                ]
              },
              {
                "unit_id": "u-L0003-02",
                "score": 1,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/",
                  "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
                ],
                "why_matched": [
                  "lexical_token:about"
                ]
              },
              {
                "unit_id": "u-L0009-01",
                "score": 1,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:about"
                ]
              },
              {
                "unit_id": "u-L0011-02",
                "score": 0,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0011-02"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Glowkindle",
              "work"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/glowkindle",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0007-01",
                "score": 10,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "lexical_token:glowkindle",
                  "route_token:glowkindle",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 10,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "lexical_token:glowkindle",
                  "route_token:glowkindle",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0003-02",
                "score": 7,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/",
                  "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
                ],
                "why_matched": [
                  "lexical_token:about",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0011-02",
                "score": 6,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "meta-session-0002-locations",
                "score": 4,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:longmont",
                  "route_token:longmont"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "meta-session-0002-locations"
            ],
            "topk_units_swapped_out": [
              "u-L0009-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s2_hook_stonebridge_grishna",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Grishna",
              "Pub",
              "Stonebridge"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Locations/stonebridge",
                "matched": true
              },
              {
                "substring": "Campaign 1/NPCs/grishna",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/rivers_edge_pub",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "meta-session-0002-locations",
                "score": 5,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:stonebridge",
                  "lexical_token:tease",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0011-02",
                "score": 4,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "lexical_token:stonebridge",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 3,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0011-03",
                "score": 0,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0011-03"
                ]
              },
              {
                "unit_id": "u-L0013-01",
                "score": 0,
                "line_start": 13,
                "line_end": 13,
                "routes": [],
                "why_matched": [
                  "expanded_adjacent:u-L0013-01"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Grishna",
              "Pub",
              "Stonebridge"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Locations/stonebridge",
                "matched": true
              },
              {
                "substring": "Campaign 1/NPCs/grishna",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/rivers_edge_pub",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0011-02",
                "score": 10,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "lexical_token:stonebridge",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "meta-session-0002-locations",
                "score": 9,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:longmont",
                  "lexical_token:stonebridge",
                  "lexical_token:tease",
                  "route_token:longmont",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 9,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0003-02",
                "score": 6,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/",
                  "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 6,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0003-02",
              "u-L0007-01"
            ],
            "topk_units_swapped_out": [
              "u-L0011-03",
              "u-L0013-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s2_hook_wizard_tower_thread",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Tower",
              "Wizard",
              "more"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Locations/wizards_tower_brewing_company",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "meta-session-0002-locations",
                "score": 9,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:thread",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 8,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0011-03",
                "score": 8,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0005-02",
                "score": 6,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0011-02",
                "score": 6,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "route_token:tower",
                  "route_token:wizard"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Tower",
              "Wizard",
              "more"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Locations/wizards_tower_brewing_company",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "meta-session-0002-locations",
                "score": 13,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:longmont",
                  "lexical_token:thread",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:longmont",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0011-02",
                "score": 12,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 11,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:longmont",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0011-03",
                "score": 11,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:longmont",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0005-02",
                "score": 9,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [],
            "topk_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s2_spider_beat",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Flaming",
              "Spider"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/magma_spider",
                "matched": true
              }
            ],
            "hit_count": 9,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0003-02",
                "score": 4,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/",
                  "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
                ],
                "why_matched": [
                  "lexical_token:spider",
                  "route_token:spider"
                ]
              },
              {
                "unit_id": "u-L0003-01",
                "score": 0,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0003-01"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 0,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0005-01"
                ]
              },
              {
                "unit_id": "u-L0005-02",
                "score": 0,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0005-02"
                ]
              },
              {
                "unit_id": "u-L0005-03",
                "score": 0,
                "line_start": 5,
                "line_end": 5,
                "routes": [],
                "why_matched": [
                  "expanded_adjacent:u-L0005-03"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Flaming",
              "Spider"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/magma_spider",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0003-02",
                "score": 10,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/",
                  "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
                ],
                "why_matched": [
                  "lexical_token:spider",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:spider"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 6,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 6,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0011-02",
                "score": 6,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "meta-session-0002-locations",
                "score": 4,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:longmont",
                  "route_token:longmont"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "meta-session-0002-locations",
              "u-L0007-01",
              "u-L0011-01",
              "u-L0011-02"
            ],
            "topk_units_swapped_out": [
              "u-L0003-01",
              "u-L0005-01",
              "u-L0005-02",
              "u-L0005-03"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s2_centipede_beat",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "centipede",
              "well"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/giant_centipede_well",
                "matched": true
              }
            ],
            "hit_count": 9,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0003-02",
                "score": 8,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/",
                  "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
                ],
                "why_matched": [
                  "lexical_token:centipede",
                  "lexical_token:giant",
                  "route_token:centipede",
                  "route_token:giant"
                ]
              },
              {
                "unit_id": "u-L0003-01",
                "score": 0,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0003-01"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 0,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0005-01"
                ]
              },
              {
                "unit_id": "u-L0005-02",
                "score": 0,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0005-02"
                ]
              },
              {
                "unit_id": "u-L0005-03",
                "score": 0,
                "line_start": 5,
                "line_end": 5,
                "routes": [],
                "why_matched": [
                  "expanded_adjacent:u-L0005-03"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "centipede",
              "well"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/giant_centipede_well",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0003-02",
                "score": 14,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/",
                  "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
                ],
                "why_matched": [
                  "lexical_token:centipede",
                  "lexical_token:giant",
                  "route_token:centipede",
                  "route_token:giant",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 6,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 6,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0011-02",
                "score": 6,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "meta-session-0002-locations",
                "score": 4,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:longmont",
                  "route_token:longmont"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "meta-session-0002-locations",
              "u-L0007-01",
              "u-L0011-01",
              "u-L0011-02"
            ],
            "topk_units_swapped_out": [
              "u-L0003-01",
              "u-L0005-01",
              "u-L0005-02",
              "u-L0005-03"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s2_non_mutating_rat",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "mutate",
              "rat"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Parties/party_merchant_guards",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "meta-session-0002-locations",
                "score": 4,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:one",
                  "route_token:one"
                ]
              },
              {
                "unit_id": "u-L0011-02",
                "score": 4,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "lexical_token:one",
                  "route_token:one"
                ]
              },
              {
                "unit_id": "u-L0009-01",
                "score": 3,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:about",
                  "lexical_token:one",
                  "lexical_token:rat"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 3,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "route_token:one"
                ]
              },
              {
                "unit_id": "u-L0003-02",
                "score": 2,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/",
                  "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
                ],
                "why_matched": [
                  "lexical_token:about",
                  "lexical_token:rat"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "mutate",
              "rat"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Parties/party_merchant_guards",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0011-02",
                "score": 10,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "lexical_token:one",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:one"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 9,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:one"
                ]
              },
              {
                "unit_id": "meta-session-0002-locations",
                "score": 8,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:longmont",
                  "lexical_token:one",
                  "route_token:longmont",
                  "route_token:one"
                ]
              },
              {
                "unit_id": "u-L0003-02",
                "score": 8,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/",
                  "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
                ],
                "why_matched": [
                  "lexical_token:about",
                  "lexical_token:rat",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 6,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0007-01"
            ],
            "topk_units_swapped_out": [
              "u-L0009-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s2_planning_glowkindle_followup",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Glowkindle",
              "alchemy",
              "contract",
              "stash"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/glowkindle",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0007-01",
                "score": 5,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "lexical_token:glowkindle",
                  "lexical_token:stash",
                  "route_token:glowkindle"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 4,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "lexical_token:glowkindle",
                  "route_token:glowkindle"
                ]
              },
              {
                "unit_id": "u-L0003-02",
                "score": 2,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/",
                  "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
                ],
                "why_matched": [
                  "lexical_token:about",
                  "lexical_token:deal"
                ]
              },
              {
                "unit_id": "u-L0009-01",
                "score": 1,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:about"
                ]
              },
              {
                "unit_id": "u-L0011-02",
                "score": 0,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0011-02"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Glowkindle",
              "alchemy",
              "contract",
              "stash"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/glowkindle",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0007-01",
                "score": 11,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "lexical_token:glowkindle",
                  "lexical_token:stash",
                  "route_token:glowkindle",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 10,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "lexical_token:glowkindle",
                  "route_token:glowkindle",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0003-02",
                "score": 8,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/",
                  "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
                ],
                "why_matched": [
                  "lexical_token:about",
                  "lexical_token:deal",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0011-02",
                "score": 6,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "meta-session-0002-locations",
                "score": 4,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:longmont",
                  "route_token:longmont"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "meta-session-0002-locations"
            ],
            "topk_units_swapped_out": [
              "u-L0009-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s2_prep_named_hostiles",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Centipede",
              "Spider",
              "rats",
              "well"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/magma_spider",
                "matched": true
              },
              {
                "substring": "Campaign 1/NPCs/giant_centipede_well",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0003-02",
                "score": 3,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/",
                  "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
                ],
                "why_matched": [
                  "lexical_token:compared",
                  "lexical_token:out",
                  "lexical_token:rats"
                ]
              },
              {
                "unit_id": "u-L0009-01",
                "score": 2,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:out",
                  "lexical_token:rats"
                ]
              },
              {
                "unit_id": "u-L0003-01",
                "score": 1,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:even"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 0,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0011-01"
                ]
              },
              {
                "unit_id": "u-L0011-02",
                "score": 0,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0011-02"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Centipede",
              "Spider",
              "rats",
              "well"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/magma_spider",
                "matched": true
              },
              {
                "substring": "Campaign 1/NPCs/giant_centipede_well",
                "matched": true
              }
            ],
            "hit_count": 13,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0003-02",
                "score": 9,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/",
                  "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
                ],
                "why_matched": [
                  "lexical_token:compared",
                  "lexical_token:out",
                  "lexical_token:rats",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 6,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0011-01",
                "score": 6,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0011-02",
                "score": 6,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0009-01",
                "score": 5,
                "line_start": 9,
                "line_end": 9,
                "routes": [
                  "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
                ],
                "why_matched": [
                  "lexical_token:out",
                  "lexical_token:rats",
                  "route_token:longmont"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0007-01"
            ],
            "topk_units_swapped_out": [
              "u-L0003-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        }
      ]
    },
    {
      "scenario_id": "c1s3",
      "question_count": 13,
      "baseline_pass_count": 13,
      "with_equivalence_pass_count": 12,
      "questions": [
        {
          "question_id": "c1s3_bubbles_mage_hand_beat",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Bubbles",
              "bites",
              "mage hand"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/PCs/ephanna",
                "matched": true
              },
              {
                "substring": "Campaign 1/NPCs/bubbles_the_float_goat",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0020-01",
                "score": 11,
                "line_start": 20,
                "line_end": 20,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:bubbles",
                  "lexical_token:ephanna",
                  "lexical_token:hand",
                  "lexical_token:mage",
                  "lexical_token:rock",
                  "route_token:bubbles",
                  "route_token:ephanna"
                ]
              },
              {
                "unit_id": "u-L0030-01",
                "score": 10,
                "line_start": 30,
                "line_end": 30,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:bubbles",
                  "lexical_token:ephanna",
                  "lexical_token:hand",
                  "lexical_token:mage",
                  "route_token:bubbles",
                  "route_token:ephanna"
                ]
              },
              {
                "unit_id": "u-L0040-07",
                "score": 9,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:ephanna",
                  "lexical_token:hand",
                  "lexical_token:mage",
                  "route_token:bubbles",
                  "route_token:ephanna"
                ]
              },
              {
                "unit_id": "u-L0041-01",
                "score": 9,
                "line_start": 41,
                "line_end": 41,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:bubbles",
                  "lexical_token:hand",
                  "lexical_token:mage",
                  "route_token:bubbles",
                  "route_token:ephanna"
                ]
              },
              {
                "unit_id": "u-L0040-05",
                "score": 8,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:bubbles",
                  "lexical_token:rock",
                  "route_token:bubbles",
                  "route_token:ephanna"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Bubbles",
              "bites",
              "mage hand"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/PCs/ephanna",
                "matched": true
              },
              {
                "substring": "Campaign 1/NPCs/bubbles_the_float_goat",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0020-01",
                "score": 17,
                "line_start": 20,
                "line_end": 20,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:bubbles",
                  "lexical_token:ephanna",
                  "lexical_token:hand",
                  "lexical_token:mage",
                  "lexical_token:rock",
                  "route_token:bubbles",
                  "route_token:ephanna",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0030-01",
                "score": 16,
                "line_start": 30,
                "line_end": 30,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:bubbles",
                  "lexical_token:ephanna",
                  "lexical_token:hand",
                  "lexical_token:mage",
                  "route_token:bubbles",
                  "route_token:ephanna",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0040-07",
                "score": 15,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:ephanna",
                  "lexical_token:hand",
                  "lexical_token:mage",
                  "route_token:bubbles",
                  "route_token:ephanna",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0041-01",
                "score": 15,
                "line_start": 41,
                "line_end": 41,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:bubbles",
                  "lexical_token:hand",
                  "lexical_token:mage",
                  "route_token:bubbles",
                  "route_token:ephanna",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0040-05",
                "score": 14,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:bubbles",
                  "lexical_token:rock",
                  "route_token:bubbles",
                  "route_token:ephanna",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [],
            "topk_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s3_pippa_ride_kegs",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Bubbles",
              "Pippa",
              "StoneBridge",
              "kegs"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/pippa",
                "matched": true
              },
              {
                "substring": "Campaign 1/NPCs/bubbles_the_float_goat",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/stonebridge",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0034-01",
                "score": 9,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:pippa",
                  "lexical_token:ride",
                  "lexical_token:stonebridge",
                  "route_token:pippa",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0034-02",
                "score": 9,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:keg",
                  "lexical_token:pippa",
                  "lexical_token:wagon",
                  "route_token:pippa",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0036-01",
                "score": 7,
                "line_start": 36,
                "line_end": 36,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:stonebridge",
                  "route_token:pippa",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0040-01",
                "score": 7,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:pippa",
                  "route_token:pippa",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0034-03",
                "score": 6,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "route_token:pippa",
                  "route_token:stonebridge"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Bubbles",
              "Pippa",
              "StoneBridge",
              "kegs"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/pippa",
                "matched": true
              },
              {
                "substring": "Campaign 1/NPCs/bubbles_the_float_goat",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/stonebridge",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0034-01",
                "score": 15,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:pippa",
                  "lexical_token:ride",
                  "lexical_token:stonebridge",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:pippa",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0034-02",
                "score": 15,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:keg",
                  "lexical_token:pippa",
                  "lexical_token:wagon",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:pippa",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0036-01",
                "score": 13,
                "line_start": 36,
                "line_end": 36,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:stonebridge",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:pippa",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0040-01",
                "score": 13,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:pippa",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:pippa",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0034-03",
                "score": 12,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:pippa",
                  "route_token:stonebridge"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [],
            "topk_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s3_grishna_comp_board",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Grishna",
              "beer",
              "board"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/grishna",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0010-01",
                "score": 7,
                "line_start": 10,
                "line_end": 10,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/kirfan/"
                ],
                "why_matched": [
                  "lexical_token:debris",
                  "lexical_token:helped",
                  "lexical_token:kirfan",
                  "lexical_token:upriver",
                  "route_token:kirfan"
                ]
              },
              {
                "unit_id": "meta-session-0003-locations",
                "score": 5,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:comp",
                  "lexical_token:grishna",
                  "route_token:comp"
                ]
              },
              {
                "unit_id": "u-L0012-01",
                "score": 5,
                "line_start": 12,
                "line_end": 12,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "lexical_token:comp",
                  "lexical_token:grishna",
                  "route_token:grishna"
                ]
              },
              {
                "unit_id": "u-L0010-02",
                "score": 4,
                "line_start": 10,
                "line_end": 10,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "lexical_token:upriver",
                  "route_token:grishna"
                ]
              },
              {
                "unit_id": "u-L0014-01",
                "score": 3,
                "line_start": 14,
                "line_end": 14,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "route_token:comp"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Grishna",
              "beer",
              "board"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/grishna",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0010-01",
                "score": 13,
                "line_start": 10,
                "line_end": 10,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/kirfan/"
                ],
                "why_matched": [
                  "lexical_token:debris",
                  "lexical_token:helped",
                  "lexical_token:kirfan",
                  "lexical_token:upriver",
                  "route_token:kirfan",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0012-01",
                "score": 11,
                "line_start": 12,
                "line_end": 12,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "lexical_token:comp",
                  "lexical_token:grishna",
                  "route_token:grishna",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "meta-session-0003-locations",
                "score": 10,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:comp",
                  "lexical_token:grishna",
                  "lexical_token:longmont",
                  "lexical_token:route",
                  "route_token:comp",
                  "route_token:longmont"
                ]
              },
              {
                "unit_id": "u-L0010-02",
                "score": 10,
                "line_start": 10,
                "line_end": 10,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "lexical_token:upriver",
                  "route_token:grishna",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0034-02",
                "score": 9,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "route_token:grishna",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0034-02"
            ],
            "topk_units_swapped_out": [
              "u-L0014-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s3_stafl_brewery_song",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Brewery",
              "Stafl",
              "song"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/PCs/stafl",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/wizards_tower_brewing_company",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "meta-session-0003-locations",
                "score": 13,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:brewery",
                  "lexical_token:pub",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:pub",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0014-01",
                "score": 13,
                "line_start": 14,
                "line_end": 14,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:brewery",
                  "lexical_token:stafl",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:stafl",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0034-05",
                "score": 7,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:stafl",
                  "route_token:pub",
                  "route_token:stafl"
                ]
              },
              {
                "unit_id": "u-L0034-02",
                "score": 6,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "route_token:pub",
                  "route_token:stafl"
                ]
              },
              {
                "unit_id": "u-L0034-03",
                "score": 6,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "route_token:pub",
                  "route_token:stafl"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Brewery",
              "Stafl",
              "song"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/PCs/stafl",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/wizards_tower_brewing_company",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "meta-session-0003-locations",
                "score": 18,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:brewery",
                  "lexical_token:longmont",
                  "lexical_token:pub",
                  "lexical_token:route",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:longmont",
                  "route_token:pub",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0014-01",
                "score": 16,
                "line_start": 14,
                "line_end": 14,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:brewery",
                  "lexical_token:stafl",
                  "lexical_token:tower",
                  "lexical_token:wizard",
                  "route_token:longmont",
                  "route_token:stafl",
                  "route_token:tower",
                  "route_token:wizard"
                ]
              },
              {
                "unit_id": "u-L0034-05",
                "score": 13,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:stafl",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:pub",
                  "route_token:stafl"
                ]
              },
              {
                "unit_id": "u-L0034-02",
                "score": 12,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:pub",
                  "route_token:stafl"
                ]
              },
              {
                "unit_id": "u-L0034-03",
                "score": 12,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:pub",
                  "route_token:stafl"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [],
            "topk_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s3_bonogo_downstream_zen",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Bonogo",
              "downstream",
              "underwater"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/PCs/bonogo",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/stonebridge",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0043-02",
                "score": 8,
                "line_start": 43,
                "line_end": 43,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:river",
                  "route_token:bonogo",
                  "route_token:river"
                ]
              },
              {
                "unit_id": "u-L0043-03",
                "score": 7,
                "line_start": 43,
                "line_end": 43,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:river",
                  "route_token:bonogo",
                  "route_token:river"
                ]
              },
              {
                "unit_id": "u-L0045-01",
                "score": 7,
                "line_start": 45,
                "line_end": 45,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:bonogo",
                  "route_token:bonogo",
                  "route_token:river"
                ]
              },
              {
                "unit_id": "u-L0040-01",
                "score": 6,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "route_token:bonogo",
                  "route_token:river"
                ]
              },
              {
                "unit_id": "u-L0043-04",
                "score": 6,
                "line_start": 43,
                "line_end": 43,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "route_token:bonogo",
                  "route_token:river"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "context_support_below_threshold",
              "semantic_verdict:fail_incomplete"
            ],
            "context_support_ratio": 0.3333333333333333,
            "context_must_hits": [
              "Bonogo"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/PCs/bonogo",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/stonebridge",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0043-02",
                "score": 14,
                "line_start": 43,
                "line_end": 43,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:river",
                  "route_token:bonogo",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:river"
                ]
              },
              {
                "unit_id": "u-L0043-03",
                "score": 13,
                "line_start": 43,
                "line_end": 43,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:river",
                  "route_token:bonogo",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:river"
                ]
              },
              {
                "unit_id": "u-L0045-01",
                "score": 13,
                "line_start": 45,
                "line_end": 45,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:bonogo",
                  "route_token:bonogo",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:river"
                ]
              },
              {
                "unit_id": "u-L0040-01",
                "score": 12,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "route_token:bonogo",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:river"
                ]
              },
              {
                "unit_id": "u-L0043-04",
                "score": 12,
                "line_start": 43,
                "line_end": 43,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "route_token:bonogo",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:river"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "regressed",
            "support_ratio_delta": -0.6667,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [],
            "topk_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s3_ephanna_second_lasso",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Bubbles",
              "lassos",
              "mage hand",
              "second"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/PCs/ephanna",
                "matched": true
              },
              {
                "substring": "Campaign 1/NPCs/bubbles_the_float_goat",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0020-01",
                "score": 9,
                "line_start": 20,
                "line_end": 20,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:bubbles",
                  "lexical_token:ephanna",
                  "lexical_token:lasso",
                  "route_token:bubbles",
                  "route_token:ephanna"
                ]
              },
              {
                "unit_id": "u-L0030-01",
                "score": 9,
                "line_start": 30,
                "line_end": 30,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:bubbles",
                  "lexical_token:ephanna",
                  "lexical_token:lasso",
                  "route_token:bubbles",
                  "route_token:ephanna"
                ]
              },
              {
                "unit_id": "u-L0040-07",
                "score": 8,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:ephanna",
                  "lexical_token:lasso",
                  "route_token:bubbles",
                  "route_token:ephanna"
                ]
              },
              {
                "unit_id": "u-L0034-01",
                "score": 7,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:ephanna",
                  "route_token:bubbles",
                  "route_token:ephanna"
                ]
              },
              {
                "unit_id": "u-L0040-05",
                "score": 7,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:bubbles",
                  "route_token:bubbles",
                  "route_token:ephanna"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Bubbles",
              "lassos",
              "mage hand",
              "second"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/PCs/ephanna",
                "matched": true
              },
              {
                "substring": "Campaign 1/NPCs/bubbles_the_float_goat",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0020-01",
                "score": 15,
                "line_start": 20,
                "line_end": 20,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:bubbles",
                  "lexical_token:ephanna",
                  "lexical_token:lasso",
                  "route_token:bubbles",
                  "route_token:ephanna",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0030-01",
                "score": 15,
                "line_start": 30,
                "line_end": 30,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:bubbles",
                  "lexical_token:ephanna",
                  "lexical_token:lasso",
                  "route_token:bubbles",
                  "route_token:ephanna",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0040-07",
                "score": 14,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:ephanna",
                  "lexical_token:lasso",
                  "route_token:bubbles",
                  "route_token:ephanna",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0034-01",
                "score": 13,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:ephanna",
                  "route_token:bubbles",
                  "route_token:ephanna",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0040-05",
                "score": 13,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:bubbles",
                  "route_token:bubbles",
                  "route_token:ephanna",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [],
            "topk_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s3_caelynn_ice_platform",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Caelynn",
              "ice",
              "platform"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/PCs/caelynn",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0034-01",
                "score": 7,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:caelynn",
                  "route_token:bubbles",
                  "route_token:caelynn"
                ]
              },
              {
                "unit_id": "u-L0040-10",
                "score": 7,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:around",
                  "lexical_token:caelynn",
                  "lexical_token:ice",
                  "lexical_token:rock",
                  "route_token:bubbles"
                ]
              },
              {
                "unit_id": "u-L0022-01",
                "score": 6,
                "line_start": 22,
                "line_end": 22,
                "routes": [
                  "Longmont Campaign/Campaign 1/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:caelynn",
                  "lexical_token:ice",
                  "lexical_token:rock",
                  "route_token:caelynn"
                ]
              },
              {
                "unit_id": "u-L0040-01",
                "score": 6,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "route_token:bubbles",
                  "route_token:caelynn"
                ]
              },
              {
                "unit_id": "u-L0040-05",
                "score": 6,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:around",
                  "lexical_token:bubbles",
                  "lexical_token:rock",
                  "route_token:bubbles"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Caelynn",
              "ice",
              "platform"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/PCs/caelynn",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0034-01",
                "score": 13,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:caelynn",
                  "route_token:bubbles",
                  "route_token:caelynn",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0040-10",
                "score": 13,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:around",
                  "lexical_token:caelynn",
                  "lexical_token:ice",
                  "lexical_token:rock",
                  "route_token:bubbles",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0040-01",
                "score": 12,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "route_token:bubbles",
                  "route_token:caelynn",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0040-05",
                "score": 12,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:around",
                  "lexical_token:bubbles",
                  "lexical_token:rock",
                  "route_token:bubbles",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0041-02",
                "score": 12,
                "line_start": 41,
                "line_end": 41,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "route_token:bubbles",
                  "route_token:caelynn",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0041-02"
            ],
            "topk_units_swapped_out": [
              "u-L0022-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s3_karsemine_zephyr_chase",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Bonogo",
              "Karsemine",
              "Zephyr",
              "arrows"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/PCs/karsemine",
                "matched": true
              },
              {
                "substring": "Campaign 1/PCs/bonogo",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/stonebridge",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0043-01",
                "score": 7,
                "line_start": 43,
                "line_end": 43,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:bank",
                  "lexical_token:karsemine",
                  "lexical_token:strike",
                  "lexical_token:zephyr",
                  "route_token:karsemine"
                ]
              },
              {
                "unit_id": "u-L0032-01",
                "score": 6,
                "line_start": 32,
                "line_end": 32,
                "routes": [
                  "Longmont Campaign/Campaign 1/PCs/karsemine/"
                ],
                "why_matched": [
                  "lexical_token:karsemine",
                  "lexical_token:strike",
                  "lexical_token:zephyr",
                  "route_token:karsemine"
                ]
              },
              {
                "unit_id": "u-L0034-01",
                "score": 4,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:karsemine",
                  "route_token:karsemine"
                ]
              },
              {
                "unit_id": "u-L0041-02",
                "score": 3,
                "line_start": 41,
                "line_end": 41,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "route_token:karsemine"
                ]
              },
              {
                "unit_id": "u-L0041-03",
                "score": 3,
                "line_start": 41,
                "line_end": 41,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "route_token:karsemine"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Bonogo",
              "Karsemine",
              "Zephyr",
              "arrows"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/PCs/karsemine",
                "matched": true
              },
              {
                "substring": "Campaign 1/PCs/bonogo",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/stonebridge",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0043-01",
                "score": 13,
                "line_start": 43,
                "line_end": 43,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:bank",
                  "lexical_token:karsemine",
                  "lexical_token:strike",
                  "lexical_token:zephyr",
                  "route_token:karsemine",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0034-01",
                "score": 10,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:karsemine",
                  "route_token:karsemine",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0032-01",
                "score": 9,
                "line_start": 32,
                "line_end": 32,
                "routes": [
                  "Longmont Campaign/Campaign 1/PCs/karsemine/"
                ],
                "why_matched": [
                  "lexical_token:karsemine",
                  "lexical_token:strike",
                  "lexical_token:zephyr",
                  "route_token:karsemine",
                  "route_token:longmont"
                ]
              },
              {
                "unit_id": "u-L0041-02",
                "score": 9,
                "line_start": 41,
                "line_end": 41,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "route_token:karsemine",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0041-03",
                "score": 9,
                "line_start": 41,
                "line_end": 41,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "route_token:karsemine",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [],
            "topk_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s3_kirfan_debris_help",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Kirfan",
              "debris",
              "upriver"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/kirfan",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0010-01",
                "score": 4,
                "line_start": 10,
                "line_end": 10,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/kirfan/"
                ],
                "why_matched": [
                  "lexical_token:broken",
                  "lexical_token:debris",
                  "lexical_token:structure",
                  "lexical_token:upriver"
                ]
              },
              {
                "unit_id": "u-L0010-02",
                "score": 1,
                "line_start": 10,
                "line_end": 10,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "lexical_token:upriver"
                ]
              },
              {
                "unit_id": "u-L0034-05",
                "score": 1,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:pulled"
                ]
              },
              {
                "unit_id": "u-L0040-04",
                "score": 1,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:broken"
                ]
              },
              {
                "unit_id": "u-L0043-03",
                "score": 1,
                "line_start": 43,
                "line_end": 43,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:were"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Kirfan",
              "debris",
              "upriver"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/NPCs/kirfan",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0010-01",
                "score": 10,
                "line_start": 10,
                "line_end": 10,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/kirfan/"
                ],
                "why_matched": [
                  "lexical_token:broken",
                  "lexical_token:debris",
                  "lexical_token:structure",
                  "lexical_token:upriver",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0010-02",
                "score": 7,
                "line_start": 10,
                "line_end": 10,
                "routes": [
                  "Longmont Campaign/Campaign 1/NPCs/grishna/"
                ],
                "why_matched": [
                  "lexical_token:upriver",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0034-05",
                "score": 7,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:pulled",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0040-04",
                "score": 7,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:broken",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0043-03",
                "score": 7,
                "line_start": 43,
                "line_end": 43,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:were",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [],
            "topk_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s3_stafl_nets_town",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Stafl",
              "bridge",
              "nets"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/PCs/stafl",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/stonebridge",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0028-01",
                "score": 6,
                "line_start": 28,
                "line_end": 28,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:nets",
                  "lexical_token:stafl",
                  "lexical_token:town",
                  "route_token:stafl"
                ]
              },
              {
                "unit_id": "u-L0014-01",
                "score": 5,
                "line_start": 14,
                "line_end": 14,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:stafl",
                  "lexical_token:town",
                  "route_token:stafl"
                ]
              },
              {
                "unit_id": "u-L0034-01",
                "score": 4,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:stafl",
                  "route_token:stafl"
                ]
              },
              {
                "unit_id": "u-L0034-05",
                "score": 4,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:stafl",
                  "route_token:stafl"
                ]
              },
              {
                "unit_id": "meta-session-0003-locations",
                "score": 3,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:during",
                  "lexical_token:flood",
                  "lexical_token:town"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Stafl",
              "bridge",
              "nets"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/PCs/stafl",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/stonebridge",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0034-01",
                "score": 10,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:stafl",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:stafl"
                ]
              },
              {
                "unit_id": "u-L0034-05",
                "score": 10,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:stafl",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:stafl"
                ]
              },
              {
                "unit_id": "u-L0028-01",
                "score": 9,
                "line_start": 28,
                "line_end": 28,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:nets",
                  "lexical_token:stafl",
                  "lexical_token:town",
                  "route_token:longmont",
                  "route_token:stafl"
                ]
              },
              {
                "unit_id": "u-L0034-02",
                "score": 9,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:stafl"
                ]
              },
              {
                "unit_id": "u-L0034-03",
                "score": 9,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:stafl"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0034-02",
              "u-L0034-03"
            ],
            "topk_units_swapped_out": [
              "meta-session-0003-locations",
              "u-L0014-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s3_bonogo_dive_rope_gone",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Baergrom",
              "Bonogo",
              "rope"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/PCs/bonogo",
                "matched": true
              },
              {
                "substring": "Campaign 1/PCs/baergrom",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/stonebridge",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0024-01",
                "score": 10,
                "line_start": 24,
                "line_end": 24,
                "routes": [
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:baergrom",
                  "lexical_token:bonogo",
                  "lexical_token:dive",
                  "lexical_token:rope",
                  "route_token:baergrom",
                  "route_token:bonogo"
                ]
              },
              {
                "unit_id": "u-L0040-09",
                "score": 9,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:baergrom",
                  "lexical_token:bonogo",
                  "lexical_token:dive",
                  "route_token:baergrom",
                  "route_token:bonogo"
                ]
              },
              {
                "unit_id": "u-L0034-01",
                "score": 7,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:baergrom",
                  "route_token:baergrom",
                  "route_token:bonogo"
                ]
              },
              {
                "unit_id": "u-L0040-10",
                "score": 7,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:desperate",
                  "route_token:baergrom",
                  "route_token:bonogo"
                ]
              },
              {
                "unit_id": "u-L0041-01",
                "score": 7,
                "line_start": 41,
                "line_end": 41,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:rope",
                  "route_token:baergrom",
                  "route_token:bonogo"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Baergrom",
              "Bonogo",
              "rope"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/PCs/bonogo",
                "matched": true
              },
              {
                "substring": "Campaign 1/PCs/baergrom",
                "matched": true
              },
              {
                "substring": "Campaign 1/Locations/stonebridge",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0040-09",
                "score": 15,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:baergrom",
                  "lexical_token:bonogo",
                  "lexical_token:dive",
                  "route_token:baergrom",
                  "route_token:bonogo",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0024-01",
                "score": 13,
                "line_start": 24,
                "line_end": 24,
                "routes": [
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:baergrom",
                  "lexical_token:bonogo",
                  "lexical_token:dive",
                  "lexical_token:rope",
                  "route_token:baergrom",
                  "route_token:bonogo",
                  "route_token:longmont"
                ]
              },
              {
                "unit_id": "u-L0034-01",
                "score": 13,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:baergrom",
                  "route_token:baergrom",
                  "route_token:bonogo",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0040-10",
                "score": 13,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:desperate",
                  "route_token:baergrom",
                  "route_token:bonogo",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0041-01",
                "score": 13,
                "line_start": 41,
                "line_end": 41,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:rope",
                  "route_token:baergrom",
                  "route_token:bonogo",
                  "route_token:longmont",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [],
            "topk_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s3_mirathorn_festival_hook",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Mirathorn",
              "Pippa",
              "festival"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Locations/mirathorn",
                "matched": true
              },
              {
                "substring": "Campaign 1/NPCs/pippa",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "meta-session-0003-locations",
                "score": 6,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:festival",
                  "lexical_token:hook",
                  "lexical_token:mirathorn",
                  "route_token:mirathorn"
                ]
              },
              {
                "unit_id": "u-L0043-02",
                "score": 3,
                "line_start": 43,
                "line_end": 43,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "route_token:mirathorn"
                ]
              },
              {
                "unit_id": "u-L0043-03",
                "score": 3,
                "line_start": 43,
                "line_end": 43,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "route_token:mirathorn"
                ]
              },
              {
                "unit_id": "u-L0043-04",
                "score": 3,
                "line_start": 43,
                "line_end": 43,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "route_token:mirathorn"
                ]
              },
              {
                "unit_id": "u-L0045-01",
                "score": 3,
                "line_start": 45,
                "line_end": 45,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "route_token:mirathorn"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Mirathorn",
              "Pippa",
              "festival"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Locations/mirathorn",
                "matched": true
              },
              {
                "substring": "Campaign 1/NPCs/pippa",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "meta-session-0003-locations",
                "score": 11,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
                ],
                "why_matched": [
                  "lexical_token:festival",
                  "lexical_token:hook",
                  "lexical_token:longmont",
                  "lexical_token:mirathorn",
                  "lexical_token:route",
                  "route_token:longmont",
                  "route_token:mirathorn"
                ]
              },
              {
                "unit_id": "u-L0043-02",
                "score": 9,
                "line_start": 43,
                "line_end": 43,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:mirathorn",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0043-03",
                "score": 9,
                "line_start": 43,
                "line_end": 43,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:mirathorn",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0043-04",
                "score": 9,
                "line_start": 43,
                "line_end": 43,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:mirathorn",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0045-01",
                "score": 9,
                "line_start": 45,
                "line_end": 45,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:mirathorn",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [],
            "topk_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "c1s3_stonebridge_npc_roster_associated",
          "question": "",
          "expected_answer": "",
          "must_hit_tokens": [],
          "expected_route_substrings": [],
          "min_context_support_ratio": 0.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Bubbles",
              "Grishna",
              "Pippa",
              "StoneBridge"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Locations/stonebridge",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0034-01",
                "score": 7,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:stonebridge",
                  "route_token:npcs",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0036-01",
                "score": 7,
                "line_start": 36,
                "line_end": 36,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:stonebridge",
                  "route_token:npcs",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0040-06",
                "score": 7,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:all",
                  "route_token:npcs",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0045-01",
                "score": 7,
                "line_start": 45,
                "line_end": 45,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:all",
                  "route_token:npcs",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0034-02",
                "score": 6,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "route_token:npcs",
                  "route_token:stonebridge"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Bubbles",
              "Grishna",
              "Pippa",
              "StoneBridge"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Campaign 1/Locations/stonebridge",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0034-01",
                "score": 13,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/caelynn/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/",
                  "Longmont Campaign/Campaign 1/PCs/karsemine/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:stonebridge",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:npcs",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0036-01",
                "score": 13,
                "line_start": 36,
                "line_end": 36,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:stonebridge",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:npcs",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0040-06",
                "score": 13,
                "line_start": 40,
                "line_end": 40,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/PCs/baergrom/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/",
                  "Longmont Campaign/Campaign 1/PCs/ephanna/"
                ],
                "why_matched": [
                  "lexical_token:all",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:npcs",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0045-01",
                "score": 13,
                "line_start": 45,
                "line_end": 45,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/mirathorn/",
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/bonogo/"
                ],
                "why_matched": [
                  "lexical_token:all",
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:npcs",
                  "route_token:stonebridge"
                ]
              },
              {
                "unit_id": "u-L0034-02",
                "score": 12,
                "line_start": 34,
                "line_end": 34,
                "routes": [
                  "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                  "Longmont Campaign/Campaign 1/Locations/stonebridge/",
                  "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                  "Longmont Campaign/Campaign 1/NPCs/grishna/",
                  "Longmont Campaign/Campaign 1/NPCs/pippa/",
                  "Longmont Campaign/Campaign 1/PCs/stafl/"
                ],
                "why_matched": [
                  "route_token:longmont",
                  "route_token:npc",
                  "route_token:npcs",
                  "route_token:stonebridge"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "lysandra",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [],
            "topk_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        }
      ]
    }
  ]
} as const;
// END GENERATED COHORT_L3_QUESTION_DEEP_DIVE

export default function CohortL3QuestionDeepDiveCanvas() {
  const payload = cohortL3QuestionDeepDiveGenerated;
  return (
    <div>
      <h1>Cohort L3 Question Deep Dive</h1>
      <p>question_count: {payload.question_count}</p>
      {payload.scenarios.flatMap((s: any) => s.questions).map((q: any) => (
        <details key={q.question_id} open={q.delta.verdict === 'regressed' || q.delta.verdict === 'improved'}>
          <summary>{q.question_id} — {q.delta.verdict}</summary>
          <pre>{JSON.stringify(q, null, 2)}</pre>
        </details>
      ))}
    </div>
  );
}
