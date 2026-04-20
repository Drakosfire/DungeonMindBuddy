<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-18T19:59:46Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: FAIL | tool_trace_gates: False | payload_gates: True | primary: artifacts/runs/2026-04-18/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--FAIL--1turn--20260418T195946Z--run004.md | cohort: 5 | run_index: 3 -->

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
corpus_fprint:    ccb576926f6db3bc7f981b961274324d
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
  round[2] input=24550 output=54 cached=17408
  round[3] input=26673 output=2014 cached=24064
  round[4] input=30880 output=3241 cached=28160
  scenario_estimated_cost_usd: 0.042288

========================================================================
§ Violations
========================================================================
  scope_b: [scope_b_grader:session_recap_ingest_session_20] get_recap_context must be called with no arguments (do not pin campaign_id or target_session for this scenario); got arguments={'campaign_id': 'longmont-c2'}.
  scope_b_tool: [scope_b_grader:session_recap_ingest_session_20] get_recap_context must be called with no arguments (do not pin campaign_id or target_session for this scenario); got arguments={'campaign_id': 'longmont-c2'}.

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Drafted the Session 20 recap at `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`.\n\n```diff\n--- a/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md\n+++ b/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md\n@@ -0,0 +1,34 @@\n+---\n+title: \"Session 20 - Recap\"\n+document_class: play\n+canon_layer: campaign\n+campaign_id: longmont-c2\n+temporal_scope: session_specific\n+session: 20\n+origin_session: 20\n+last_updated_session: 20\n+source_class: observed_session_recap\n+---\n+# Session 20 Rec
...[truncated, total_chars=13858]...
ont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md","recap_path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","prep_append_line":"> Companion recap: [Session 20 - Recap](../Session Recaps/Session 20 - Recap.md)","recap_append_line":"> Companion prep: [session_20_stacey_stuart_marla_reference](../Session Prep/session_20_stacey_stuart_marla_reference.md)"},"notes_for_gm":"The draft removed one duplicated paragraph pair from the raw notes. The recap includes the raw-session spelling/wording as assembled; no further normalization was applied."}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-18T19:59:46Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 3,
  "cohort_size": 5,
  "gates_passed": false,
  "tool_trace_gates_passed": false,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.042288,
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
  "corpus_fingerprint": "ccb576926f6db3bc7f981b961274324d",
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
        "paragraph_preview": "Back in town, Bonogo is being guided by Stuart down an alley to a half burned building. According to Stuart this is where they will find Stacey...",
        "recommended_action": "remove_later"
      }
    ],
    "npc_audit": {
      "timeline_append_candidates": [],
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
          "rationale": "Stacey is named, scene-driving, and clearly positioned as a recurring Mossford child NPC with meaningful future utility."
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
          "rationale": "Marla is a named local authority figure with immediate scene impact and strong recurring-town-NPC potential."
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
          "rationale": "Stuart is a named child NPC with a distinct relationship web and likely follow-up utility."
        }
      ],
      "dismissed": [
        {
          "name": "Sara",
          "reason": "Named operator voice-only contact in this recap; she appears useful but not yet hub-worthy from this session alone."
        },
        {
          "name": "Professor Tealeaf",
          "reason": "Only appears as a failed call target here, with no on-scene characterization or immediate recurring function established."
        },
        {
          "name": "Lysandra",
          "reason": "Already established elsewhere and not first-appearance in this session; treat as existing campaign NPC rather than a new hub proposal."
        },
        {
          "name": "Thrin",
          "reason": "Player-facing ally/PC-like party member in the recap context, so skipped silently for hub auditing."
        },
        {
          "name": "Ephanna",
          "reason": "Player-facing ally/PC-like party member in the recap context, so skipped silently for hub auditing."
        },
        {
          "name": "Karesmine",
          "reason": "Player-facing ally/PC-like party member in the recap context, so skipped silently for hub auditing."
        },
        {
          "name": "Caelynn",
          "reason": "Player-facing ally/PC-like party member in the recap context, so skipped silently for hub auditing."
        },
        {
          "name": "Bonogo",
          "reason": "Player-facing ally/PC-like party member in the recap context, so skipped silently for hub auditing."
        },
        {
          "name": "Stafl",
          "reason": "Player-facing ally/PC-like party member in the recap context, so skipped silently for hub auditing."
        },
        {
          "name": "Stacey's father / the other bugbear woman",
          "reason": "Unnamed in the recap and not enough for a hub proposal."
        }
      ]
    },
    "plot_artifacts": [
      {
        "name": "Top-down tower blueprint",
        "evidence_quote": "It appears to be a top-down blueprint of a tower and is very well done.",
        "proposed_locations": [
          "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
          "Longmont Campaign/Campaign 2/Campaign 2 Notes.md",
          "Longmont Campaign/Campaign 2/Session Prep/"
        ]
      },
      {
        "name": "Tainted meat stash",
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
      "prep_append_line": "> Companion recap: [Session 20 - Recap](../Session Recaps/Session 20 - Recap.md)",
      "recap_append_line": "> Companion prep: [session_20_stacey_stuart_marla_reference](../Session Prep/session_20_stacey_stuart_marla_reference.md)"
    },
    "notes_for_gm": "The draft removed one duplicated paragraph pair from the raw notes. The recap includes the raw-session spelling/wording as assembled; no further normalization was applied."
  },
  "recap_write_payload_sha256_16": "8269eec836a16160",
  "final_text_chars": 13858,
  "primary_response_id": "resp_0a5f2534920ecfdd0069e3e2a3c77881a39eb872a0fe57c603",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.042288,
    "planner_cost_by_round_usd": [
      0.001476,
      0.002346,
      0.006905,
      0.012825,
      0.018736
    ],
    "planner_usage_totals": {
      "input_tokens": 116496,
      "output_tokens": 5495,
      "total_tokens": 121991,
      "cached_tokens": 103424
    },
    "pricing_note": "approximate public list prices; verify against billing",
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.042288
  }
}
```
