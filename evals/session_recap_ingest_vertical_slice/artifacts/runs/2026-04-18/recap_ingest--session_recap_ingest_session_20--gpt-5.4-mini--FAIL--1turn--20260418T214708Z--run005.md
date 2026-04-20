<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-18T21:47:08Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: FAIL | tool_trace_gates: False | payload_gates: True | primary: artifacts/runs/2026-04-18/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--FAIL--1turn--20260418T214708Z--run005.md | cohort: 5 | run_index: 4 -->

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
corpus_fprint:    1e233aa583ee6cd7354f3575747722b0
corpus_dir:       /tmp/session_recap_pre_state_qyfffxvj/eldyrwild-markdown
hit_tool_limit:   False
tool_trace rows:  7

========================================================================
§ Prompt payload sizes
========================================================================
instructions:  {'chars': 22653, 'bytes': 24843, 'sha256_16': '5d3e498d3b4e6329'}
user_line:     {'chars': 26894, 'bytes': 27006, 'sha256_16': 'd8211a736b03fb36'}

========================================================================
§ Token usage (per round)
========================================================================
  round[0] input=17113 output=16 cached=16896
  round[1] input=17436 output=162 cached=16896
  round[2] input=24624 output=54 cached=24064
  round[3] input=26747 output=2014 cached=26624
  round[4] input=30954 output=3113 cached=30720
  scenario_estimated_cost_usd: 0.034011

========================================================================
§ Violations
========================================================================
  scope_b: [scope_b_grader:session_recap_ingest_session_20] two_phase_commit_required: write_corpus_file must be called at least twice (preview with dry_run=true, then commit with dry_run=false); saw 1 call(s).
  scope_b_tool: [scope_b_grader:session_recap_ingest_session_20] two_phase_commit_required: write_corpus_file must be called at least twice (preview with dry_run=true, then commit with dry_run=false); saw 1 call(s).

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Drafted the Session 20 recap at `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`.\n\n```diff\n--- a/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md\n+++ b/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md\n@@ -0,0 +1,34 @@\n+---\n+title: \"Session 20 - Recap\"\n+document_class: play\n+canon_layer: campaign\n+campaign_id: longmont-c2\n+temporal_scope: session_specific\n+session: 20\n+origin_session: 20\n+last_updated_session: 20\n+source_class: observed_session_recap\n+---\n+# Session 20 Rec
...[truncated, total_chars=13226]...
Prep/session_20_stacey_stuart_marla_reference.md","recap_path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","prep_append_line":"> Companion recap: [Session 20 - Recap](../Session Recaps/Session 20 - Recap.md)","recap_append_line":"> Companion prep: [session_20_stacey_stuart_marla_reference](../Session Prep/session_20_stacey_stuart_marla_reference.md)"},"notes_for_gm":"The recap draft removed one duplicated paragraph block mechanically. The prep doc suggests full surnames for Stacey, Stuart, and Marla Brambleback; the recap body intentionally keeps the raw-note naming."}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-18T21:47:08Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 4,
  "cohort_size": 5,
  "gates_passed": false,
  "tool_trace_gates_passed": false,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.034011,
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
      "[scope_b_grader:session_recap_ingest_session_20] two_phase_commit_required: write_corpus_file must be called at least twice (preview with dry_run=true, then commit with dry_run=false); saw 1 call(s)."
    ],
    "scope_b": [
      "[scope_b_grader:session_recap_ingest_session_20] two_phase_commit_required: write_corpus_file must be called at least twice (preview with dry_run=true, then commit with dry_run=false); saw 1 call(s)."
    ]
  },
  "corpus_fingerprint": "1e233aa583ee6cd7354f3575747722b0",
  "corpus_dir": "/tmp/session_recap_pre_state_qyfffxvj/eldyrwild-markdown",
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
          "rationale": "Stacey is named, has a distinct role, and looks likely to recur as a local child power-center."
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
          "rationale": "Marla is named, socially important in Mossford, and functionally tied to town labor and future interactions."
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
          "evidence_quote": "According to Stuart this is where they will find Stacey.",
          "rationale": "Stuart is a named recurring child NPC with immediate scene impact and likely future relevance."
        },
        {
          "proposed_slug": "sara",
          "campaign_or_setting": "campaign",
          "proposed_location": "Longmont Campaign/Campaign 2/NPCs/sara/",
          "initial_files": [
            "README.md",
            "sara_character_dossier.md",
            "timeline.md"
          ],
          "evidence_quote": "After a brief pause she is connected with the familiar voice of Sara, one half of the operators in Mirathorn.",
          "rationale": "Sara is named, voiced, and already acting as a communications node for the party."
        }
      ],
      "dismissed": [
        {
          "name": "The mayor",
          "reason": "A title rather than a uniquely named NPC in this recap, so not proposed as a hub from this session alone."
        },
        {
          "name": "the sheriff",
          "reason": "A title rather than a uniquely named NPC in this recap, so not proposed as a hub from this session alone."
        },
        {
          "name": "Professor Tealeaf",
          "reason": "Mentioned only as a contact the call fails to reach; not enough first-appearance identity details to justify a hub from this recap alone."
        }
      ]
    },
    "plot_artifacts": [
      {
        "name": "Top-down tower blueprint",
        "evidence_quote": "It appears to be a top-down blueprint of a tower and is very well done.",
        "proposed_locations": [
          "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
          "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md",
          "Longmont Campaign/Campaign 2/Campaign 2 Notes.md"
        ]
      },
      {
        "name": "Tainted meat cache",
        "evidence_quote": "Mixed in with the meat is cleverly disguised tainted meat.",
        "proposed_locations": [
          "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
          "Longmont Campaign/Campaign 2/Campaign 2 Notes.md",
          "Longmont Campaign/Campaign 2/Elderwyld_Narrative_Ledger_2.md"
        ]
      }
    ],
    "prep_pointer_proposal": {
      "prep_path": "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md",
      "recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "prep_append_line": "> Companion recap: [Session 20 - Recap](../Session Recaps/Session 20 - Recap.md)",
      "recap_append_line": "> Companion prep: [session_20_stacey_stuart_marla_reference](../Session Prep/session_20_stacey_stuart_marla_reference.md)"
    },
    "notes_for_gm": "The recap draft removed one duplicated paragraph block mechanically. The prep doc suggests full surnames for Stacey, Stuart, and Marla Brambleback; the recap body intentionally keeps the raw-note naming."
  },
  "recap_write_payload_sha256_16": "05f774ff4d073d71",
  "final_text_chars": 13226,
  "primary_response_id": "resp_0a6949ebe56203f90069e3fbd0821c81a3bf2f3b93df5068be",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.034011,
    "planner_cost_by_round_usd": [
      0.001502,
      0.002401,
      0.002468,
      0.011152,
      0.016488
    ],
    "planner_usage_totals": {
      "input_tokens": 116874,
      "output_tokens": 5359,
      "total_tokens": 122233,
      "cached_tokens": 115200
    },
    "pricing_note": "approximate public list prices; verify against billing",
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.034011
  }
}
```
