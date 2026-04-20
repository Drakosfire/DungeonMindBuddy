<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-18T21:53:00Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: FAIL | tool_trace_gates: False | payload_gates: True | primary: artifacts/runs/2026-04-18/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--FAIL--2turn--20260418T215300Z--run001.md | cohort: 5 | run_index: 0 -->

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
corpus_fprint:    f77fc9511176bc60ed926f65daba3d73
corpus_dir:       /tmp/session_recap_pre_state_7d9nbgng/eldyrwild-markdown
hit_tool_limit:   False
tool_trace rows:  8

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
  round[4] input=30954 output=3427 cached=30720
  round[5] input=34431 output=2037 cached=30720
  round[6] input=36632 output=626 cached=36352
  scenario_estimated_cost_usd: 0.055431

========================================================================
§ Violations
========================================================================
  scope_b: [scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/Session Recaps/Session 17 - Migrating Forest and Thrin.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/session recaps/session 17 - migrating forest and thrin.md' not in allowlist).
  scope_b: [scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/session prep/session_20_stacey_stuart_marla_reference.md' not in allowlist).
  scope_b: [scope_b_grader:session_recap_ingest_session_20] assemble_recap_draft.target_session want 21 got 20.
  scope_b_tool: [scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/Session Recaps/Session 17 - Migrating Forest and Thrin.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/session recaps/session 17 - migrating forest and thrin.md' not in allowlist).
  scope_b_tool: [scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/session prep/session_20_stacey_stuart_marla_reference.md' not in allowlist).
  scope_b_tool: [scope_b_grader:session_recap_ingest_session_20] assemble_recap_draft.target_session want 21 got 20.

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Committed the Session 20 recap to `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`.\n\nNo NPC timeline rows were queued from this recap, so there was nothing to preview or append.","unsure_queue":null,"recap_write":{"schema_version":"recap_write_v1","recap_preview":{"path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","mode":"create","confirm_token":"959df16cedceab2219ca87575348e850"},"duplicate_paragraphs":[{"source_lines":[6,6],"paragraph_preview":"Back in town, Bonogo is being guided by Stuart down 
...[truncated, total_chars=2532]...
marla_reference.md","recap_path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","prep_append_line":"> See also: `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`","recap_append_line":"> See also: `Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md`"},"notes_for_gm":"The raw notes included one duplicated paragraph block, which was removed mechanically in the recap draft. The prep packet strongly frames Stacey, Stuart, and Marla Brambleback, but the recap itself does not establish enough recurrence for new NPC hubs yet."}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-18T21:53:00Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 0,
  "cohort_size": 5,
  "gates_passed": false,
  "tool_trace_gates_passed": false,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.055431,
  "tool_trace_rows": 8,
  "tool_trace_tools": [
    "get_recap_context",
    "read_corpus_file",
    "read_corpus_file",
    "read_corpus_file",
    "read_corpus_file",
    "assemble_recap_draft",
    "write_corpus_file",
    "write_corpus_file"
  ],
  "violation_counts": {
    "scope_b_tool": 3,
    "scope_b": 3
  },
  "violations": {
    "scope_b_tool": [
      "[scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/Session Recaps/Session 17 - Migrating Forest and Thrin.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/session recaps/session 17 - migrating forest and thrin.md' not in allowlist).",
      "[scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/session prep/session_20_stacey_stuart_marla_reference.md' not in allowlist).",
      "[scope_b_grader:session_recap_ingest_session_20] assemble_recap_draft.target_session want 21 got 20."
    ],
    "scope_b": [
      "[scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/Session Recaps/Session 17 - Migrating Forest and Thrin.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/session recaps/session 17 - migrating forest and thrin.md' not in allowlist).",
      "[scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/session prep/session_20_stacey_stuart_marla_reference.md' not in allowlist).",
      "[scope_b_grader:session_recap_ingest_session_20] assemble_recap_draft.target_session want 21 got 20."
    ]
  },
  "corpus_fingerprint": "f77fc9511176bc60ed926f65daba3d73",
  "corpus_dir": "/tmp/session_recap_pre_state_7d9nbgng/eldyrwild-markdown",
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
      "new_hub_proposals": [],
      "dismissed": [
        {
          "name": "Stuart",
          "reason": "Child NPC with a single-session scene and no evidence yet of recurring hub-worthy presence."
        },
        {
          "name": "Stacey",
          "reason": "Important local child, but still reads as a one-town supporting NPC unless she recurs in later sessions."
        },
        {
          "name": "Marla",
          "reason": "Memorable town adult, but this recap alone does not establish enough cross-session recurrence for a new hub."
        },
        {
          "name": "Sara",
          "reason": "Named operator contact, but this session only uses her as a relay voice and not as a scene-driving NPC."
        },
        {
          "name": "Professor Tealeaf",
          "reason": "Mentioned only as an unanswered call target; no on-page action to audit."
        }
      ]
    },
    "plot_artifacts": [
      {
        "name": "Top-down tower blueprint",
        "evidence_quote": "It appears to be a top-down blueprint of a tower and is very well done.",
        "proposed_locations": [
          "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md",
          "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
          "Longmont Campaign/Campaign 2/Campaign 2 Notes.md"
        ]
      }
    ],
    "prep_pointer_proposal": {
      "prep_path": "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md",
      "recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "prep_append_line": "> See also: `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`",
      "recap_append_line": "> See also: `Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md`"
    },
    "notes_for_gm": "The raw notes included one duplicated paragraph block, which was removed mechanically in the recap draft. The prep packet strongly frames Stacey, Stuart, and Marla Brambleback, but the recap itself does not establish enough recurrence for new NPC hubs yet."
  },
  "recap_write_payload_sha256_16": "06aabd0e7dac9f3c",
  "final_text_chars": 2532,
  "primary_response_id": "resp_0931e29adcc3e6770069e3fd39434481969846753a9f9f4746",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.055431,
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.055431,
    "planner_cost_by_round_usd": [
      0.001502,
      0.002401,
      0.002468,
      0.011152,
      0.017901,
      0.014254,
      0.005753
    ],
    "planner_usage_totals": {
      "input_tokens": 187937,
      "cached_tokens": 182272,
      "total_tokens": 196273,
      "output_tokens": 8336
    },
    "pricing_note": "approximate public list prices; verify against billing"
  }
}
```
