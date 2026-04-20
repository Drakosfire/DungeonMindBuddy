<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-18T19:58:36Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: FAIL | tool_trace_gates: False | payload_gates: True | primary: artifacts/runs/2026-04-18/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--FAIL--1turn--20260418T195836Z--run003.md | cohort: 5 | run_index: 2 -->

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
corpus_fprint:    59b268d89d5b7bed8c023833232a1913
corpus_dir:       /tmp/session_recap_pre_state_8ye3lqv5/eldyrwild-markdown
hit_tool_limit:   False
tool_trace rows:  8

========================================================================
§ Prompt payload sizes
========================================================================
instructions:  {'chars': 22309, 'bytes': 24495, 'sha256_16': 'e90c1800676d4da1'}
user_line:     {'chars': 26894, 'bytes': 27006, 'sha256_16': 'd8211a736b03fb36'}

========================================================================
§ Token usage (per round)
========================================================================
  round[0] input=17031 output=66 cached=16896
  round[1] input=17570 output=162 cached=16896
  round[2] input=24758 output=54 cached=17408
  round[3] input=26881 output=2014 cached=24576
  round[4] input=31098 output=3209 cached=28672
  scenario_estimated_cost_usd: 0.042274

========================================================================
§ Violations
========================================================================
  scope_b: [scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/_ingest_staging/session_20_raw_notes.md' not in allowlist).
  scope_b_tool: [scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/_ingest_staging/session_20_raw_notes.md' not in allowlist).

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Drafted the Session 20 recap and previewed the create write for `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`.\n\n```diff\n--- a/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md\n+++ b/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md\n@@ -0,0 +1,34 @@\n+---\n+title: \"Session 20 - Recap\"\n+document_class: play\n+canon_layer: campaign\n+campaign_id: longmont-c2\n+temporal_scope: session_specific\n+session: 20\n+origin_session: 20\n+last_updated_session: 20\n+source_class: observed_sessio
...[truncated, total_chars=13577]...
for the played-out Mossford side scene, Stacey/Stuart/Marla beats, and Lysandra's tower blueprint discovery.","recap_append_line":"> See `Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md` for the Stacey/Stuart/Marla reference packet that informed this session's Mossford side scene."},"notes_for_gm":"I did not commit the recap yet; this is the preview only. `duplicate_paragraphs` reports the repeated Bonogo/Stacey scene that the assembler removed. I also kept the prep-doc pointer as a proposal only, since prep docs are outside the current write allowlist."}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-18T19:58:36Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 2,
  "cohort_size": 5,
  "gates_passed": false,
  "tool_trace_gates_passed": false,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.042274,
  "tool_trace_rows": 8,
  "tool_trace_tools": [
    "get_recap_context",
    "read_corpus_file",
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
      "[scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/_ingest_staging/session_20_raw_notes.md' not in allowlist)."
    ],
    "scope_b": [
      "[scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/_ingest_staging/session_20_raw_notes.md' not in allowlist)."
    ]
  },
  "corpus_fingerprint": "59b268d89d5b7bed8c023833232a1913",
  "corpus_dir": "/tmp/session_recap_pre_state_8ye3lqv5/eldyrwild-markdown",
  "recap_write_payload": {
    "schema_version": "recap_write_v1",
    "recap_preview": {
      "path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "mode": "create",
      "confirm_token": "eb7ec241301bd6c2e2c130866ab7ecf2"
    },
    "duplicate_paragraphs": [
      {
        "source_lines": [
          6,
          6
        ],
        "paragraph_preview": "Back in town, Bonogo is being guided by Stuart down an alley to a half burned building.",
        "recommended_action": "remove_later"
      }
    ],
    "npc_audit": {
      "timeline_append_candidates": [
        {
          "slug": "captain_lysandra_ironveil",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
          "reason": "Lysandra was contacted, reported being disoriented, and had a cult-like shimmer in her eyes plus a tower blueprint scene."
        },
        {
          "slug": "torbin_jove",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/torbin_jove/",
          "reason": "Torbin was not in this session recap; no timeline row candidate."
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
          "rationale": "Named, recurring child with a strong role in the Mossford crisis scene and clear future utility."
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
          "rationale": "Named authority figure with scene presence, social influence, and likely recurring town relevance."
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
          "evidence_quote": "Stuart is so happy with the outcome that he runs out the door, racing off to tell his mom the good news.",
          "rationale": "Named, emotionally salient child who recurs through the Bonogo side scene and may keep appearing."
        }
      ],
      "dismissed": [
        {
          "name": "Thrin",
          "reason": "Already established in the campaign and not a new hub proposal from this recap-only audit."
        },
        {
          "name": "Sara",
          "reason": "Operator contact only; not enough evidence here for a hub-worthy recurring NPC."
        },
        {
          "name": "Professor Tealeaf",
          "reason": "Mentioned only as an unanswered call target in this recap."
        },
        {
          "name": "The mayor",
          "reason": "Role-title only in this recap and not uniquely named."
        },
        {
          "name": "the sheriff",
          "reason": "Role-title only in this recap and not uniquely named."
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
          "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md"
        ]
      }
    ],
    "prep_pointer_proposal": {
      "prep_path": "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md",
      "recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "prep_append_line": "> See `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md` for the played-out Mossford side scene, Stacey/Stuart/Marla beats, and Lysandra's tower blueprint discovery.",
      "recap_append_line": "> See `Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md` for the Stacey/Stuart/Marla reference packet that informed this session's Mossford side scene."
    },
    "notes_for_gm": "I did not commit the recap yet; this is the preview only. `duplicate_paragraphs` reports the repeated Bonogo/Stacey scene that the assembler removed. I also kept the prep-doc pointer as a proposal only, since prep docs are outside the current write allowlist."
  },
  "recap_write_payload_sha256_16": "55e88e766d4f05e8",
  "final_text_chars": 13577,
  "primary_response_id": "resp_00864e3f5e6f80300069e3e25ec3508190bcedf6166f9887ea",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.042274,
    "planner_cost_by_round_usd": [
      0.001665,
      0.002502,
      0.007061,
      0.012635,
      0.01841
    ],
    "planner_usage_totals": {
      "input_tokens": 117338,
      "output_tokens": 5505,
      "total_tokens": 122843,
      "cached_tokens": 104448
    },
    "pricing_note": "approximate public list prices; verify against billing",
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.042274
  }
}
```
