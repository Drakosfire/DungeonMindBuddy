<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-18T20:00:27Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: FAIL | tool_trace_gates: False | payload_gates: True | primary: artifacts/runs/2026-04-18/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--FAIL--1turn--20260418T200027Z--run005.md | cohort: 5 | run_index: 4 -->

## Review (printed)

```
========================================================================
SESSION RECAP INGEST — PLANNER REVIEW
========================================================================
scenario_id:      session_recap_ingest_session_20
model_id:         gpt-5.4-mini
gates_passed:     False
tool_trace_gates: False
payload_gates:    True
review_mode:      summary
corpus_fprint:    37509249b5d8de35c9a87c4719d8aa9c
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
  round[0] input=17031 output=24 cached=16896
  round[1] input=17362 output=162 cached=16896
  round[2] input=24550 output=54 cached=24064
  round[3] input=26673 output=2014 cached=26112
  round[4] input=30880 output=3191 cached=30720
  scenario_estimated_cost_usd: 0.03446

========================================================================
§ Violations
========================================================================
  scope_b: [scope_b_grader:session_recap_ingest_session_20] get_recap_context must be called with no arguments (do not pin campaign_id or target_session for this scenario); got arguments={'campaign_id': 'longmont-c2'}.
  scope_b_tool: [scope_b_grader:session_recap_ingest_session_20] get_recap_context must be called with no arguments (do not pin campaign_id or target_session for this scenario); got arguments={'campaign_id': 'longmont-c2'}.

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Drafted the Session 20 recap at `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`.\n\n```diff\n--- a/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md\n+++ b/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md\n@@ -0,0 +1,34 @@\n+---\n+title: \"Session 20 - Recap\"\n+document_class: play\n+canon_layer: campaign\n+campaign_id: longmont-c2\n+temporal_scope: session_specific\n+session: 20\n+origin_session: 20\n+last_updated_session: 20\n+source_class: observed_session_recap\n+---\n+# Session 20 Rec
...[truncated, total_chars=13619]...
ce.md` are companion files for the Stacey/Stuart/Marla side scene.","recap_append_line":"> Prep↔recap pointer: Session 20 recap and `session_20_stacey_stuart_marla_reference.md` are companion files for the Stacey/Stuart/Marla side scene."},"notes_for_gm":"The recap body preserves the raw notes exactly apart from deterministic duplicate-paragraph removal and title-strip normalization. One timeline candidate is proposed for captain_lysandra_ironveil because the recap gives a concrete new status/lead; the rest of the recap NPCs are first-appearance proposals or dismissed as PCs/role-functions."}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-18T20:00:27Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 4,
  "cohort_size": 5,
  "gates_passed": false,
  "tool_trace_gates_passed": false,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.03446,
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
  "violation_counts": {
    "scope_b_tool": 1,
    "scope_b": 1
  },
  "violations": {
    "scope_b_tool": [
      "[scope_b_grader:session_recap_ingest_session_20] get_recap_context must be called with no arguments (do not pin campaign_id or target_session for this scenario); got arguments={'campaign_id': 'longmont-c2'}."
    ],
    "scope_b": [
      "[scope_b_grader:session_recap_ingest_session_20] get_recap_context must be called with no arguments (do not pin campaign_id or target_session for this scenario); got arguments={'campaign_id': 'longmont-c2'}."
    ]
  },
  "corpus_fingerprint": "37509249b5d8de35c9a87c4719d8aa9c",
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
          10
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
          "reason": "Lysandra was contacted, found disoriented and cult-touched, and gave the party a new lead involving a tower blueprint and voices in the dark."
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
          "rationale": "Stacey is a named, recurring child NPC with a distinct relationship web involving Stuart and Marla."
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
          "evidence_quote": "A farmer whispers to him that Stafl better step in and help because Marla is not someone to mess with.",
          "rationale": "Marla is a named town power-center NPC who directly intervened and appears likely to recur."
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
          "evidence_quote": "Bonogo is being guided by Stuart down an alley to a half burned building.",
          "rationale": "Stuart is a named child NPC with immediate scene importance and a clear ongoing relationship to Stacey and Bonogo."
        }
      ],
      "dismissed": [
        {
          "name": "Stafl",
          "reason": "PCs are skipped silently and are not proposed as NPC hubs."
        },
        {
          "name": "Ephanna",
          "reason": "PCs are skipped silently and are not proposed as NPC hubs."
        },
        {
          "name": "Karesmine",
          "reason": "PCs are skipped silently and are not proposed as NPC hubs."
        },
        {
          "name": "Caelynn",
          "reason": "PCs are skipped silently and are not proposed as NPC hubs."
        },
        {
          "name": "Thrin",
          "reason": "Existing recurring NPC with no new hub decision needed in this skill; would be handled separately if needed."
        },
        {
          "name": "Sara",
          "reason": "Mentioned only as a radio operator with no direct scene action beyond relaying a call."
        },
        {
          "name": "Professor Tealeaf",
          "reason": "Mentioned only as a call recipient who did not answer."
        },
        {
          "name": "The mayor",
          "reason": "Role-function town authority with no unique individual name in the recap."
        },
        {
          "name": "the sheriff",
          "reason": "Role-function town authority with no unique individual name in the recap."
        }
      ]
    },
    "plot_artifacts": [
      {
        "name": "Tower blueprint drawing",
        "evidence_quote": "She says it is a tower where the voices are coming from and she knows where it is.",
        "proposed_locations": [
          "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
          "Longmont Campaign/Campaign 2/Campaign 2 Notes.md",
          "Longmont Campaign/Campaign 2/Session Prep/Session 2 Prep.md"
        ]
      }
    ],
    "prep_pointer_proposal": {
      "prep_path": "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md",
      "recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "prep_append_line": "> Prep↔recap pointer: Session 20 recap and `session_20_stacey_stuart_marla_reference.md` are companion files for the Stacey/Stuart/Marla side scene.",
      "recap_append_line": "> Prep↔recap pointer: Session 20 recap and `session_20_stacey_stuart_marla_reference.md` are companion files for the Stacey/Stuart/Marla side scene."
    },
    "notes_for_gm": "The recap body preserves the raw notes exactly apart from deterministic duplicate-paragraph removal and title-strip normalization. One timeline candidate is proposed for captain_lysandra_ironveil because the recap gives a concrete new status/lead; the rest of the recap NPCs are first-appearance proposals or dismissed as PCs/role-functions."
  },
  "recap_write_payload_sha256_16": "bfefd017d54c5a3a",
  "final_text_chars": 13619,
  "primary_response_id": "resp_0b761e367760a78c0069e3e2cd2b74819fbde520f5adcca8d1",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.03446,
    "planner_cost_by_round_usd": [
      0.001476,
      0.002346,
      0.002412,
      0.011442,
      0.016783
    ],
    "planner_usage_totals": {
      "input_tokens": 116496,
      "output_tokens": 5445,
      "total_tokens": 121941,
      "cached_tokens": 114688
    },
    "pricing_note": "approximate public list prices; verify against billing",
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.03446
  }
}
```
