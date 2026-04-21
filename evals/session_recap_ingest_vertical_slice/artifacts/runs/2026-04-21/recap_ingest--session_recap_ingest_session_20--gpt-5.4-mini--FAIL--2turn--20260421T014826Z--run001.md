<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-21T01:48:26Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: FAIL | tool_trace_gates: False | payload_gates: True | primary: artifacts/runs/2026-04-21/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--FAIL--2turn--20260421T014826Z--run001.md | cohort: 3 | run_index: 0 -->

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
corpus_fprint:    743a24310acfd7bce94c1590823efea4
corpus_dir:       /tmp/session_recap_pre_state_s5zd5i02/eldyrwild-markdown
hit_tool_limit:   False
tool_trace rows:  9

========================================================================
§ Prompt payload sizes
========================================================================
instructions:  {'chars': 30014, 'bytes': 32736, 'sha256_16': 'b7bc7624a9a7fef1'}
user_line:     {'chars': 30352, 'bytes': 30474, 'sha256_16': '5de2eccefe317442'}

========================================================================
§ Token usage (per round)
========================================================================
  round[0] input=20383 output=16 cached=19968
  round[1] input=20706 output=162 cached=19968
  round[2] input=27896 output=54 cached=27136
  round[3] input=30019 output=53 cached=29184
  round[4] input=30398 output=2015 cached=30208
  round[5] input=34617 output=558 cached=32256
  round[6] input=35314 output=2043 cached=34304
  round[7] input=37405 output=427 cached=36864
  scenario_estimated_cost_usd: 0.046355

========================================================================
§ Violations
========================================================================
  scope_b: [scope_b_grader:session_recap_ingest_session_20] commit_required: last write_corpus_file commit at trace index 8 did not succeed (server returned ok=false / Error response). Server response: 'stale confirm_token (file or content changed since dry_run). Re-run with dry_run=true to get a fresh token.'. The two-phase contract requires the final dry_run=false call to land bytes; a refused commit means nothing was written.
  scope_b_tool: [scope_b_grader:session_recap_ingest_session_20] commit_required: last write_corpus_file commit at trace index 8 did not succeed (server returned ok=false / Error response). Server response: 'stale confirm_token (file or content changed since dry_run). Re-run with dry_run=true to get a fresh token.'. The two-phase contract requires the final dry_run=false call to land bytes; a refused commit means nothing was written.

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"The commit token went stale before the final write could land, so the recap was not committed. I need a fresh dry-run preview before I can safely apply `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`.","unsure_queue":null,"recap_write":{"schema_version":"recap_write_v1","recap_preview":{"path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","mode":"create","confirm_token":"e7177c85a19403dd0d7cea58c8a835ad"},"duplicate_paragraphs":[{"source_lines":[6,10],"paragraph_preview":"Back in town, Bonogo is being guided by Stuart down an alley to a half burned building. According to Stuart this is where they will find Stacey. As soon as they step inside the large warehouse they f…","recommended_action":"remove_later"}],"npc_audit":{"timeline_append_candidates":[],"new_hub_proposals":[],"dismissed":[]},"plot_artifacts":[],"prep_pointer_proposal":{"prep_path":"Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md","recap_path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","prep_append_line":"> **Prep:** See `Session Prep/session_20_stacey_stuart_marla_reference.md`. (Expand with session-specific prep-vs-play notes in `notes_for_gm`.)","recap_append_line":"> **Played:** See `Session Recaps/Session 20 - Recap.md`. (Expand with play-vs-prep deltas in `notes_for_gm`.)"},"notes_for_gm":"The final commit failed because the confirm token became stale between preview and apply; the file likely changed or the preview window expired. A new dry-run preview is required before retrying."}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-21T01:48:26Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 0,
  "cohort_size": 3,
  "gates_passed": false,
  "tool_trace_gates_passed": false,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.046355,
  "tool_trace_rows": 9,
  "tool_trace_tools": [
    "get_recap_context",
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
      "[scope_b_grader:session_recap_ingest_session_20] commit_required: last write_corpus_file commit at trace index 8 did not succeed (server returned ok=false / Error response). Server response: 'stale confirm_token (file or content changed since dry_run). Re-run with dry_run=true to get a fresh token.'. The two-phase contract requires the final dry_run=false call to land bytes; a refused commit means nothing was written."
    ],
    "scope_b": [
      "[scope_b_grader:session_recap_ingest_session_20] commit_required: last write_corpus_file commit at trace index 8 did not succeed (server returned ok=false / Error response). Server response: 'stale confirm_token (file or content changed since dry_run). Re-run with dry_run=true to get a fresh token.'. The two-phase contract requires the final dry_run=false call to land bytes; a refused commit means nothing was written."
    ]
  },
  "corpus_fingerprint": "743a24310acfd7bce94c1590823efea4",
  "corpus_dir": "/tmp/session_recap_pre_state_s5zd5i02/eldyrwild-markdown",
  "recap_write_payload": {
    "schema_version": "recap_write_v1",
    "recap_preview": {
      "path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "mode": "create",
      "confirm_token": "e7177c85a19403dd0d7cea58c8a835ad"
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
    "notes_for_gm": "The final commit failed because the confirm token became stale between preview and apply; the file likely changed or the preview window expired. A new dry-run preview is required before retrying."
  },
  "recap_write_payload_sha256_16": "d7bb5e0b1f219901",
  "final_text_chars": 1635,
  "primary_response_id": "resp_0a8bbc60b9539c9a0069e6d7669288819394ca2f786da9e241",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.046355,
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.046355,
    "planner_cost_by_round_usd": [
      0.001881,
      0.00278,
      0.002848,
      0.003054,
      0.011476,
      0.006701,
      0.012524,
      0.005092
    ],
    "planner_usage_totals": {
      "output_tokens": 5328,
      "cached_tokens": 229888,
      "input_tokens": 236738,
      "total_tokens": 242066
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
      "succeeded": false,
      "phase": null,
      "error": "stale confirm_token (file or content changed since dry_run). Re-run with dry_run=true to get a fresh token."
    },
    "preview_required": true,
    "commit_required": true,
    "build_recap_write_payload_called": true,
    "mechanical_fields_match": true,
    "read_allowlist_soft_observations": [],
    "mechanical_fields_diff": {}
  }
}
```
