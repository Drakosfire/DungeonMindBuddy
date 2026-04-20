<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-18T21:46:16Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: FAIL | tool_trace_gates: False | payload_gates: True | primary: artifacts/runs/2026-04-18/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--FAIL--1turn--20260418T214616Z--run004.md | cohort: 5 | run_index: 3 -->

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
corpus_fprint:    53d783c946c7ac0697978f400560a7a4
corpus_dir:       /tmp/session_recap_pre_state_cba_tevn/eldyrwild-markdown
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
  round[4] input=30954 output=2873 cached=30720
  scenario_estimated_cost_usd: 0.032931

========================================================================
§ Violations
========================================================================
  scope_b: [scope_b_grader:session_recap_ingest_session_20] two_phase_commit_required: write_corpus_file must be called at least twice (preview with dry_run=true, then commit with dry_run=false); saw 1 call(s).
  scope_b_tool: [scope_b_grader:session_recap_ingest_session_20] two_phase_commit_required: write_corpus_file must be called at least twice (preview with dry_run=true, then commit with dry_run=false); saw 1 call(s).

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Drafted the Session 20 recap at `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`.\n\n```diff\n--- a/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md\n+++ b/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md\n@@ -0,0 +1,34 @@\n+---\n+title: \"Session 20 - Recap\"\n+document_class: play\n+canon_layer: campaign\n+campaign_id: longmont-c2\n+temporal_scope: session_specific\n+session: 20\n+origin_session: 20\n+last_updated_session: 20\n+source_class: observed_session_recap\n+---\n+# Session 20 Rec
...[truncated, total_chars=12295]...
Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md` for Stacey, Stuart, and Marla Brambleback reference material.","recap_append_line":"> See also: `Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md` for the companion Stacey/Stuart/Marla reference packet."},"notes_for_gm":"The preview includes one mechanically detected duplicate paragraph pair from the raw notes, already removed in the draft body. I did not append any NPC timelines because this skill’s contract is recap-only; the recap is ready for commit after explicit approval."}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-18T21:46:16Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 3,
  "cohort_size": 5,
  "gates_passed": false,
  "tool_trace_gates_passed": false,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.032931,
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
  "corpus_fingerprint": "53d783c946c7ac0697978f400560a7a4",
  "corpus_dir": "/tmp/session_recap_pre_state_cba_tevn/eldyrwild-markdown",
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
        "paragraph_preview": "Back in town, Bonogo is being guided by Stuart down an alley to a half burned building. According to Stuart this is where they will find Stacey...",
        "recommended_action": "remove_later"
      }
    ],
    "npc_audit": {
      "timeline_append_candidates": [],
      "new_hub_proposals": [],
      "dismissed": [
        {
          "name": "Stacey",
          "reason": "First-appearance town child; notable but not yet a hub-worthy recurring NPC from this session alone."
        },
        {
          "name": "Stuart",
          "reason": "First-appearance town child; important in-scene, but still a minor local without enough evidence for a hub."
        },
        {
          "name": "Marla Brambleback",
          "reason": "Named local adult with one strong scene, but the recap does not yet show recurring cross-session importance for a hub proposal."
        },
        {
          "name": "Sara",
          "reason": "Existing operator voice on the line, but no evidence here that she needs a hub proposal from this session recap alone."
        },
        {
          "name": "Professor Tealeaf",
          "reason": "Mentioned only as a called contact who did not answer; too thin for a hub proposal."
        },
        {
          "name": "The mayor",
          "reason": "Titled town authority without a named identity in the recap; not a hub candidate from this record."
        },
        {
          "name": "the sheriff",
          "reason": "Titled town authority without a named identity in the recap; not a hub candidate from this record."
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
          "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md"
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
      "prep_append_line": "> See also: `Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md` for Stacey, Stuart, and Marla Brambleback reference material.",
      "recap_append_line": "> See also: `Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md` for the companion Stacey/Stuart/Marla reference packet."
    },
    "notes_for_gm": "The preview includes one mechanically detected duplicate paragraph pair from the raw notes, already removed in the draft body. I did not append any NPC timelines because this skill’s contract is recap-only; the recap is ready for commit after explicit approval."
  },
  "recap_write_payload_sha256_16": "d164dbfe52772770",
  "final_text_chars": 12295,
  "primary_response_id": "resp_059ab6a53f7e457d0069e3fb8a097c81a089f99110ea58eaee",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.032931,
    "planner_cost_by_round_usd": [
      0.001502,
      0.002401,
      0.002468,
      0.011152,
      0.015408
    ],
    "planner_usage_totals": {
      "input_tokens": 116874,
      "output_tokens": 5119,
      "total_tokens": 121993,
      "cached_tokens": 115200
    },
    "pricing_note": "approximate public list prices; verify against billing",
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.032931
  }
}
```
