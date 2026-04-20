<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-18T21:37:03Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: FAIL | tool_trace_gates: False | payload_gates: True | primary: artifacts/runs/2026-04-18/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--FAIL--1turn--20260418T213703Z--run001.md | cohort: 5 | run_index: 0 -->

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
corpus_fprint:    9c2d8bc1c80456fa0385bae53b123e50
corpus_dir:       /tmp/session_recap_pre_state_wv0cqx_y/eldyrwild-markdown
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
  round[0] input=17113 output=16 cached=0
  round[1] input=17436 output=162 cached=16896
  round[2] input=24624 output=54 cached=17408
  round[3] input=26747 output=2014 cached=24576
  round[4] input=30954 output=3251 cached=28672
  scenario_estimated_cost_usd: 0.053294

========================================================================
§ Violations
========================================================================
  scope_b: [scope_b_grader:session_recap_ingest_session_20] two_phase_commit_required: write_corpus_file must be called at least twice (preview with dry_run=true, then commit with dry_run=false); saw 1 call(s).
  scope_b_tool: [scope_b_grader:session_recap_ingest_session_20] two_phase_commit_required: write_corpus_file must be called at least twice (preview with dry_run=true, then commit with dry_run=false); saw 1 call(s).

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Drafted `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md` and surfaced the mechanical preview below. The recap body is the raw session prose with the duplicate-paragraph removal already applied by the ingest helper; the preview adds standard frontmatter and the H1 in the surveyed recap shape.\n\n```diff\n--- a/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md\n+++ b/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md\n@@ -0,0 +1,34 @@\n+---\n+title: \"Session 20 - Recap\"\n+document_class: play\
...[truncated, total_chars=13868]...
cap.md` for the played version of the Stacey / Stuart / Marla scene.","recap_append_line":"> See `Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md` for the prep notes behind the Stacey / Stuart / Marla scene."},"notes_for_gm":"The recap draft is ready to commit, but I have not applied the write yet. The duplicate paragraph was removed mechanically from the body preview. The NPC audit includes hub-worthy first appearances from the session notes; if you want stricter timeline filtering, only Lysandra clearly warrants a row from the material read this turn."}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-18T21:37:03Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 0,
  "cohort_size": 5,
  "gates_passed": false,
  "tool_trace_gates_passed": false,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.053294,
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
  "corpus_fingerprint": "9c2d8bc1c80456fa0385bae53b123e50",
  "corpus_dir": "/tmp/session_recap_pre_state_wv0cqx_y/eldyrwild-markdown",
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
      "timeline_append_candidates": [
        {
          "slug": "captain_lysandra_ironveil",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
          "reason": "Lysandra is contacted, found disoriented, and revealed to have a shimmery-eyed influence plus a tower blueprint worth a timeline update."
        },
        {
          "slug": "torbin_jove",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/torbin_jove/",
          "reason": "Torbin is not present in this session recap; no timeline row is warranted from the material provided."
        }
      ],
      "new_hub_proposals": [
        {
          "proposed_slug": "marla_brambleback",
          "campaign_or_setting": "campaign",
          "proposed_location": "Longmont Campaign/Campaign 2/NPCs/marla_brambleback/",
          "initial_files": [
            "README.md",
            "marla_brambleback_character_dossier.md",
            "timeline.md"
          ],
          "evidence_quote": "Marla approaches Caelynn and asks her how she should deal with Bonogo",
          "rationale": "Marla is a named, forceful town leader with clear recurring potential and a strong scene presence."
        },
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
          "rationale": "Stacey is a named child with a distinct role in the Mossford scene and clear future recurrence potential."
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
          "rationale": "Stuart is a named, emotionally legible recurring child NPC whose relationship web is already established."
        }
      ],
      "dismissed": [
        {
          "name": "Stafl",
          "reason": "Already existing party-adjacent figure, but the recap does not establish him as a new hub-worthy NPC here."
        },
        {
          "name": "Sara",
          "reason": "Existing operator contact, but this session only uses her as a call intermediary with no new hub-level development."
        },
        {
          "name": "Professor Tealeaf",
          "reason": "Mentioned only as an unanswered contact; no new actionable appearance."
        },
        {
          "name": "The mayor",
          "reason": "Anonymous town authority, not uniquely named in the recap."
        },
        {
          "name": "the sheriff",
          "reason": "Anonymous town authority, not uniquely named in the recap."
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
        "name": "Tainted meat stash",
        "evidence_quote": "Mixed in with the meat is cleverly disguised tainted meat.",
        "proposed_locations": [
          "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
          "Longmont Campaign/Campaign 2/Campaign 2 Notes.md",
          "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md"
        ]
      }
    ],
    "prep_pointer_proposal": {
      "prep_path": "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md",
      "recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "prep_append_line": "> See `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md` for the played version of the Stacey / Stuart / Marla scene.",
      "recap_append_line": "> See `Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md` for the prep notes behind the Stacey / Stuart / Marla scene."
    },
    "notes_for_gm": "The recap draft is ready to commit, but I have not applied the write yet. The duplicate paragraph was removed mechanically from the body preview. The NPC audit includes hub-worthy first appearances from the session notes; if you want stricter timeline filtering, only Lysandra clearly warrants a row from the material read this turn."
  },
  "recap_write_payload_sha256_16": "4efda6c4866b29a8",
  "final_text_chars": 13868,
  "primary_response_id": "resp_0c410153d4ca2a0d0069e3f96f3324819ca93c09a1055f6376",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.053294,
    "planner_cost_by_round_usd": [
      0.012907,
      0.002401,
      0.006961,
      0.012534,
      0.018491
    ],
    "planner_usage_totals": {
      "input_tokens": 116874,
      "output_tokens": 5497,
      "total_tokens": 122371,
      "cached_tokens": 87552
    },
    "pricing_note": "approximate public list prices; verify against billing",
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.053294
  }
}
```
