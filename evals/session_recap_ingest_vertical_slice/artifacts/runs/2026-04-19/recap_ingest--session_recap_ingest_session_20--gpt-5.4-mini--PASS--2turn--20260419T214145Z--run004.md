<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-19T21:41:45Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: PASS | tool_trace_gates: True | payload_gates: True | primary: artifacts/runs/2026-04-19/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--PASS--2turn--20260419T214145Z--run004.md | cohort: 5 | run_index: 3 -->

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
corpus_fprint:    2467a5759aaa796ab1dbe8e0bfd5f2cc
corpus_dir:       /tmp/session_recap_pre_state_9hs4em9w/eldyrwild-markdown
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
  round[0] input=17959 output=16 cached=17408
  round[1] input=18282 output=162 cached=17920
  round[2] input=25472 output=54 cached=25088
  round[3] input=27595 output=2015 cached=27136
  round[4] input=31814 output=4366 cached=31744
  round[5] input=36319 output=2043 cached=31232
  round[6] input=38530 output=1027 cached=37888
  scenario_estimated_cost_usd: 0.063371

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Committed the recap to `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`.\n\nNew corpus fingerprint: `9a8f51e59d6043d060e2ac2f657216ff`.\n\nNo NPC timeline rows were queued from the previous payload, so there was nothing further to append.","unsure_queue":null,"recap_write":{"schema_version":"recap_write_v1","recap_preview":{"path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","mode":"create","confirm_token":"e7177c85a19403dd0d7cea58c8a835ad"},"duplicate_paragraphs":[{"source_lines":[6,10],"paragraph_pr
...[truncated, total_chars=4199]...
_path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","prep_append_line":"> See recap: `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`","recap_append_line":"> Companion prep: `Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md`"},"notes_for_gm":"The recap draft preserves the raw-note wording and the mechanically removed duplicate paragraph is surfaced above. The prep doc strongly supports a fuller interpretation of Stacey, Stuart, and Marla than the recap itself, but that material was not merged into the recap body."}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-19T21:41:45Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 3,
  "cohort_size": 5,
  "gates_passed": true,
  "tool_trace_gates_passed": true,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.063371,
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
  "corpus_fingerprint": "2467a5759aaa796ab1dbe8e0bfd5f2cc",
  "corpus_dir": "/tmp/session_recap_pre_state_9hs4em9w/eldyrwild-markdown",
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
          "rationale": "She is a named, recurring child NPC with direct ties to town conflict and future utility in the Mossford side story."
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
          "rationale": "She is a named local authority figure with strong scene presence and likely repeat relevance around Mossford labor and evacuation politics."
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
          "rationale": "He is a named, sympathetic child NPC who clearly recurs in the Mossford social web and is likely to matter again."
        }
      ],
      "dismissed": [
        {
          "name": "Mayor",
          "reason": "Important scene authority, but unnamed in the recap and not a hub-worthy unique NPC from this text alone."
        },
        {
          "name": "Sheriff",
          "reason": "Important scene authority, but unnamed in the recap and not a hub-worthy unique NPC from this text alone."
        },
        {
          "name": "Professor Tealeaf",
          "reason": "Mentioned only as a contact point here; the recap gives no first-appearance detail beyond the call attempt."
        },
        {
          "name": "Sara",
          "reason": "Existing operator role is referenced, but this recap does not establish a new first appearance worth a new hub."
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
      "prep_append_line": "> See recap: `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`",
      "recap_append_line": "> Companion prep: `Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md`"
    },
    "notes_for_gm": "The recap draft preserves the raw-note wording and the mechanically removed duplicate paragraph is surfaced above. The prep doc strongly supports a fuller interpretation of Stacey, Stuart, and Marla than the recap itself, but that material was not merged into the recap body."
  },
  "recap_write_payload_sha256_16": "31e26de2eb295166",
  "final_text_chars": 4199,
  "primary_response_id": "resp_088d9393cbd7d5570069e54c1122d8819783d20f18369b716d",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.063371,
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.063371,
    "planner_cost_by_round_usd": [
      0.001791,
      0.002345,
      0.002413,
      0.011447,
      0.02208,
      0.015351,
      0.007945
    ],
    "planner_usage_totals": {
      "total_tokens": 205654,
      "input_tokens": 195971,
      "cached_tokens": 188416,
      "output_tokens": 9683
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
