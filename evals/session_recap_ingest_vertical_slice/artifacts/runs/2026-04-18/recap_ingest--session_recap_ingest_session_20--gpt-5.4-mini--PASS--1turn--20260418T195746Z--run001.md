<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-18T19:57:46Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: PASS | tool_trace_gates: True | payload_gates: True | primary: artifacts/runs/2026-04-18/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--PASS--1turn--20260418T195746Z--run001.md | cohort: 5 | run_index: 0 -->

## Review (printed)

```
========================================================================
SESSION RECAP INGEST — PLANNER REVIEW
========================================================================
scenario_id:      session_recap_ingest_session_20
model_id:         gpt-5.4-mini
gates_passed:     True
tool_trace_gates: True
payload_gates:    True
review_mode:      summary
corpus_fprint:    8f3c9674ac255b99fa77edb67d81ef4c
corpus_dir:       /tmp/session_recap_pre_state_8ye3lqv5/eldyrwild-markdown
hit_tool_limit:   False
tool_trace rows:  7

========================================================================
§ Prompt payload sizes
========================================================================
instructions:  {'chars': 22309, 'bytes': 24495, 'sha256_16': 'e90c1800676d4da1'}
user_line:     {'chars': 26894, 'bytes': 27006, 'sha256_16': 'd8211a736b03fb36'}

========================================================================
§ Token usage (per round)
========================================================================
  round[0] input=17031 output=16 cached=0
  round[1] input=17354 output=162 cached=16896
  round[2] input=24542 output=54 cached=17408
  round[3] input=26665 output=2019 cached=24064
  round[4] input=30877 output=3284 cached=28160
  scenario_estimated_cost_usd: 0.053853

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Drafted the Session 20 recap at `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`.\n\n```diff\n--- a/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md\n+++ b/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md\n@@ -0,0 +1,34 @@\n+---\n+title: \"Session 20 - Recap\"\n+document_class: play\n+canon_layer: campaign\n+campaign_id: longmont-c2\n+temporal_scope: session_specific\n+session: 20\n+origin_session: 20\n+last_updated_session: 20\n+source_class: observed_session_recap\n+---\n+# Session 20 Rec
...[truncated, total_chars=14031]...
ap_path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","prep_append_line":"> Session 20 recap: Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","recap_append_line":"> Session 20 prep companion: Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md"},"notes_for_gm":"The raw notes contained one duplicated paragraph, which the draft removed mechanically. The prep packet uses the surname Brambleback for Stacey and Marla; the recap body keeps the names as written in the raw notes and does not silently merge that prep detail."}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-18T19:57:46Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 0,
  "cohort_size": 5,
  "gates_passed": true,
  "tool_trace_gates_passed": true,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.053853,
  "tool_trace_rows": 7,
  "tool_trace_tools": [
    "get_recap_context",
    "read_corpus_file",
    "read_corpus_file",
    "read_corpus_file",
    "read_corpus_file",
    "assemble_recap_draft",
    "write_corpus_file"
  ],
  "violation_counts": {},
  "violations": {},
  "corpus_fingerprint": "8f3c9674ac255b99fa77edb67d81ef4c",
  "corpus_dir": "/tmp/session_recap_pre_state_8ye3lqv5/eldyrwild-markdown",
  "recap_write_payload": {
    "schema_version": "recap_write_v1",
    "recap_preview": {
      "path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "mode": "create",
      "confirm_token": "959df16cedceab2219ca87575348e850"
    },
    "duplicate_paragraphs": [
      {
        "source_lines": [
          6,
          6
        ],
        "paragraph_preview": "Back in town, Bonogo is being guided by Stuart down an alley to a half burned building. According to Stuart this is where they will find Stacey.",
        "recommended_action": "remove_later"
      }
    ],
    "npc_audit": {
      "timeline_append_candidates": [
        {
          "slug": "captain_lysandra_ironveil",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
          "reason": "Lysandra was located, was briefly mystified/controlled, then recovered after the tea antidote; that is a meaningful timeline beat for her hub."
        },
        {
          "slug": "dustwalker",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/dustwalker/",
          "reason": "Thrin actively participated in the forest testing, the swarm fight, and then remained under close watch during travel; this is a session beat worth logging if his hub is the active campaign hub."
        }
      ],
      "new_hub_proposals": [
        {
          "proposed_slug": "stacey_brambleback",
          "campaign_or_setting": "campaign",
          "proposed_location": "Longmont Campaign/Campaign 2/NPCs/stacey_brambleback/",
          "initial_files": [
            "README.md",
            "stacey_brambleback_character_dossier.md",
            "timeline.md"
          ],
          "evidence_quote": "One of them is Stacey, the bugbear girl they are looking for.",
          "rationale": "Stacey is a named, textured local child with recurring social potential and direct ties to Mossford crisis scenes."
        },
        {
          "proposed_slug": "marla_brambleback",
          "campaign_or_setting": "campaign",
          "proposed_location": "Longmont Campaign/Campaign 2/NPCs/marla_brambleback/",
          "initial_files": [
            "README.md",
            "marla_brambleback_character_dossier.md",
            "timeline.md"
          ],
          "evidence_quote": "they reveal that she is in charge of the workers in town and she means business.",
          "rationale": "Marla is a memorable local authority figure who clearly has ongoing relevance to Mossford's crisis response."
        },
        {
          "proposed_slug": "stuart",
          "campaign_or_setting": "campaign",
          "proposed_location": "Longmont Campaign/Campaign 2/NPCs/stuart/",
          "initial_files": [
            "README.md",
            "stuart_character_dossier.md",
            "timeline.md"
          ],
          "evidence_quote": "Stuart is so happy with the outcome that he runs out the door, racing off to tell his mom the good news.",
          "rationale": "Stuart is a named child with a distinct relationship web and likely repeat utility in Mossford scenes."
        }
      ],
      "dismissed": [
        {
          "name": "Stafl",
          "reason": "Already part of the ongoing party context rather than a new NPC needing hub creation from this session."
        },
        {
          "name": "Professor Tealeaf",
          "reason": "Mentioned only as an attempted call recipient; no new on-scene characterization or actionable first appearance here."
        },
        {
          "name": "Sara",
          "reason": "Only heard on the rockie-talkie as an operator voice, not enough evidence in this recap alone to warrant a new hub."
        },
        {
          "name": "the mayor",
          "reason": "Role is civic functionary with no personal name in the recap, so no hub proposal."
        },
        {
          "name": "the sheriff",
          "reason": "Role is civic functionary with no personal name in the recap, so no hub proposal."
        },
        {
          "name": "the farmer",
          "reason": "Unnamed background witness used to convey social pressure, not a hub-worthy NPC."
        }
      ]
    },
    "plot_artifacts": [
      {
        "name": "tower blueprint",
        "evidence_quote": "It appears to be a top-down blueprint of a tower and is very well done.",
        "proposed_locations": [
          "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
          "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md",
          "Longmont Campaign/Campaign 2/Campaign 2 Notes.md"
        ]
      },
      {
        "name": "tainted meat cache",
        "evidence_quote": "Mixed in with the meat is cleverly disguised tainted meat.",
        "proposed_locations": [
          "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
          "Longmont Campaign/Campaign 2/Campaign 2 Notes.md",
          "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md"
        ]
      }
    ],
    "prep_pointer_proposal": {
      "prep_path": "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md",
      "recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "prep_append_line": "> Session 20 recap: Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "recap_append_line": "> Session 20 prep companion: Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md"
    },
    "notes_for_gm": "The raw notes contained one duplicated paragraph, which the draft removed mechanically. The prep packet uses the surname Brambleback for Stacey and Marla; the recap body keeps the names as written in the raw notes and does not silently merge that prep detail."
  },
  "recap_write_payload_sha256_16": "4cc2ef57a9c1b916",
  "final_text_chars": 14031,
  "primary_response_id": "resp_0caf334971adf0af0069e3e22c5e888190b37beacb76256504",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.053853,
    "planner_cost_by_round_usd": [
      0.012845,
      0.00234,
      0.006899,
      0.012841,
      0.018928
    ],
    "planner_usage_totals": {
      "input_tokens": 116469,
      "output_tokens": 5535,
      "total_tokens": 122004,
      "cached_tokens": 86528
    },
    "pricing_note": "approximate public list prices; verify against billing",
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.053853
  }
}
```
