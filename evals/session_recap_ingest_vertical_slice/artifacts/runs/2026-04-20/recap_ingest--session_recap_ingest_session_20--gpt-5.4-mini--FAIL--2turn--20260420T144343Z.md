<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-20T14:43:43Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: FAIL | tool_trace_gates: False | payload_gates: True | primary: artifacts/runs/2026-04-20/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--FAIL--2turn--20260420T144343Z.md -->

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
corpus_fprint:    90d61d30d3251a757eec4f4e2c8c3a76
corpus_dir:       /tmp/session_recap_pre_state_xi45_725/eldyrwild-markdown
hit_tool_limit:   False
tool_trace rows:  10

========================================================================
§ Prompt payload sizes
========================================================================
instructions:  {'chars': 25416, 'bytes': 27994, 'sha256_16': '3939671996289316'}
user_line:     {'chars': 27744, 'bytes': 27856, 'sha256_16': 'bc18fecdc3663e3d'}

========================================================================
§ Token usage (per round)
========================================================================
  round[0] input=18595 output=66 cached=0
  round[1] input=19134 output=162 cached=18432
  round[2] input=26324 output=54 cached=18944
  round[3] input=28447 output=53 cached=26112
  round[4] input=28826 output=2014 cached=28160
  round[5] input=33033 output=2518 cached=30720
  round[6] input=35690 output=2037 cached=32768
  round[7] input=37888 output=409 cached=37376
  scenario_estimated_cost_usd: 0.073915

========================================================================
§ Violations
========================================================================
  scope_b: [scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/_ingest_staging/session_20_raw_notes.md' not in allowlist).
  scope_b_tool: [scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/_ingest_staging/session_20_raw_notes.md' not in allowlist).

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Committed `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md` successfully. New corpus fingerprint: `b64dc0149d3394984be46cee7dca123e`.\n\nNo NPC timeline rows were proposed from this recap, so there were no `append_timeline_row` follow-ups to run.","unsure_queue":null,"recap_write":{"schema_version":"recap_write_v1","recap_preview":{"path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","mode":"create","confirm_token":"959df16cedceab2219ca87575348e850"},"duplicate_paragraphs":[{"source_lines":[6,10],"paragraph_preview":"Back in town, Bonogo is being guided by Stuart down an alley to a half burned building. According to Stuart this is where they will find Stacey. As soon as they step inside the large warehouse they f…","recommended_action":"remove_later"}],"npc_audit":{"timeline_append_candidates":[],"new_hub_proposals":[],"dismissed":[]},"plot_artifacts":[],"prep_pointer_proposal":{"prep_path":"Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md","recap_path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","prep_append_line":"> **Prep:** See `Session Prep/session_20_stacey_stuart_marla_reference.md`. (Expand with session-specific prep-vs-play notes in `notes_for_gm`.)","recap_append_line":"> **Played:** See `Session Recaps/Session 20 - Recap.md`. (Expand with play-vs-prep deltas in `notes_for_gm`.)"},"notes_for_gm":""}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-20T14:43:43Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": null,
  "cohort_size": null,
  "gates_passed": false,
  "tool_trace_gates_passed": false,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.073915,
  "tool_trace_rows": 10,
  "tool_trace_tools": [
    "get_recap_context",
    "read_corpus_file",
    "read_corpus_file",
    "read_corpus_file",
    "read_corpus_file",
    "read_corpus_file",
    "assemble_recap_draft",
    "build_recap_write_payload",
    "write_corpus_file",
    "write_corpus_file"
  ],
  "violation_counts": {
    "scope_b_tool": 1,
    "scope_b": 1
  },
  "violations": {
    "scope_b_tool": [
      "[scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/_ingest_staging/session_20_raw_notes.md' not in allowlist)."
    ],
    "scope_b": [
      "[scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/_ingest_staging/session_20_raw_notes.md' not in allowlist)."
    ]
  },
  "corpus_fingerprint": "90d61d30d3251a757eec4f4e2c8c3a76",
  "corpus_dir": "/tmp/session_recap_pre_state_xi45_725/eldyrwild-markdown",
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
        "paragraph_preview": "Back in town, Bonogo is being guided by Stuart down an alley to a half burned building. According to Stuart this is where they will find Stacey. As soon as they step inside the large warehouse they f…",
        "recommended_action": "remove_later"
      }
    ],
    "npc_audit": {
      "timeline_append_candidates": [],
      "new_hub_proposals": [],
      "dismissed": []
    },
    "plot_artifacts": [],
    "prep_pointer_proposal": {
      "prep_path": "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md",
      "recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "prep_append_line": "> **Prep:** See `Session Prep/session_20_stacey_stuart_marla_reference.md`. (Expand with session-specific prep-vs-play notes in `notes_for_gm`.)",
      "recap_append_line": "> **Played:** See `Session Recaps/Session 20 - Recap.md`. (Expand with play-vs-prep deltas in `notes_for_gm`.)"
    },
    "notes_for_gm": ""
  },
  "recap_write_payload_sha256_16": "05dc457667a62cc1",
  "final_text_chars": 1484,
  "primary_response_id": "resp_0949e3f37264a5590069e63b9cd090819fac3a3091638e3338",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.073915,
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.073915,
    "planner_cost_by_round_usd": [
      0.014243,
      0.002638,
      0.007199,
      0.003948,
      0.011675,
      0.01537,
      0.013816,
      0.005028
    ],
    "planner_usage_totals": {
      "input_tokens": 227937,
      "output_tokens": 7313,
      "cached_tokens": 192512,
      "total_tokens": 235250
    },
    "pricing_note": "approximate public list prices; verify against billing"
  },
  "scope_b_extras": {
    "write_corpus_file_phases": {
      "calls": 2,
      "previews": 1,
      "commits": 1,
      "phases": "preview→commit"
    },
    "write_corpus_file_soft_observations": [],
    "write_corpus_file_last_commit_outcome": {
      "succeeded": true,
      "phase": "committed",
      "error": null
    },
    "preview_required": true,
    "commit_required": true,
    "build_recap_write_payload_called": true,
    "mechanical_fields_match": true,
    "mechanical_fields_diff": {}
  }
}
```
