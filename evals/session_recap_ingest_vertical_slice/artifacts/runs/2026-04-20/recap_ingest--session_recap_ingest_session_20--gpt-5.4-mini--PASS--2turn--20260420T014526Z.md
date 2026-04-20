<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-20T01:45:26Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: PASS | tool_trace_gates: True | payload_gates: True | primary: artifacts/runs/2026-04-20/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--PASS--2turn--20260420T014526Z.md -->

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
corpus_fprint:    ec9eeb5f89756077489df6d11747a98e
corpus_dir:       /tmp/session_recap_pre_state_ix86yri9/eldyrwild-markdown
hit_tool_limit:   False
tool_trace rows:  9

========================================================================
§ Prompt payload sizes
========================================================================
instructions:  {'chars': 25416, 'bytes': 27994, 'sha256_16': '3939671996289316'}
user_line:     {'chars': 27744, 'bytes': 27856, 'sha256_16': 'bc18fecdc3663e3d'}

========================================================================
§ Token usage (per round)
========================================================================
  round[0] input=18595 output=22 cached=0
  round[1] input=18918 output=162 cached=18432
  round[2] input=26108 output=54 cached=18944
  round[3] input=28231 output=53 cached=25600
  round[4] input=28610 output=2015 cached=28160
  round[5] input=32829 output=2507 cached=30208
  round[6] input=35475 output=2043 cached=32256
  round[7] input=37566 output=399 cached=37376
  scenario_estimated_cost_usd: 0.073488

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"The commit failed because the confirm token is stale, so the corpus changed between preview and apply. I need a fresh dry-run before I can commit `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`.","unsure_queue":null,"recap_write":{"schema_version":"recap_write_v1","recap_preview":{"path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","mode":"create","confirm_token":"e7177c85a19403dd0d7cea58c8a835ad"},"duplicate_paragraphs":[{"source_lines":[6,10],"paragraph_preview":"Back in town, Bonogo is being guided by Stuart down an alley to a half burned building. According to Stuart this is where they will find Stacey. As soon as they step inside the large warehouse they f…","recommended_action":"remove_later"}],"npc_audit":{"timeline_append_candidates":[],"new_hub_proposals":[],"dismissed":[]},"plot_artifacts":[],"prep_pointer_proposal":{"prep_path":"Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md","recap_path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","prep_append_line":"> **Prep:** See `Session Prep/session_20_stacey_stuart_marla_reference.md`. (Expand with session-specific prep-vs-play notes in `notes_for_gm`.)","recap_append_line":"> **Played:** See `Session Recaps/Session 20 - Recap.md`. (Expand with play-vs-prep deltas in `notes_for_gm`.)"},"notes_for_gm":"Stale token on commit; no write completed."}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-20T01:45:26Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": null,
  "cohort_size": null,
  "gates_passed": true,
  "tool_trace_gates_passed": true,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.073488,
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
  "corpus_fingerprint": "ec9eeb5f89756077489df6d11747a98e",
  "corpus_dir": "/tmp/session_recap_pre_state_ix86yri9/eldyrwild-markdown",
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
    "notes_for_gm": "Stale token on commit; no write completed."
  },
  "recap_write_payload_sha256_16": "2550b13ca142aec2",
  "final_text_chars": 1476,
  "primary_response_id": "resp_0758719470e28f3f0069e585307bc881a3a79c3738b969b2be",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.073488,
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.073488,
    "planner_cost_by_round_usd": [
      0.014045,
      0.002476,
      0.007037,
      0.004132,
      0.011517,
      0.015513,
      0.014027,
      0.004741
    ],
    "planner_usage_totals": {
      "output_tokens": 7255,
      "input_tokens": 226332,
      "cached_tokens": 190976,
      "total_tokens": 233587
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
    "preview_required": true,
    "commit_required": true,
    "build_recap_write_payload_called": true,
    "mechanical_fields_match": true,
    "mechanical_fields_diff": {}
  }
}
```
