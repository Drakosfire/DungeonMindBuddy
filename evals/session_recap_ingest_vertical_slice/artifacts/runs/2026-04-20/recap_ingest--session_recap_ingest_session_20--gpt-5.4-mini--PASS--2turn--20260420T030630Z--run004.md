<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-20T03:06:30Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: PASS | tool_trace_gates: True | payload_gates: True | primary: artifacts/runs/2026-04-20/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--PASS--2turn--20260420T030630Z--run004.md | cohort: 5 | run_index: 3 -->

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
corpus_fprint:    1afc69781016531940da18f301489a54
corpus_dir:       /tmp/session_recap_pre_state_k2f3j1tf/eldyrwild-markdown
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
  round[0] input=18595 output=16 cached=18432
  round[1] input=18918 output=162 cached=18432
  round[2] input=26108 output=54 cached=25600
  round[3] input=28231 output=53 cached=25600
  round[4] input=28610 output=2015 cached=28160
  round[5] input=32829 output=2497 cached=30208
  round[6] input=35465 output=2043 cached=32256
  round[7] input=37672 output=407 cached=0
  scenario_estimated_cost_usd: 0.081818

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Committed `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md` successfully; the new corpus fingerprint is `04bffb2f5601695fbc1ec209ca64b705`. No NPC timeline rows were queued in the prior payload, so there was nothing else to append.","unsure_queue":null,"recap_write":{"schema_version":"recap_write_v1","recap_preview":{"path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","mode":"create","confirm_token":"e7177c85a19403dd0d7cea58c8a835ad"},"duplicate_paragraphs":[{"source_lines":[6,10],"paragraph_preview":"Back in town, Bonogo is being guided by Stuart down an alley to a half burned building. According to Stuart this is where they will find Stacey. As soon as they step inside the large warehouse they f…","recommended_action":"remove_later"}],"npc_audit":{"timeline_append_candidates":[],"new_hub_proposals":[],"dismissed":[]},"plot_artifacts":[],"prep_pointer_proposal":{"prep_path":"Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md","recap_path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","prep_append_line":"> **Prep:** See `Session Prep/session_20_stacey_stuart_marla_reference.md`. (Expand with session-specific prep-vs-play notes in `notes_for_gm`.)","recap_append_line":"> **Played:** See `Session Recaps/Session 20 - Recap.md`. (Expand with play-vs-prep deltas in `notes_for_gm`.)"},"notes_for_gm":""}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-20T03:06:30Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 3,
  "cohort_size": 5,
  "gates_passed": true,
  "tool_trace_gates_passed": true,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.081818,
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
  "corpus_fingerprint": "1afc69781016531940da18f301489a54",
  "corpus_dir": "/tmp/session_recap_pre_state_k2f3j1tf/eldyrwild-markdown",
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
  "final_text_chars": 1469,
  "primary_response_id": "resp_013267ea14b09da20069e598331db8819e850214603181e26c",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.081818,
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.081818,
    "planner_cost_by_round_usd": [
      0.001577,
      0.002476,
      0.002544,
      0.004132,
      0.011517,
      0.015468,
      0.014019,
      0.030085
    ],
    "planner_usage_totals": {
      "total_tokens": 233675,
      "output_tokens": 7247,
      "cached_tokens": 178688,
      "input_tokens": 226428
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
