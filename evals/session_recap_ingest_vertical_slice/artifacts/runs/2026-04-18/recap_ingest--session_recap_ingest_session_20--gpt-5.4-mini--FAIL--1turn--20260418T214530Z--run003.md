<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-18T21:45:30Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: FAIL | tool_trace_gates: False | payload_gates: True | primary: artifacts/runs/2026-04-18/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--FAIL--1turn--20260418T214530Z--run003.md | cohort: 5 | run_index: 2 -->

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
corpus_fprint:    958896202dcfe69ef0fa31cc1bdbf7d4
corpus_dir:       /tmp/session_recap_pre_state_pq9slc4e/eldyrwild-markdown
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
  round[4] input=30954 output=2945 cached=30720
  scenario_estimated_cost_usd: 0.033255

========================================================================
§ Violations
========================================================================
  scope_b: [scope_b_grader:session_recap_ingest_session_20] two_phase_commit_required: write_corpus_file must be called at least twice (preview with dry_run=true, then commit with dry_run=false); saw 1 call(s).
  scope_b_tool: [scope_b_grader:session_recap_ingest_session_20] two_phase_commit_required: write_corpus_file must be called at least twice (preview with dry_run=true, then commit with dry_run=false); saw 1 call(s).

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Drafted Session 20 recap at `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`.\n\n```diff\n--- a/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md\n+++ b/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md\n@@ -0,0 +1,34 @@\n+---\n+title: \"Session 20 - Recap\"\n+document_class: play\n+canon_layer: campaign\n+campaign_id: longmont-c2\n+temporal_scope: session_specific\n+session: 20\n+origin_session: 20\n+last_updated_session: 20\n+source_class: observed_session_recap\n+---\n+# Session 20 Recap\n
...[truncated, total_chars=12602]...
":"> Related recap: [Session 20 Recap](../Session Recaps/Session 20 - Recap.md)","recap_append_line":"> Related prep: [session_20_stacey_stuart_marla_reference](../Session Prep/session_20_stacey_stuart_marla_reference.md)"},"notes_for_gm":"The recap draft removed one duplicated paragraph mechanically. The prep packet suggests Stacey and Marla Brambleback as fuller names, but the recap itself keeps only the names present in the raw notes. I did not include a timeline-append candidate list because the skill contract here stops at recap drafting; the NPCs are surfaced as hub proposals instead."}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-18T21:45:30Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 2,
  "cohort_size": 5,
  "gates_passed": false,
  "tool_trace_gates_passed": false,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.033255,
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
  "corpus_fingerprint": "958896202dcfe69ef0fa31cc1bdbf7d4",
  "corpus_dir": "/tmp/session_recap_pre_state_pq9slc4e/eldyrwild-markdown",
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
          "rationale": "Named, recurring, and socially important enough to merit an NPC hub."
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
          "evidence_quote": "They reveal that she is in charge of the workers in town and she means business.",
          "rationale": "Introduced as a named authority figure with clear ongoing town significance."
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
          "rationale": "Named child NPC with an established relationship to Stacey and Bonogo who may recur."
        }
      ],
      "dismissed": [
        {
          "name": "Sara",
          "reason": "Operating voice on the rockie-talkie; appears functional but not newly hub-worthy from this recap alone."
        },
        {
          "name": "Professor Tealeaf",
          "reason": "Mentioned only as a contact who did not answer; no on-page action to support a hub."
        },
        {
          "name": "Mayor",
          "reason": "Unspecified town leader in this recap; not uniquely identified enough here for a hub proposal."
        },
        {
          "name": "Sheriff",
          "reason": "Unspecified town authority in this recap; not uniquely identified enough here for a hub proposal."
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
      }
    ],
    "prep_pointer_proposal": {
      "prep_path": "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md",
      "recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "prep_append_line": "> Related recap: [Session 20 Recap](../Session Recaps/Session 20 - Recap.md)",
      "recap_append_line": "> Related prep: [session_20_stacey_stuart_marla_reference](../Session Prep/session_20_stacey_stuart_marla_reference.md)"
    },
    "notes_for_gm": "The recap draft removed one duplicated paragraph mechanically. The prep packet suggests Stacey and Marla Brambleback as fuller names, but the recap itself keeps only the names present in the raw notes. I did not include a timeline-append candidate list because the skill contract here stops at recap drafting; the NPCs are surfaced as hub proposals instead."
  },
  "recap_write_payload_sha256_16": "a4bae0aa34e5e3ba",
  "final_text_chars": 12602,
  "primary_response_id": "resp_0aa056f1a584285c0069e3fb6e7c9481948811f9c1aec8e0b5",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.033255,
    "planner_cost_by_round_usd": [
      0.001502,
      0.002401,
      0.002468,
      0.011152,
      0.015732
    ],
    "planner_usage_totals": {
      "input_tokens": 116874,
      "output_tokens": 5191,
      "total_tokens": 122065,
      "cached_tokens": 115200
    },
    "pricing_note": "approximate public list prices; verify against billing",
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.033255
  }
}
```
