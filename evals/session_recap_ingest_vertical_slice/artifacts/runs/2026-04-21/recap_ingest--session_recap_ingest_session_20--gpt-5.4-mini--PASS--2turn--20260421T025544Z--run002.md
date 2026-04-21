<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-21T02:55:44Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: PASS | tool_trace_gates: True | payload_gates: True | primary: artifacts/runs/2026-04-21/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--PASS--2turn--20260421T025544Z--run002.md | cohort: 3 | run_index: 1 -->

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
corpus_fprint:    cf0190be3ad626f12d2a5ea5640b0838
corpus_dir:       /tmp/session_recap_pre_state_96nx55oh/eldyrwild-markdown
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
  round[0] input=20383 output=16 cached=0
  round[1] input=20706 output=162 cached=20480
  round[2] input=27896 output=54 cached=27648
  round[3] input=30019 output=53 cached=29184
  round[4] input=30398 output=2015 cached=30208
  round[5] input=34617 output=420 cached=34304
  round[6] input=35176 output=2043 cached=34304
  round[7] input=37385 output=378 cached=36864
  scenario_estimated_cost_usd: 0.0568

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Committed `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`. No timeline rows were pending from the previous audit, so there was nothing else to append.","unsure_queue":[],"recap_write":{"schema_version":"recap_write_v1","recap_preview":{"path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","mode":"create","confirm_token":"e7177c85a19403dd0d7cea58c8a835ad"},"duplicate_paragraphs":[{"source_lines":[6,10],"paragraph_preview":"Back in town, Bonogo is being guided by Stuart down an alley to a half burned building. According to Stuart this is where they will find Stacey. As soon as they step inside the large warehouse they f…","recommended_action":"remove_later"}],"npc_audit":{"timeline_append_candidates":[],"new_hub_proposals":[],"dismissed":[]},"plot_artifacts":[],"prep_pointer_proposal":{"prep_path":"Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md","recap_path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","prep_append_line":"> **Prep:** See `Session Prep/session_20_stacey_stuart_marla_reference.md`. (Expand with session-specific prep-vs-play notes in `notes_for_gm`.)","recap_append_line":"> **Played:** See `Session Recaps/Session 20 - Recap.md`. (Expand with play-vs-prep deltas in `notes_for_gm`.)"},"notes_for_gm":""}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-21T02:55:44Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 1,
  "cohort_size": 3,
  "gates_passed": true,
  "tool_trace_gates_passed": true,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.0568,
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
  "violation_counts": {},
  "violations": {},
  "corpus_fingerprint": "cf0190be3ad626f12d2a5ea5640b0838",
  "corpus_dir": "/tmp/session_recap_pre_state_96nx55oh/eldyrwild-markdown",
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
    "notes_for_gm": ""
  },
  "recap_write_payload_sha256_16": "44ab26722a763174",
  "final_text_chars": 1388,
  "primary_response_id": "resp_0bbcc5d6ff921f5b0069e6e72d32048197bb11f697b9aa842e",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.0568,
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.0568,
    "planner_cost_by_round_usd": [
      0.015359,
      0.002435,
      0.002503,
      0.003054,
      0.011476,
      0.004698,
      0.01242,
      0.004857
    ],
    "planner_usage_totals": {
      "output_tokens": 5141,
      "total_tokens": 241721,
      "cached_tokens": 212992,
      "input_tokens": 236580
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
    "read_allowlist_soft_observations": [],
    "mechanical_fields_diff": {}
  }
}
```
