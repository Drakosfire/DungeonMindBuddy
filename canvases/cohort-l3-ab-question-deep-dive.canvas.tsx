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
  "failure_diagnostic_summary": {
    "passed": 42,
    "equivalence_helped": 0,
    "ranking_regression": 2,
    "missing_lexical_handle": 0,
    "retriever_support_gap": 0,
    "gold_or_rubric_gap": 0
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
          "question": "Who was in the merchant-guard party when the group reached Stonebridge?",
          "expected_answer": "The merchant-guard party was Karsemine, Stafl, Caelynn, Ephanna, Bonogo, and Baergrom; they had been traveling together and reached the town of Stonebridge.",
          "must_hit_tokens": [
            "merchant",
            "Stonebridge",
            "Karsemine",
            "Stafl",
            "Caelynn",
            "Ephanna",
            "Bonogo",
            "Baergrom"
          ],
          "expected_route_substrings": [
            "Campaign 1/Parties/party_merchant_guards",
            "Campaign 1/PCs/karsemine",
            "Campaign 1/PCs/baergrom"
          ],
          "min_context_support_ratio": 0.55,
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
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s1_party_classes_species",
          "question": "What species or classes are attached to each starting party member in the first recap?",
          "expected_answer": "Karsemine is the Tiefling Ranger, Stafl is the Human Bard, Caelynn is the Half Elf Sorcerer, Ephanna is the Kenku Warlock, Bonogo is the Bugbear Rogue, and Baergrom is the Dwarf Fighter.",
          "must_hit_tokens": [
            "Tiefling",
            "Ranger",
            "Bard",
            "Sorcerer",
            "Kenku",
            "Warlock",
            "Bugbear",
            "Rogue",
            "Dwarf",
            "Fighter"
          ],
          "expected_route_substrings": [
            "Campaign 1/PCs/karsemine",
            "Campaign 1/PCs/stafl"
          ],
          "min_context_support_ratio": 0.55,
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
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [
              "u-L0005-02"
            ],
            "full_units_swapped_out": [
              "u-L0007-02"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s1_stonebridge_known_for",
          "question": "What is Stonebridge known for at the start of the campaign?",
          "expected_answer": "Stonebridge is known mostly for the Stonebridge over the river, the River's Edge Pub run by Grishna, a job board, and Glowkindle's posted request for mercenaries to help clean up rats.",
          "must_hit_tokens": [
            "Stonebridge",
            "river",
            "Grishna",
            "Glowkindle",
            "rats",
            "job"
          ],
          "expected_route_substrings": [
            "Campaign 1/Locations/stonebridge",
            "Campaign 1/NPCs/grishna",
            "Campaign 1/NPCs/glowkindle"
          ],
          "min_context_support_ratio": 0.55,
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
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [
              "u-L0011-02",
              "u-L0013-03",
              "u-L0013-04",
              "u-L0015-01"
            ],
            "full_units_swapped_out": [
              "u-L0007-03",
              "u-L0007-04",
              "u-L0017-01",
              "u-L0017-02"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s1_glowkindle_job_source",
          "question": "Who posted the first job hook, and what did they need help with?",
          "expected_answer": "Glowkindle posted the help request and spread word that he needed mercenaries. The job was to clear out giant rats that had attacked his excavation crew after they broke through a wall while expanding the fermentation cellar.",
          "must_hit_tokens": [
            "Glowkindle",
            "mercenaries",
            "rats",
            "fermentation"
          ],
          "expected_route_substrings": [
            "Campaign 1/NPCs/glowkindle",
            "Campaign 1/Locations/wizards_tower_brewing_company"
          ],
          "min_context_support_ratio": 0.55,
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
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [
              "u-L0009-01",
              "u-L0009-02",
              "u-L0011-01"
            ],
            "full_units_swapped_out": [
              "u-L0007-02",
              "u-L0007-03",
              "u-L0007-04"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s1_grishna_directions",
          "question": "What did Grishna tell the party about finding the brewery?",
          "expected_answer": "Grishna told them the Wizard's Tower Brewing Co was upriver, west at the big rock, and then to walk until they saw it.",
          "must_hit_tokens": [
            "Grishna",
            "brewing",
            "boulder"
          ],
          "expected_route_substrings": [
            "Campaign 1/NPCs/grishna",
            "Campaign 1/Locations/rivers_edge_pub",
            "Campaign 1/Locations/wizards_tower_brewing_company"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Grishna",
              "boulder",
              "brewing"
            ],
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [
              "meta-session-0001-locations"
            ],
            "full_units_swapped_out": [
              "u-L0007-04"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s1_brewery_compass_direction",
          "question": "What compass direction from Stonebridge did Grishna give for reaching the brewery?",
          "expected_answer": "Grishna directed the party upriver and then west at the big rock to find the Wizard's Tower Brewing Co.",
          "must_hit_tokens": [
            "Grishna",
            "west",
            "up river",
            "brewing"
          ],
          "expected_route_substrings": [
            "Campaign 1/NPCs/grishna",
            "Campaign 1/Locations/stonebridge",
            "Campaign 1/Locations/wizards_tower_brewing_company"
          ],
          "min_context_support_ratio": 1.0,
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
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [
              "west",
              "up river"
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
            "full_units_swapped_in": [
              "u-L0011-02",
              "u-L0013-03",
              "u-L0013-04",
              "u-L0015-01"
            ],
            "full_units_swapped_out": [
              "u-L0007-02",
              "u-L0007-03",
              "u-L0017-01",
              "u-L0017-02"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "ranking_regression",
            "reasons": [
              "equivalence_lost_context_support_ratio",
              "equivalence_lost_required_must_hits",
              "verdict_regressed"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s1_bonogo_firkin",
          "question": "What did Bonogo buy before the hike to the brewery?",
          "expected_answer": "Bonogo bought a firkin of ale for two gold because he was enjoying the beer and did not care much about the cost.",
          "must_hit_tokens": [
            "Bonogo",
            "firkin",
            "ale",
            "gold"
          ],
          "expected_route_substrings": [
            "Campaign 1/PCs/bonogo",
            "Campaign 1/Locations/rivers_edge_pub"
          ],
          "min_context_support_ratio": 0.55,
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
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [
              "u-L0011-02",
              "u-L0013-03",
              "u-L0013-04",
              "u-L0015-01"
            ],
            "full_units_swapped_out": [
              "u-L0005-01",
              "u-L0007-04",
              "u-L0017-01",
              "u-L0017-02"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s1_route_to_brewery",
          "question": "How did the group get from Stonebridge toward the Wizard's Tower Brewing Company?",
          "expected_answer": "They followed Grishna's directions upriver and west to the big rock, found it was an enormous boulder shaped like the foot of a huge statue, and then walked along the trail to the Wizard's Tower Brewing Company.",
          "must_hit_tokens": [
            "trail",
            "boulder",
            "brewing"
          ],
          "expected_route_substrings": [
            "Campaign 1/Parties/party_merchant_guards",
            "Campaign 1/Locations/stonebridge",
            "Campaign 1/Locations/wizards_tower_brewing_company"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 0.6666666666666666,
            "context_must_hits": [
              "brewing",
              "trail"
            ],
            "context_must_hits_missing": [
              "boulder"
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [
              "u-L0005-03",
              "u-L0007-02",
              "u-L0009-02",
              "u-L0009-03",
              "u-L0009-04"
            ],
            "full_units_swapped_out": [
              "u-L0013-04",
              "u-L0015-01",
              "u-L0017-01",
              "u-L0017-02",
              "u-L0017-03"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s1_stone_foot_landmark",
          "question": "What was the big rock landmark on the way to the brewery?",
          "expected_answer": "The big rock was an enormous boulder that looked like the foot of a once-enormous statue.",
          "must_hit_tokens": [
            "foot"
          ],
          "expected_route_substrings": [
            "Campaign 1/Locations/wizards_tower_brewing_company",
            "Campaign 1/Parties/party_merchant_guards"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "foot"
            ],
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [
              "u-L0005-02",
              "u-L0005-03",
              "u-L0007-03"
            ],
            "full_units_swapped_out": [
              "u-L0017-01",
              "u-L0017-02",
              "u-L0017-03"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s1_brewery_arrival",
          "question": "What was the Wizard's Tower Brewing Company like when the group arrived?",
          "expected_answer": "The Wizard's Tower Brewing Company was bustling and smelled of brewing. Its tap room was lit by magical crystals and was empty except for gnomes busily brewing.",
          "must_hit_tokens": [
            "bustling",
            "crystals",
            "gnomes",
            "brewing"
          ],
          "expected_route_substrings": [
            "Campaign 1/Locations/wizards_tower_brewing_company",
            "Campaign 1/NPCs/glowkindle"
          ],
          "min_context_support_ratio": 0.55,
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
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [
              "u-L0005-02",
              "u-L0005-03"
            ],
            "full_units_swapped_out": [
              "u-L0009-03",
              "u-L0009-04"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s1_glowkindle_offer",
          "question": "What did Glowkindle offer the team for clearing the rats?",
          "expected_answer": "Glowkindle offered 25 gold pieces each if the team cleared out the rats.",
          "must_hit_tokens": [
            "Glowkindle",
            "25",
            "gold",
            "rats"
          ],
          "expected_route_substrings": [
            "Campaign 1/NPCs/glowkindle",
            "Campaign 1/Parties/party_merchant_guards"
          ],
          "min_context_support_ratio": 0.55,
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
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [
              "u-L0009-02"
            ],
            "full_units_swapped_out": [
              "u-L0007-02"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s1_rat_incident_origin",
          "question": "What caused the giant-rat problem at the brewery?",
          "expected_answer": "The giant rats assaulted the excavation crew after they broke through a wall while expanding the fermentation cellar.",
          "must_hit_tokens": [
            "rats",
            "cellar",
            "wall",
            "excavation"
          ],
          "expected_route_substrings": [
            "Campaign 1/NPCs/glowkindle",
            "Campaign 1/Locations/wizards_tower_brewing_company"
          ],
          "min_context_support_ratio": 0.55,
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
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [
              "u-L0005-02"
            ],
            "full_units_swapped_out": [
              "u-L0017-03"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s1_first_combat_cost",
          "question": "How rough was the party's first combat with the rats?",
          "expected_answer": "It was much harder than expected. Multiple people went down, a mysterious cat owl was tossed into the room to help, and many health potions were consumed.",
          "must_hit_tokens": [
            "harder",
            "potions",
            "cat owl",
            "blood"
          ],
          "expected_route_substrings": [
            "Campaign 1/Parties/party_merchant_guards",
            "Campaign 1/PCs/karsemine"
          ],
          "min_context_support_ratio": 0.55,
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
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [
              "u-L0005-02"
            ],
            "full_units_swapped_out": [
              "u-L0007-02"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s1_post_combat_exploration",
          "question": "What did the team find after they were free to explore?",
          "expected_answer": "They found a beautifully tiled hallway, a trapped mosaic on the ground, and a room full of broken alchemical tools.",
          "must_hit_tokens": [
            "hallway",
            "mosaic",
            "alchemical"
          ],
          "expected_route_substrings": [
            "Campaign 1/Parties/party_merchant_guards",
            "Campaign 1/Locations/wizards_tower_brewing_company"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "alchemical",
              "hallway",
              "mosaic"
            ],
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [
              "meta-session-0001-locations",
              "u-L0005-02",
              "u-L0005-03"
            ],
            "full_units_swapped_out": [
              "u-L0007-02",
              "u-L0007-03",
              "u-L0009-04"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s1_karsemine_spider_reveal",
          "question": "What did Karsemine discover while searching the room?",
          "expected_answer": "Karsemine searched the room, looked up, and made eye contact with a flaming magma-infused spider monstrosity in the shattered mage's tower context.",
          "must_hit_tokens": [
            "Karsemine",
            "spider",
            "magma"
          ],
          "expected_route_substrings": [
            "Campaign 1/PCs/karsemine",
            "Campaign 1/Locations/shatter_mages_tower"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Karsemine",
              "magma",
              "spider"
            ],
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [
              "meta-session-0001-locations",
              "u-L0005-02",
              "u-L0005-03"
            ],
            "full_units_swapped_out": [
              "u-L0007-02",
              "u-L0007-03",
              "u-L0009-04"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s1_final_threat",
          "question": "What threat ends the Session 1 recap?",
          "expected_answer": "The recap ends on the reveal of a flaming, magma-infused spider monstrosity.",
          "must_hit_tokens": [
            "spider",
            "magma",
            "monstrosity"
          ],
          "expected_route_substrings": [
            "Campaign 1/Locations/shatter_mages_tower",
            "Campaign 1/PCs/karsemine"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 0.6666666666666666,
            "context_must_hits": [
              "magma",
              "spider"
            ],
            "context_must_hits_missing": [
              "monstrosity"
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
            "context_must_hits_missing": [
              "monstrosity"
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
            "full_units_swapped_in": [
              "u-L0007-02",
              "u-L0009-01",
              "u-L0009-02",
              "u-L0009-03",
              "u-L0009-04",
              "u-L0011-02",
              "u-L0013-01",
              "u-L0013-02",
              "u-L0013-03",
              "u-L0013-04",
              "u-L0015-01"
            ],
            "full_units_swapped_out": [
              "u-L0007-03",
              "u-L0007-04",
              "u-L0017-02"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
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
          "question": "After the rat-clearing job, what bigger threats does the recap say were 'no big deal' by comparison?",
          "expected_answer": "Compared to the rats, the Giant Flaming Spider, the Giant Centipede from the well, and the rat that was absolutely not about to mutate were no big deal.",
          "must_hit_tokens": [
            "rats",
            "Spider",
            "Centipede",
            "well",
            "mutate"
          ],
          "expected_route_substrings": [
            "Campaign 1/Parties/party_merchant_guards",
            "Campaign 1/NPCs/magma_spider",
            "Campaign 1/NPCs/giant_centipede_well"
          ],
          "min_context_support_ratio": 0.55,
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
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s2_basement_clearing_payoff",
          "question": "What did the group find after clearing more of the wizard's tower basement?",
          "expected_answer": "They found a sack of gems, mystery potions on corpses in the well, and broke through a wall into a room full of healing potions, alchemical tools, and ancient ingredients they do not know how to use.",
          "must_hit_tokens": [
            "gems",
            "potions",
            "well",
            "healing",
            "alchemical",
            "wall"
          ],
          "expected_route_substrings": [
            "Campaign 1/Locations/wizards_tower_brewing_company"
          ],
          "min_context_support_ratio": 0.55,
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
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s2_glowkindle_stash_deal",
          "question": "What arrangement did the party negotiate with Glowkindle about the extra discoveries?",
          "expected_answer": "Because the hidden room and much of the place were outside the original contract, they negotiated with Glowkindle for the right to stash gear in the hidden alchemy room.",
          "must_hit_tokens": [
            "Glowkindle",
            "stash",
            "alchemy",
            "contract"
          ],
          "expected_route_substrings": [
            "Campaign 1/NPCs/glowkindle"
          ],
          "min_context_support_ratio": 0.55,
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
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s2_god_forsaken_scope",
          "question": "How does the recap characterize the scope of what was (and wasn't) covered by the original contract?",
          "expected_answer": "The hidden room was not part of the original contract, and neither was the rest of the god-forsaken place.",
          "must_hit_tokens": [
            "contract",
            "forsaken"
          ],
          "expected_route_substrings": [
            "Campaign 1/NPCs/glowkindle"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "contract",
              "forsaken"
            ],
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [
              "meta-session-0002-locations",
              "u-L0003-01",
              "u-L0011-03",
              "u-L0013-01"
            ],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s2_pay_and_loot_summary",
          "question": "How much money did each party member make, and what else did they walk away with?",
          "expected_answer": "They made pretty good money \u2014 25 gp each \u2014 plus a bit of loot.",
          "must_hit_tokens": [
            "25",
            "gp",
            "loot"
          ],
          "expected_route_substrings": [
            "Campaign 1/Parties/party_merchant_guards"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "25",
              "gp",
              "loot"
            ],
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s2_party_commitment",
          "question": "What did the group decide about staying together after this session's pay-off?",
          "expected_answer": "They decided to stick together and see where the winds take them.",
          "must_hit_tokens": [
            "stick together",
            "winds"
          ],
          "expected_route_substrings": [
            "Campaign 1/Parties/party_merchant_guards"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "stick together",
              "winds"
            ],
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s2_basement_lesson",
          "question": "What lesson does the recap say the party learned from clearing rats out of basements?",
          "expected_answer": "They learned a lot about the dangers of clearing rats out of basements.",
          "must_hit_tokens": [
            "rats",
            "basements",
            "dangers"
          ],
          "expected_route_substrings": [
            "Campaign 1/Parties/party_merchant_guards"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "basements",
              "dangers",
              "rats"
            ],
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s2_hook_more_work_glowkindle",
          "question": "What open question does the recap pose about Glowkindle?",
          "expected_answer": "Whether they will ask Glowkindle for more work.",
          "must_hit_tokens": [
            "Glowkindle",
            "work"
          ],
          "expected_route_substrings": [
            "Campaign 1/NPCs/glowkindle"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Glowkindle",
              "work"
            ],
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s2_hook_stonebridge_grishna",
          "question": "What return trip to Stonebridge does the recap tease?",
          "expected_answer": "They might head back to Stonebridge to say hi to Grishna at the River's Edge Pub.",
          "must_hit_tokens": [
            "Stonebridge",
            "Grishna",
            "Pub"
          ],
          "expected_route_substrings": [
            "Campaign 1/Locations/stonebridge",
            "Campaign 1/NPCs/grishna",
            "Campaign 1/Locations/rivers_edge_pub"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Grishna",
              "Pub",
              "Stonebridge"
            ],
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s2_hook_wizard_tower_thread",
          "question": "What Wizard's Tower thread does this recap tee up without answering yet?",
          "expected_answer": "The recap only tees up the question of whether there is more to the Wizard's Tower; it does not answer what is there.",
          "must_hit_tokens": [
            "Wizard",
            "Tower",
            "more"
          ],
          "expected_route_substrings": [
            "Campaign 1/Locations/wizards_tower_brewing_company"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Tower",
              "Wizard",
              "more"
            ],
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s2_spider_beat",
          "question": "Which large spider threat is named in the Session 2 recap?",
          "expected_answer": "The Giant Flaming Spider.",
          "must_hit_tokens": [
            "Spider",
            "Flaming"
          ],
          "expected_route_substrings": [
            "Campaign 1/NPCs/magma_spider"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Flaming",
              "Spider"
            ],
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [
              "u-L0007-02",
              "u-L0009-01",
              "u-L0011-03",
              "u-L0013-01"
            ],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s2_centipede_beat",
          "question": "Where did the giant centipede come from in the recap's threat list?",
          "expected_answer": "The giant centipede crawled out of the well.",
          "must_hit_tokens": [
            "centipede",
            "well"
          ],
          "expected_route_substrings": [
            "Campaign 1/NPCs/giant_centipede_well"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "centipede",
              "well"
            ],
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [
              "u-L0007-02",
              "u-L0009-01",
              "u-L0011-03",
              "u-L0013-01"
            ],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s2_non_mutating_rat",
          "question": "What does the recap emphasize about one rat versus mutation?",
          "expected_answer": "There was a rat that absolutely was not about to mutate.",
          "must_hit_tokens": [
            "mutate",
            "rat"
          ],
          "expected_route_substrings": [
            "Campaign 1/Parties/party_merchant_guards"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "mutate",
              "rat"
            ],
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s2_planning_glowkindle_followup",
          "question": "If we're prepping the next Glowkindle beat, what should we remember about the stash deal from Session 2?",
          "expected_answer": "They negotiated with Glowkindle for the right to stash gear in the hidden alchemy room because that space was outside the original contract.",
          "must_hit_tokens": [
            "Glowkindle",
            "stash",
            "alchemy",
            "contract"
          ],
          "expected_route_substrings": [
            "Campaign 1/NPCs/glowkindle"
          ],
          "min_context_support_ratio": 0.55,
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
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s2_prep_named_hostiles",
          "question": "For combat prep, which named or clearly typed hostile creatures does Session 2 call out (even as 'easy' compared to rats)?",
          "expected_answer": "The Giant Flaming Spider, the Giant Centipede from the well, ordinary rats, and the rat that was not about to mutate.",
          "must_hit_tokens": [
            "Spider",
            "Centipede",
            "rats",
            "well"
          ],
          "expected_route_substrings": [
            "Campaign 1/NPCs/magma_spider",
            "Campaign 1/NPCs/giant_centipede_well"
          ],
          "min_context_support_ratio": 0.55,
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
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
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
          "question": "For the Bubbles rescue, what was Ephanna's first mage-hand plan on the rock, and how did Bubbles handle it?",
          "expected_answer": "Ephanna used mage hand to lasso Bubbles on the rock, but Bubbles is too panicked and bites the mage hand.",
          "must_hit_tokens": [
            "mage hand",
            "Bubbles",
            "bites"
          ],
          "expected_route_substrings": [
            "Campaign 1/PCs/ephanna",
            "Campaign 1/NPCs/bubbles_the_float_goat"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Bubbles",
              "bites",
              "mage hand"
            ],
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s3_pippa_ride_kegs",
          "question": "Remind me how they got to StoneBridge with Pippa: who gave the ride, and what was pulling the keg wagon?",
          "expected_answer": "Pippa offered the ride toward StoneBridge, and Bubbles the Float Goat was hitched to her wagon full of kegs.",
          "must_hit_tokens": [
            "Pippa",
            "StoneBridge",
            "Bubbles",
            "kegs"
          ],
          "expected_route_substrings": [
            "Campaign 1/NPCs/pippa",
            "Campaign 1/NPCs/bubbles_the_float_goat",
            "Campaign 1/Locations/stonebridge"
          ],
          "min_context_support_ratio": 0.55,
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
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s3_grishna_comp_board",
          "question": "After they helped Kirfan with the upriver debris, what did Grishna comp them?",
          "expected_answer": "Grishna comped them beer and board.",
          "must_hit_tokens": [
            "Grishna",
            "beer",
            "board"
          ],
          "expected_route_substrings": [
            "Campaign 1/NPCs/grishna"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Grishna",
              "beer",
              "board"
            ],
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [
              "u-L0036-05"
            ],
            "full_units_swapped_out": [
              "u-L0014-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s3_stafl_brewery_song",
          "question": "What did Stafl do in the pub to sell the Wizard's Tower Brewery story to the room?",
          "expected_answer": "Stafl wrote and played an incredible song that wooed the town in the retelling of the Wizard's Tower Brewery adventure.",
          "must_hit_tokens": [
            "Stafl",
            "song",
            "Brewery"
          ],
          "expected_route_substrings": [
            "Campaign 1/PCs/stafl",
            "Campaign 1/Locations/wizards_tower_brewing_company"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Brewery",
              "Stafl",
              "song"
            ],
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [
              "u-L0034-01"
            ],
            "full_units_swapped_out": [
              "u-L0028-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s3_bonogo_downstream_zen",
          "question": "Where does Bonogo end up in the early flood outline once the river takes him?",
          "expected_answer": "Bonogo flows downstream and has a wonderful zen underwater adventure.",
          "must_hit_tokens": [
            "Bonogo",
            "downstream",
            "underwater"
          ],
          "expected_route_substrings": [
            "Campaign 1/PCs/bonogo",
            "Campaign 1/Locations/stonebridge"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Bonogo",
              "downstream",
              "underwater"
            ],
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [
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
            "full_units_swapped_in": [
              "u-L0034-02",
              "u-L0034-03"
            ],
            "full_units_swapped_out": [
              "u-L0024-01",
              "u-L0026-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "ranking_regression",
            "reasons": [
              "equivalence_lost_context_support_ratio",
              "equivalence_lost_required_must_hits",
              "verdict_regressed"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s3_ephanna_second_lasso",
          "question": "When does Ephanna finally get Bubbles on the lasso?",
          "expected_answer": "On the second attempt, Ephanna's mage hand succeeds, lassos Bubbles, and leads her back to Ephanna.",
          "must_hit_tokens": [
            "second",
            "lassos",
            "Bubbles",
            "mage hand"
          ],
          "expected_route_substrings": [
            "Campaign 1/PCs/ephanna",
            "Campaign 1/NPCs/bubbles_the_float_goat"
          ],
          "min_context_support_ratio": 0.55,
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
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s3_caelynn_ice_platform",
          "question": "What does Caelynn do with ice around Bubbles' rock?",
          "expected_answer": "Caelynn uses ice to freeze the base of the rock and make a platform.",
          "must_hit_tokens": [
            "Caelynn",
            "ice",
            "platform"
          ],
          "expected_route_substrings": [
            "Campaign 1/PCs/caelynn"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Caelynn",
              "ice",
              "platform"
            ],
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [
              "u-L0040-11"
            ],
            "full_units_swapped_out": [
              "u-L0022-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s3_karsemine_zephyr_chase",
          "question": "When everything is falling apart, what does Karsemine do along the bank with Zephyr Strike?",
          "expected_answer": "Karsemine casts Zephyr Strike, runs down the bank, and shoots arrows where Bonogo probably was.",
          "must_hit_tokens": [
            "Karsemine",
            "Zephyr",
            "arrows",
            "Bonogo"
          ],
          "expected_route_substrings": [
            "Campaign 1/PCs/karsemine",
            "Campaign 1/PCs/bonogo",
            "Campaign 1/Locations/stonebridge"
          ],
          "min_context_support_ratio": 0.55,
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
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s3_kirfan_debris_help",
          "question": "Who were they helping when they pulled up debris from the broken upriver structure?",
          "expected_answer": "They helped Kirfan pull up debris from the broken structure from upriver.",
          "must_hit_tokens": [
            "Kirfan",
            "debris",
            "upriver"
          ],
          "expected_route_substrings": [
            "Campaign 1/NPCs/kirfan"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Kirfan",
              "debris",
              "upriver"
            ],
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [
              "u-L0003-01",
              "u-L0004-01",
              "u-L0004-02",
              "u-L0006-01",
              "u-L0040-01"
            ],
            "full_units_swapped_out": [
              "u-L0045-04",
              "u-L0045-05",
              "u-L0045-06",
              "u-L0045-07",
              "u-L0045-08"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s3_stafl_nets_town",
          "question": "What does Stafl get the town doing with nets during the flood response?",
          "expected_answer": "Stafl gathers town support and gets nets dropped across the bridge flow ways.",
          "must_hit_tokens": [
            "Stafl",
            "nets",
            "bridge"
          ],
          "expected_route_substrings": [
            "Campaign 1/PCs/stafl",
            "Campaign 1/Locations/stonebridge"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Stafl",
              "bridge",
              "nets"
            ],
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [
              "u-L0040-01",
              "u-L0040-02",
              "u-L0040-03",
              "u-L0040-04",
              "u-L0040-05",
              "u-L0040-06",
              "u-L0040-07",
              "u-L0040-08",
              "u-L0040-09",
              "u-L0040-10",
              "u-L0040-11"
            ],
            "full_units_swapped_out": [
              "meta-session-0003-locations",
              "u-L0014-01",
              "u-L0022-01",
              "u-L0024-01",
              "u-L0026-01",
              "u-L0030-01",
              "u-L0032-01",
              "u-L0036-02",
              "u-L0036-03",
              "u-L0036-04",
              "u-L0036-05"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s3_bonogo_dive_rope_gone",
          "question": "On Bonogo's desperate dive, what happens to Baergrom and the rope?",
          "expected_answer": "Bonogo dives into the river trusting Baergrom to hold the rope, but the rope is immediately torn out of Baergrom's hand.",
          "must_hit_tokens": [
            "Bonogo",
            "Baergrom",
            "rope"
          ],
          "expected_route_substrings": [
            "Campaign 1/PCs/bonogo",
            "Campaign 1/PCs/baergrom",
            "Campaign 1/Locations/stonebridge"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Baergrom",
              "Bonogo",
              "rope"
            ],
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s3_mirathorn_festival_hook",
          "question": "At the end, what Mirathorn/festival hook is the recap teeing up?",
          "expected_answer": "The recap tees up Mirathorn: Pippa had mentioned a city with a festival, and it might be interesting even if it is a long walk.",
          "must_hit_tokens": [
            "Mirathorn",
            "festival",
            "Pippa"
          ],
          "expected_route_substrings": [
            "Campaign 1/Locations/mirathorn",
            "Campaign 1/NPCs/pippa"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Mirathorn",
              "Pippa",
              "festival"
            ],
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [
              "u-L0004-01",
              "u-L0041-04",
              "u-L0041-05"
            ],
            "full_units_swapped_out": [
              "u-L0045-06",
              "u-L0045-07",
              "u-L0045-08"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "c1s3_stonebridge_npc_roster_associated",
          "question": "Give me a list of all NPCs that live in StoneBridge.",
          "expected_answer": "From the C1S3 beats that carry a StoneBridge location tag, the recap co-tags Pippa, Bubbles the Float Goat, and Grishna on those units \u2014 that's scene association in the index, not a residency ledger. Kirfan shows up in the hook line but isn't on a StoneBridge-location tag with those same units.",
          "must_hit_tokens": [
            "Pippa",
            "Bubbles",
            "Grishna",
            "StoneBridge"
          ],
          "expected_route_substrings": [
            "Campaign 1/Locations/stonebridge"
          ],
          "min_context_support_ratio": 0.45,
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
            "context_must_hits_missing": [],
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
            "context_must_hits_missing": [],
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
            "full_units_swapped_in": [],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "passed",
            "reasons": [
              "both_modes_pass"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        }
      ]
    }
  ]
} as const;
// END GENERATED COHORT_L3_QUESTION_DEEP_DIVE

export default function CohortL3QuestionDeepDiveCanvas() {
  const payload = cohortL3QuestionDeepDiveGenerated;
  const renderUnitDiff = (q: any) => {
    const topMissed = Array.isArray(q?.delta?.topk_units_swapped_out) ? q.delta.topk_units_swapped_out : [];
    const fullMissed = Array.isArray(q?.delta?.full_units_swapped_out) ? q.delta.full_units_swapped_out : [];
    const topAdded = Array.isArray(q?.delta?.topk_units_swapped_in) ? q.delta.topk_units_swapped_in : [];
    const fullAdded = Array.isArray(q?.delta?.full_units_swapped_in) ? q.delta.full_units_swapped_in : [];
    return (
      <div style={{ border: "1px solid #f59e0b", borderRadius: 6, padding: 8, marginBottom: 8 }}>
        <div><strong>Swapped out vs legacy-only reference:</strong> {fullMissed.length ? fullMissed.join(", ") : "none"}</div>
        <div><strong>Top-5 swapped out:</strong> {topMissed.length ? topMissed.join(", ") : "none"}</div>
        <div><strong>Swapped in under default (equivalence) ranking:</strong> {fullAdded.length ? fullAdded.join(", ") : "none"}</div>
        <div><strong>Top-5 swapped in:</strong> {topAdded.length ? topAdded.join(", ") : "none"}</div>
      </div>
    );
  };
  const renderDefaultLaneMustHits = (q: any) => {
    const mode = "with_equivalence" as const;
    const required = Array.isArray(q.must_hit_tokens) ? q.must_hit_tokens : [];
    const matched = Array.isArray(q[mode]?.context_must_hits) ? q[mode].context_must_hits : [];
    const missing = Array.isArray(q[mode]?.context_must_hits_missing)
      ? q[mode].context_must_hits_missing
      : required.filter((tok: string) => !matched.includes(tok));
    return (
      <div>
        <div><strong>Required must-hit tokens:</strong> {required.length ? required.join(", ") : "none"}</div>
        <div><strong>Matched must-hit tokens:</strong> {matched.length ? matched.join(", ") : "none"}</div>
        <div><strong>Missing must-hit tokens:</strong> {missing.length ? missing.join(", ") : "none"}</div>
      </div>
    );
  };
  return (
    <div>
      <h1>Cohort L3 Question Deep Dive</h1>
      <p>question_count: {payload.question_count}</p>
      {payload.scenarios.flatMap((s: any) => s.questions).map((q: any) => (
        <details key={q.question_id} open={q.delta.verdict === 'regressed' || q.delta.verdict === 'improved'}>
          <summary>{q.question_id} — {q.delta.verdict}</summary>
          {renderUnitDiff(q)}
          <h3>Default (equivalence-augmented ranking)</h3>
          {renderDefaultLaneMustHits(q)}
          <pre>{JSON.stringify((() => { const { baseline, ...rest } = q; return rest; })(), null, 2)}</pre>
        </details>
      ))}
    </div>
  );
}
