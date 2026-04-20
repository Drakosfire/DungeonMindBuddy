<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-19T21:41:40Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: PASS | tool_trace_gates: True | payload_gates: True | primary: artifacts/runs/2026-04-19/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--PASS--2turn--20260419T214140Z--run003.md | cohort: 5 | run_index: 2 -->

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
corpus_fprint:    7945fb0f2aa6376e88447eda63e9dc51
corpus_dir:       /tmp/session_recap_pre_state_pc3h9ynx/eldyrwild-markdown
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
  round[0] input=17959 output=16 cached=0
  round[1] input=18282 output=162 cached=17408
  round[2] input=25472 output=54 cached=25088
  round[3] input=27595 output=2015 cached=27136
  round[4] input=31814 output=3304 cached=31744
  round[5] input=35257 output=2043 cached=31744
  round[6] input=37462 output=1098 cached=36864
  scenario_estimated_cost_usd: 0.069755

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Committed **Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md** successfully. New corpus fingerprint: `431eb655d0ac60c6315b038b87ec5982`.\n\nI did not append any timeline rows in this turn; the earlier `npc_audit.timeline_append_candidates` was not acted on here.","unsure_queue":null,"recap_write":{"schema_version":"recap_write_v1","recap_preview":{"path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","mode":"create","confirm_token":"e7177c85a19403dd0d7cea58c8a835ad"},"duplicate_paragraphs":[{"source_lines
...[truncated, total_chars=4459]...
paign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md","recap_path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","prep_append_line":"> See also: Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","recap_append_line":"> See also: Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md"},"notes_for_gm":"The recap has been committed. The previous structured audit contained one obvious non-NPC false positive in timeline candidates (`torbin_jove`), which should be ignored if you hand off timeline work later."}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-19T21:41:40Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 2,
  "cohort_size": 5,
  "gates_passed": true,
  "tool_trace_gates_passed": true,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.069755,
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
  "corpus_fingerprint": "7945fb0f2aa6376e88447eda63e9dc51",
  "corpus_dir": "/tmp/session_recap_pre_state_pc3h9ynx/eldyrwild-markdown",
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
        "paragraph_preview": "Back in town, Bonogo is being guided by Stuart down an alley to a half burned building. According to Stuart this is where they will find Stacey.",
        "recommended_action": "remove_later"
      }
    ],
    "npc_audit": {
      "timeline_append_candidates": [
        {
          "slug": "captain_lysandra_ironveil",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
          "reason": "Lysandra is contacted, reported disoriented, and found under a likely spell with cult-like shimmer in her eyes; this is a meaningful status beat for her timeline."
        },
        {
          "slug": "torbin_jove",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/torbin_jove/",
          "reason": "Torbin is not in the session, so no timeline append is warranted."
        }
      ],
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
          "rationale": "Stacey is a named recurring child with clear relationship hooks, local importance, and likely future appearances."
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
          "rationale": "Marla is a named town power figure with immediate authority, strong scene presence, and likely recurring civic relevance."
        },
        {
          "proposed_slug": "stuart",
          "campaign_or_setting": "campaign",
          "proposed_location": "Longmont Campaign/Campaign 2/NPCs/stuart/",
          "initial_files": [
            "README.md",
            "stuart_character_dossier.md",
            "timeline.md"
          ],
          "evidence_quote": "According to Stuart this is where they will find Stacey.",
          "rationale": "Stuart is a named child with a distinct relationship web and likely ongoing utility as a sympathetic local contact."
        }
      ],
      "dismissed": [
        {
          "name": "The mayor",
          "reason": "Already an established town functionary with no new first-appearance hub need from this session."
        },
        {
          "name": "the sheriff",
          "reason": "Already an established town functionary with no new first-appearance hub need from this session."
        },
        {
          "name": "Professor Tealeaf",
          "reason": "Mentioned only as an unanswered contact; no new on-screen action this session."
        },
        {
          "name": "Sara",
          "reason": "An operator contact with no new material beyond relaying the call."
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
      },
      {
        "name": "Tainted meat cache",
        "evidence_quote": "Mixed in with the meat is cleverly disguised tainted meat.",
        "proposed_locations": [
          "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
          "Longmont Campaign/Campaign 2/Campaign 2 Notes.md",
          "Longmont Campaign/Campaign 2/Story threads backlog.md"
        ]
      }
    ],
    "prep_pointer_proposal": {
      "prep_path": "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md",
      "recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "prep_append_line": "> See also: Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "recap_append_line": "> See also: Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md"
    },
    "notes_for_gm": "The recap has been committed. The previous structured audit contained one obvious non-NPC false positive in timeline candidates (`torbin_jove`), which should be ignored if you hand off timeline work later."
  },
  "recap_write_payload_sha256_16": "d4cb1b3804aa37ed",
  "final_text_chars": 4459,
  "primary_response_id": "resp_01c3bbd1d28e3f770069e54c1022988195a0cf51d1c8d2715a",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.069755,
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.069755,
    "planner_cost_by_round_usd": [
      0.013541,
      0.00269,
      0.002413,
      0.011447,
      0.017301,
      0.014209,
      0.008154
    ],
    "planner_usage_totals": {
      "total_tokens": 202533,
      "input_tokens": 193841,
      "cached_tokens": 169984,
      "output_tokens": 8692
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
