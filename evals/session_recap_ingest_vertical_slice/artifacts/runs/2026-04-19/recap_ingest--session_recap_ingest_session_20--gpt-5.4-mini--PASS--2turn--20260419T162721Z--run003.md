<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-19T16:27:21Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: PASS | tool_trace_gates: True | payload_gates: True | primary: artifacts/runs/2026-04-19/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--PASS--2turn--20260419T162721Z--run003.md | cohort: 5 | run_index: 2 -->

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
corpus_fprint:    54422fdc41fef2eb3713853716a78d02
corpus_dir:       /tmp/session_recap_pre_state_lsmjnxjp/eldyrwild-markdown
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
  round[4] input=31814 output=2994 cached=31232
  round[5] input=34947 output=2043 cached=31744
  round[6] input=37158 output=935 cached=36864
  scenario_estimated_cost_usd: 0.055416

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Committed the recap at `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`.\n\nNo timeline-row candidates were produced in the prior review, so there was nothing to append after commit.","unsure_queue":null,"recap_write":{"schema_version":"recap_write_v1","recap_preview":{"path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","mode":"create","confirm_token":"e7177c85a19403dd0d7cea58c8a835ad"},"duplicate_paragraphs":[{"source_lines":[6,6],"paragraph_preview":"Back in town, Bonogo is being guided by Stuart do
...[truncated, total_chars=3868]...
ampaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md","recap_path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","prep_append_line":"\n> Companion recap: Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","recap_append_line":"\n> Companion prep: Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md"},"notes_for_gm":"The raw notes include one duplicated Bonogo/Stacey scene paragraph; the assembler removed the later copy. The recap body is otherwise a direct mechanical transform of the supplied notes."}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-19T16:27:21Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 2,
  "cohort_size": 5,
  "gates_passed": true,
  "tool_trace_gates_passed": true,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.055416,
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
  "corpus_fingerprint": "54422fdc41fef2eb3713853716a78d02",
  "corpus_dir": "/tmp/session_recap_pre_state_lsmjnxjp/eldyrwild-markdown",
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
        "paragraph_preview": "Back in town, Bonogo is being guided by Stuart down an alley to a half burned building. According to Stuart this is where they will find Stacey....",
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
          "rationale": "Named, recurring child NPC with clear scene impact and future-use potential."
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
          "rationale": "Named child NPC with a defined relationship to Stacey and Bonogo, likely to recur."
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
          "rationale": "Memorable named adult with authority over town labor and immediate future relevance."
        }
      ],
      "dismissed": [
        {
          "name": "Stafl",
          "reason": "Already established in-session but no hub evidence was needed for a new proposal here."
        },
        {
          "name": "Sara",
          "reason": "Identified as one of Mirathorn's operators, but no hub confirmation was opened and the recap only uses her in a phone relay role."
        },
        {
          "name": "Professor Tealeaf",
          "reason": "Mentioned only as a contact attempt and not enough for a hub proposal from this recap alone."
        },
        {
          "name": "Lysandra",
          "reason": "Existing campaign NPC with prior hub elsewhere, but this skill does not read dossiers or statblocks and does not propose timeline rows here."
        },
        {
          "name": "Thrin",
          "reason": "Existing recurring figure, but this skill does not propose timeline rows without a confirmed hub read."
        },
        {
          "name": "Stacey's mother Marla",
          "reason": "Covered under the formal new hub proposal for Marla Brambleback."
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
      "prep_append_line": "\n> Companion recap: Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "recap_append_line": "\n> Companion prep: Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md"
    },
    "notes_for_gm": "The raw notes include one duplicated Bonogo/Stacey scene paragraph; the assembler removed the later copy. The recap body is otherwise a direct mechanical transform of the supplied notes."
  },
  "recap_write_payload_sha256_16": "ea724b0e15f41ce7",
  "final_text_chars": 3868,
  "primary_response_id": "resp_095c5a84ee355baa0069e50262d8bc819eb2930b7d317032f8",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.055416,
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.055416,
    "planner_cost_by_round_usd": [
      0.001791,
      0.002345,
      0.002413,
      0.011447,
      0.016252,
      0.013977,
      0.007193
    ],
    "planner_usage_totals": {
      "input_tokens": 193227,
      "cached_tokens": 187392,
      "output_tokens": 8219,
      "total_tokens": 201446
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
