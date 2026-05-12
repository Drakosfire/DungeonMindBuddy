import React from "react";

// BEGIN GENERATED COHORT_L3_QUESTION_DEEP_DIVE
const cohortL3QuestionDeepDiveGenerated = {
  "schema_id": "dmb_breadcrumb_query_cohort_l3_question_delta_v1",
  "cohort_manifest": "evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json",
  "scenario_level_delta_path": "evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s13_v1.json",
  "baseline_schema": "dmb_breadcrumb_query_cohort_summary_v2",
  "question_count": 25,
  "summary": {
    "regressed": 0,
    "improved": 0,
    "unchanged_pass": 0,
    "unchanged_fail": 25
  },
  "scenarios": [
    {
      "scenario_id": "c1s13",
      "question_count": 25,
      "baseline_pass_count": 0,
      "with_equivalence_pass_count": 0,
      "questions": [
        {
          "question_id": "wolf_head_why_academy",
          "question": "Why did the party take Wolf\u2019s head to Stormspire Academy instead of just carrying the whole body?",
          "expected_answer": "The group wanted someone at Stormspire Academy to help cast Speak with Dead so they could learn more about Wolf\u2019s plans. Bonogo did not want to carry an entire body, so he removed Wolf\u2019s head and brought that instead.",
          "must_hit_tokens": [
            "Wolf",
            "Stormspire Academy",
            "Speak with Dead",
            "Bonogo",
            "head"
          ],
          "expected_route_substrings": [
            "Wolf",
            "Stormspire Academy",
            "Bonogo"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Bonogo",
              "Speak with Dead",
              "Stormspire Academy",
              "Wolf",
              "head"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Wolf",
                "matched": false
              },
              {
                "substring": "Stormspire Academy",
                "matched": false
              },
              {
                "substring": "Bonogo",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0021-04",
                "score": 5,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy",
                  "lexical_token:body",
                  "lexical_token:head",
                  "lexical_token:take",
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0021-01",
                "score": 4,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy",
                  "lexical_token:stormspire",
                  "lexical_token:take",
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0025-01",
                "score": 2,
                "line_start": 25,
                "line_end": 25,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy",
                  "lexical_token:stormspire"
                ]
              },
              {
                "unit_id": "u-L0025-05",
                "score": 2,
                "line_start": 25,
                "line_end": 25,
                "routes": [],
                "why_matched": [
                  "lexical_token:head",
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0029-01",
                "score": 2,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:head",
                  "lexical_token:wolf"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Bonogo",
              "Speak with Dead",
              "Stormspire Academy",
              "Wolf",
              "head"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Wolf",
                "matched": false
              },
              {
                "substring": "Stormspire Academy",
                "matched": false
              },
              {
                "substring": "Bonogo",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0021-04",
                "score": 5,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy",
                  "lexical_token:body",
                  "lexical_token:head",
                  "lexical_token:take",
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0021-01",
                "score": 4,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy",
                  "lexical_token:stormspire",
                  "lexical_token:take",
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0029-01",
                "score": 3,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:head",
                  "lexical_token:torbin",
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0025-01",
                "score": 2,
                "line_start": 25,
                "line_end": 25,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy",
                  "lexical_token:stormspire"
                ]
              },
              {
                "unit_id": "u-L0025-05",
                "score": 2,
                "line_start": 25,
                "line_end": 25,
                "routes": [],
                "why_matched": [
                  "lexical_token:head",
                  "lexical_token:wolf"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
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
              "u-L0005-01"
            ],
            "full_units_swapped_out": [
              "u-L0017-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "guards_oily_eyes_alert",
          "question": "What did Thalia do when the guards stopped the group outside the Council Chambers?",
          "expected_answer": "Thalia explained the situation to the guards and set them on alert for anyone with oily eyes.",
          "must_hit_tokens": [
            "Thalia",
            "guards",
            "Council Chambers",
            "oily eyes"
          ],
          "expected_route_substrings": [
            "thalia",
            "council_chambers"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Council Chambers",
              "Thalia",
              "guards",
              "oily eyes"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "thalia",
                "matched": false
              },
              {
                "substring": "council_chambers",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0021-02",
                "score": 5,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:chambers",
                  "lexical_token:council",
                  "lexical_token:guards",
                  "lexical_token:outside",
                  "lexical_token:stopped"
                ]
              },
              {
                "unit_id": "u-L0035-01",
                "score": 2,
                "line_start": 35,
                "line_end": 35,
                "routes": [],
                "why_matched": [
                  "lexical_token:group",
                  "lexical_token:outside"
                ]
              },
              {
                "unit_id": "u-L0017-02",
                "score": 1,
                "line_start": 17,
                "line_end": 17,
                "routes": [],
                "why_matched": [
                  "lexical_token:group"
                ]
              },
              {
                "unit_id": "u-L0021-01",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:group"
                ]
              },
              {
                "unit_id": "u-L0021-03",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:thalia"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Council Chambers",
              "Thalia",
              "guards",
              "oily eyes"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "thalia",
                "matched": false
              },
              {
                "substring": "council_chambers",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0021-02",
                "score": 5,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:chambers",
                  "lexical_token:council",
                  "lexical_token:guards",
                  "lexical_token:outside",
                  "lexical_token:stopped"
                ]
              },
              {
                "unit_id": "u-L0027-02",
                "score": 2,
                "line_start": 27,
                "line_end": 27,
                "routes": [],
                "why_matched": [
                  "lexical_token:group",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0029-01",
                "score": 2,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:group",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0035-01",
                "score": 2,
                "line_start": 35,
                "line_end": 35,
                "routes": [],
                "why_matched": [
                  "lexical_token:group",
                  "lexical_token:outside"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 1,
                "line_start": 5,
                "line_end": 5,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
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
              "u-L0005-01",
              "u-L0027-02",
              "u-L0029-01"
            ],
            "topk_units_swapped_out": [
              "u-L0017-02",
              "u-L0021-01",
              "u-L0021-03"
            ],
            "full_units_swapped_in": [
              "u-L0005-01",
              "u-L0027-02",
              "u-L0029-01",
              "u-L0031-01"
            ],
            "full_units_swapped_out": [
              "u-L0023-02",
              "u-L0023-03",
              "u-L0023-04",
              "u-L0025-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "covert_ops_meat_check",
          "question": "What weird checkpoint did the covert ops group create in the street, and how did the party respond?",
          "expected_answer": "A covert ops group shone a light on the party and demanded to know if they were carrying any meat. Bonogo and Baergrom dumped hundreds of pounds of meat into the street, and the guards acted quickly while a mage burned the tainted meat.",
          "must_hit_tokens": [
            "covert ops",
            "meat",
            "Bonogo",
            "Baergrom",
            "burned"
          ],
          "expected_route_substrings": [
            "Bonogo",
            "Baergrom"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Baergrom",
              "Bonogo",
              "burned",
              "covert ops",
              "meat"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Bonogo",
                "matched": false
              },
              {
                "substring": "Baergrom",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0017-02",
                "score": 3,
                "line_start": 17,
                "line_end": 17,
                "routes": [],
                "why_matched": [
                  "lexical_token:covert",
                  "lexical_token:group",
                  "lexical_token:ops"
                ]
              },
              {
                "unit_id": "u-L0023-02",
                "score": 3,
                "line_start": 23,
                "line_end": 23,
                "routes": [],
                "why_matched": [
                  "lexical_token:covert",
                  "lexical_token:group",
                  "lexical_token:ops"
                ]
              },
              {
                "unit_id": "u-L0021-01",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:group"
                ]
              },
              {
                "unit_id": "u-L0023-01",
                "score": 1,
                "line_start": 23,
                "line_end": 23,
                "routes": [],
                "why_matched": [
                  "lexical_token:street"
                ]
              },
              {
                "unit_id": "u-L0023-03",
                "score": 1,
                "line_start": 23,
                "line_end": 23,
                "routes": [],
                "why_matched": [
                  "lexical_token:street"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Baergrom",
              "Bonogo",
              "burned",
              "covert ops",
              "meat"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Bonogo",
                "matched": false
              },
              {
                "substring": "Baergrom",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0017-02",
                "score": 3,
                "line_start": 17,
                "line_end": 17,
                "routes": [],
                "why_matched": [
                  "lexical_token:covert",
                  "lexical_token:group",
                  "lexical_token:ops"
                ]
              },
              {
                "unit_id": "u-L0023-02",
                "score": 3,
                "line_start": 23,
                "line_end": 23,
                "routes": [],
                "why_matched": [
                  "lexical_token:covert",
                  "lexical_token:group",
                  "lexical_token:ops"
                ]
              },
              {
                "unit_id": "u-L0027-02",
                "score": 2,
                "line_start": 27,
                "line_end": 27,
                "routes": [],
                "why_matched": [
                  "lexical_token:group",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0029-01",
                "score": 2,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:group",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 1,
                "line_start": 5,
                "line_end": 5,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
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
              "u-L0005-01",
              "u-L0027-02",
              "u-L0029-01"
            ],
            "topk_units_swapped_out": [
              "u-L0021-01",
              "u-L0023-01",
              "u-L0023-03"
            ],
            "full_units_swapped_in": [
              "u-L0005-01",
              "u-L0029-03",
              "u-L0031-01",
              "u-L0031-02"
            ],
            "full_units_swapped_out": [
              "u-L0021-02",
              "u-L0021-03",
              "u-L0021-04",
              "u-L0025-05"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "stormspire_activity_arrival",
          "question": "When the group arrived at Stormspire Academy, what was the Academy already doing to respond to the crisis?",
          "expected_answer": "Stormspire Academy was bustling with activity. Wizards were making potions, crafting runes, and working on wards.",
          "must_hit_tokens": [
            "Stormspire Academy",
            "potions",
            "runes",
            "wards"
          ],
          "expected_route_substrings": [
            "Stormspire Academy"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "context_support_below_threshold",
              "missing_expected_route_hit",
              "semantic_verdict:fail_incomplete"
            ],
            "context_support_ratio": 0.25,
            "context_must_hits": [
              "Stormspire Academy"
            ],
            "context_must_hits_missing": [
              "potions",
              "runes",
              "wards"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Stormspire Academy",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0021-01",
                "score": 3,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy",
                  "lexical_token:group",
                  "lexical_token:stormspire"
                ]
              },
              {
                "unit_id": "u-L0025-01",
                "score": 3,
                "line_start": 25,
                "line_end": 25,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy",
                  "lexical_token:group",
                  "lexical_token:stormspire"
                ]
              },
              {
                "unit_id": "u-L0017-02",
                "score": 2,
                "line_start": 17,
                "line_end": 17,
                "routes": [],
                "why_matched": [
                  "lexical_token:already",
                  "lexical_token:group"
                ]
              },
              {
                "unit_id": "u-L0023-04",
                "score": 2,
                "line_start": 23,
                "line_end": 23,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy",
                  "lexical_token:group"
                ]
              },
              {
                "unit_id": "u-L0035-01",
                "score": 2,
                "line_start": 35,
                "line_end": 35,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy",
                  "lexical_token:group"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "context_support_below_threshold",
              "missing_expected_route_hit",
              "semantic_verdict:fail_incomplete"
            ],
            "context_support_ratio": 0.5,
            "context_must_hits": [
              "Stormspire Academy",
              "potions"
            ],
            "context_must_hits_missing": [
              "runes",
              "wards"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Stormspire Academy",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0021-01",
                "score": 3,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy",
                  "lexical_token:group",
                  "lexical_token:stormspire"
                ]
              },
              {
                "unit_id": "u-L0025-01",
                "score": 3,
                "line_start": 25,
                "line_end": 25,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy",
                  "lexical_token:group",
                  "lexical_token:stormspire"
                ]
              },
              {
                "unit_id": "u-L0017-02",
                "score": 2,
                "line_start": 17,
                "line_end": 17,
                "routes": [],
                "why_matched": [
                  "lexical_token:already",
                  "lexical_token:group"
                ]
              },
              {
                "unit_id": "u-L0023-04",
                "score": 2,
                "line_start": 23,
                "line_end": 23,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy",
                  "lexical_token:group"
                ]
              },
              {
                "unit_id": "u-L0027-02",
                "score": 2,
                "line_start": 27,
                "line_end": 27,
                "routes": [],
                "why_matched": [
                  "lexical_token:group",
                  "lexical_token:torbin"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
            "support_ratio_delta": 0.25,
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
              "u-L0027-02"
            ],
            "topk_units_swapped_out": [
              "u-L0035-01"
            ],
            "full_units_swapped_in": [
              "u-L0005-01",
              "u-L0027-02",
              "u-L0031-01"
            ],
            "full_units_swapped_out": [
              "u-L0023-02",
              "u-L0025-03",
              "u-L0025-05"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "mossglade_study_room_torbin",
          "question": "What two useful things did Mossglade tell the party before they split up?",
          "expected_answer": "Mossglade told them about the study room where they could rest and recharge, and she told them Torbin was in the infirmary under Professor Tealeaf\u2019s care.",
          "must_hit_tokens": [
            "Mossglade",
            "study room",
            "Torbin",
            "infirmary",
            "Professor Tealeaf"
          ],
          "expected_route_substrings": [
            "mossglade",
            "torbin",
            "professor_tealeaf"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Mossglade",
              "Professor Tealeaf",
              "Torbin",
              "infirmary",
              "study room"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "mossglade",
                "matched": false
              },
              {
                "substring": "torbin",
                "matched": false
              },
              {
                "substring": "professor_tealeaf",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0027-01",
                "score": 3,
                "line_start": 27,
                "line_end": 27,
                "routes": [],
                "why_matched": [
                  "lexical_token:before",
                  "lexical_token:mossglade",
                  "lexical_token:tell"
                ]
              },
              {
                "unit_id": "u-L0035-02",
                "score": 3,
                "line_start": 35,
                "line_end": 35,
                "routes": [],
                "why_matched": [
                  "lexical_token:split",
                  "lexical_token:things",
                  "lexical_token:two"
                ]
              },
              {
                "unit_id": "u-L0057-02",
                "score": 2,
                "line_start": 57,
                "line_end": 57,
                "routes": [],
                "why_matched": [
                  "lexical_token:before",
                  "lexical_token:party"
                ]
              },
              {
                "unit_id": "u-L0017-02",
                "score": 1,
                "line_start": 17,
                "line_end": 17,
                "routes": [],
                "why_matched": [
                  "lexical_token:mossglade"
                ]
              },
              {
                "unit_id": "u-L0023-02",
                "score": 1,
                "line_start": 23,
                "line_end": 23,
                "routes": [],
                "why_matched": [
                  "lexical_token:tell"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Mossglade",
              "Professor Tealeaf",
              "Torbin",
              "infirmary",
              "study room"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "mossglade",
                "matched": false
              },
              {
                "substring": "torbin",
                "matched": false
              },
              {
                "substring": "professor_tealeaf",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0027-01",
                "score": 3,
                "line_start": 27,
                "line_end": 27,
                "routes": [],
                "why_matched": [
                  "lexical_token:before",
                  "lexical_token:mossglade",
                  "lexical_token:tell"
                ]
              },
              {
                "unit_id": "u-L0035-02",
                "score": 3,
                "line_start": 35,
                "line_end": 35,
                "routes": [],
                "why_matched": [
                  "lexical_token:split",
                  "lexical_token:things",
                  "lexical_token:two"
                ]
              },
              {
                "unit_id": "u-L0027-02",
                "score": 2,
                "line_start": 27,
                "line_end": 27,
                "routes": [],
                "why_matched": [
                  "lexical_token:tell",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0057-02",
                "score": 2,
                "line_start": 57,
                "line_end": 57,
                "routes": [],
                "why_matched": [
                  "lexical_token:before",
                  "lexical_token:party"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 1,
                "line_start": 5,
                "line_end": 5,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
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
              "u-L0005-01",
              "u-L0027-02"
            ],
            "topk_units_swapped_out": [
              "u-L0017-02",
              "u-L0023-02"
            ],
            "full_units_swapped_in": [
              "u-L0005-01",
              "u-L0029-01",
              "u-L0035-01",
              "u-L0035-03",
              "u-L0035-04",
              "u-L0037-02"
            ],
            "full_units_swapped_out": [
              "u-L0029-02",
              "u-L0039-01",
              "u-L0039-02",
              "u-L0041-01",
              "u-L0041-02",
              "u-L0043-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "party_first_split_assignments",
          "question": "When the party first split at the Academy, who went to check on Torbin and who went toward the Necromancer?",
          "expected_answer": "Ephanna and Baergrom went to check on Torbin. Karsemine, Bonogo, Stafl, and Caelynn went to meet with the Necromancer.",
          "must_hit_tokens": [
            "Ephanna",
            "Baergrom",
            "Torbin",
            "Karsemine",
            "Bonogo",
            "Stafl",
            "Caelynn",
            "Necromancer"
          ],
          "expected_route_substrings": [
            "Ephanna",
            "Baergrom",
            "Karsemine",
            "Bonogo",
            "Stafl",
            "Caelynn",
            "Necromancer"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Baergrom",
              "Bonogo",
              "Caelynn",
              "Ephanna",
              "Karsemine",
              "Necromancer",
              "Stafl",
              "Torbin"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Ephanna",
                "matched": false
              },
              {
                "substring": "Baergrom",
                "matched": false
              },
              {
                "substring": "Karsemine",
                "matched": false
              },
              {
                "substring": "Bonogo",
                "matched": false
              },
              {
                "substring": "Stafl",
                "matched": false
              },
              {
                "substring": "Caelynn",
                "matched": false
              },
              {
                "substring": "Necromancer",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0029-01",
                "score": 4,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:check",
                  "lexical_token:first",
                  "lexical_token:necromancer",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0029-03",
                "score": 3,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:check",
                  "lexical_token:necromancer",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 1,
                "line_start": 5,
                "line_end": 5,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0021-01",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy"
                ]
              },
              {
                "unit_id": "u-L0021-04",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Baergrom",
              "Bonogo",
              "Caelynn",
              "Ephanna",
              "Karsemine",
              "Necromancer",
              "Stafl",
              "Torbin"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Ephanna",
                "matched": false
              },
              {
                "substring": "Baergrom",
                "matched": false
              },
              {
                "substring": "Karsemine",
                "matched": false
              },
              {
                "substring": "Bonogo",
                "matched": false
              },
              {
                "substring": "Stafl",
                "matched": false
              },
              {
                "substring": "Caelynn",
                "matched": false
              },
              {
                "substring": "Necromancer",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0029-01",
                "score": 4,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:check",
                  "lexical_token:first",
                  "lexical_token:necromancer",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0029-03",
                "score": 3,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:check",
                  "lexical_token:necromancer",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 1,
                "line_start": 5,
                "line_end": 5,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0021-01",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy"
                ]
              },
              {
                "unit_id": "u-L0021-04",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
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
              "route"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [],
            "topk_units_swapped_out": [],
            "full_units_swapped_in": [],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "tealeaf_unable_to_help",
          "question": "What did Ephanna and Baergrom learn about Tealeaf\u2019s situation with Torbin?",
          "expected_answer": "They learned that Professor Tealeaf had been unable to help Torbin and had also not been able to help work on potions.",
          "must_hit_tokens": [
            "Ephanna",
            "Baergrom",
            "Tealeaf",
            "Torbin",
            "potions"
          ],
          "expected_route_substrings": [
            "ephanna",
            "baergrom",
            "professor_tealeaf",
            "torbin"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Baergrom",
              "Ephanna",
              "Tealeaf",
              "Torbin",
              "potions"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "ephanna",
                "matched": false
              },
              {
                "substring": "baergrom",
                "matched": false
              },
              {
                "substring": "professor_tealeaf",
                "matched": false
              },
              {
                "substring": "torbin",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0031-01",
                "score": 4,
                "line_start": 31,
                "line_end": 31,
                "routes": [],
                "why_matched": [
                  "lexical_token:baergrom",
                  "lexical_token:ephanna",
                  "lexical_token:tealeaf",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0029-03",
                "score": 3,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:baergrom",
                  "lexical_token:ephanna",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0021-01",
                "score": 2,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:about",
                  "lexical_token:learn"
                ]
              },
              {
                "unit_id": "u-L0027-02",
                "score": 2,
                "line_start": 27,
                "line_end": 27,
                "routes": [],
                "why_matched": [
                  "lexical_token:tealeaf",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0031-02",
                "score": 2,
                "line_start": 31,
                "line_end": 31,
                "routes": [],
                "why_matched": [
                  "lexical_token:tealeaf",
                  "lexical_token:torbin"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Baergrom",
              "Ephanna",
              "Tealeaf",
              "Torbin",
              "potions"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "ephanna",
                "matched": false
              },
              {
                "substring": "baergrom",
                "matched": false
              },
              {
                "substring": "professor_tealeaf",
                "matched": false
              },
              {
                "substring": "torbin",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0031-01",
                "score": 4,
                "line_start": 31,
                "line_end": 31,
                "routes": [],
                "why_matched": [
                  "lexical_token:baergrom",
                  "lexical_token:ephanna",
                  "lexical_token:tealeaf",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0029-03",
                "score": 3,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:baergrom",
                  "lexical_token:ephanna",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0021-01",
                "score": 2,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:about",
                  "lexical_token:learn"
                ]
              },
              {
                "unit_id": "u-L0027-02",
                "score": 2,
                "line_start": 27,
                "line_end": 27,
                "routes": [],
                "why_matched": [
                  "lexical_token:tealeaf",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0031-02",
                "score": 2,
                "line_start": 31,
                "line_end": 31,
                "routes": [],
                "why_matched": [
                  "lexical_token:tealeaf",
                  "lexical_token:torbin"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
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
              "route"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [],
            "topk_units_swapped_out": [],
            "full_units_swapped_in": [],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "study_room_short_rest_song",
          "question": "What happened during the magical short rest in the study room?",
          "expected_answer": "The group used the study room for a magical short rest, and Caelynn played a wonderful song on her mother\u2019s pan flute.",
          "must_hit_tokens": [
            "study room",
            "magical short rest",
            "Caelynn",
            "mother's pan flute"
          ],
          "expected_route_substrings": [
            "Caelynn"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Caelynn",
              "magical short rest",
              "mother's pan flute",
              "study room"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Caelynn",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0033-04",
                "score": 5,
                "line_start": 33,
                "line_end": 33,
                "routes": [],
                "why_matched": [
                  "lexical_token:magical",
                  "lexical_token:rest",
                  "lexical_token:room",
                  "lexical_token:short",
                  "lexical_token:study"
                ]
              },
              {
                "unit_id": "u-L0027-01",
                "score": 3,
                "line_start": 27,
                "line_end": 27,
                "routes": [],
                "why_matched": [
                  "lexical_token:rest",
                  "lexical_token:room",
                  "lexical_token:study"
                ]
              },
              {
                "unit_id": "u-L0033-05",
                "score": 2,
                "line_start": 33,
                "line_end": 33,
                "routes": [],
                "why_matched": [
                  "lexical_token:rest",
                  "lexical_token:short"
                ]
              },
              {
                "unit_id": "u-L0057-01",
                "score": 2,
                "line_start": 57,
                "line_end": 57,
                "routes": [],
                "why_matched": [
                  "lexical_token:happened",
                  "lexical_token:room"
                ]
              },
              {
                "unit_id": "u-L0025-05",
                "score": 1,
                "line_start": 25,
                "line_end": 25,
                "routes": [],
                "why_matched": [
                  "lexical_token:rest"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Caelynn",
              "magical short rest",
              "mother's pan flute",
              "study room"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Caelynn",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0033-04",
                "score": 5,
                "line_start": 33,
                "line_end": 33,
                "routes": [],
                "why_matched": [
                  "lexical_token:magical",
                  "lexical_token:rest",
                  "lexical_token:room",
                  "lexical_token:short",
                  "lexical_token:study"
                ]
              },
              {
                "unit_id": "u-L0027-01",
                "score": 3,
                "line_start": 27,
                "line_end": 27,
                "routes": [],
                "why_matched": [
                  "lexical_token:rest",
                  "lexical_token:room",
                  "lexical_token:study"
                ]
              },
              {
                "unit_id": "u-L0031-02",
                "score": 2,
                "line_start": 31,
                "line_end": 31,
                "routes": [],
                "why_matched": [
                  "lexical_token:room",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0033-05",
                "score": 2,
                "line_start": 33,
                "line_end": 33,
                "routes": [],
                "why_matched": [
                  "lexical_token:rest",
                  "lexical_token:short"
                ]
              },
              {
                "unit_id": "u-L0057-01",
                "score": 2,
                "line_start": 57,
                "line_end": 57,
                "routes": [],
                "why_matched": [
                  "lexical_token:happened",
                  "lexical_token:room"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
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
              "u-L0031-02"
            ],
            "topk_units_swapped_out": [
              "u-L0025-05"
            ],
            "full_units_swapped_in": [
              "u-L0005-01",
              "u-L0027-02",
              "u-L0029-01"
            ],
            "full_units_swapped_out": [
              "u-L0033-01",
              "u-L0033-02",
              "u-L0037-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "escaped_meat_second_split",
          "question": "After the rest, what problem forced the party to split again, and who took each job?",
          "expected_answer": "A piece of meat from Caelynn\u2019s bag had escaped and was loose in the Academy. Stafl and Bonogo went to the Necromancer for the ritual, Caelynn, Baergrom, and Karsemine hunted the meat, and Ephanna stayed with Torbin.",
          "must_hit_tokens": [
            "Caelynn\u2019s bag",
            "meat",
            "Stafl",
            "Bonogo",
            "Necromancer",
            "Baergrom",
            "Karsemine",
            "Ephanna",
            "Torbin"
          ],
          "expected_route_substrings": [
            "Caelynn",
            "Stafl",
            "Bonogo",
            "Baergrom",
            "Karsemine",
            "Ephanna",
            "Torbin",
            "Necromancer"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Baergrom",
              "Bonogo",
              "Caelynn\u2019s bag",
              "Ephanna",
              "Karsemine",
              "Necromancer",
              "Stafl",
              "Torbin",
              "meat"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Caelynn",
                "matched": false
              },
              {
                "substring": "Stafl",
                "matched": false
              },
              {
                "substring": "Bonogo",
                "matched": false
              },
              {
                "substring": "Baergrom",
                "matched": false
              },
              {
                "substring": "Karsemine",
                "matched": false
              },
              {
                "substring": "Ephanna",
                "matched": false
              },
              {
                "substring": "Torbin",
                "matched": false
              },
              {
                "substring": "Necromancer",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0035-02",
                "score": 2,
                "line_start": 35,
                "line_end": 35,
                "routes": [],
                "why_matched": [
                  "lexical_token:again",
                  "lexical_token:split"
                ]
              },
              {
                "unit_id": "u-L0017-03",
                "score": 1,
                "line_start": 17,
                "line_end": 17,
                "routes": [],
                "why_matched": [
                  "lexical_token:each"
                ]
              },
              {
                "unit_id": "u-L0023-03",
                "score": 1,
                "line_start": 23,
                "line_end": 23,
                "routes": [],
                "why_matched": [
                  "lexical_token:after"
                ]
              },
              {
                "unit_id": "u-L0025-05",
                "score": 1,
                "line_start": 25,
                "line_end": 25,
                "routes": [],
                "why_matched": [
                  "lexical_token:rest"
                ]
              },
              {
                "unit_id": "u-L0027-01",
                "score": 1,
                "line_start": 27,
                "line_end": 27,
                "routes": [],
                "why_matched": [
                  "lexical_token:rest"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Baergrom",
              "Bonogo",
              "Caelynn\u2019s bag",
              "Ephanna",
              "Karsemine",
              "Necromancer",
              "Stafl",
              "Torbin",
              "meat"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Caelynn",
                "matched": false
              },
              {
                "substring": "Stafl",
                "matched": false
              },
              {
                "substring": "Bonogo",
                "matched": false
              },
              {
                "substring": "Baergrom",
                "matched": false
              },
              {
                "substring": "Karsemine",
                "matched": false
              },
              {
                "substring": "Ephanna",
                "matched": false
              },
              {
                "substring": "Torbin",
                "matched": false
              },
              {
                "substring": "Necromancer",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0035-02",
                "score": 2,
                "line_start": 35,
                "line_end": 35,
                "routes": [],
                "why_matched": [
                  "lexical_token:again",
                  "lexical_token:split"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 1,
                "line_start": 5,
                "line_end": 5,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0017-03",
                "score": 1,
                "line_start": 17,
                "line_end": 17,
                "routes": [],
                "why_matched": [
                  "lexical_token:each"
                ]
              },
              {
                "unit_id": "u-L0023-03",
                "score": 1,
                "line_start": 23,
                "line_end": 23,
                "routes": [],
                "why_matched": [
                  "lexical_token:after"
                ]
              },
              {
                "unit_id": "u-L0025-05",
                "score": 1,
                "line_start": 25,
                "line_end": 25,
                "routes": [],
                "why_matched": [
                  "lexical_token:rest"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
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
              "u-L0005-01"
            ],
            "topk_units_swapped_out": [
              "u-L0027-01"
            ],
            "full_units_swapped_in": [
              "u-L0005-01",
              "u-L0027-02",
              "u-L0029-01"
            ],
            "full_units_swapped_out": [
              "u-L0031-01",
              "u-L0031-02",
              "u-L0033-02"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "speak_with_dead_question_allocation",
          "question": "Why did Stafl and Bonogo only get four questions for Wolf during the Speak with Dead ritual?",
          "expected_answer": "The Speak with Dead ritual granted five questions, but Stafl had promised one question to the Necromancer, leaving Stafl and Bonogo with four.",
          "must_hit_tokens": [
            "Speak with Dead",
            "5 questions",
            "Stafl",
            "Necromancer",
            "4"
          ],
          "expected_route_substrings": [
            "Stafl",
            "Bonogo",
            "Necromancer",
            "Wolf"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "4",
              "5 questions",
              "Necromancer",
              "Speak with Dead",
              "Stafl"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Stafl",
                "matched": false
              },
              {
                "substring": "Bonogo",
                "matched": false
              },
              {
                "substring": "Necromancer",
                "matched": false
              },
              {
                "substring": "Wolf",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0037-01",
                "score": 4,
                "line_start": 37,
                "line_end": 37,
                "routes": [],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:ritual",
                  "lexical_token:stafl",
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0021-01",
                "score": 3,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:dead",
                  "lexical_token:speak",
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0035-03",
                "score": 3,
                "line_start": 35,
                "line_end": 35,
                "routes": [],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:ritual",
                  "lexical_token:stafl"
                ]
              },
              {
                "unit_id": "u-L0037-02",
                "score": 3,
                "line_start": 37,
                "line_end": 37,
                "routes": [],
                "why_matched": [
                  "lexical_token:dead",
                  "lexical_token:questions",
                  "lexical_token:speak"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 2,
                "line_start": 7,
                "line_end": 7,
                "routes": [],
                "why_matched": [
                  "lexical_token:dead",
                  "lexical_token:speak"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "4",
              "5 questions",
              "Necromancer",
              "Speak with Dead",
              "Stafl"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Stafl",
                "matched": false
              },
              {
                "substring": "Bonogo",
                "matched": false
              },
              {
                "substring": "Necromancer",
                "matched": false
              },
              {
                "substring": "Wolf",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0037-01",
                "score": 4,
                "line_start": 37,
                "line_end": 37,
                "routes": [],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:ritual",
                  "lexical_token:stafl",
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0021-01",
                "score": 3,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:dead",
                  "lexical_token:speak",
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0029-01",
                "score": 3,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:speak",
                  "lexical_token:torbin",
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0029-03",
                "score": 3,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:stafl",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0035-03",
                "score": 3,
                "line_start": 35,
                "line_end": 35,
                "routes": [],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:ritual",
                  "lexical_token:stafl"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
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
              "u-L0029-01",
              "u-L0029-03"
            ],
            "topk_units_swapped_out": [
              "u-L0007-01",
              "u-L0037-02"
            ],
            "full_units_swapped_in": [],
            "full_units_swapped_out": [],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "wolf_killer_disambiguation",
          "question": "When Wolf was asked what killed him, who did he indicate, and why is that easy to confuse with the later fight?",
          "expected_answer": "Wolf indicated Bonogo by nodding toward him. This is distinct from the later basement fight where Bonogo kills Draven and later attacks a sleeping guard.",
          "must_hit_tokens": [
            "Wolf",
            "Tell us what killed you",
            "nods",
            "Bonogo",
            "Draven"
          ],
          "expected_route_substrings": [
            "Wolf",
            "Bonogo"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit",
              "semantic_verdict:fail_incomplete"
            ],
            "context_support_ratio": 0.6,
            "context_must_hits": [
              "Bonogo",
              "Tell us what killed you",
              "Wolf"
            ],
            "context_must_hits_missing": [
              "nods",
              "Draven"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Wolf",
                "matched": false
              },
              {
                "substring": "Bonogo",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0021-01",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0021-04",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0025-05",
                "score": 1,
                "line_start": 25,
                "line_end": 25,
                "routes": [],
                "why_matched": [
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0029-01",
                "score": 1,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0033-02",
                "score": 1,
                "line_start": 33,
                "line_end": 33,
                "routes": [],
                "why_matched": [
                  "lexical_token:wolf"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "context_support_below_threshold",
              "missing_expected_route_hit",
              "semantic_verdict:fail_incomplete"
            ],
            "context_support_ratio": 0.4,
            "context_must_hits": [
              "Bonogo",
              "Wolf"
            ],
            "context_must_hits_missing": [
              "Tell us what killed you",
              "nods",
              "Draven"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Wolf",
                "matched": false
              },
              {
                "substring": "Bonogo",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0029-01",
                "score": 2,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin",
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 1,
                "line_start": 5,
                "line_end": 5,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0021-01",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0021-04",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0025-05",
                "score": 1,
                "line_start": 25,
                "line_end": 25,
                "routes": [],
                "why_matched": [
                  "lexical_token:wolf"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
            "support_ratio_delta": -0.2,
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
              "u-L0005-01"
            ],
            "topk_units_swapped_out": [
              "u-L0033-02"
            ],
            "full_units_swapped_in": [
              "u-L0005-01",
              "u-L0025-01",
              "u-L0025-02",
              "u-L0025-03",
              "u-L0027-01",
              "u-L0027-02",
              "u-L0029-02",
              "u-L0029-03",
              "u-L0031-01",
              "u-L0031-02",
              "u-L0033-01",
              "u-L0033-03",
              "u-L0033-04"
            ],
            "full_units_swapped_out": [
              "u-L0037-01",
              "u-L0039-01",
              "u-L0041-01",
              "u-L0043-01",
              "u-L0043-02",
              "u-L0045-01",
              "u-L0045-02",
              "u-L0045-03",
              "u-L0047-01",
              "u-L0047-02",
              "u-L0047-03",
              "u-L0047-04",
              "u-L0047-05"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "lira_shepherd_plot_disambiguation",
          "question": "What did Wolf say about Lira versus the Shepherd, and what should I not conflate between them?",
          "expected_answer": "Wolf said the plotters operate in small groups, so the total number is not known, but Lira will finish the plot before she dies. Separately, Wolf said the Shepherd is everywhere, in the minds of the people, and that the Shepherd will rise from below at the break of dawn.",
          "must_hit_tokens": [
            "Lira",
            "finish the plot",
            "Shepherd",
            "everywhere",
            "minds",
            "break of dawn",
            "rises from below"
          ],
          "expected_route_substrings": [
            "Lira",
            "Shepherd",
            "Wolf"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit",
              "semantic_verdict:fail_incomplete"
            ],
            "context_support_ratio": 0.7142857142857143,
            "context_must_hits": [
              "Lira",
              "Shepherd",
              "everywhere",
              "finish the plot",
              "minds"
            ],
            "context_must_hits_missing": [
              "break of dawn",
              "rises from below"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Lira",
                "matched": false
              },
              {
                "substring": "Shepherd",
                "matched": false
              },
              {
                "substring": "Wolf",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0021-01",
                "score": 2,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:about",
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0021-04",
                "score": 2,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:not",
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0037-01",
                "score": 2,
                "line_start": 37,
                "line_end": 37,
                "routes": [],
                "why_matched": [
                  "lexical_token:about",
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0043-02",
                "score": 2,
                "line_start": 43,
                "line_end": 43,
                "routes": [],
                "why_matched": [
                  "lexical_token:lira",
                  "lexical_token:not"
                ]
              },
              {
                "unit_id": "u-L0025-05",
                "score": 1,
                "line_start": 25,
                "line_end": 25,
                "routes": [],
                "why_matched": [
                  "lexical_token:wolf"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit",
              "semantic_verdict:fail_incomplete"
            ],
            "context_support_ratio": 0.7142857142857143,
            "context_must_hits": [
              "Lira",
              "Shepherd",
              "everywhere",
              "finish the plot",
              "minds"
            ],
            "context_must_hits_missing": [
              "break of dawn",
              "rises from below"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Lira",
                "matched": false
              },
              {
                "substring": "Shepherd",
                "matched": false
              },
              {
                "substring": "Wolf",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0021-01",
                "score": 2,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:about",
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0021-04",
                "score": 2,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:not",
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0029-01",
                "score": 2,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin",
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0031-01",
                "score": 2,
                "line_start": 31,
                "line_end": 31,
                "routes": [],
                "why_matched": [
                  "lexical_token:not",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0037-01",
                "score": 2,
                "line_start": 37,
                "line_end": 37,
                "routes": [],
                "why_matched": [
                  "lexical_token:about",
                  "lexical_token:wolf"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
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
              "u-L0029-01",
              "u-L0031-01"
            ],
            "topk_units_swapped_out": [
              "u-L0025-05",
              "u-L0043-02"
            ],
            "full_units_swapped_in": [
              "u-L0005-01"
            ],
            "full_units_swapped_out": [
              "u-L0033-02"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "cinderbranch_draven_door_disambiguation",
          "question": "Right before the ambush, what did Cinderbranch do and what did Draven do?",
          "expected_answer": "After the ritual, Professor Cinderbranch left the room. Just as that happened, Draven closed and locked the door.",
          "must_hit_tokens": [
            "Professor Cinderbranch",
            "leaves the room",
            "Draven",
            "closes",
            "locks the door"
          ],
          "expected_route_substrings": [
            "professor_cinderbranch",
            "draven"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Draven",
              "Professor Cinderbranch",
              "closes",
              "leaves the room",
              "locks the door"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "professor_cinderbranch",
                "matched": false
              },
              {
                "substring": "draven",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0027-01",
                "score": 2,
                "line_start": 27,
                "line_end": 27,
                "routes": [],
                "why_matched": [
                  "lexical_token:before",
                  "lexical_token:cinderbranch"
                ]
              },
              {
                "unit_id": "u-L0049-01",
                "score": 2,
                "line_start": 49,
                "line_end": 49,
                "routes": [],
                "why_matched": [
                  "lexical_token:cinderbranch",
                  "lexical_token:draven"
                ]
              },
              {
                "unit_id": "u-L0025-05",
                "score": 1,
                "line_start": 25,
                "line_end": 25,
                "routes": [],
                "why_matched": [
                  "lexical_token:cinderbranch"
                ]
              },
              {
                "unit_id": "u-L0043-02",
                "score": 1,
                "line_start": 43,
                "line_end": 43,
                "routes": [],
                "why_matched": [
                  "lexical_token:before"
                ]
              },
              {
                "unit_id": "u-L0051-01",
                "score": 1,
                "line_start": 51,
                "line_end": 51,
                "routes": [],
                "why_matched": [
                  "lexical_token:draven"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Draven",
              "Professor Cinderbranch",
              "closes",
              "leaves the room",
              "locks the door"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "professor_cinderbranch",
                "matched": false
              },
              {
                "substring": "draven",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0027-01",
                "score": 2,
                "line_start": 27,
                "line_end": 27,
                "routes": [],
                "why_matched": [
                  "lexical_token:before",
                  "lexical_token:cinderbranch"
                ]
              },
              {
                "unit_id": "u-L0049-01",
                "score": 2,
                "line_start": 49,
                "line_end": 49,
                "routes": [],
                "why_matched": [
                  "lexical_token:cinderbranch",
                  "lexical_token:draven"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 1,
                "line_start": 5,
                "line_end": 5,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0025-05",
                "score": 1,
                "line_start": 25,
                "line_end": 25,
                "routes": [],
                "why_matched": [
                  "lexical_token:cinderbranch"
                ]
              },
              {
                "unit_id": "u-L0027-02",
                "score": 1,
                "line_start": 27,
                "line_end": 27,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
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
              "u-L0005-01",
              "u-L0027-02"
            ],
            "topk_units_swapped_out": [
              "u-L0043-02",
              "u-L0051-01"
            ],
            "full_units_swapped_in": [
              "u-L0005-01",
              "u-L0027-02",
              "u-L0029-01",
              "u-L0029-03",
              "u-L0031-01",
              "u-L0031-02",
              "u-L0033-01",
              "u-L0047-02",
              "u-L0047-03",
              "u-L0047-04",
              "u-L0047-05",
              "u-L0049-03"
            ],
            "full_units_swapped_out": [
              "u-L0043-02",
              "u-L0051-03",
              "u-L0051-04",
              "u-L0051-05",
              "u-L0053-01",
              "u-L0053-02",
              "u-L0053-03",
              "u-L0053-04",
              "u-L0055-01",
              "u-L0055-02",
              "u-L0057-01",
              "u-L0057-02"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "elite_guards_city_guards_disambiguation",
          "question": "Which guards were helpful earlier, and which guards attacked Stafl and Bonogo later?",
          "expected_answer": "Earlier, city guards stopped the group but Thalia explained the situation and set them on alert; guards also acted when the tainted meat was dumped in the street. Later, two Elite Guards entered the basement morgue with the Sewer Meat Monster and attacked Stafl and Bonogo.",
          "must_hit_tokens": [
            "guards",
            "Thalia",
            "tainted meat",
            "Elite Guards",
            "basement morgue",
            "Stafl",
            "Bonogo"
          ],
          "expected_route_substrings": [
            "elite_guard",
            "stafl",
            "bonogo",
            "basement_morgue"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit",
              "semantic_verdict:fail_incomplete"
            ],
            "context_support_ratio": 0.7142857142857143,
            "context_must_hits": [
              "Bonogo",
              "Elite Guards",
              "Stafl",
              "basement morgue",
              "guards"
            ],
            "context_must_hits_missing": [
              "Thalia",
              "tainted meat"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "elite_guard",
                "matched": false
              },
              {
                "substring": "stafl",
                "matched": false
              },
              {
                "substring": "bonogo",
                "matched": false
              },
              {
                "substring": "basement_morgue",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0021-02",
                "score": 2,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:guards",
                  "lexical_token:were"
                ]
              },
              {
                "unit_id": "u-L0023-03",
                "score": 2,
                "line_start": 23,
                "line_end": 23,
                "routes": [],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:guards"
                ]
              },
              {
                "unit_id": "u-L0029-03",
                "score": 2,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:stafl"
                ]
              },
              {
                "unit_id": "u-L0035-03",
                "score": 2,
                "line_start": 35,
                "line_end": 35,
                "routes": [],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:stafl"
                ]
              },
              {
                "unit_id": "u-L0037-01",
                "score": 2,
                "line_start": 37,
                "line_end": 37,
                "routes": [],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:stafl"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit",
              "semantic_verdict:fail_incomplete"
            ],
            "context_support_ratio": 0.7142857142857143,
            "context_must_hits": [
              "Bonogo",
              "Elite Guards",
              "Stafl",
              "basement morgue",
              "guards"
            ],
            "context_must_hits_missing": [
              "Thalia",
              "tainted meat"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "elite_guard",
                "matched": false
              },
              {
                "substring": "stafl",
                "matched": false
              },
              {
                "substring": "bonogo",
                "matched": false
              },
              {
                "substring": "basement_morgue",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0029-03",
                "score": 3,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:stafl",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0021-02",
                "score": 2,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:guards",
                  "lexical_token:were"
                ]
              },
              {
                "unit_id": "u-L0023-03",
                "score": 2,
                "line_start": 23,
                "line_end": 23,
                "routes": [],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:guards"
                ]
              },
              {
                "unit_id": "u-L0035-03",
                "score": 2,
                "line_start": 35,
                "line_end": 35,
                "routes": [],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:stafl"
                ]
              },
              {
                "unit_id": "u-L0037-01",
                "score": 2,
                "line_start": 37,
                "line_end": 37,
                "routes": [],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:stafl"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
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
              "u-L0005-01",
              "u-L0027-02",
              "u-L0039-01"
            ],
            "full_units_swapped_out": [
              "u-L0037-03",
              "u-L0039-02",
              "u-L0043-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "meat_storage_strongholds_locations",
          "question": "Where did Wolf say the meat-storage strongholds were?",
          "expected_answer": "Wolf said the meat-storage strongholds were hidden in the walls, the guardhouses, and underground.",
          "must_hit_tokens": [
            "meat storage",
            "hidden in the walls",
            "guardhouses",
            "underground"
          ],
          "expected_route_substrings": [
            "Wolf"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "guardhouses",
              "hidden in the walls",
              "meat storage",
              "underground"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Wolf",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0041-01",
                "score": 3,
                "line_start": 41,
                "line_end": 41,
                "routes": [],
                "why_matched": [
                  "lexical_token:meat",
                  "lexical_token:storage",
                  "lexical_token:strongholds"
                ]
              },
              {
                "unit_id": "u-L0021-01",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0021-02",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:were"
                ]
              },
              {
                "unit_id": "u-L0021-04",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0023-02",
                "score": 1,
                "line_start": 23,
                "line_end": 23,
                "routes": [],
                "why_matched": [
                  "lexical_token:meat"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "guardhouses",
              "hidden in the walls",
              "meat storage",
              "underground"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Wolf",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0041-01",
                "score": 3,
                "line_start": 41,
                "line_end": 41,
                "routes": [],
                "why_matched": [
                  "lexical_token:meat",
                  "lexical_token:storage",
                  "lexical_token:strongholds"
                ]
              },
              {
                "unit_id": "u-L0029-01",
                "score": 2,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin",
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 1,
                "line_start": 5,
                "line_end": 5,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0021-01",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0021-02",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:were"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
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
              "u-L0005-01",
              "u-L0029-01"
            ],
            "topk_units_swapped_out": [
              "u-L0021-04",
              "u-L0023-02"
            ],
            "full_units_swapped_in": [
              "u-L0005-01"
            ],
            "full_units_swapped_out": [
              "u-L0025-05"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "shepherd_break_of_dawn_hook",
          "question": "What exactly is the unresolved dawn threat the party learned from Wolf?",
          "expected_answer": "Wolf said there is no stopping the plan, that they are gathering now and will soon erupt as something new led by the Shepherd. The sign of completion will be at the break of dawn, when the Shepherd rises from below. The recap does not resolve what the Shepherd physically is or exactly where below means.",
          "must_hit_tokens": [
            "break of dawn",
            "Shepherd",
            "rises from below",
            "gathering now",
            "erupt",
            "something new"
          ],
          "expected_route_substrings": [
            "Wolf",
            "Shepherd"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "context_support_below_threshold",
              "missing_expected_route_hit",
              "semantic_verdict:fail_incomplete"
            ],
            "context_support_ratio": 0.5,
            "context_must_hits": [
              "Shepherd",
              "break of dawn",
              "rises from below"
            ],
            "context_must_hits_missing": [
              "gathering now",
              "erupt",
              "something new"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Wolf",
                "matched": false
              },
              {
                "substring": "Shepherd",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0021-01",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0021-04",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0025-05",
                "score": 1,
                "line_start": 25,
                "line_end": 25,
                "routes": [],
                "why_matched": [
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0029-01",
                "score": 1,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0033-02",
                "score": 1,
                "line_start": 33,
                "line_end": 33,
                "routes": [],
                "why_matched": [
                  "lexical_token:wolf"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "context_support_below_threshold",
              "missing_expected_route_hit",
              "semantic_verdict:fail_incomplete"
            ],
            "context_support_ratio": 0.0,
            "context_must_hits": [],
            "context_must_hits_missing": [
              "break of dawn",
              "Shepherd",
              "rises from below",
              "gathering now",
              "erupt",
              "something new"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Wolf",
                "matched": false
              },
              {
                "substring": "Shepherd",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0029-01",
                "score": 2,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin",
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 1,
                "line_start": 5,
                "line_end": 5,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0021-01",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0021-04",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0025-05",
                "score": 1,
                "line_start": 25,
                "line_end": 25,
                "routes": [],
                "why_matched": [
                  "lexical_token:wolf"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
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
              "u-L0005-01"
            ],
            "topk_units_swapped_out": [
              "u-L0033-02"
            ],
            "full_units_swapped_in": [
              "u-L0005-01",
              "u-L0025-01",
              "u-L0025-02",
              "u-L0025-03",
              "u-L0027-01",
              "u-L0027-02",
              "u-L0029-02",
              "u-L0029-03",
              "u-L0031-01",
              "u-L0031-02",
              "u-L0033-01",
              "u-L0033-03",
              "u-L0033-04"
            ],
            "full_units_swapped_out": [
              "u-L0037-01",
              "u-L0047-01",
              "u-L0047-02",
              "u-L0047-05",
              "u-L0049-01",
              "u-L0049-02",
              "u-L0049-03",
              "u-L0051-01",
              "u-L0053-04",
              "u-L0055-01",
              "u-L0055-02",
              "u-L0057-01",
              "u-L0057-02"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "empty_ritual_room_bad_sign",
          "question": "Why is the empty ritual room a bad sign after Stafl and Bonogo explain what happened?",
          "expected_answer": "After Stafl and Bonogo explained the ambush to Cinderbranch, the ritual room was found empty. The recap frames that as a bad sign of what is to come, but it does not specify exactly who or what removed the contents or what immediate consequence follows.",
          "must_hit_tokens": [
            "Cinderbranch",
            "ritual room",
            "empty",
            "bad sign",
            "what is to come"
          ],
          "expected_route_substrings": [
            "professor_cinderbranch"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Cinderbranch",
              "bad sign",
              "empty",
              "ritual room",
              "what is to come"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "professor_cinderbranch",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0057-01",
                "score": 8,
                "line_start": 57,
                "line_end": 57,
                "routes": [],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:bad",
                  "lexical_token:empty",
                  "lexical_token:explain",
                  "lexical_token:happened",
                  "lexical_token:ritual",
                  "lexical_token:room",
                  "lexical_token:sign"
                ]
              },
              {
                "unit_id": "u-L0035-03",
                "score": 3,
                "line_start": 35,
                "line_end": 35,
                "routes": [],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:ritual",
                  "lexical_token:stafl"
                ]
              },
              {
                "unit_id": "u-L0037-01",
                "score": 3,
                "line_start": 37,
                "line_end": 37,
                "routes": [],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:ritual",
                  "lexical_token:stafl"
                ]
              },
              {
                "unit_id": "u-L0049-01",
                "score": 3,
                "line_start": 49,
                "line_end": 49,
                "routes": [],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:ritual",
                  "lexical_token:room"
                ]
              },
              {
                "unit_id": "u-L0023-03",
                "score": 2,
                "line_start": 23,
                "line_end": 23,
                "routes": [],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:bonogo"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Cinderbranch",
              "bad sign",
              "empty",
              "ritual room",
              "what is to come"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "professor_cinderbranch",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0057-01",
                "score": 8,
                "line_start": 57,
                "line_end": 57,
                "routes": [],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:bad",
                  "lexical_token:empty",
                  "lexical_token:explain",
                  "lexical_token:happened",
                  "lexical_token:ritual",
                  "lexical_token:room",
                  "lexical_token:sign"
                ]
              },
              {
                "unit_id": "u-L0029-03",
                "score": 3,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:stafl",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0035-03",
                "score": 3,
                "line_start": 35,
                "line_end": 35,
                "routes": [],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:ritual",
                  "lexical_token:stafl"
                ]
              },
              {
                "unit_id": "u-L0037-01",
                "score": 3,
                "line_start": 37,
                "line_end": 37,
                "routes": [],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:ritual",
                  "lexical_token:stafl"
                ]
              },
              {
                "unit_id": "u-L0049-01",
                "score": 3,
                "line_start": 49,
                "line_end": 49,
                "routes": [],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:ritual",
                  "lexical_token:room"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
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
              "u-L0029-03"
            ],
            "topk_units_swapped_out": [
              "u-L0023-03"
            ],
            "full_units_swapped_in": [
              "u-L0031-02"
            ],
            "full_units_swapped_out": [
              "u-L0021-03"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "escaped_meat_academy_hook",
          "question": "What unresolved Academy problem exists outside the morgue fight?",
          "expected_answer": "A piece of meat from Caelynn\u2019s bag escaped and was loose in the Academy. Caelynn, Baergrom, and Karsemine went to hunt it, but the recap does not describe the resolution of that hunt.",
          "must_hit_tokens": [
            "Caelynn\u2019s bag",
            "escaped",
            "loose in the Academy",
            "Baergrom",
            "Karsemine",
            "hunt"
          ],
          "expected_route_substrings": [
            "caelynn",
            "baergrom",
            "karsemine",
            "Stormspire Academy"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "context_support_below_threshold",
              "missing_expected_route_hit",
              "semantic_verdict:fail_incomplete"
            ],
            "context_support_ratio": 0.5,
            "context_must_hits": [
              "Caelynn\u2019s bag",
              "escaped",
              "loose in the Academy"
            ],
            "context_must_hits_missing": [
              "Baergrom",
              "Karsemine",
              "hunt"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "caelynn",
                "matched": false
              },
              {
                "substring": "baergrom",
                "matched": false
              },
              {
                "substring": "karsemine",
                "matched": false
              },
              {
                "substring": "Stormspire Academy",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0035-01",
                "score": 2,
                "line_start": 35,
                "line_end": 35,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy",
                  "lexical_token:outside"
                ]
              },
              {
                "unit_id": "u-L0021-01",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy"
                ]
              },
              {
                "unit_id": "u-L0021-02",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:outside"
                ]
              },
              {
                "unit_id": "u-L0021-04",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy"
                ]
              },
              {
                "unit_id": "u-L0023-01",
                "score": 1,
                "line_start": 23,
                "line_end": 23,
                "routes": [],
                "why_matched": [
                  "lexical_token:outside"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Baergrom",
              "Caelynn\u2019s bag",
              "Karsemine",
              "escaped",
              "hunt",
              "loose in the Academy"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "caelynn",
                "matched": false
              },
              {
                "substring": "baergrom",
                "matched": false
              },
              {
                "substring": "karsemine",
                "matched": false
              },
              {
                "substring": "Stormspire Academy",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0035-01",
                "score": 2,
                "line_start": 35,
                "line_end": 35,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy",
                  "lexical_token:outside"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 1,
                "line_start": 5,
                "line_end": 5,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0021-01",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy"
                ]
              },
              {
                "unit_id": "u-L0021-02",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:outside"
                ]
              },
              {
                "unit_id": "u-L0021-04",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
            "support_ratio_delta": 0.5,
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
              "u-L0005-01"
            ],
            "topk_units_swapped_out": [
              "u-L0023-01"
            ],
            "full_units_swapped_in": [
              "u-L0005-01",
              "u-L0027-02",
              "u-L0031-01",
              "u-L0033-02",
              "u-L0033-03",
              "u-L0033-04",
              "u-L0033-05",
              "u-L0035-02",
              "u-L0035-03",
              "u-L0035-04"
            ],
            "full_units_swapped_out": [
              "u-L0039-01",
              "u-L0039-02",
              "u-L0053-01",
              "u-L0053-02",
              "u-L0053-03",
              "u-L0053-04",
              "u-L0055-01",
              "u-L0055-02",
              "u-L0057-01",
              "u-L0057-02"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "morgue_combat_mechanical_prep",
          "question": "If I need to reconstruct the morgue ambush mechanically, what enemies and battlefield effects are explicitly established?",
          "expected_answer": "The ambush includes Draven, two Elite Guards, and a large disgusting Sewer Meat Monster. The monster moves to the center of the room and oozes goo in a 10-foot radius. Draven casts Fear on Bonogo, the Elite Guards can poison with their attacks, and the Sewer Meat Monster bites Bonogo.",
          "must_hit_tokens": [
            "Draven",
            "2 Elite Guards",
            "Sewer Meat Monster",
            "10 foot radius",
            "Fear",
            "poisoning",
            "bites"
          ],
          "expected_route_substrings": [
            "elite_guard",
            "sewer_meat_monster",
            "bonogo",
            "basement_morgue"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "context_support_below_threshold",
              "missing_expected_route_hit",
              "semantic_verdict:fail_incomplete"
            ],
            "context_support_ratio": 0.2857142857142857,
            "context_must_hits": [
              "bites",
              "poisoning"
            ],
            "context_must_hits_missing": [
              "Draven",
              "2 Elite Guards",
              "Sewer Meat Monster",
              "10 foot radius",
              "Fear"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "elite_guard",
                "matched": false
              },
              {
                "substring": "sewer_meat_monster",
                "matched": false
              },
              {
                "substring": "bonogo",
                "matched": false
              },
              {
                "substring": "basement_morgue",
                "matched": false
              }
            ],
            "hit_count": 17,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0037-01",
                "score": 1,
                "line_start": 37,
                "line_end": 37,
                "routes": [],
                "why_matched": [
                  "lexical_token:morgue"
                ]
              },
              {
                "unit_id": "u-L0055-01",
                "score": 1,
                "line_start": 55,
                "line_end": 55,
                "routes": [],
                "why_matched": [
                  "lexical_token:enemies"
                ]
              },
              {
                "unit_id": "u-L0055-02",
                "score": 0,
                "line_start": 55,
                "line_end": 55,
                "routes": [],
                "why_matched": [
                  "expanded_adjacent:u-L0055-02"
                ]
              },
              {
                "unit_id": "u-L0057-01",
                "score": 0,
                "line_start": 57,
                "line_end": 57,
                "routes": [],
                "why_matched": [
                  "expanded_adjacent:u-L0057-01"
                ]
              },
              {
                "unit_id": "u-L0057-02",
                "score": 0,
                "line_start": 57,
                "line_end": 57,
                "routes": [],
                "why_matched": [
                  "expanded_adjacent:u-L0057-02"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "context_support_below_threshold",
              "missing_expected_route_hit",
              "semantic_verdict:fail_incomplete"
            ],
            "context_support_ratio": 0.2857142857142857,
            "context_must_hits": [
              "bites",
              "poisoning"
            ],
            "context_must_hits_missing": [
              "Draven",
              "2 Elite Guards",
              "Sewer Meat Monster",
              "10 foot radius",
              "Fear"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "elite_guard",
                "matched": false
              },
              {
                "substring": "sewer_meat_monster",
                "matched": false
              },
              {
                "substring": "bonogo",
                "matched": false
              },
              {
                "substring": "basement_morgue",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0005-01",
                "score": 1,
                "line_start": 5,
                "line_end": 5,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0027-02",
                "score": 1,
                "line_start": 27,
                "line_end": 27,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0029-01",
                "score": 1,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0029-03",
                "score": 1,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0031-01",
                "score": 1,
                "line_start": 31,
                "line_end": 31,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
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
              "u-L0005-01",
              "u-L0027-02",
              "u-L0029-01",
              "u-L0029-03",
              "u-L0031-01"
            ],
            "topk_units_swapped_out": [
              "u-L0037-01",
              "u-L0055-01",
              "u-L0055-02",
              "u-L0057-01",
              "u-L0057-02"
            ],
            "full_units_swapped_in": [
              "u-L0005-01",
              "u-L0027-02",
              "u-L0029-01",
              "u-L0029-03",
              "u-L0031-01",
              "u-L0031-02"
            ],
            "full_units_swapped_out": [
              "u-L0035-01",
              "u-L0035-02",
              "u-L0035-03",
              "u-L0037-02",
              "u-L0037-03"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "sleep_spell_chain_mechanical_prep",
          "question": "How did Sleep change the morgue fight, and who used it?",
          "expected_answer": "Stafl cast Sleep on Draven, causing Draven to fall asleep, which let Bonogo sneak attack him for massive damage and kill him. Later, after running outside the door and yelling for help, Stafl cast Sleep on the remaining enemies.",
          "must_hit_tokens": [
            "Stafl",
            "Sleep",
            "Draven",
            "falls asleep",
            "Bonogo",
            "sneak attacks",
            "remaining enemies"
          ],
          "expected_route_substrings": [
            "Stafl",
            "Draven",
            "Bonogo"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Bonogo",
              "Draven",
              "Sleep",
              "Stafl",
              "falls asleep",
              "remaining enemies",
              "sneak attacks"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Stafl",
                "matched": false
              },
              {
                "substring": "Draven",
                "matched": false
              },
              {
                "substring": "Bonogo",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0037-01",
                "score": 1,
                "line_start": 37,
                "line_end": 37,
                "routes": [],
                "why_matched": [
                  "lexical_token:morgue"
                ]
              },
              {
                "unit_id": "u-L0051-04",
                "score": 1,
                "line_start": 51,
                "line_end": 51,
                "routes": [],
                "why_matched": [
                  "lexical_token:sleep"
                ]
              },
              {
                "unit_id": "u-L0051-05",
                "score": 1,
                "line_start": 51,
                "line_end": 51,
                "routes": [],
                "why_matched": [
                  "lexical_token:sleep"
                ]
              },
              {
                "unit_id": "u-L0055-01",
                "score": 1,
                "line_start": 55,
                "line_end": 55,
                "routes": [],
                "why_matched": [
                  "lexical_token:sleep"
                ]
              },
              {
                "unit_id": "u-L0055-02",
                "score": 1,
                "line_start": 55,
                "line_end": 55,
                "routes": [],
                "why_matched": [
                  "lexical_token:sleep"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 0.8571428571428571,
            "context_must_hits": [
              "Bonogo",
              "Draven",
              "Sleep",
              "Stafl",
              "falls asleep",
              "sneak attacks"
            ],
            "context_must_hits_missing": [
              "remaining enemies"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Stafl",
                "matched": false
              },
              {
                "substring": "Draven",
                "matched": false
              },
              {
                "substring": "Bonogo",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0005-01",
                "score": 1,
                "line_start": 5,
                "line_end": 5,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0027-02",
                "score": 1,
                "line_start": 27,
                "line_end": 27,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0029-01",
                "score": 1,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0029-03",
                "score": 1,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0031-01",
                "score": 1,
                "line_start": 31,
                "line_end": 31,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
            "support_ratio_delta": -0.1429,
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
              "u-L0005-01",
              "u-L0027-02",
              "u-L0029-01",
              "u-L0029-03",
              "u-L0031-01"
            ],
            "topk_units_swapped_out": [
              "u-L0037-01",
              "u-L0051-04",
              "u-L0051-05",
              "u-L0055-01",
              "u-L0055-02"
            ],
            "full_units_swapped_in": [
              "u-L0005-01",
              "u-L0027-02",
              "u-L0029-01",
              "u-L0029-03",
              "u-L0031-01",
              "u-L0031-02",
              "u-L0035-04"
            ],
            "full_units_swapped_out": [
              "u-L0037-02",
              "u-L0039-02",
              "u-L0053-04",
              "u-L0055-01",
              "u-L0055-02",
              "u-L0057-01",
              "u-L0057-02"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "stormspire_who_shows_up_location_entity_list",
          "question": "Who shows up or is meaningfully present at Stormspire Academy during this session?",
          "expected_answer": "At Stormspire Academy, the recap meaningfully places Head Clerk Mossglade, Professor Cinderbranch, Professor Tealeaf, Torbin in the infirmary, the Necromancer, Draven, Stafl, Bonogo, Caelynn, Baergrom, Karsemine, Ephanna, wizards or mages working on potions, runes, and wards, two Elite Guards, and the Sewer Meat Monster. Wolf\u2019s head is also brought there for the ritual, but Wolf is dead rather than living there.",
          "must_hit_tokens": [
            "Stormspire Academy",
            "Mossglade",
            "Professor Cinderbranch",
            "Professor Tealeaf",
            "Torbin",
            "Necromancer",
            "Draven",
            "Elite Guards",
            "Sewer Meat Monster"
          ],
          "expected_route_substrings": [
            "Stormspire Academy"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit",
              "missing_location_entity_summary",
              "query_mode_mismatch",
              "semantic_verdict:fail_incomplete"
            ],
            "context_support_ratio": 0.5555555555555556,
            "context_must_hits": [
              "Mossglade",
              "Necromancer",
              "Professor Cinderbranch",
              "Stormspire Academy",
              "Torbin"
            ],
            "context_must_hits_missing": [
              "Professor Tealeaf",
              "Draven",
              "Elite Guards",
              "Sewer Meat Monster"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Stormspire Academy",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0021-01",
                "score": 2,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy",
                  "lexical_token:stormspire"
                ]
              },
              {
                "unit_id": "u-L0025-01",
                "score": 2,
                "line_start": 25,
                "line_end": 25,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy",
                  "lexical_token:stormspire"
                ]
              },
              {
                "unit_id": "u-L0021-04",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy"
                ]
              },
              {
                "unit_id": "u-L0023-04",
                "score": 1,
                "line_start": 23,
                "line_end": 23,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy"
                ]
              },
              {
                "unit_id": "u-L0035-01",
                "score": 1,
                "line_start": 35,
                "line_end": 35,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit",
              "missing_location_entity_summary",
              "query_mode_mismatch",
              "semantic_verdict:fail_incomplete"
            ],
            "context_support_ratio": 0.6666666666666666,
            "context_must_hits": [
              "Mossglade",
              "Necromancer",
              "Professor Cinderbranch",
              "Professor Tealeaf",
              "Stormspire Academy",
              "Torbin"
            ],
            "context_must_hits_missing": [
              "Draven",
              "Elite Guards",
              "Sewer Meat Monster"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Stormspire Academy",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0021-01",
                "score": 2,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy",
                  "lexical_token:stormspire"
                ]
              },
              {
                "unit_id": "u-L0025-01",
                "score": 2,
                "line_start": 25,
                "line_end": 25,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy",
                  "lexical_token:stormspire"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 1,
                "line_start": 5,
                "line_end": 5,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0021-04",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy"
                ]
              },
              {
                "unit_id": "u-L0023-04",
                "score": 1,
                "line_start": 23,
                "line_end": 23,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
            "support_ratio_delta": 0.1111,
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
              "u-L0005-01"
            ],
            "topk_units_swapped_out": [
              "u-L0035-01"
            ],
            "full_units_swapped_in": [
              "u-L0005-01",
              "u-L0027-01",
              "u-L0027-02",
              "u-L0029-01",
              "u-L0029-02",
              "u-L0029-03",
              "u-L0031-01",
              "u-L0031-02",
              "u-L0033-01"
            ],
            "full_units_swapped_out": [
              "u-L0023-01",
              "u-L0025-05",
              "u-L0033-04",
              "u-L0033-05",
              "u-L0035-01",
              "u-L0035-02",
              "u-L0035-03",
              "u-L0035-04",
              "u-L0037-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "mossglade_residency_vs_association",
          "question": "Does the recap establish that Mossglade lives at Stormspire Academy, or only that she works there?",
          "expected_answer": "The recap only establishes that Mossglade is the Head Clerk at Stormspire Academy and is at the desk when the party arrives. It does not say she lives there.",
          "must_hit_tokens": [
            "Mossglade",
            "Head Clerk",
            "Stormspire Academy",
            "desk"
          ],
          "expected_route_substrings": [
            "Mossglade",
            "Stormspire Academy"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Head Clerk",
              "Mossglade",
              "Stormspire Academy",
              "desk"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Mossglade",
                "matched": false
              },
              {
                "substring": "Stormspire Academy",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0021-01",
                "score": 2,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy",
                  "lexical_token:stormspire"
                ]
              },
              {
                "unit_id": "u-L0025-01",
                "score": 2,
                "line_start": 25,
                "line_end": 25,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy",
                  "lexical_token:stormspire"
                ]
              },
              {
                "unit_id": "u-L0017-02",
                "score": 1,
                "line_start": 17,
                "line_end": 17,
                "routes": [],
                "why_matched": [
                  "lexical_token:mossglade"
                ]
              },
              {
                "unit_id": "u-L0021-03",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:there"
                ]
              },
              {
                "unit_id": "u-L0021-04",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Head Clerk",
              "Mossglade",
              "Stormspire Academy",
              "desk"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Mossglade",
                "matched": false
              },
              {
                "substring": "Stormspire Academy",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0021-01",
                "score": 2,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy",
                  "lexical_token:stormspire"
                ]
              },
              {
                "unit_id": "u-L0025-01",
                "score": 2,
                "line_start": 25,
                "line_end": 25,
                "routes": [],
                "why_matched": [
                  "lexical_token:academy",
                  "lexical_token:stormspire"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 1,
                "line_start": 5,
                "line_end": 5,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0017-02",
                "score": 1,
                "line_start": 17,
                "line_end": 17,
                "routes": [],
                "why_matched": [
                  "lexical_token:mossglade"
                ]
              },
              {
                "unit_id": "u-L0021-03",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:there"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
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
              "u-L0005-01"
            ],
            "topk_units_swapped_out": [
              "u-L0021-04"
            ],
            "full_units_swapped_in": [
              "u-L0005-01",
              "u-L0023-01",
              "u-L0023-02",
              "u-L0025-02",
              "u-L0025-04",
              "u-L0025-05",
              "u-L0027-02",
              "u-L0029-02",
              "u-L0029-03"
            ],
            "full_units_swapped_out": [
              "u-L0033-02",
              "u-L0033-03",
              "u-L0033-04",
              "u-L0033-05",
              "u-L0035-01",
              "u-L0035-02",
              "u-L0035-03",
              "u-L0035-04",
              "u-L0037-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "necromancer_question_identity_trap",
          "question": "What did the Necromancer ask Wolf, and is the Necromancer identified as Draven before the ambush?",
          "expected_answer": "The Necromancer asked: what is the plan and how will we know when it is complete? The recap does not explicitly state that the Necromancer and Draven are the same person before the ambush, though Draven closes and locks the door immediately after Cinderbranch leaves.",
          "must_hit_tokens": [
            "Necromancer",
            "What is the plan",
            "how will we know",
            "Draven",
            "closes and locks the door"
          ],
          "expected_route_substrings": [
            "necromancer",
            "wolf"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit",
              "semantic_verdict:fail_incomplete"
            ],
            "context_support_ratio": 0.6,
            "context_must_hits": [
              "Necromancer",
              "What is the plan",
              "how will we know"
            ],
            "context_must_hits_missing": [
              "Draven",
              "closes and locks the door"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "necromancer",
                "matched": false
              },
              {
                "substring": "wolf",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0029-01",
                "score": 2,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:necromancer",
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0047-01",
                "score": 2,
                "line_start": 47,
                "line_end": 47,
                "routes": [],
                "why_matched": [
                  "lexical_token:ask",
                  "lexical_token:necromancer"
                ]
              },
              {
                "unit_id": "u-L0017-01",
                "score": 1,
                "line_start": 17,
                "line_end": 17,
                "routes": [],
                "why_matched": [
                  "lexical_token:ask"
                ]
              },
              {
                "unit_id": "u-L0021-01",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0021-04",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:wolf"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit",
              "semantic_verdict:fail_incomplete"
            ],
            "context_support_ratio": 0.6,
            "context_must_hits": [
              "Necromancer",
              "What is the plan",
              "how will we know"
            ],
            "context_must_hits_missing": [
              "Draven",
              "closes and locks the door"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "necromancer",
                "matched": false
              },
              {
                "substring": "wolf",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0029-01",
                "score": 3,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:necromancer",
                  "lexical_token:torbin",
                  "lexical_token:wolf"
                ]
              },
              {
                "unit_id": "u-L0029-03",
                "score": 2,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:necromancer",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0047-01",
                "score": 2,
                "line_start": 47,
                "line_end": 47,
                "routes": [],
                "why_matched": [
                  "lexical_token:ask",
                  "lexical_token:necromancer"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 1,
                "line_start": 5,
                "line_end": 5,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0017-01",
                "score": 1,
                "line_start": 17,
                "line_end": 17,
                "routes": [],
                "why_matched": [
                  "lexical_token:ask"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
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
              "u-L0005-01",
              "u-L0029-03"
            ],
            "topk_units_swapped_out": [
              "u-L0021-01",
              "u-L0021-04"
            ],
            "full_units_swapped_in": [
              "u-L0005-01"
            ],
            "full_units_swapped_out": [
              "u-L0027-01"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "bonogo_poison_bite_sequence",
          "question": "What happened to Bonogo after he missed Elite Guard 2?",
          "expected_answer": "After Bonogo missed Elite Guard 2 with his bonus attack, that guard attacked and hit Bonogo, poisoning him. Just as he was being poisoned, the Sewer Meat Monster bit him and dealt more damage.",
          "must_hit_tokens": [
            "Bonogo",
            "Elite Guard 2",
            "misses",
            "poisoning",
            "Sewer Monster",
            "bites"
          ],
          "expected_route_substrings": [
            "bonogo",
            "elite_guard",
            "sewer_meat_monster"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Bonogo",
              "Elite Guard 2",
              "Sewer Monster",
              "bites",
              "misses",
              "poisoning"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "bonogo",
                "matched": false
              },
              {
                "substring": "elite_guard",
                "matched": false
              },
              {
                "substring": "sewer_meat_monster",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0023-03",
                "score": 3,
                "line_start": 23,
                "line_end": 23,
                "routes": [],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:bonogo",
                  "lexical_token:guard"
                ]
              },
              {
                "unit_id": "u-L0053-01",
                "score": 3,
                "line_start": 53,
                "line_end": 53,
                "routes": [],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:elite",
                  "lexical_token:guard"
                ]
              },
              {
                "unit_id": "u-L0049-02",
                "score": 2,
                "line_start": 49,
                "line_end": 49,
                "routes": [],
                "why_matched": [
                  "lexical_token:elite",
                  "lexical_token:guard"
                ]
              },
              {
                "unit_id": "u-L0051-03",
                "score": 2,
                "line_start": 51,
                "line_end": 51,
                "routes": [],
                "why_matched": [
                  "lexical_token:elite",
                  "lexical_token:guard"
                ]
              },
              {
                "unit_id": "u-L0053-02",
                "score": 2,
                "line_start": 53,
                "line_end": 53,
                "routes": [],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:guard"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Bonogo",
              "Elite Guard 2",
              "Sewer Monster",
              "bites",
              "misses",
              "poisoning"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "bonogo",
                "matched": false
              },
              {
                "substring": "elite_guard",
                "matched": false
              },
              {
                "substring": "sewer_meat_monster",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0023-03",
                "score": 3,
                "line_start": 23,
                "line_end": 23,
                "routes": [],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:bonogo",
                  "lexical_token:guard"
                ]
              },
              {
                "unit_id": "u-L0053-01",
                "score": 3,
                "line_start": 53,
                "line_end": 53,
                "routes": [],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:elite",
                  "lexical_token:guard"
                ]
              },
              {
                "unit_id": "u-L0029-03",
                "score": 2,
                "line_start": 29,
                "line_end": 29,
                "routes": [],
                "why_matched": [
                  "lexical_token:bonogo",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0049-02",
                "score": 2,
                "line_start": 49,
                "line_end": 49,
                "routes": [],
                "why_matched": [
                  "lexical_token:elite",
                  "lexical_token:guard"
                ]
              },
              {
                "unit_id": "u-L0051-03",
                "score": 2,
                "line_start": 51,
                "line_end": 51,
                "routes": [],
                "why_matched": [
                  "lexical_token:elite",
                  "lexical_token:guard"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
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
              "u-L0029-03"
            ],
            "topk_units_swapped_out": [
              "u-L0053-02"
            ],
            "full_units_swapped_in": [
              "u-L0005-01",
              "u-L0029-03"
            ],
            "full_units_swapped_out": [
              "u-L0021-02",
              "u-L0021-03"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        },
        {
          "question_id": "torbin_thread_status_end",
          "question": "By the end of the recap, what has actually been resolved about Torbin?",
          "expected_answer": "Nothing in the recap resolves Torbin\u2019s condition. Ephanna stays with him, and earlier Ephanna and Baergrom learned that Tealeaf had been unable to help him, but the recap does not state that Torbin recovers.",
          "must_hit_tokens": [
            "Torbin",
            "Ephanna",
            "Tealeaf",
            "unable to help",
            "infirmary"
          ],
          "expected_route_substrings": [
            "torbin",
            "ephanna",
            "professor_tealeaf"
          ],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Ephanna",
              "Tealeaf",
              "Torbin",
              "infirmary",
              "unable to help"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "torbin",
                "matched": false
              },
              {
                "substring": "ephanna",
                "matched": false
              },
              {
                "substring": "professor_tealeaf",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0031-01",
                "score": 2,
                "line_start": 31,
                "line_end": 31,
                "routes": [],
                "why_matched": [
                  "lexical_token:been",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 1,
                "line_start": 5,
                "line_end": 5,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0021-01",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:about"
                ]
              },
              {
                "unit_id": "u-L0025-05",
                "score": 1,
                "line_start": 25,
                "line_end": 25,
                "routes": [],
                "why_matched": [
                  "lexical_token:end"
                ]
              },
              {
                "unit_id": "u-L0027-01",
                "score": 1,
                "line_start": 27,
                "line_end": 27,
                "routes": [],
                "why_matched": [
                  "lexical_token:about"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "Ephanna",
              "Tealeaf",
              "Torbin",
              "infirmary",
              "unable to help"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "torbin",
                "matched": false
              },
              {
                "substring": "ephanna",
                "matched": false
              },
              {
                "substring": "professor_tealeaf",
                "matched": false
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0031-01",
                "score": 2,
                "line_start": 31,
                "line_end": 31,
                "routes": [],
                "why_matched": [
                  "lexical_token:been",
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0005-01",
                "score": 1,
                "line_start": 5,
                "line_end": 5,
                "routes": [],
                "why_matched": [
                  "lexical_token:torbin"
                ]
              },
              {
                "unit_id": "u-L0021-01",
                "score": 1,
                "line_start": 21,
                "line_end": 21,
                "routes": [],
                "why_matched": [
                  "lexical_token:about"
                ]
              },
              {
                "unit_id": "u-L0025-05",
                "score": 1,
                "line_start": 25,
                "line_end": 25,
                "routes": [],
                "why_matched": [
                  "lexical_token:end"
                ]
              },
              {
                "unit_id": "u-L0027-01",
                "score": 1,
                "line_start": 27,
                "line_end": 27,
                "routes": [],
                "why_matched": [
                  "lexical_token:about"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
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
              "route"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [],
            "topk_units_swapped_out": [],
            "full_units_swapped_in": [],
            "full_units_swapped_out": [],
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
  const renderUnitDiff = (q: any) => {
    const topMissed = Array.isArray(q?.delta?.topk_units_swapped_out) ? q.delta.topk_units_swapped_out : [];
    const fullMissed = Array.isArray(q?.delta?.full_units_swapped_out) ? q.delta.full_units_swapped_out : [];
    const topAdded = Array.isArray(q?.delta?.topk_units_swapped_in) ? q.delta.topk_units_swapped_in : [];
    const fullAdded = Array.isArray(q?.delta?.full_units_swapped_in) ? q.delta.full_units_swapped_in : [];
    return (
      <div style={{ border: "1px solid #f59e0b", borderRadius: 6, padding: 8, marginBottom: 8 }}>
        <div><strong>Missed units (baseline only):</strong> {fullMissed.length ? fullMissed.join(", ") : "none"}</div>
        <div><strong>Top-5 missed units:</strong> {topMissed.length ? topMissed.join(", ") : "none"}</div>
        <div><strong>Units added (equivalence only):</strong> {fullAdded.length ? fullAdded.join(", ") : "none"}</div>
        <div><strong>Top-5 added units:</strong> {topAdded.length ? topAdded.join(", ") : "none"}</div>
      </div>
    );
  };
  const renderMustHitComparison = (q: any, mode: "baseline" | "with_equivalence") => {
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
          <h3>Baseline</h3>
          {renderMustHitComparison(q, "baseline")}
          <h3>With Equivalence</h3>
          {renderMustHitComparison(q, "with_equivalence")}
          <pre>{JSON.stringify(q, null, 2)}</pre>
        </details>
      ))}
    </div>
  );
}
