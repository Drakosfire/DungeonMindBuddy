<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-19T21:41:39Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: PASS | tool_trace_gates: True | payload_gates: True | primary: artifacts/runs/2026-04-19/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--PASS--2turn--20260419T214139Z--run001.md | cohort: 5 | run_index: 0 -->

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
corpus_fprint:    8eb2965499b529c9486f89a7c03d9af8
corpus_dir:       /tmp/session_recap_pre_state_wpjyq64j/eldyrwild-markdown
hit_tool_limit:   False
tool_trace rows:  8

========================================================================
§ Prompt payload sizes
========================================================================
instructions:  {'chars': 24639, 'bytes': 27217, 'sha256_16': '2bb3b828b52270e0'}
user_line:     {'chars': 26894, 'bytes': 27006, 'sha256_16': 'd8211a736b03fb36'}

========================================================================
§ Token usage (per round)
========================================================================
  round[0] input=17959 output=16 cached=15360
  round[1] input=18282 output=162 cached=17920
  round[2] input=25472 output=54 cached=17920
  round[3] input=27595 output=2015 cached=27136
  round[4] input=31814 output=3526 cached=31744
  round[5] input=35479 output=2043 cached=31744
  round[6] input=37686 output=702 cached=37376
  scenario_estimated_cost_usd: 0.063086

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Committed the recap to `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`.\n\nNew corpus fingerprint: `04e3db8f477c1069afd9aced01bc0a80`.\n\nNo timeline-row candidates were returned for this session, so there were no `append_timeline_row` follow-ups to run.","unsure_queue":null,"recap_write":{"schema_version":"recap_write_v1","recap_preview":{"path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","mode":"create","confirm_token":"e7177c85a19403dd0d7cea58c8a835ad"},"duplicate_paragraphs":[{"source_lines":[6,
...[truncated, total_chars=2855]...
caps/Session 20 - Recap.md","prep_append_line":"> See Session 20 recap: Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","recap_append_line":"> Companion prep reference: Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md"},"notes_for_gm":"The prep doc strongly clarifies Stacey/Marla/Stuart texture and the tower clue; the recap body intentionally leaves that as observed session prose rather than merging prep-only details. The raw notes included a duplicated Bonogo/Stuart/Stacey warehouse paragraph, and the assembler removed the later copy."}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-19T21:41:39Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 0,
  "cohort_size": 5,
  "gates_passed": true,
  "tool_trace_gates_passed": true,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.063086,
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
  "violation_counts": {},
  "violations": {},
  "corpus_fingerprint": "8eb2965499b529c9486f89a7c03d9af8",
  "corpus_dir": "/tmp/session_recap_pre_state_wpjyq64j/eldyrwild-markdown",
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
        "paragraph_preview": "Back in town, Bonogo is being guided by Stuart down an alley to a half burned building. According to Stuart this is where they will find Stacey...",
        "recommended_action": "remove_later"
      }
    ],
    "npc_audit": {
      "timeline_append_candidates": [],
      "new_hub_proposals": [],
      "dismissed": [
        {
          "name": "Stuart",
          "reason": "First-appearance child NPC with a local one-scene role; useful, but not hub-worthy from this session alone."
        },
        {
          "name": "Stacey Brambleback",
          "reason": "Named child NPC with recurring potential, but the corpus already frames her as a local side character rather than a hub-level recurring figure this session."
        },
        {
          "name": "Marla Brambleback",
          "reason": "Named local functionary with strong scene presence, but still best treated as a town-side NPC for timeline tracking rather than a new hub proposal here."
        },
        {
          "name": "Sara",
          "reason": "Operator voice on the call, but the session does not establish enough distinct on-screen material to warrant a hub proposal."
        },
        {
          "name": "Professor Tealeaf",
          "reason": "Mentioned only as an unanswered call target; no direct on-screen action in this recap."
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
      "prep_append_line": "> See Session 20 recap: Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "recap_append_line": "> Companion prep reference: Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md"
    },
    "notes_for_gm": "The prep doc strongly clarifies Stacey/Marla/Stuart texture and the tower clue; the recap body intentionally leaves that as observed session prose rather than merging prep-only details. The raw notes included a duplicated Bonogo/Stuart/Stacey warehouse paragraph, and the assembler removed the later copy."
  },
  "recap_write_payload_sha256_16": "582ddcf8f3a694fc",
  "final_text_chars": 2855,
  "primary_response_id": "resp_04a55fd8055ad4130069e54c101ba081a1a838636f173b3154",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.063086,
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.063086,
    "planner_cost_by_round_usd": [
      0.003173,
      0.002345,
      0.007251,
      0.011447,
      0.0183,
      0.014376,
      0.006195
    ],
    "planner_usage_totals": {
      "total_tokens": 202805,
      "input_tokens": 194287,
      "cached_tokens": 179200,
      "output_tokens": 8518
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
    "commit_required": true
  }
}
```
