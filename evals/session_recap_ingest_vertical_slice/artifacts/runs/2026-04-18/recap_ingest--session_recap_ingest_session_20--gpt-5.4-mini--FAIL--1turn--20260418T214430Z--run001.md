<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-18T21:44:30Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: FAIL | tool_trace_gates: False | payload_gates: True | primary: artifacts/runs/2026-04-18/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--FAIL--1turn--20260418T214430Z--run001.md | cohort: 5 | run_index: 0 -->

## Review (printed)

```
========================================================================
SESSION RECAP INGEST — PLANNER REVIEW
========================================================================
scenario_id:      session_recap_ingest_session_20
model_id:         gpt-5.4-mini
gates_passed:     False
tool_trace_gates: False
payload_gates:    True
review_mode:      summary
corpus_fprint:    30cf494fbf87b8111ca5e824a7f50904
corpus_dir:       /tmp/session_recap_pre_state_1etn461q/eldyrwild-markdown
hit_tool_limit:   False
tool_trace rows:  7

========================================================================
§ Prompt payload sizes
========================================================================
instructions:  {'chars': 22653, 'bytes': 24843, 'sha256_16': '5d3e498d3b4e6329'}
user_line:     {'chars': 26894, 'bytes': 27006, 'sha256_16': 'd8211a736b03fb36'}

========================================================================
§ Token usage (per round)
========================================================================
  round[0] input=17113 output=16 cached=16896
  round[1] input=17436 output=162 cached=16896
  round[2] input=24624 output=54 cached=24064
  round[3] input=26747 output=2014 cached=26624
  round[4] input=30954 output=3211 cached=30720
  scenario_estimated_cost_usd: 0.034452

========================================================================
§ Violations
========================================================================
  scope_b: [scope_b_grader:session_recap_ingest_session_20] two_phase_commit_required: write_corpus_file must be called at least twice (preview with dry_run=true, then commit with dry_run=false); saw 1 call(s).
  scope_b_tool: [scope_b_grader:session_recap_ingest_session_20] two_phase_commit_required: write_corpus_file must be called at least twice (preview with dry_run=true, then commit with dry_run=false); saw 1 call(s).

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Drafted the Session 20 recap and surfaced the mechanical preview below. It creates `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md` with the standard 8-field frontmatter and the de-duplicated body from the raw notes.\n\n```diff\n--- a/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md\n+++ b/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md\n@@ -0,0 +1,34 @@\n+---\n+title: \"Session 20 - Recap\"\n+document_class: play\n+canon_layer: campaign\n+campaign_id: longmont-c2\n+temporal_scope: session
...[truncated, total_chars=13777]...
"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","prep_append_line":"> Companion recap: Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","recap_append_line":"> Companion prep: Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md"},"notes_for_gm":"The prep doc gave the best naming spellings for Stacey, Stuart, and Marla Brambleback; the recap body does not incorporate surnames, per ingest rules. The raw notes include a repeated Bonogo/Stuart/Stacey warehouse paragraph, and the mechanical ingest removed the later duplicate."}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-18T21:44:30Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 0,
  "cohort_size": 5,
  "gates_passed": false,
  "tool_trace_gates_passed": false,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.034452,
  "tool_trace_rows": 7,
  "tool_trace_tools": [
    "get_recap_context",
    "read_corpus_file",
    "read_corpus_file",
    "read_corpus_file",
    "read_corpus_file",
    "assemble_recap_draft",
    "write_corpus_file"
  ],
  "violation_counts": {
    "scope_b_tool": 1,
    "scope_b": 1
  },
  "violations": {
    "scope_b_tool": [
      "[scope_b_grader:session_recap_ingest_session_20] two_phase_commit_required: write_corpus_file must be called at least twice (preview with dry_run=true, then commit with dry_run=false); saw 1 call(s)."
    ],
    "scope_b": [
      "[scope_b_grader:session_recap_ingest_session_20] two_phase_commit_required: write_corpus_file must be called at least twice (preview with dry_run=true, then commit with dry_run=false); saw 1 call(s)."
    ]
  },
  "corpus_fingerprint": "30cf494fbf87b8111ca5e824a7f50904",
  "corpus_dir": "/tmp/session_recap_pre_state_1etn461q/eldyrwild-markdown",
  "recap_write_payload": {
    "schema_version": "recap_write_v1",
    "recap_preview": {
      "path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "mode": "create",
      "confirm_token": "959df16cedceab2219ca87575348e850"
    },
    "duplicate_paragraphs": [
      {
        "source_lines": [
          6,
          6
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
          "rationale": "Named, scene-driving recurring child NPC with clear future utility and strong hub-worthy texture."
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
          "rationale": "Named local authority with memorable presence and likely recurrence in Mossford-related continuity."
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
          "rationale": "Named, sympathetic child NPC who is already active in the session and likely to recur around the child social triangle."
        }
      ],
      "dismissed": [
        {
          "name": "Bonogo",
          "reason": "PC; PCs are skipped silently for this audit."
        },
        {
          "name": "Ephanna",
          "reason": "PC; PCs are skipped silently for this audit."
        },
        {
          "name": "Karesmine",
          "reason": "PC; PCs are skipped silently for this audit."
        },
        {
          "name": "Caelynn",
          "reason": "PC; PCs are skipped silently for this audit."
        },
        {
          "name": "Thrin",
          "reason": "NPC-like companion/ally but not enough evidence in the recap alone for a new hub proposal here, and no existing hub was confirmed this turn."
        },
        {
          "name": "Stafl",
          "reason": "NPC-like ally already in the party, but no hub confirmation was opened this turn and the recap does not clearly establish a separate hub-worthy continuity need."
        },
        {
          "name": "Sara",
          "reason": "Support voice on the rockie-talkie with no strong indication of recurring standalone hub need."
        },
        {
          "name": "Professor Tealeaf",
          "reason": "Off-screen contact only; no appearance or direct session agency in the recap."
        },
        {
          "name": "the mayor",
          "reason": "Title/function only, not a clearly named NPC identity in the recap."
        },
        {
          "name": "the sheriff",
          "reason": "Title/function only, not a clearly named NPC identity in the recap."
        }
      ]
    },
    "plot_artifacts": [
      {
        "name": "Topped-down tower blueprint",
        "evidence_quote": "It appears to be a top-down blueprint of a tower and is very well done.",
        "proposed_locations": [
          "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
          "Longmont Campaign/Campaign 2/Campaign 2 Notes.md",
          "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md"
        ]
      },
      {
        "name": "Tainted meat stash",
        "evidence_quote": "Mixed in with the meat is cleverly disguised tainted meat.",
        "proposed_locations": [
          "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
          "Longmont Campaign/Campaign 2/Campaign 2 Notes.md",
          "Longmont Campaign/Campaign 2/Elderwywyld_Narrative_Ledger_2.md"
        ]
      }
    ],
    "prep_pointer_proposal": {
      "prep_path": "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md",
      "recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "prep_append_line": "> Companion recap: Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "recap_append_line": "> Companion prep: Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md"
    },
    "notes_for_gm": "The prep doc gave the best naming spellings for Stacey, Stuart, and Marla Brambleback; the recap body does not incorporate surnames, per ingest rules. The raw notes include a repeated Bonogo/Stuart/Stacey warehouse paragraph, and the mechanical ingest removed the later duplicate."
  },
  "recap_write_payload_sha256_16": "a844bf8d66915ef8",
  "final_text_chars": 13777,
  "primary_response_id": "resp_042ae585e7637d300069e3fb31fcfc819fa4056cbec4ca69eb",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.034452,
    "planner_cost_by_round_usd": [
      0.001502,
      0.002401,
      0.002468,
      0.011152,
      0.016929
    ],
    "planner_usage_totals": {
      "input_tokens": 116874,
      "output_tokens": 5457,
      "total_tokens": 122331,
      "cached_tokens": 115200
    },
    "pricing_note": "approximate public list prices; verify against billing",
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.034452
  }
}
```
