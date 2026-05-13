import React from "react";

// BEGIN GENERATED COHORT_L3_QUESTION_DEEP_DIVE
const cohortL3QuestionDeepDiveGenerated = {
  "schema_id": "dmb_breadcrumb_query_cohort_l3_question_delta_v1",
  "cohort_manifest": "evals/sentence_routing_retrieval_falsification/cohorts/natural_v1.json",
  "scenario_level_delta_path": "evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s1_to_c1s3_v1.json",
  "baseline_schema": "dmb_breadcrumb_query_cohort_summary_v2",
  "question_count": 12,
  "summary": {
    "regressed": 0,
    "improved": 1,
    "unchanged_pass": 7,
    "unchanged_fail": 4
  },
  "failure_diagnostic_summary": {
    "passed": 7,
    "equivalence_helped": 1,
    "ranking_regression": 2,
    "missing_lexical_handle": 1,
    "retriever_support_gap": 0,
    "gold_or_rubric_gap": 1
  },
  "scenarios": [
    {
      "scenario_id": "natural_v1",
      "question_count": 12,
      "baseline_pass_count": 7,
      "with_equivalence_pass_count": 8,
      "questions": [
        {
          "question_id": "nat_captain_after_forest",
          "question": "What happened to the captain after the migrating forest pulled back?",
          "expected_answer": "After the forest pulls back, Caelynn reaches Lysandra through Sara in Mirathorn. Lysandra is relieved but exhausted and disoriented, with fragmented memories of going around the forest, smelling meat, voices in the dark, and something strange happening to time. The party tracks her to a wagon camp, where she has shimmer-like eyes and is drawing a tower tied to the voices. Caelynn makes antidote tea; after drinking it, Lysandra comes out of the spell but remains confused about where she is and how she got there.",
          "must_hit_tokens": [
            "captain",
            "forest",
            "tower",
            "tea"
          ],
          "expected_route_substrings": [
            "NPCs/captain_lysandra_ironveil",
            "NPCs/sara_mirathorn_operator"
          ],
          "min_context_support_ratio": 0.75,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "captain",
              "forest",
              "tea",
              "tower"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "NPCs/captain_lysandra_ironveil",
                "matched": true
              },
              {
                "substring": "NPCs/sara_mirathorn_operator",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0017-04",
                "score": 11,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:forest",
                  "lexical_token:happened",
                  "route_token:captain",
                  "route_token:forest",
                  "route_token:migrating"
                ]
              },
              {
                "unit_id": "u-L0017-07",
                "score": 11,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:forest",
                  "route_token:captain",
                  "route_token:forest",
                  "route_token:migrating"
                ]
              },
              {
                "unit_id": "u-L0019-13",
                "score": 11,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:forest",
                  "route_token:captain",
                  "route_token:forest",
                  "route_token:migrating"
                ]
              },
              {
                "unit_id": "u-L0019-11",
                "score": 10,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:after",
                  "route_token:captain",
                  "route_token:forest",
                  "route_token:migrating"
                ]
              },
              {
                "unit_id": "u-L0017-03",
                "score": 9,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "route_token:captain",
                  "route_token:forest",
                  "route_token:migrating"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "captain",
              "forest",
              "tea",
              "tower"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "NPCs/captain_lysandra_ironveil",
                "matched": true
              },
              {
                "substring": "NPCs/sara_mirathorn_operator",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0017-07",
                "score": 27,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:forest",
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:forest",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:migrating",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-04",
                "score": 26,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:forest",
                  "lexical_token:happened",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:forest",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:migrating",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0019-11",
                "score": 26,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:forest",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:migrating",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0019-13",
                "score": 26,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:forest",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:forest",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:migrating",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-03",
                "score": 25,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:forest",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:migrating",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_pass",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
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
              "u-L0019-04",
              "u-L0019-05",
              "u-L0019-06"
            ],
            "full_units_swapped_out": [
              "meta-session-0020-locations",
              "u-L0021-01",
              "u-L0021-02"
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
          "question_id": "nat_mirathorn_threads",
          "question": "What Mirathorn-linked people, places, and supply concerns showed up in the recap?",
          "expected_answer": "The Mirathorn-linked thread includes Sara, one of Mirathorn's operators, relaying Caelynn's contact with Lysandra. It also includes Professor Tealeaf through Sara's attempted transfer, with Tealeaf not picking up; the route context ties that thread to Stormspire Academy. The supply concern is tainted meat: Stafl suspects someone slipped tainted meat into the provisions before leaving Mirathorn, Caelynn reports the bad meat to Sara, and Sara worries about who can be trusted in the city.",
          "must_hit_tokens": [
            "mirathorn",
            "tealeaf",
            "sara",
            "meat"
          ],
          "expected_route_substrings": [
            "Mirathorn",
            "Stormspire Academy"
          ],
          "min_context_support_ratio": 0.75,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "meat",
              "mirathorn",
              "sara",
              "tealeaf"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Mirathorn",
                "matched": true
              },
              {
                "substring": "Stormspire Academy",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "meta-session-0020-locations",
                "score": 5,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Elderwyld/Cities and Towns/Mirathorn/",
                  "Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/",
                  "Elderwyld/Cities and Towns/Mossford/",
                  "Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Half-Burned Warehouse.md",
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/"
                ],
                "why_matched": [
                  "lexical_token:mirathorn",
                  "lexical_token:places",
                  "route_token:mirathorn"
                ]
              },
              {
                "unit_id": "meta-session-0020-open-loops",
                "score": 4,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/NPCs/professor_merril_tealeaf/",
                  "Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Half-Burned Warehouse.md",
                  "Elderwyld/Unknown Sites/Voices Tower/"
                ],
                "why_matched": [
                  "lexical_token:mirathorn",
                  "route_token:mirathorn"
                ]
              },
              {
                "unit_id": "u-L0017-02",
                "score": 4,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Cities and Towns/Mirathorn/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/"
                ],
                "why_matched": [
                  "lexical_token:mirathorn",
                  "route_token:mirathorn"
                ]
              },
              {
                "unit_id": "u-L0021-03",
                "score": 4,
                "line_start": 21,
                "line_end": 21,
                "routes": [
                  "Elderwyld/Cities and Towns/Mirathorn/",
                  "Longmont Campaign/Campaign 2/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:mirathorn",
                  "route_token:mirathorn"
                ]
              },
              {
                "unit_id": "u-L0017-03",
                "score": 3,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
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
              "meat",
              "mirathorn",
              "sara",
              "tealeaf"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Mirathorn",
                "matched": true
              },
              {
                "substring": "Stormspire Academy",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0017-03",
                "score": 22,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:mirathorn",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-04",
                "score": 21,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:mirathorn",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-05",
                "score": 19,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:mirathorn",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-07",
                "score": 19,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0019-11",
                "score": 19,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
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
              "u-L0017-04",
              "u-L0017-05",
              "u-L0017-07",
              "u-L0019-11"
            ],
            "topk_units_swapped_out": [
              "meta-session-0020-locations",
              "meta-session-0020-open-loops",
              "u-L0017-02",
              "u-L0021-03"
            ],
            "full_units_swapped_in": [
              "u-L0017-06",
              "u-L0017-07",
              "u-L0017-08",
              "u-L0019-06",
              "u-L0019-11"
            ],
            "full_units_swapped_out": [
              "meta-session-0020-locations",
              "meta-session-0020-open-loops",
              "u-L0017-02",
              "u-L0023-02",
              "u-L0023-03"
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
          "question_id": "nat_voices_tower_officer",
          "question": "Does the recap tie voices or a tower drawing to a specific officer?",
          "expected_answer": "Yes. The recap ties the voices and tower drawing to Captain Lysandra Ironveil. Caelynn finds Lysandra drawing in the dirt; Lysandra says the voices are coming from a tower and that she knows where it is. Caelynn later examines the drawing and sees a well-made top-down blueprint of a tower. Lysandra's shimmery eyes and recovery after antidote tea frame the tower/voices clue as part of her impaired state.",
          "must_hit_tokens": [
            "voices",
            "tower",
            "captain",
            "blueprint"
          ],
          "expected_route_substrings": [
            "NPCs/captain_lysandra_ironveil"
          ],
          "min_context_support_ratio": 1.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "blueprint",
              "captain",
              "tower",
              "voices"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "NPCs/captain_lysandra_ironveil",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "meta-session-0020-locations",
                "score": 13,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Elderwyld/Cities and Towns/Mirathorn/",
                  "Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/",
                  "Elderwyld/Cities and Towns/Mossford/",
                  "Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Half-Burned Warehouse.md",
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/"
                ],
                "why_matched": [
                  "lexical_token:specific",
                  "lexical_token:tie",
                  "lexical_token:tower",
                  "lexical_token:voices",
                  "route_token:tie",
                  "route_token:tower",
                  "route_token:voices"
                ]
              },
              {
                "unit_id": "meta-session-0020-open-loops",
                "score": 12,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/NPCs/professor_merril_tealeaf/",
                  "Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Half-Burned Warehouse.md",
                  "Elderwyld/Unknown Sites/Voices Tower/"
                ],
                "why_matched": [
                  "lexical_token:tie",
                  "lexical_token:tower",
                  "lexical_token:voices",
                  "route_token:tie",
                  "route_token:tower",
                  "route_token:voices"
                ]
              },
              {
                "unit_id": "u-L0019-13",
                "score": 10,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:voices",
                  "route_token:tie",
                  "route_token:tower",
                  "route_token:voices"
                ]
              },
              {
                "unit_id": "u-L0019-11",
                "score": 9,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "route_token:tie",
                  "route_token:tower",
                  "route_token:voices"
                ]
              },
              {
                "unit_id": "u-L0019-12",
                "score": 9,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "route_token:tie",
                  "route_token:tower",
                  "route_token:voices"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "blueprint",
              "captain",
              "tower",
              "voices"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "NPCs/captain_lysandra_ironveil",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0019-11",
                "score": 28,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc",
                  "route_token:tie",
                  "route_token:tower",
                  "route_token:voices"
                ]
              },
              {
                "unit_id": "u-L0019-13",
                "score": 28,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:voices",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc",
                  "route_token:tie",
                  "route_token:tower",
                  "route_token:voices"
                ]
              },
              {
                "unit_id": "u-L0019-12",
                "score": 27,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc",
                  "route_token:tie",
                  "route_token:tower",
                  "route_token:voices"
                ]
              },
              {
                "unit_id": "u-L0019-06",
                "score": 26,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/"
                ],
                "why_matched": [
                  "lexical_token:tower",
                  "lexical_token:voices",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc",
                  "route_token:tower",
                  "route_token:voices"
                ]
              },
              {
                "unit_id": "meta-session-0020-open-loops",
                "score": 22,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/NPCs/professor_merril_tealeaf/",
                  "Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Half-Burned Warehouse.md",
                  "Elderwyld/Unknown Sites/Voices Tower/"
                ],
                "why_matched": [
                  "lexical_token:elderwyld",
                  "lexical_token:lysandra",
                  "lexical_token:npc",
                  "lexical_token:route",
                  "lexical_token:tie",
                  "lexical_token:tower",
                  "lexical_token:voices",
                  "route_token:elderwyld",
                  "route_token:npc",
                  "route_token:tie",
                  "route_token:tower",
                  "route_token:voices"
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
              "u-L0019-06"
            ],
            "topk_units_swapped_out": [
              "meta-session-0020-locations"
            ],
            "full_units_swapped_in": [
              "u-L0017-03",
              "u-L0017-06",
              "u-L0017-07",
              "u-L0017-08",
              "u-L0019-01"
            ],
            "full_units_swapped_out": [
              "meta-session-0020-locations",
              "u-L0007-01",
              "u-L0021-01",
              "u-L0021-02",
              "u-L0021-03"
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
          "question_id": "q_lysandra_change_unresolved",
          "question": "What exactly changed for Captain Lysandra after the party returned from the forest, and what remains unresolved?",
          "expected_answer": "Captain Lysandra is no longer simply missing: Caelynn reaches her through Sara, the party tracks her to a wagon camp, and antidote tea breaks the spell-like condition she is under. What changed is that Lysandra can speak again, but she remains exhausted and confused, with fragmented memories of the forest leaving, time behaving strangely, smelling meat, and hearing voices. The unresolved threads are the tower she links to the voices, the detailed tower drawing or blueprint, the tainted meat and trust problem in Mirathorn, Professor Tealeaf not answering, and the storm moving in on the camp.",
          "must_hit_tokens": [
            "captain",
            "tower",
            "tealeaf",
            "meat"
          ],
          "expected_route_substrings": [
            "NPCs/captain_lysandra_ironveil",
            "Stormspire Academy"
          ],
          "min_context_support_ratio": 0.75,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 0.75,
            "context_must_hits": [
              "captain",
              "meat",
              "tower"
            ],
            "context_must_hits_missing": [
              "tealeaf"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "NPCs/captain_lysandra_ironveil",
                "matched": true
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
                "unit_id": "u-L0017-07",
                "score": 12,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:forest",
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:forest",
                  "route_token:lysandra"
                ]
              },
              {
                "unit_id": "u-L0019-11",
                "score": 11,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:forest",
                  "route_token:lysandra"
                ]
              },
              {
                "unit_id": "u-L0019-13",
                "score": 11,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:forest",
                  "route_token:captain",
                  "route_token:forest",
                  "route_token:lysandra"
                ]
              },
              {
                "unit_id": "u-L0017-03",
                "score": 10,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:forest",
                  "route_token:lysandra"
                ]
              },
              {
                "unit_id": "u-L0017-04",
                "score": 10,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:forest",
                  "route_token:captain",
                  "route_token:forest",
                  "route_token:lysandra"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_route_hit"
            ],
            "context_support_ratio": 0.75,
            "context_must_hits": [
              "captain",
              "meat",
              "tower"
            ],
            "context_must_hits_missing": [
              "tealeaf"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "NPCs/captain_lysandra_ironveil",
                "matched": true
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
                "unit_id": "u-L0017-07",
                "score": 24,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:forest",
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:forest",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0019-11",
                "score": 23,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:forest",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0019-13",
                "score": 23,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:forest",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:forest",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-03",
                "score": 22,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:forest",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-04",
                "score": 22,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:forest",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:forest",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
            "support_ratio_delta": 0.0,
            "tokens_added_by_equivalences": [
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [],
            "topk_units_swapped_out": [],
            "full_units_swapped_in": [
              "u-L0019-04",
              "u-L0019-05",
              "u-L0019-06"
            ],
            "full_units_swapped_out": [
              "u-L0017-05",
              "u-L0021-01",
              "u-L0021-02"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "missing_lexical_handle",
            "reasons": [
              "equivalence_missing_expected_route_substrings"
            ],
            "baseline_missing_route_substrings": [
              "Stormspire Academy"
            ],
            "with_equivalence_missing_route_substrings": [
              "Stormspire Academy"
            ]
          }
        },
        {
          "question_id": "q_lysandra_regroups",
          "question": "What happens with Lysandra when she regroups with the team?",
          "expected_answer": "When the team regroups with Lysandra, Karesmine tracks her away from Mossford to a wagon camp with crates and wandering horses. Caelynn approaches the shelter and finds Lysandra drawing in the dirt; Lysandra says it is a tower where the voices are coming from and claims she knows where it is. Caelynn notices Lysandra's eyes are shimmery like the cultists, makes antidote tea from her bag, and after Lysandra drinks it she comes out of the spell but remains confused about where she is and how she arrived.",
          "must_hit_tokens": [
            "wagon",
            "drawing",
            "tower",
            "tea"
          ],
          "expected_route_substrings": [
            "NPCs/captain_lysandra_ironveil",
            "Voices Tower"
          ],
          "min_context_support_ratio": 0.75,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "drawing",
              "tea",
              "tower",
              "wagon"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "NPCs/captain_lysandra_ironveil",
                "matched": true
              },
              {
                "substring": "Voices Tower",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0015-07",
                "score": 4,
                "line_start": 15,
                "line_end": 15,
                "routes": [
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:lysandra"
                ]
              },
              {
                "unit_id": "u-L0017-01",
                "score": 4,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:lysandra"
                ]
              },
              {
                "unit_id": "u-L0017-03",
                "score": 4,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:lysandra"
                ]
              },
              {
                "unit_id": "u-L0017-05",
                "score": 4,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:lysandra"
                ]
              },
              {
                "unit_id": "u-L0017-07",
                "score": 4,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:lysandra"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "drawing",
              "tea",
              "tower",
              "wagon"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "NPCs/captain_lysandra_ironveil",
                "matched": true
              },
              {
                "substring": "Voices Tower",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0017-03",
                "score": 19,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-07",
                "score": 19,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0019-11",
                "score": 19,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-04",
                "score": 18,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-06",
                "score": 18,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
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
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0017-04",
              "u-L0017-06",
              "u-L0019-11"
            ],
            "topk_units_swapped_out": [
              "u-L0015-07",
              "u-L0017-01",
              "u-L0017-05"
            ],
            "full_units_swapped_in": [
              "u-L0017-04",
              "u-L0017-06",
              "u-L0017-08",
              "u-L0019-12",
              "u-L0019-13"
            ],
            "full_units_swapped_out": [
              "u-L0015-07",
              "u-L0017-01",
              "u-L0017-02",
              "u-L0017-05",
              "u-L0017-09"
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
          "question_id": "q_relevant_locations",
          "question": "What are the locations nearby and relevant?",
          "expected_answer": "The nearby and relevant locations are Mossford, the migrating forest, Lysandra's wagon camp outside town, Mirathorn, and the tower indicated by Lysandra's voices/drawing. Mossford is where the townsfolk, ditches, fires, mayor, sheriff, and immediate social aftermath are centered. The migrating forest is the threat that pulls back and turns away from town. Mirathorn matters through Sara, the tainted-supply suspicion, and Tealeaf/Stormspire contact. The tower is still only a clue, but Lysandra says the voices come from it and her drawing gives it a concrete direction for follow-up.",
          "must_hit_tokens": [
            "mossford",
            "forest",
            "mirathorn",
            "tower"
          ],
          "expected_route_substrings": [
            "Mossford",
            "Migrating Forest",
            "Mirathorn",
            "Voices Tower"
          ],
          "min_context_support_ratio": 0.75,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "forest",
              "mirathorn",
              "mossford",
              "tower"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Mossford",
                "matched": true
              },
              {
                "substring": "Migrating Forest",
                "matched": true
              },
              {
                "substring": "Mirathorn",
                "matched": true
              },
              {
                "substring": "Voices Tower",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "meta-session-0020-locations",
                "score": 1,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Elderwyld/Cities and Towns/Mirathorn/",
                  "Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/",
                  "Elderwyld/Cities and Towns/Mossford/",
                  "Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Half-Burned Warehouse.md",
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/"
                ],
                "why_matched": [
                  "lexical_token:locations"
                ]
              },
              {
                "unit_id": "u-L0003-01",
                "score": 0,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/PCs/ephanna/",
                  "Longmont Campaign/Campaign 2/PCs/karsemine/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0003-01"
                ]
              },
              {
                "unit_id": "u-L0003-02",
                "score": 0,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0003-02"
                ]
              },
              {
                "unit_id": "u-L0003-03",
                "score": 0,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0003-03"
                ]
              },
              {
                "unit_id": "meta-session-0020-open-loops",
                "score": 0,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/NPCs/professor_merril_tealeaf/",
                  "Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Half-Burned Warehouse.md",
                  "Elderwyld/Unknown Sites/Voices Tower/"
                ],
                "why_matched": [
                  "expanded_adjacent:meta-session-0020-open-loops"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "forest",
              "mirathorn",
              "mossford",
              "tower"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Mossford",
                "matched": true
              },
              {
                "substring": "Migrating Forest",
                "matched": true
              },
              {
                "substring": "Mirathorn",
                "matched": true
              },
              {
                "substring": "Voices Tower",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0017-03",
                "score": 19,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-07",
                "score": 19,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0019-11",
                "score": 19,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-04",
                "score": 18,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-06",
                "score": 18,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
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
              "u-L0017-03",
              "u-L0017-04",
              "u-L0017-06",
              "u-L0017-07",
              "u-L0019-11"
            ],
            "topk_units_swapped_out": [
              "meta-session-0020-locations",
              "meta-session-0020-open-loops",
              "u-L0003-01",
              "u-L0003-02",
              "u-L0003-03"
            ],
            "full_units_swapped_in": [
              "u-L0017-03",
              "u-L0017-04",
              "u-L0017-06",
              "u-L0017-07",
              "u-L0017-08",
              "u-L0019-01",
              "u-L0019-02",
              "u-L0019-03",
              "u-L0019-04",
              "u-L0019-05",
              "u-L0019-07",
              "u-L0019-08",
              "u-L0019-11",
              "u-L0019-12",
              "u-L0019-13"
            ],
            "full_units_swapped_out": [
              "meta-session-0020-locations",
              "meta-session-0020-open-loops",
              "u-L0003-01",
              "u-L0003-02",
              "u-L0003-03",
              "u-L0005-06",
              "u-L0007-01",
              "u-L0007-03",
              "u-L0009-02",
              "u-L0011-01",
              "u-L0011-02",
              "u-L0013-03",
              "u-L0017-02",
              "u-L0021-03",
              "u-L0021-08"
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
          "question_id": "q_communication_chain",
          "question": "What chain of communication connects Caelynn, Sara, Lysandra, and Tealeaf in the recap?",
          "expected_answer": "The communication chain starts with Caelynn using the rockie-talkie to call Lysandra. Instead of reaching Lysandra directly at first, she is connected to Sara, one of the Mirathorn operators. Sara relays Caelynn's request and connects Caelynn directly to Lysandra. Later, after Lysandra is safe and the tainted meat is discovered, Caelynn calls Sara again; Sara tries to transfer her to Professor Tealeaf at Stormspire Academy, but Tealeaf does not pick up while the group sets camp.",
          "must_hit_tokens": [
            "caelynn",
            "sara",
            "lysandra",
            "tealeaf"
          ],
          "expected_route_substrings": [
            "NPCs/sara_mirathorn_operator",
            "NPCs/captain_lysandra_ironveil",
            "Stormspire Academy"
          ],
          "min_context_support_ratio": 1.0,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_unit_id_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "caelynn",
              "lysandra",
              "sara",
              "tealeaf"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "NPCs/sara_mirathorn_operator",
                "matched": true
              },
              {
                "substring": "NPCs/captain_lysandra_ironveil",
                "matched": true
              },
              {
                "substring": "Stormspire Academy",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0017-05",
                "score": 13,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:caelynn",
                  "lexical_token:connects",
                  "lexical_token:lysandra",
                  "lexical_token:sara",
                  "route_token:caelynn",
                  "route_token:lysandra",
                  "route_token:sara"
                ]
              },
              {
                "unit_id": "u-L0017-03",
                "score": 12,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:caelynn",
                  "lexical_token:lysandra",
                  "lexical_token:sara",
                  "route_token:caelynn",
                  "route_token:lysandra",
                  "route_token:sara"
                ]
              },
              {
                "unit_id": "u-L0021-07",
                "score": 12,
                "line_start": 21,
                "line_end": 21,
                "routes": [
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:caelynn",
                  "lexical_token:lysandra",
                  "lexical_token:sara",
                  "route_token:caelynn",
                  "route_token:lysandra",
                  "route_token:sara"
                ]
              },
              {
                "unit_id": "u-L0017-04",
                "score": 10,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:caelynn",
                  "route_token:caelynn",
                  "route_token:lysandra",
                  "route_token:sara"
                ]
              },
              {
                "unit_id": "u-L0015-07",
                "score": 8,
                "line_start": 15,
                "line_end": 15,
                "routes": [
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:caelynn",
                  "lexical_token:lysandra",
                  "route_token:caelynn",
                  "route_token:lysandra"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_unit_id_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "caelynn",
              "lysandra",
              "sara",
              "tealeaf"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "NPCs/sara_mirathorn_operator",
                "matched": true
              },
              {
                "substring": "NPCs/captain_lysandra_ironveil",
                "matched": true
              },
              {
                "substring": "Stormspire Academy",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0017-03",
                "score": 27,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:caelynn",
                  "lexical_token:lysandra",
                  "lexical_token:sara",
                  "route_token:caelynn",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc",
                  "route_token:sara"
                ]
              },
              {
                "unit_id": "u-L0017-04",
                "score": 25,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:caelynn",
                  "route_token:caelynn",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc",
                  "route_token:sara"
                ]
              },
              {
                "unit_id": "u-L0017-05",
                "score": 25,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:caelynn",
                  "lexical_token:connects",
                  "lexical_token:lysandra",
                  "lexical_token:sara",
                  "route_token:caelynn",
                  "route_token:captain",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc",
                  "route_token:sara"
                ]
              },
              {
                "unit_id": "u-L0021-07",
                "score": 24,
                "line_start": 21,
                "line_end": 21,
                "routes": [
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:caelynn",
                  "lexical_token:lysandra",
                  "lexical_token:sara",
                  "route_token:caelynn",
                  "route_token:captain",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc",
                  "route_token:sara"
                ]
              },
              {
                "unit_id": "u-L0017-06",
                "score": 22,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:caelynn",
                  "route_token:caelynn",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
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
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0017-06"
            ],
            "topk_units_swapped_out": [
              "u-L0015-07"
            ],
            "full_units_swapped_in": [
              "u-L0017-06",
              "u-L0017-07",
              "u-L0017-08",
              "u-L0019-01"
            ],
            "full_units_swapped_out": [
              "u-L0019-03",
              "u-L0019-04",
              "u-L0019-07",
              "u-L0023-03"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "gold_or_rubric_gap",
            "reasons": [
              "no_deterministic_failure_explanation_found"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "q_lysandra_memory_contrast",
          "question": "What does Lysandra remember versus fail to remember after the spell breaks?",
          "expected_answer": "After the spell breaks, Lysandra remembers only fragments. She can report or is reported as remembering that the forest left, that something strange happened to time, that she went around the forest, that she smelled meat while trying to sleep, and that she heard voices in the dark after the group entered the forest. What she fails to remember is the coherent chain of events: she is confused about where she is and how she got there.",
          "must_hit_tokens": [
            "voices",
            "time",
            "meat",
            "confused"
          ],
          "expected_route_substrings": [
            "NPCs/captain_lysandra_ironveil"
          ],
          "min_context_support_ratio": 1.0,
          "baseline": {
            "ok": false,
            "violations": [
              "context_support_below_threshold",
              "missing_expected_unit_id_hit"
            ],
            "context_support_ratio": 0.75,
            "context_must_hits": [
              "confused",
              "meat",
              "voices"
            ],
            "context_must_hits_missing": [
              "time"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "NPCs/captain_lysandra_ironveil",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "u-L0017-07",
                "score": 6,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:lysandra",
                  "lexical_token:remember",
                  "route_token:lysandra"
                ]
              },
              {
                "unit_id": "u-L0019-11",
                "score": 6,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:lysandra",
                  "lexical_token:spell",
                  "route_token:lysandra"
                ]
              },
              {
                "unit_id": "u-L0019-13",
                "score": 5,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:remember",
                  "route_token:lysandra"
                ]
              },
              {
                "unit_id": "u-L0015-07",
                "score": 4,
                "line_start": 15,
                "line_end": 15,
                "routes": [
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:lysandra"
                ]
              },
              {
                "unit_id": "u-L0017-01",
                "score": 4,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:lysandra"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "confused",
              "meat",
              "time",
              "voices"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "NPCs/captain_lysandra_ironveil",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0017-07",
                "score": 21,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:lysandra",
                  "lexical_token:remember",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0019-11",
                "score": 21,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:lysandra",
                  "lexical_token:spell",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0019-13",
                "score": 20,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:after",
                  "lexical_token:remember",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-03",
                "score": 19,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-04",
                "score": 18,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "improved",
            "support_ratio_delta": 0.25,
            "tokens_added_by_equivalences": [
              "captain",
              "dustwalker",
              "elderwyld",
              "ironveil",
              "jove",
              "longmont",
              "npc",
              "route",
              "torbin"
            ],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": [
              "u-L0017-03",
              "u-L0017-04"
            ],
            "topk_units_swapped_out": [
              "u-L0015-07",
              "u-L0017-01"
            ],
            "full_units_swapped_in": [
              "u-L0017-04",
              "u-L0017-06",
              "u-L0017-08"
            ],
            "full_units_swapped_out": [
              "u-L0015-07",
              "u-L0017-01",
              "u-L0017-05"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "equivalence_helped",
            "reasons": [
              "equivalence_mode_passed"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "q_mirathorn_vs_mossford",
          "question": "How is Mirathorn relevant currently, and how is Mossford relevant currently?",
          "expected_answer": "Mirathorn is relevant as the communications and supply-trust thread: Sara is one of its operators, Caelynn reaches Lysandra through Sara, Stafl suspects the tainted meat entered the provisions before leaving Mirathorn, Sara worries about who can be trusted in the city, and Sara tries to transfer Caelynn to Professor Tealeaf at Stormspire Academy. Mossford is relevant as the immediate scene: the town faces the migrating forest, the ditches and fires drive the forest back, the mayor and sheriff thank the party, and the party deals with the local social fallout around Marla, Bonogo, and the workers.",
          "must_hit_tokens": [
            "mirathorn",
            "sara",
            "tealeaf",
            "meat",
            "mossford"
          ],
          "expected_route_substrings": [
            "Mirathorn",
            "Mossford",
            "Stormspire Academy"
          ],
          "min_context_support_ratio": 0.8,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "meat",
              "mirathorn",
              "mossford",
              "sara",
              "tealeaf"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Mirathorn",
                "matched": true
              },
              {
                "substring": "Mossford",
                "matched": true
              },
              {
                "substring": "Stormspire Academy",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "meta-session-0020-locations",
                "score": 8,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Elderwyld/Cities and Towns/Mirathorn/",
                  "Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/",
                  "Elderwyld/Cities and Towns/Mossford/",
                  "Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Half-Burned Warehouse.md",
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/"
                ],
                "why_matched": [
                  "lexical_token:mirathorn",
                  "lexical_token:mossford",
                  "route_token:mirathorn",
                  "route_token:mossford"
                ]
              },
              {
                "unit_id": "meta-session-0020-open-loops",
                "score": 8,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/NPCs/professor_merril_tealeaf/",
                  "Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Half-Burned Warehouse.md",
                  "Elderwyld/Unknown Sites/Voices Tower/"
                ],
                "why_matched": [
                  "lexical_token:mirathorn",
                  "lexical_token:mossford",
                  "route_token:mirathorn",
                  "route_token:mossford"
                ]
              },
              {
                "unit_id": "u-L0017-02",
                "score": 4,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Cities and Towns/Mirathorn/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/"
                ],
                "why_matched": [
                  "lexical_token:mirathorn",
                  "route_token:mirathorn"
                ]
              },
              {
                "unit_id": "u-L0021-03",
                "score": 4,
                "line_start": 21,
                "line_end": 21,
                "routes": [
                  "Elderwyld/Cities and Towns/Mirathorn/",
                  "Longmont Campaign/Campaign 2/PCs/stafl/"
                ],
                "why_matched": [
                  "lexical_token:mirathorn",
                  "route_token:mirathorn"
                ]
              },
              {
                "unit_id": "u-L0007-01",
                "score": 3,
                "line_start": 7,
                "line_end": 7,
                "routes": [
                  "Elderwyld/Cities and Towns/Mossford/",
                  "Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Half-Burned Warehouse.md",
                  "Elderwyld/Cities and Towns/Mossford/NPCs/stuart/",
                  "Longmont Campaign/Campaign 2/PCs/bonogo/"
                ],
                "why_matched": [
                  "route_token:mossford"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "meat",
              "mirathorn",
              "mossford",
              "sara",
              "tealeaf"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Mirathorn",
                "matched": true
              },
              {
                "substring": "Mossford",
                "matched": true
              },
              {
                "substring": "Stormspire Academy",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0017-03",
                "score": 22,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:mirathorn",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-04",
                "score": 21,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:mirathorn",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-05",
                "score": 19,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:mirathorn",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-07",
                "score": 19,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0019-11",
                "score": 19,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
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
              "u-L0017-03",
              "u-L0017-04",
              "u-L0017-05",
              "u-L0017-07",
              "u-L0019-11"
            ],
            "topk_units_swapped_out": [
              "meta-session-0020-locations",
              "meta-session-0020-open-loops",
              "u-L0007-01",
              "u-L0017-02",
              "u-L0021-03"
            ],
            "full_units_swapped_in": [
              "u-L0017-03",
              "u-L0017-04",
              "u-L0017-05",
              "u-L0017-06",
              "u-L0017-07",
              "u-L0017-08",
              "u-L0019-11",
              "u-L0021-08",
              "u-L0021-09",
              "u-L0023-01"
            ],
            "full_units_swapped_out": [
              "meta-session-0020-locations",
              "u-L0007-01",
              "u-L0007-02",
              "u-L0007-03",
              "u-L0007-04",
              "u-L0007-05",
              "u-L0017-01",
              "u-L0017-02",
              "u-L0019-12",
              "u-L0019-13"
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
          "question_id": "q_tower_knowns",
          "question": "What do we know about this tower that came up?",
          "expected_answer": "The recap does not establish the tower as a known visited location yet, but it gives several concrete clues. Lysandra says the voices are coming from a tower and that she knows where it is. Caelynn finds Lysandra drawing in the dirt, then later studies the drawing and sees that it is a well-made top-down blueprint of a tower. The route context treats it as the Voices Tower clue or unknown-site candidate rather than a settled hub.",
          "must_hit_tokens": [
            "voices",
            "tower",
            "blueprint"
          ],
          "expected_route_substrings": [
            "Voices Tower"
          ],
          "min_context_support_ratio": 1.0,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "blueprint",
              "tower",
              "voices"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Voices Tower",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "meta-session-0020-locations",
                "score": 8,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Elderwyld/Cities and Towns/Mirathorn/",
                  "Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/",
                  "Elderwyld/Cities and Towns/Mossford/",
                  "Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Half-Burned Warehouse.md",
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/"
                ],
                "why_matched": [
                  "lexical_token:know",
                  "lexical_token:tower",
                  "route_token:know",
                  "route_token:tower"
                ]
              },
              {
                "unit_id": "meta-session-0020-open-loops",
                "score": 8,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/NPCs/professor_merril_tealeaf/",
                  "Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Half-Burned Warehouse.md",
                  "Elderwyld/Unknown Sites/Voices Tower/"
                ],
                "why_matched": [
                  "lexical_token:know",
                  "lexical_token:tower",
                  "route_token:know",
                  "route_token:tower"
                ]
              },
              {
                "unit_id": "u-L0019-06",
                "score": 8,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/"
                ],
                "why_matched": [
                  "lexical_token:know",
                  "lexical_token:tower",
                  "route_token:know",
                  "route_token:tower"
                ]
              },
              {
                "unit_id": "u-L0019-10",
                "score": 7,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:tower",
                  "route_token:know",
                  "route_token:tower"
                ]
              },
              {
                "unit_id": "u-L0019-09",
                "score": 6,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "route_token:know",
                  "route_token:tower"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "blueprint",
              "tower",
              "voices"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Voices Tower",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0019-06",
                "score": 26,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/"
                ],
                "why_matched": [
                  "lexical_token:know",
                  "lexical_token:tower",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:know",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc",
                  "route_token:tower"
                ]
              },
              {
                "unit_id": "u-L0019-11",
                "score": 25,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:know",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc",
                  "route_token:tower"
                ]
              },
              {
                "unit_id": "u-L0019-12",
                "score": 24,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:know",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc",
                  "route_token:tower"
                ]
              },
              {
                "unit_id": "u-L0019-13",
                "score": 24,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:know",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc",
                  "route_token:tower"
                ]
              },
              {
                "unit_id": "u-L0017-03",
                "score": 19,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
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
              "u-L0017-03",
              "u-L0019-11",
              "u-L0019-12",
              "u-L0019-13"
            ],
            "topk_units_swapped_out": [
              "meta-session-0020-locations",
              "meta-session-0020-open-loops",
              "u-L0019-09",
              "u-L0019-10"
            ],
            "full_units_swapped_in": [
              "u-L0017-03",
              "u-L0017-04",
              "u-L0017-06",
              "u-L0017-07",
              "u-L0019-01"
            ],
            "full_units_swapped_out": [
              "meta-session-0020-locations",
              "u-L0007-06",
              "u-L0021-01",
              "u-L0021-02",
              "u-L0021-03"
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
          "question_id": "q_party_learned_next_prep",
          "question": "What did the party learn from the forest episode that affects next-session prep?",
          "expected_answer": "The forest episode gives the party several prep-relevant facts. The migrating forest responds to the town's fortifications and ditch fires by pulling back and turning east, so terrain manipulation and fire changed its behavior. Lysandra's condition adds a tower/voices lead and shows she may still have dangerous missing-memory gaps after the forest episode. The party also learns that the provisions include tainted meat likely slipped in before leaving Mirathorn, creating a supply and trust problem. Finally, a storm with magical shimmering rain is approaching the camp, so shelter and animal protection matter immediately.",
          "must_hit_tokens": [
            "forest",
            "meat",
            "lysandra",
            "storm"
          ],
          "expected_route_substrings": [
            "Migrating Forest",
            "Mirathorn",
            "NPCs/captain_lysandra_ironveil"
          ],
          "min_context_support_ratio": 0.75,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_unit_id_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "forest",
              "lysandra",
              "meat",
              "storm"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Migrating Forest",
                "matched": true
              },
              {
                "substring": "Mirathorn",
                "matched": true
              },
              {
                "substring": "NPCs/captain_lysandra_ironveil",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "meta-session-0020-locations",
                "score": 4,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Elderwyld/Cities and Towns/Mirathorn/",
                  "Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/",
                  "Elderwyld/Cities and Towns/Mossford/",
                  "Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Half-Burned Warehouse.md",
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/"
                ],
                "why_matched": [
                  "lexical_token:forest",
                  "route_token:forest"
                ]
              },
              {
                "unit_id": "u-L0003-01",
                "score": 4,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/PCs/ephanna/",
                  "Longmont Campaign/Campaign 2/PCs/karsemine/"
                ],
                "why_matched": [
                  "lexical_token:forest",
                  "route_token:forest"
                ]
              },
              {
                "unit_id": "u-L0005-06",
                "score": 4,
                "line_start": 5,
                "line_end": 5,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:forest",
                  "route_token:forest"
                ]
              },
              {
                "unit_id": "u-L0011-02",
                "score": 4,
                "line_start": 11,
                "line_end": 11,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/PCs/ephanna/",
                  "Longmont Campaign/Campaign 2/PCs/karsemine/"
                ],
                "why_matched": [
                  "lexical_token:forest",
                  "route_token:forest"
                ]
              },
              {
                "unit_id": "u-L0013-08",
                "score": 4,
                "line_start": 13,
                "line_end": 13,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:forest",
                  "route_token:forest"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "missing_expected_unit_id_hit"
            ],
            "context_support_ratio": 0.75,
            "context_must_hits": [
              "forest",
              "lysandra",
              "meat"
            ],
            "context_must_hits_missing": [
              "storm"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Migrating Forest",
                "matched": true
              },
              {
                "substring": "Mirathorn",
                "matched": true
              },
              {
                "substring": "NPCs/captain_lysandra_ironveil",
                "matched": true
              }
            ],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": true,
            "top_hits": [
              {
                "unit_id": "u-L0017-07",
                "score": 23,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:forest",
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:forest",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-03",
                "score": 22,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:forest",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-04",
                "score": 22,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:forest",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:forest",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0019-11",
                "score": 22,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:forest",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0019-13",
                "score": 22,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:forest",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:forest",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              }
            ]
          },
          "delta": {
            "verdict": "unchanged_fail",
            "support_ratio_delta": -0.25,
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
              "u-L0017-03",
              "u-L0017-04",
              "u-L0017-07",
              "u-L0019-11",
              "u-L0019-13"
            ],
            "topk_units_swapped_out": [
              "meta-session-0020-locations",
              "u-L0003-01",
              "u-L0005-06",
              "u-L0011-02",
              "u-L0013-08"
            ],
            "full_units_swapped_in": [
              "u-L0019-03",
              "u-L0019-04",
              "u-L0019-05",
              "u-L0019-06",
              "u-L0019-07",
              "u-L0019-08",
              "u-L0019-09",
              "u-L0019-10",
              "u-L0019-11",
              "u-L0019-12",
              "u-L0019-13"
            ],
            "full_units_swapped_out": [
              "meta-session-0020-locations",
              "u-L0003-01",
              "u-L0005-06",
              "u-L0011-02",
              "u-L0013-08",
              "u-L0015-01",
              "u-L0015-02",
              "u-L0017-01",
              "u-L0017-02",
              "u-L0017-05",
              "u-L0017-09"
            ],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "ranking_regression",
            "reasons": [
              "equivalence_lost_required_must_hits"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": []
          }
        },
        {
          "question_id": "q_open_loops_next_session",
          "question": "Which open loops from the recap are actionable for next session?",
          "expected_answer": "The actionable open loops are the tower/voices lead, Lysandra's follow-up condition, the Mirathorn communications thread, the tainted provisions, and the approaching storm. The tower is actionable because Lysandra says the voices come from it and draws a detailed blueprint. Lysandra is awake but confused, so her memories and condition still need follow-up. Sara tries to reach Professor Tealeaf and does not get an answer, while Sara is also worried about who can be trusted in Mirathorn. The tainted meat has to be burned or replaced, Ephanna plans a return to town for supplies, and the party needs shelter from the storm and magical shimmering rain.",
          "must_hit_tokens": [
            "tower",
            "tealeaf",
            "storm",
            "supplies"
          ],
          "expected_route_substrings": [
            "Voices Tower",
            "Stormspire Academy"
          ],
          "min_context_support_ratio": 1.0,
          "baseline": {
            "ok": false,
            "violations": [
              "missing_expected_unit_id_hit"
            ],
            "context_support_ratio": 1.0,
            "context_must_hits": [
              "storm",
              "supplies",
              "tealeaf",
              "tower"
            ],
            "context_must_hits_missing": [],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Voices Tower",
                "matched": true
              },
              {
                "substring": "Stormspire Academy",
                "matched": true
              }
            ],
            "hit_count": 17,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [
              {
                "unit_id": "meta-session-0020-open-loops",
                "score": 2,
                "line_start": 0,
                "line_end": 0,
                "routes": [
                  "Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/NPCs/professor_merril_tealeaf/",
                  "Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Half-Burned Warehouse.md",
                  "Elderwyld/Unknown Sites/Voices Tower/"
                ],
                "why_matched": [
                  "lexical_token:loops",
                  "lexical_token:open"
                ]
              },
              {
                "unit_id": "u-L0003-01",
                "score": 0,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/PCs/ephanna/",
                  "Longmont Campaign/Campaign 2/PCs/karsemine/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0003-01"
                ]
              },
              {
                "unit_id": "u-L0003-02",
                "score": 0,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0003-02"
                ]
              },
              {
                "unit_id": "u-L0003-03",
                "score": 0,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0003-03"
                ]
              },
              {
                "unit_id": "u-L0003-04",
                "score": 0,
                "line_start": 3,
                "line_end": 3,
                "routes": [
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "expanded_adjacent:u-L0003-04"
                ]
              }
            ]
          },
          "with_equivalence": {
            "ok": false,
            "violations": [
              "context_support_below_threshold",
              "missing_expected_route_hit",
              "missing_expected_unit_id_hit",
              "semantic_verdict:fail_incomplete"
            ],
            "context_support_ratio": 0.5,
            "context_must_hits": [
              "supplies",
              "tower"
            ],
            "context_must_hits_missing": [
              "tealeaf",
              "storm"
            ],
            "semantic_verdict": "",
            "expected_route_substring_breakdown": [
              {
                "substring": "Voices Tower",
                "matched": true
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
                "unit_id": "u-L0017-03",
                "score": 19,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-07",
                "score": 19,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0019-11",
                "score": 19,
                "line_start": 19,
                "line_end": 19,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Elderwyld/Unknown Sites/Voices Tower/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "lexical_token:lysandra",
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-04",
                "score": 18,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/"
                ],
                "why_matched": [
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
                ]
              },
              {
                "unit_id": "u-L0017-06",
                "score": 18,
                "line_start": 17,
                "line_end": 17,
                "routes": [
                  "Elderwyld/Migrating Forest/",
                  "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                  "Longmont Campaign/Campaign 2/PCs/caelynn/",
                  "Longmont Campaign/Campaign 2/Parties/questionable_company/"
                ],
                "why_matched": [
                  "route_token:captain",
                  "route_token:elderwyld",
                  "route_token:ironveil",
                  "route_token:longmont",
                  "route_token:lysandra",
                  "route_token:npc"
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
              "u-L0017-03",
              "u-L0017-04",
              "u-L0017-06",
              "u-L0017-07",
              "u-L0019-11"
            ],
            "topk_units_swapped_out": [
              "meta-session-0020-open-loops",
              "u-L0003-01",
              "u-L0003-02",
              "u-L0003-03",
              "u-L0003-04"
            ],
            "full_units_swapped_in": [
              "u-L0017-03",
              "u-L0017-04",
              "u-L0017-06",
              "u-L0017-07",
              "u-L0017-08",
              "u-L0019-01",
              "u-L0019-02",
              "u-L0019-03",
              "u-L0019-04",
              "u-L0019-05",
              "u-L0019-07",
              "u-L0019-08",
              "u-L0019-11",
              "u-L0019-12",
              "u-L0019-13"
            ],
            "full_units_swapped_out": [
              "meta-session-0020-locations",
              "meta-session-0020-open-loops",
              "u-L0003-01",
              "u-L0003-02",
              "u-L0003-03",
              "u-L0003-04",
              "u-L0007-01",
              "u-L0007-03",
              "u-L0011-01",
              "u-L0013-03",
              "u-L0017-02",
              "u-L0021-03",
              "u-L0021-09",
              "u-L0023-01"
            ],
            "substrings_flipped_lost": [
              "Stormspire Academy"
            ],
            "substrings_flipped_gained": []
          },
          "failure_diagnostic": {
            "bucket": "ranking_regression",
            "reasons": [
              "equivalence_lost_context_support_ratio",
              "equivalence_lost_required_must_hits",
              "equivalence_lost_route_substrings"
            ],
            "baseline_missing_route_substrings": [],
            "with_equivalence_missing_route_substrings": [
              "Stormspire Academy"
            ]
          }
        }
      ]
    }
  ]
} as const;
// END GENERATED COHORT_L3_QUESTION_DEEP_DIVE

