import React from "react";

// BEGIN GENERATED COHORT_L3_ALIAS_SATURATION
const cohortL3AliasSaturationGenerated = {
  "schema_id": "dmb_cohort_l3_alias_saturation_v1",
  "inputs": [
    "evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json",
    "evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json"
  ],
  "question_count": 56,
  "verdict_counts": {
    "regressed": 2,
    "improved": 1,
    "unchanged_pass": 49,
    "unchanged_fail": 4
  },
  "rows": [
    {
      "scenario_id": "c1s1",
      "question_id": "c1s1_party_roster_origin",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0013-01"
      ],
      "topk_swapped_out": [
        "u-L0011-01"
      ],
      "contested_slot_unit_in": "u-L0013-01",
      "contested_slot_unit_out": "u-L0011-01",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s1",
      "question_id": "c1s1_party_classes_species",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0013-01"
      ],
      "topk_swapped_out": [
        "u-L0003-01"
      ],
      "contested_slot_unit_in": "u-L0013-01",
      "contested_slot_unit_out": "u-L0003-01",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s1",
      "question_id": "c1s1_stonebridge_known_for",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [],
      "topk_swapped_out": [],
      "contested_slot_unit_in": null,
      "contested_slot_unit_out": null,
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s1",
      "question_id": "c1s1_glowkindle_job_source",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0005-02",
        "u-L0007-01",
        "u-L0009-01",
        "u-L0013-01"
      ],
      "topk_swapped_out": [
        "u-L0013-04",
        "u-L0015-01",
        "u-L0017-01",
        "u-L0017-02"
      ],
      "contested_slot_unit_in": "u-L0005-02",
      "contested_slot_unit_out": "u-L0013-04",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s1",
      "question_id": "c1s1_grishna_directions",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0005-03"
      ],
      "topk_swapped_out": [
        "u-L0003-01"
      ],
      "contested_slot_unit_in": "u-L0005-03",
      "contested_slot_unit_out": "u-L0003-01",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s1",
      "question_id": "c1s1_brewery_compass_direction",
      "verdict": "regressed",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0005-03",
        "u-L0007-01"
      ],
      "topk_swapped_out": [
        "u-L0003-01",
        "u-L0005-01"
      ],
      "contested_slot_unit_in": "u-L0005-03",
      "contested_slot_unit_out": "u-L0003-01",
      "support_ratio_delta": -0.5
    },
    {
      "scenario_id": "c1s1",
      "question_id": "c1s1_bonogo_firkin",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0005-02",
        "u-L0005-03"
      ],
      "topk_swapped_out": [
        "u-L0007-02",
        "u-L0007-04"
      ],
      "contested_slot_unit_in": "u-L0005-02",
      "contested_slot_unit_out": "u-L0007-02",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s1",
      "question_id": "c1s1_route_to_brewery",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [],
      "topk_swapped_out": [],
      "contested_slot_unit_in": null,
      "contested_slot_unit_out": null,
      "support_ratio_delta": 0.3333
    },
    {
      "scenario_id": "c1s1",
      "question_id": "c1s1_stone_foot_landmark",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0005-02",
        "u-L0005-03",
        "u-L0009-01",
        "u-L0013-01"
      ],
      "topk_swapped_out": [
        "meta-session-0001-locations",
        "u-L0007-02",
        "u-L0007-04",
        "u-L0009-04"
      ],
      "contested_slot_unit_in": "u-L0005-02",
      "contested_slot_unit_out": "meta-session-0001-locations",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s1",
      "question_id": "c1s1_brewery_arrival",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [],
      "topk_swapped_out": [],
      "contested_slot_unit_in": null,
      "contested_slot_unit_out": null,
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s1",
      "question_id": "c1s1_glowkindle_offer",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [],
      "topk_swapped_out": [],
      "contested_slot_unit_in": null,
      "contested_slot_unit_out": null,
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s1",
      "question_id": "c1s1_rat_incident_origin",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0005-02",
        "u-L0007-01",
        "u-L0009-01"
      ],
      "topk_swapped_out": [
        "u-L0007-04",
        "u-L0013-02",
        "u-L0013-03"
      ],
      "contested_slot_unit_in": "u-L0005-02",
      "contested_slot_unit_out": "u-L0007-04",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s1",
      "question_id": "c1s1_first_combat_cost",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0009-01",
        "u-L0013-01"
      ],
      "topk_swapped_out": [
        "u-L0003-01",
        "u-L0013-03"
      ],
      "contested_slot_unit_in": "u-L0009-01",
      "contested_slot_unit_out": "u-L0003-01",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s1",
      "question_id": "c1s1_post_combat_exploration",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0005-02",
        "u-L0005-03",
        "u-L0007-01",
        "u-L0013-01"
      ],
      "topk_swapped_out": [
        "u-L0003-01",
        "u-L0013-02",
        "u-L0013-03",
        "u-L0017-01"
      ],
      "contested_slot_unit_in": "u-L0005-02",
      "contested_slot_unit_out": "u-L0003-01",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s1",
      "question_id": "c1s1_karsemine_spider_reveal",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0005-02"
      ],
      "topk_swapped_out": [
        "u-L0011-02"
      ],
      "contested_slot_unit_in": "u-L0005-02",
      "contested_slot_unit_out": "u-L0011-02",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s1",
      "question_id": "c1s1_final_threat",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0007-01",
        "u-L0009-01",
        "u-L0013-01"
      ],
      "topk_swapped_out": [
        "meta-session-0001-locations",
        "u-L0003-01",
        "u-L0005-01"
      ],
      "contested_slot_unit_in": "u-L0007-01",
      "contested_slot_unit_out": "meta-session-0001-locations",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s2",
      "question_id": "c1s2_threat_inventory",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0007-01",
        "u-L0011-01"
      ],
      "topk_swapped_out": [
        "u-L0005-01",
        "u-L0011-03"
      ],
      "contested_slot_unit_in": "u-L0007-01",
      "contested_slot_unit_out": "u-L0005-01",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s2",
      "question_id": "c1s2_basement_clearing_payoff",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [],
      "topk_swapped_out": [],
      "contested_slot_unit_in": null,
      "contested_slot_unit_out": null,
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s2",
      "question_id": "c1s2_glowkindle_stash_deal",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [],
      "topk_swapped_out": [],
      "contested_slot_unit_in": null,
      "contested_slot_unit_out": null,
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s2",
      "question_id": "c1s2_god_forsaken_scope",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "meta-session-0002-locations",
        "u-L0003-02",
        "u-L0011-01",
        "u-L0011-02"
      ],
      "topk_swapped_out": [
        "u-L0005-01",
        "u-L0005-02",
        "u-L0007-02",
        "u-L0009-01"
      ],
      "contested_slot_unit_in": "meta-session-0002-locations",
      "contested_slot_unit_out": "u-L0005-01",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s2",
      "question_id": "c1s2_pay_and_loot_summary",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0003-02",
        "u-L0007-01"
      ],
      "topk_swapped_out": [
        "u-L0005-01",
        "u-L0007-02"
      ],
      "contested_slot_unit_in": "u-L0003-02",
      "contested_slot_unit_out": "u-L0005-01",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s2",
      "question_id": "c1s2_party_commitment",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0007-01"
      ],
      "topk_swapped_out": [
        "u-L0005-01"
      ],
      "contested_slot_unit_in": "u-L0007-01",
      "contested_slot_unit_out": "u-L0005-01",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s2",
      "question_id": "c1s2_basement_lesson",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0007-01"
      ],
      "topk_swapped_out": [
        "u-L0005-01"
      ],
      "contested_slot_unit_in": "u-L0007-01",
      "contested_slot_unit_out": "u-L0005-01",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s2",
      "question_id": "c1s2_hook_more_work_glowkindle",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "meta-session-0002-locations"
      ],
      "topk_swapped_out": [
        "u-L0009-01"
      ],
      "contested_slot_unit_in": "meta-session-0002-locations",
      "contested_slot_unit_out": "u-L0009-01",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s2",
      "question_id": "c1s2_hook_stonebridge_grishna",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0003-02",
        "u-L0007-01"
      ],
      "topk_swapped_out": [
        "u-L0011-03",
        "u-L0013-01"
      ],
      "contested_slot_unit_in": "u-L0003-02",
      "contested_slot_unit_out": "u-L0011-03",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s2",
      "question_id": "c1s2_hook_wizard_tower_thread",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [],
      "topk_swapped_out": [],
      "contested_slot_unit_in": null,
      "contested_slot_unit_out": null,
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s2",
      "question_id": "c1s2_spider_beat",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "meta-session-0002-locations",
        "u-L0007-01",
        "u-L0011-01",
        "u-L0011-02"
      ],
      "topk_swapped_out": [
        "u-L0003-01",
        "u-L0005-01",
        "u-L0005-02",
        "u-L0005-03"
      ],
      "contested_slot_unit_in": "meta-session-0002-locations",
      "contested_slot_unit_out": "u-L0003-01",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s2",
      "question_id": "c1s2_centipede_beat",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "meta-session-0002-locations",
        "u-L0007-01",
        "u-L0011-01",
        "u-L0011-02"
      ],
      "topk_swapped_out": [
        "u-L0003-01",
        "u-L0005-01",
        "u-L0005-02",
        "u-L0005-03"
      ],
      "contested_slot_unit_in": "meta-session-0002-locations",
      "contested_slot_unit_out": "u-L0003-01",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s2",
      "question_id": "c1s2_non_mutating_rat",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0007-01"
      ],
      "topk_swapped_out": [
        "u-L0009-01"
      ],
      "contested_slot_unit_in": "u-L0007-01",
      "contested_slot_unit_out": "u-L0009-01",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s2",
      "question_id": "c1s2_planning_glowkindle_followup",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "meta-session-0002-locations"
      ],
      "topk_swapped_out": [
        "u-L0009-01"
      ],
      "contested_slot_unit_in": "meta-session-0002-locations",
      "contested_slot_unit_out": "u-L0009-01",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s2",
      "question_id": "c1s2_prep_named_hostiles",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0007-01"
      ],
      "topk_swapped_out": [
        "u-L0003-01"
      ],
      "contested_slot_unit_in": "u-L0007-01",
      "contested_slot_unit_out": "u-L0003-01",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s3",
      "question_id": "c1s3_bubbles_mage_hand_beat",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [],
      "topk_swapped_out": [],
      "contested_slot_unit_in": null,
      "contested_slot_unit_out": null,
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s3",
      "question_id": "c1s3_pippa_ride_kegs",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [],
      "topk_swapped_out": [],
      "contested_slot_unit_in": null,
      "contested_slot_unit_out": null,
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s3",
      "question_id": "c1s3_grishna_comp_board",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0034-02"
      ],
      "topk_swapped_out": [
        "u-L0014-01"
      ],
      "contested_slot_unit_in": "u-L0034-02",
      "contested_slot_unit_out": "u-L0014-01",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s3",
      "question_id": "c1s3_stafl_brewery_song",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [],
      "topk_swapped_out": [],
      "contested_slot_unit_in": null,
      "contested_slot_unit_out": null,
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s3",
      "question_id": "c1s3_bonogo_downstream_zen",
      "verdict": "regressed",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [],
      "topk_swapped_out": [],
      "contested_slot_unit_in": null,
      "contested_slot_unit_out": null,
      "support_ratio_delta": -0.6667
    },
    {
      "scenario_id": "c1s3",
      "question_id": "c1s3_ephanna_second_lasso",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [],
      "topk_swapped_out": [],
      "contested_slot_unit_in": null,
      "contested_slot_unit_out": null,
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s3",
      "question_id": "c1s3_caelynn_ice_platform",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0041-02"
      ],
      "topk_swapped_out": [
        "u-L0022-01"
      ],
      "contested_slot_unit_in": "u-L0041-02",
      "contested_slot_unit_out": "u-L0022-01",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s3",
      "question_id": "c1s3_karsemine_zephyr_chase",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [],
      "topk_swapped_out": [],
      "contested_slot_unit_in": null,
      "contested_slot_unit_out": null,
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s3",
      "question_id": "c1s3_kirfan_debris_help",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [],
      "topk_swapped_out": [],
      "contested_slot_unit_in": null,
      "contested_slot_unit_out": null,
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s3",
      "question_id": "c1s3_stafl_nets_town",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0034-02",
        "u-L0034-03"
      ],
      "topk_swapped_out": [
        "meta-session-0003-locations",
        "u-L0014-01"
      ],
      "contested_slot_unit_in": "u-L0034-02",
      "contested_slot_unit_out": "meta-session-0003-locations",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s3",
      "question_id": "c1s3_bonogo_dive_rope_gone",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [],
      "topk_swapped_out": [],
      "contested_slot_unit_in": null,
      "contested_slot_unit_out": null,
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s3",
      "question_id": "c1s3_mirathorn_festival_hook",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [],
      "topk_swapped_out": [],
      "contested_slot_unit_in": null,
      "contested_slot_unit_out": null,
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "c1s3",
      "question_id": "c1s3_stonebridge_npc_roster_associated",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [],
      "topk_swapped_out": [],
      "contested_slot_unit_in": null,
      "contested_slot_unit_out": null,
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "natural_v1",
      "question_id": "nat_captain_after_forest",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 9,
      "topk_swapped_in": [],
      "topk_swapped_out": [],
      "contested_slot_unit_in": null,
      "contested_slot_unit_out": null,
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "natural_v1",
      "question_id": "nat_mirathorn_threads",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0017-04",
        "u-L0017-05",
        "u-L0017-07",
        "u-L0019-11"
      ],
      "topk_swapped_out": [
        "meta-session-0020-locations",
        "meta-session-0020-open-loops",
        "u-L0017-02",
        "u-L0021-03"
      ],
      "contested_slot_unit_in": "u-L0017-04",
      "contested_slot_unit_out": "meta-session-0020-locations",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "natural_v1",
      "question_id": "nat_voices_tower_officer",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0019-06"
      ],
      "topk_swapped_out": [
        "meta-session-0020-locations"
      ],
      "contested_slot_unit_in": "u-L0019-06",
      "contested_slot_unit_out": "meta-session-0020-locations",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "natural_v1",
      "question_id": "q_lysandra_change_unresolved",
      "verdict": "unchanged_fail",
      "alias_tokens_added": [
        "dustwalker",
        "elderwyld",
        "ironveil",
        "jove",
        "longmont",
        "npc",
        "route",
        "torbin"
      ],
      "alias_count": 8,
      "topk_swapped_in": [],
      "topk_swapped_out": [],
      "contested_slot_unit_in": null,
      "contested_slot_unit_out": null,
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "natural_v1",
      "question_id": "q_lysandra_regroups",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 9,
      "topk_swapped_in": [
        "u-L0017-04",
        "u-L0017-06",
        "u-L0019-11"
      ],
      "topk_swapped_out": [
        "u-L0015-07",
        "u-L0017-01",
        "u-L0017-05"
      ],
      "contested_slot_unit_in": "u-L0017-04",
      "contested_slot_unit_out": "u-L0015-07",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "natural_v1",
      "question_id": "q_relevant_locations",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0017-03",
        "u-L0017-04",
        "u-L0017-06",
        "u-L0017-07",
        "u-L0019-11"
      ],
      "topk_swapped_out": [
        "meta-session-0020-locations",
        "meta-session-0020-open-loops",
        "u-L0003-01",
        "u-L0003-02",
        "u-L0003-03"
      ],
      "contested_slot_unit_in": "u-L0017-03",
      "contested_slot_unit_out": "meta-session-0020-locations",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "natural_v1",
      "question_id": "q_communication_chain",
      "verdict": "unchanged_fail",
      "alias_tokens_added": [
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
      "alias_count": 9,
      "topk_swapped_in": [
        "u-L0017-06"
      ],
      "topk_swapped_out": [
        "u-L0015-07"
      ],
      "contested_slot_unit_in": "u-L0017-06",
      "contested_slot_unit_out": "u-L0015-07",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "natural_v1",
      "question_id": "q_lysandra_memory_contrast",
      "verdict": "improved",
      "alias_tokens_added": [
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
      "alias_count": 9,
      "topk_swapped_in": [
        "u-L0017-03",
        "u-L0017-04"
      ],
      "topk_swapped_out": [
        "u-L0015-07",
        "u-L0017-01"
      ],
      "contested_slot_unit_in": "u-L0017-03",
      "contested_slot_unit_out": "u-L0015-07",
      "support_ratio_delta": 0.25
    },
    {
      "scenario_id": "natural_v1",
      "question_id": "q_mirathorn_vs_mossford",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0017-03",
        "u-L0017-04",
        "u-L0017-05",
        "u-L0017-07",
        "u-L0019-11"
      ],
      "topk_swapped_out": [
        "meta-session-0020-locations",
        "meta-session-0020-open-loops",
        "u-L0007-01",
        "u-L0017-02",
        "u-L0021-03"
      ],
      "contested_slot_unit_in": "u-L0017-03",
      "contested_slot_unit_out": "meta-session-0020-locations",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "natural_v1",
      "question_id": "q_tower_knowns",
      "verdict": "unchanged_pass",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0017-03",
        "u-L0019-11",
        "u-L0019-12",
        "u-L0019-13"
      ],
      "topk_swapped_out": [
        "meta-session-0020-locations",
        "meta-session-0020-open-loops",
        "u-L0019-09",
        "u-L0019-10"
      ],
      "contested_slot_unit_in": "u-L0017-03",
      "contested_slot_unit_out": "meta-session-0020-locations",
      "support_ratio_delta": 0.0
    },
    {
      "scenario_id": "natural_v1",
      "question_id": "q_party_learned_next_prep",
      "verdict": "unchanged_fail",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0017-03",
        "u-L0017-04",
        "u-L0017-07",
        "u-L0019-11",
        "u-L0019-13"
      ],
      "topk_swapped_out": [
        "meta-session-0020-locations",
        "u-L0003-01",
        "u-L0005-06",
        "u-L0011-02",
        "u-L0013-08"
      ],
      "contested_slot_unit_in": "u-L0017-03",
      "contested_slot_unit_out": "meta-session-0020-locations",
      "support_ratio_delta": -0.25
    },
    {
      "scenario_id": "natural_v1",
      "question_id": "q_open_loops_next_session",
      "verdict": "unchanged_fail",
      "alias_tokens_added": [
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
      "alias_count": 10,
      "topk_swapped_in": [
        "u-L0017-03",
        "u-L0017-04",
        "u-L0017-06",
        "u-L0017-07",
        "u-L0019-11"
      ],
      "topk_swapped_out": [
        "meta-session-0020-open-loops",
        "u-L0003-01",
        "u-L0003-02",
        "u-L0003-03",
        "u-L0003-04"
      ],
      "contested_slot_unit_in": "u-L0017-03",
      "contested_slot_unit_out": "meta-session-0020-open-loops",
      "support_ratio_delta": -0.5
    }
  ],
  "threshold_scan": [
    {
      "threshold_alias_count": 0,
      "at_or_below": {
        "regressed": 0,
        "improved": 0,
        "unchanged_pass": 0,
        "unchanged_fail": 0
      },
      "above": {
        "regressed": 2,
        "improved": 1,
        "unchanged_pass": 49,
        "unchanged_fail": 4
      }
    },
    {
      "threshold_alias_count": 1,
      "at_or_below": {
        "regressed": 0,
        "improved": 0,
        "unchanged_pass": 0,
        "unchanged_fail": 0
      },
      "above": {
        "regressed": 2,
        "improved": 1,
        "unchanged_pass": 49,
        "unchanged_fail": 4
      }
    },
    {
      "threshold_alias_count": 2,
      "at_or_below": {
        "regressed": 0,
        "improved": 0,
        "unchanged_pass": 0,
        "unchanged_fail": 0
      },
      "above": {
        "regressed": 2,
        "improved": 1,
        "unchanged_pass": 49,
        "unchanged_fail": 4
      }
    },
    {
      "threshold_alias_count": 3,
      "at_or_below": {
        "regressed": 0,
        "improved": 0,
        "unchanged_pass": 0,
        "unchanged_fail": 0
      },
      "above": {
        "regressed": 2,
        "improved": 1,
        "unchanged_pass": 49,
        "unchanged_fail": 4
      }
    },
    {
      "threshold_alias_count": 4,
      "at_or_below": {
        "regressed": 0,
        "improved": 0,
        "unchanged_pass": 0,
        "unchanged_fail": 0
      },
      "above": {
        "regressed": 2,
        "improved": 1,
        "unchanged_pass": 49,
        "unchanged_fail": 4
      }
    },
    {
      "threshold_alias_count": 5,
      "at_or_below": {
        "regressed": 0,
        "improved": 0,
        "unchanged_pass": 0,
        "unchanged_fail": 0
      },
      "above": {
        "regressed": 2,
        "improved": 1,
        "unchanged_pass": 49,
        "unchanged_fail": 4
      }
    },
    {
      "threshold_alias_count": 6,
      "at_or_below": {
        "regressed": 0,
        "improved": 0,
        "unchanged_pass": 0,
        "unchanged_fail": 0
      },
      "above": {
        "regressed": 2,
        "improved": 1,
        "unchanged_pass": 49,
        "unchanged_fail": 4
      }
    },
    {
      "threshold_alias_count": 7,
      "at_or_below": {
        "regressed": 0,
        "improved": 0,
        "unchanged_pass": 0,
        "unchanged_fail": 0
      },
      "above": {
        "regressed": 2,
        "improved": 1,
        "unchanged_pass": 49,
        "unchanged_fail": 4
      }
    },
    {
      "threshold_alias_count": 8,
      "at_or_below": {
        "regressed": 0,
        "improved": 0,
        "unchanged_pass": 0,
        "unchanged_fail": 1
      },
      "above": {
        "regressed": 2,
        "improved": 1,
        "unchanged_pass": 49,
        "unchanged_fail": 3
      }
    },
    {
      "threshold_alias_count": 9,
      "at_or_below": {
        "regressed": 0,
        "improved": 1,
        "unchanged_pass": 2,
        "unchanged_fail": 2
      },
      "above": {
        "regressed": 2,
        "improved": 0,
        "unchanged_pass": 47,
        "unchanged_fail": 2
      }
    },
    {
      "threshold_alias_count": 10,
      "at_or_below": {
        "regressed": 2,
        "improved": 1,
        "unchanged_pass": 49,
        "unchanged_fail": 4
      },
      "above": {
        "regressed": 0,
        "improved": 0,
        "unchanged_pass": 0,
        "unchanged_fail": 0
      }
    }
  ],
  "promotion_gate_candidate": {
    "threshold_alias_count": null,
    "rule": "no_regressed_above_threshold_and_net_nonnegative_below",
    "status": "none_found"
  }
} as const;
// END GENERATED COHORT_L3_ALIAS_SATURATION

