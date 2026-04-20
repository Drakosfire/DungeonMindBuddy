<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-19T21:45:53Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: PASS | tool_trace_gates: True | payload_gates: True | primary: artifacts/runs/2026-04-19/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--PASS--2turn--20260419T214553Z--run002.md | cohort: 5 | run_index: 1 -->

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
corpus_fprint:    c56eb6fbd4a437166e6d99b5bc9d394d
corpus_dir:       /tmp/session_recap_pre_state_q216k628/eldyrwild-markdown
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
  round[1] input=18282 output=162 cached=17408
  round[2] input=25472 output=54 cached=17920
  round[3] input=27595 output=2020 cached=27136
  round[4] input=31819 output=2880 cached=29184
  round[5] input=34838 output=2043 cached=31744
  round[6] input=37051 output=842 cached=36352
  scenario_estimated_cost_usd: 0.062643

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Committed `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md` successfully.\n\nCorpus fingerprint: `63a0ed0c2ef3e923d3df656f9c61374c`.\n\nNo timeline append candidates were identified in the previous audit, so no `append_timeline_row` calls were needed.","unsure_queue":null,"recap_write":{"schema_version":"recap_write_v1","recap_preview":{"path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","mode":"create","confirm_token":"e7177c85a19403dd0d7cea58c8a835ad"},"duplicate_paragraphs":[{"source_lines":[6,6],"p
...[truncated, total_chars=3423]...
ath":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","prep_append_line":"> See also: `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`","recap_append_line":"> See also: `Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md`"},"notes_for_gm":"The recap draft includes one mechanically detected duplicate paragraph pair that the ingest helper already removed. I also noted a likely naming inconsistency in the raw notes: the session alternates between Karsemine/Karesmine. The draft preserves the raw-note spelling as assembled."}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-19T21:45:53Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 1,
  "cohort_size": 5,
  "gates_passed": true,
  "tool_trace_gates_passed": true,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.062643,
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
  "corpus_fingerprint": "c56eb6fbd4a437166e6d99b5bc9d394d",
  "corpus_dir": "/tmp/session_recap_pre_state_q216k628/eldyrwild-markdown",
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
          6
        ],
        "paragraph_preview": "Back in town, Bonogo is being guided by Stuart down an alley to a half burned building. According to Stuart this is where they will find Stacey. As soon as they step inside the large warehouse they find a group of children formed into two groups with what appear to be the leaders arguing in the middle.",
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
          "rationale": "Named, recurring, and socially important enough to merit a hub after a first strong session appearance."
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
          "rationale": "Marla is a memorable named town power with direct story relevance and recurring potential."
        }
      ],
      "dismissed": [
        {
          "name": "Stuart",
          "reason": "A child NPC with clear scene utility, but the prep packet frames him as a side character rather than a hub-worthy recurring power center."
        },
        {
          "name": "Professor Tealeaf",
          "reason": "Mentioned only as a call target with no on-page appearance in this session."
        },
        {
          "name": "Sara",
          "reason": "Important operator voice but not materially introduced beyond a call connection here."
        }
      ]
    },
    "plot_artifacts": [
      {
        "name": "Top-down blueprint of a tower",
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
      "prep_append_line": "> See also: `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`",
      "recap_append_line": "> See also: `Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md`"
    },
    "notes_for_gm": "The recap draft includes one mechanically detected duplicate paragraph pair that the ingest helper already removed. I also noted a likely naming inconsistency in the raw notes: the session alternates between Karsemine/Karesmine. The draft preserves the raw-note spelling as assembled."
  },
  "recap_write_payload_sha256_16": "6afed3cab7dfccdc",
  "final_text_chars": 3423,
  "primary_response_id": "resp_033587d4ea61f94c0069e54d0ceea0819d9e03dbfb8e4c7d87",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.062643,
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.062643,
    "planner_cost_by_round_usd": [
      0.003173,
      0.00269,
      0.007251,
      0.011469,
      0.017125,
      0.013895,
      0.00704
    ],
    "planner_usage_totals": {
      "total_tokens": 201033,
      "input_tokens": 193016,
      "cached_tokens": 175104,
      "output_tokens": 8017
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
