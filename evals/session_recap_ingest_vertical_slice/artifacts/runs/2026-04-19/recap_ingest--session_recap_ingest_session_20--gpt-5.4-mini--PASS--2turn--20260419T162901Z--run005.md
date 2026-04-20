<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-19T16:29:01Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: PASS | tool_trace_gates: True | payload_gates: True | primary: artifacts/runs/2026-04-19/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--PASS--2turn--20260419T162901Z--run005.md | cohort: 5 | run_index: 4 -->

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
corpus_fprint:    42c0e9f8fbdb3d5b9d1ffa0999db2fa4
corpus_dir:       /tmp/session_recap_pre_state_c7wr9ujr/eldyrwild-markdown
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
  round[0] input=17959 output=22 cached=17408
  round[1] input=18282 output=162 cached=17920
  round[2] input=25472 output=54 cached=25088
  round[3] input=27595 output=2015 cached=27136
  round[4] input=31814 output=3348 cached=31744
  round[5] input=35301 output=2043 cached=33280
  round[6] input=37507 output=1321 cached=36864
  scenario_estimated_cost_usd: 0.057918

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Committed the recap at `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`.\n\nCorpus fingerprint: `e07f290f127fdf52e494ce6bd9de6778`.\n\nNo timeline-row append was run, because the prior structured payload’s `npc_audit.timeline_append_candidates` was not populated with any actionable existing-hub beats for this turn.","unsure_queue":null,"recap_write":{"schema_version":"recap_write_v1","recap_preview":{"path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","mode":"create","confirm_token":"e7177c85a19403dd0
...[truncated, total_chars=5454]...
 Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md` for Stacey / Stuart / Marla reference details."},"notes_for_gm":"The recap draft removed one duplicated paragraph mechanically. `Session 18 - Recap:` in the prior survey has a trailing colon in its title, but the new recap uses the clean canonical `Session 20 - Recap` styling. `npc_audit.timeline_append_candidates` is intentionally conservative; it only includes Lysandra because her scene clearly changes status. If you want timeline rows for any other recurring NPCs later, those can be handled in a separate pass."}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-19T16:29:01Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 4,
  "cohort_size": 5,
  "gates_passed": true,
  "tool_trace_gates_passed": true,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.057918,
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
  "corpus_fingerprint": "42c0e9f8fbdb3d5b9d1ffa0999db2fa4",
  "corpus_dir": "/tmp/session_recap_pre_state_c7wr9ujr/eldyrwild-markdown",
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
        "paragraph_preview": "Back in town, Bonogo is being guided by Stuart down an alley to a half burned building. According to Stuart this is where they will find Stacey....",
        "recommended_action": "remove_later"
      }
    ],
    "npc_audit": {
      "timeline_append_candidates": [
        {
          "slug": "captain_lysandra_ironveil",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
          "reason": "Lysandra was contacted, reported disorientation and missing memories, and was found under apparent cult influence with a tower blueprint."
        },
        {
          "slug": "torbin_jove",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/torbin_jove/",
          "reason": "Torbin was not a featured scene NPC this session, but if his hub exists as a recurring ally/operator he may merit a later timeline review; no row proposed here."
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
          "rationale": "Named, speaking child with recurring-family and town-crisis relevance; likely to recur."
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
          "rationale": "Named, emotionally distinct child who drove a memorable interaction and may recur as a town contact."
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
          "evidence_quote": "A farmer whispers to him that Stafl better step in and help because Marla is not someone to mess with.",
          "rationale": "Memorable adult authority figure with immediate town-function relevance and likely recurrence."
        }
      ],
      "dismissed": [
        {
          "name": "Stafl",
          "reason": "PC; skipped silently for NPC audit."
        },
        {
          "name": "Ephanna",
          "reason": "PC; skipped silently for NPC audit."
        },
        {
          "name": "Karesmine",
          "reason": "PC; skipped silently for NPC audit."
        },
        {
          "name": "Caelynn",
          "reason": "PC; skipped silently for NPC audit."
        },
        {
          "name": "Bonogo",
          "reason": "PC; skipped silently for NPC audit."
        },
        {
          "name": "Thrin",
          "reason": "NPC already in campaign context, but no separate hub/timeline action was proposed from this recap because his status change is not clearly a new beat here."
        },
        {
          "name": "Sara",
          "reason": "Operator/voice contact in the call chain, but not enough standalone scene presence in this recap for a hub proposal."
        },
        {
          "name": "Professor Tealeaf",
          "reason": "Mentioned only as an unanswered call target, with no direct on-screen action."
        },
        {
          "name": "Mayor",
          "reason": "Town official role without a named identity in this recap; not hub-worthy from this scene alone."
        },
        {
          "name": "Sheriff",
          "reason": "Town official role without a named identity in this recap; not hub-worthy from this scene alone."
        }
      ]
    },
    "plot_artifacts": [
      {
        "name": "Tower blueprint drawing",
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
      "prep_append_line": "> Prep note: see `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md` for the playthrough outcome and continuity beats.",
      "recap_append_line": "> Prep note: see `Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md` for Stacey / Stuart / Marla reference details."
    },
    "notes_for_gm": "The recap draft removed one duplicated paragraph mechanically. `Session 18 - Recap:` in the prior survey has a trailing colon in its title, but the new recap uses the clean canonical `Session 20 - Recap` styling. `npc_audit.timeline_append_candidates` is intentionally conservative; it only includes Lysandra because her scene clearly changes status. If you want timeline rows for any other recurring NPCs later, those can be handled in a separate pass."
  },
  "recap_write_payload_sha256_16": "cd21d94c8a5b5e5e",
  "final_text_chars": 5454,
  "primary_response_id": "resp_0be384d32ab4917d0069e502c62978819f893164d84e06ab9a",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.057918,
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.057918,
    "planner_cost_by_round_usd": [
      0.001818,
      0.002345,
      0.002413,
      0.011447,
      0.017499,
      0.013205,
      0.009192
    ],
    "planner_usage_totals": {
      "input_tokens": 193930,
      "cached_tokens": 189440,
      "output_tokens": 8965,
      "total_tokens": 202895
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
    "commit_required": false
  }
}
```