export default function CohortL3AliasSaturationCanvas() {
  const payload = cohortL3AliasSaturationGenerated;
  const highlighted = payload.rows.filter((r: any) => r.verdict === "regressed" || r.verdict === "unchanged_fail");
  return (
    <div>
      <h1>Cohort L3 Alias Saturation</h1>
      <h2>Verdict counts</h2>
      <pre>{JSON.stringify(payload.verdict_counts, null, 2)}</pre>
      <h2>Promotion gate candidate</h2>
      <pre>{JSON.stringify(payload.promotion_gate_candidate, null, 2)}</pre>
      <h2>Regressed + unchanged_fail rows</h2>
      {highlighted.map((r: any) => (
        <details key={`${r.scenario_id}::${r.question_id}`} open>
          <summary>{r.scenario_id} / {r.question_id} — {r.verdict} (alias_count={r.alias_count})</summary>
          <div><strong>alias_tokens_added:</strong> {r.alias_tokens_added.length ? r.alias_tokens_added.join(", ") : "none"}</div>
          <div><strong>contested_slot_unit_in:</strong> {r.contested_slot_unit_in ?? "none"}</div>
          <div><strong>contested_slot_unit_out:</strong> {r.contested_slot_unit_out ?? "none"}</div>
          <pre>{JSON.stringify(r, null, 2)}</pre>
        </details>
      ))}
    </div>
  );
}
