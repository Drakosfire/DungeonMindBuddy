<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-20T18:09:17Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: PASS | tool_trace_gates: True | payload_gates: True | primary: artifacts/runs/2026-04-20/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--PASS--2turn--20260420T180917Z.md -->

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
corpus_fprint:    d7f7236b6d37ba9b2e1a3d842b5e4b14
corpus_dir:       /tmp/session_recap_pre_state_za_obl7t/eldyrwild-markdown
hit_tool_limit:   False
tool_trace rows:  9

========================================================================
§ Prompt payload sizes
========================================================================
instructions:  {'chars': 30039, 'bytes': 32769, 'sha256_16': 'a8db0aad0f219082'}
user_line:     {'chars': 27744, 'bytes': 27856, 'sha256_16': 'bc18fecdc3663e3d'}

========================================================================
§ Token usage (per round)
========================================================================
  round[0] input=19788 output=16 cached=11776
  round[1] input=20111 output=162 cached=19456
  round[2] input=27301 output=54 cached=19968
  round[3] input=29424 output=53 cached=27136
  round[4] input=29803 output=2015 cached=29184
  round[5] input=34022 output=2466 cached=31744
  round[6] input=36627 output=2043 cached=33792
  round[7] input=38835 output=412 cached=38400
  scenario_estimated_cost_usd: 0.066695

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Committed `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`.\n\nCorpus fingerprint: `ac4b77aaaae98d0867cb99b7a6454c62`.\n\nNo `npc_audit.timeline_append_candidates` were returned, so no timeline-row appends were needed.","unsure_queue":null,"recap_write":{"schema_version":"recap_write_v1","recap_preview":{"path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","mode":"create","confirm_token":"e7177c85a19403dd0d7cea58c8a835ad"},"duplicate_paragraphs":[{"source_lines":[6,10],"paragraph_preview":"Back in town, Bonogo is being guided by Stuart down an alley to a half burned building. According to Stuart this is where they will find Stacey. As soon as they step inside the large warehouse they f…","recommended_action":"remove_later"}],"npc_audit":{"timeline_append_candidates":[],"new_hub_proposals":[],"dismissed":[]},"plot_artifacts":[],"prep_pointer_proposal":{"prep_path":"Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md","recap_path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","prep_append_line":"> **Prep:** See `Session Prep/session_20_stacey_stuart_marla_reference.md`. (Expand with session-specific prep-vs-play notes in `notes_for_gm`.)","recap_append_line":"> **Played:** See `Session Recaps/Session 20 - Recap.md`. (Expand with play-vs-prep deltas in `notes_for_gm`.)"},"notes_for_gm":""}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-20T18:09:17Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": null,
  "cohort_size": null,
  "gates_passed": true,
  "tool_trace_gates_passed": true,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.066695,
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
  "corpus_fingerprint": "d7f7236b6d37ba9b2e1a3d842b5e4b14",
  "corpus_dir": "/tmp/session_recap_pre_state_za_obl7t/eldyrwild-markdown",
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
  "final_text_chars": 1457,
  "primary_response_id": "resp_077da1a42e1755960069e66bc92f3081918c03bc3cbe472f27",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.066695,
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.066695,
    "planner_cost_by_round_usd": [
      0.006964,
      0.002679,
      0.00724,
      0.00399,
      0.011721,
      0.015186,
      0.013854,
      0.00506
    ],
    "planner_usage_totals": {
      "input_tokens": 235911,
      "cached_tokens": 211456,
      "total_tokens": 243132,
      "output_tokens": 7221
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