export default function CohortL3QuestionDeepDiveCanvas() {
  const payload = cohortL3QuestionDeepDiveGenerated;
  const cohortId = String(payload?.cohort_manifest || "").split("/").pop()?.replace(/\.json$/i, "") || "unknown";
  const summary = payload?.summary || {};
  const scenario = Array.isArray(payload?.scenarios) && payload.scenarios.length > 0 ? payload.scenarios[0] : {};
  const failureSummary = payload?.failure_diagnostic_summary || {};

  const renderMustHitComparison = (q: any) => {
    const required = Array.isArray(q?.must_hit_tokens) ? q.must_hit_tokens : [];
    const baselineMatched = Array.isArray(q?.baseline?.context_must_hits) ? q.baseline.context_must_hits : [];
    const baselineMissing = Array.isArray(q?.baseline?.context_must_hits_missing)
      ? q.baseline.context_must_hits_missing
      : required.filter((tok: string) => !baselineMatched.includes(tok));
    const defaultMatched = Array.isArray(q?.with_equivalence?.context_must_hits) ? q.with_equivalence.context_must_hits : [];
    const defaultMissing = Array.isArray(q?.with_equivalence?.context_must_hits_missing)
      ? q.with_equivalence.context_must_hits_missing
      : required.filter((tok: string) => !defaultMatched.includes(tok));

    return (
      <div style={{ border: "1px solid #e5e7eb", borderRadius: 6, padding: 8, marginBottom: 8 }}>
        <div><strong>Required must-hit tokens:</strong> {required.length ? required.join(", ") : "none"}</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 6 }}>
          <div>
            <strong>Baseline</strong>
            <div>Matched: {baselineMatched.length ? baselineMatched.join(", ") : "none"}</div>
            <div>Missing: {baselineMissing.length ? baselineMissing.join(", ") : "none"}</div>
          </div>
          <div>
            <strong>Default</strong>
            <div>Matched: {defaultMatched.length ? defaultMatched.join(", ") : "none"}</div>
            <div>Missing: {defaultMissing.length ? defaultMissing.join(", ") : "none"}</div>
          </div>
        </div>
      </div>
    );
  };

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

  return (
    <div>
      <h1>Cohort L3 Question Deep Dive — {cohortId}</h1>
      <div>
        <p>question_count: {payload.question_count}</p>
        <p>summary.regressed: {summary.regressed ?? 0}</p>
        <p>summary.improved: {summary.improved ?? 0}</p>
        <p>summary.unchanged_pass: {summary.unchanged_pass ?? 0}</p>
        <p>summary.unchanged_fail: {summary.unchanged_fail ?? 0}</p>
        <p>scenario baseline_pass_count: {scenario.baseline_pass_count ?? 0}</p>
        <p>scenario with_equivalence_pass_count: {scenario.with_equivalence_pass_count ?? 0}</p>
      </div>
      <h2>failure_diagnostic_summary</h2>
      <ul>
        {Object.entries(failureSummary).map(([k, v]) => (
          <li key={k}>{k}: {String(v)}</li>
        ))}
      </ul>
      {payload.scenarios.flatMap((s: any) => s.questions).map((q: any) => (
        <details key={q.question_id} open={["regressed", "improved", "unchanged_fail"].includes(q.delta.verdict)}>
          <summary>{q.question_id} — {q.delta.verdict}</summary>
          <div><strong>failure_diagnostic.bucket:</strong> {q?.failure_diagnostic?.bucket || "n/a"}</div>
          <div><strong>failure_diagnostic.reasons:</strong> {Array.isArray(q?.failure_diagnostic?.reasons) && q.failure_diagnostic.reasons.length ? q.failure_diagnostic.reasons.join(", ") : "none"}</div>
          <div><strong>support_ratio_delta:</strong> {q?.delta?.support_ratio_delta ?? "n/a"}</div>
          {renderUnitDiff(q)}
          {(q.delta.verdict === "regressed" || q.delta.verdict === "unchanged_fail") && renderMustHitComparison(q)}
          <h3>Default (equivalence-augmented ranking)</h3>
          <pre>{JSON.stringify((() => { const { baseline, ...rest } = q; return rest; })(), null, 2)}</pre>
        </details>
      ))}
    </div>
  );
}
