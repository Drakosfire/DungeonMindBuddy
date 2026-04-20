<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-18T21:54:32Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: FAIL | tool_trace_gates: False | payload_gates: True | primary: artifacts/runs/2026-04-18/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--FAIL--2turn--20260418T215432Z--run003.md | cohort: 5 | run_index: 2 -->

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
corpus_fprint:    e09a8809fccc50235093f43494aec9e0
corpus_dir:       /tmp/session_recap_pre_state_0ko2ckv8/eldyrwild-markdown
hit_tool_limit:   False
tool_trace rows:  8

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
  round[4] input=30954 output=3229 cached=30720
  round[5] input=34233 output=2037 cached=32256
  round[6] input=36432 output=1172 cached=35840
  scenario_estimated_cost_usd: 0.056007

========================================================================
§ Violations
========================================================================
  scope_b: [scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/Session Recaps/Session 17 - Migrating Forest and Thrin.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/session recaps/session 17 - migrating forest and thrin.md' not in allowlist).
  scope_b: [scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/session prep/session_20_stacey_stuart_marla_reference.md' not in allowlist).
  scope_b: [scope_b_grader:session_recap_ingest_session_20] assemble_recap_draft.target_session want 21 got 20.
  scope_b_tool: [scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/Session Recaps/Session 17 - Migrating Forest and Thrin.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/session recaps/session 17 - migrating forest and thrin.md' not in allowlist).
  scope_b_tool: [scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/session prep/session_20_stacey_stuart_marla_reference.md' not in allowlist).
  scope_b_tool: [scope_b_grader:session_recap_ingest_session_20] assemble_recap_draft.target_session want 21 got 20.

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Committed the recap at `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`.\n\nNo timeline rows were appended in this turn, so there was nothing to preview or commit there. The recap is now written with the confirmed corpus fingerprint `9357de764b6daed745861a5c6d738133`.","unsure_queue":null,"recap_write":{"schema_version":"recap_write_v1","recap_preview":{"path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","mode":"create","confirm_token":"959df16cedceab2219ca87575348e850"},"duplicate_paragraphs":[{"sour
...[truncated, total_chars=4800]...
ecap pointer: see `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md` for the played scene.","recap_append_line":"> Prep ↔ recap pointer: see `Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md` for the companion reference."},"notes_for_gm":"The recap body contains one repeated paragraph from the raw notes that the ingest tool removed mechanically in the draft; the preview shown here is the de-duplicated version. The prep doc explicitly spells the bugbear family name as Brambleback and gives additional texture for Stacey, Stuart, and Marla."}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-18T21:54:32Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 2,
  "cohort_size": 5,
  "gates_passed": false,
  "tool_trace_gates_passed": false,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.056007,
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
  "violation_counts": {
    "scope_b_tool": 3,
    "scope_b": 3
  },
  "violations": {
    "scope_b_tool": [
      "[scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/Session Recaps/Session 17 - Migrating Forest and Thrin.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/session recaps/session 17 - migrating forest and thrin.md' not in allowlist).",
      "[scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/session prep/session_20_stacey_stuart_marla_reference.md' not in allowlist).",
      "[scope_b_grader:session_recap_ingest_session_20] assemble_recap_draft.target_session want 21 got 20."
    ],
    "scope_b": [
      "[scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/Session Recaps/Session 17 - Migrating Forest and Thrin.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/session recaps/session 17 - migrating forest and thrin.md' not in allowlist).",
      "[scope_b_grader:session_recap_ingest_session_20] after get_recap_context, read_corpus_file path 'Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md' is not in recent_recaps ∪ prep_doc_path (normalized 'longmont campaign/campaign 2/session prep/session_20_stacey_stuart_marla_reference.md' not in allowlist).",
      "[scope_b_grader:session_recap_ingest_session_20] assemble_recap_draft.target_session want 21 got 20."
    ]
  },
  "corpus_fingerprint": "e09a8809fccc50235093f43494aec9e0",
  "corpus_dir": "/tmp/session_recap_pre_state_0ko2ckv8/eldyrwild-markdown",
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
        "paragraph_preview": "Back in town, Bonogo is being guided by Stuart down an alley to a half burned building. According to Stuart this is where they will find Stacey....",
        "recommended_action": "remove_later"
      }
    ],
    "npc_audit": {
      "timeline_append_candidates": [
        {
          "slug": "captain_lysandra_ironveil",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
          "reason": "Lysandra is contacted, reported disoriented, and found under apparent influence with a tower blueprint clue."
        },
        {
          "slug": "dustwalker",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/dustwalker/",
          "reason": "Thrin is present throughout the session, contributes to the forest test fight, and remains under close watch as the group leaves town."
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
          "rationale": "Stacey is a named recurring town child with a distinct role, family link, and future scene potential."
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
          "evidence_quote": "Back in town, Bonogo is being guided by Stuart down an alley to a half burned building.",
          "rationale": "Stuart has a clear named identity, repeated scene presence, and an explicit relationship web with Stacey and Marla."
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
          "rationale": "Marla is a named adult authority in Mossford with immediate influence, a family tie, and strong reuse potential."
        }
      ],
      "dismissed": [
        {
          "name": "The mayor",
          "reason": "Functionary already established in town politics; the recap does not add a new identity beyond an existing civic role."
        },
        {
          "name": "the sheriff",
          "reason": "Functionary already established in town politics; the recap adds no distinct recurring arc beyond this scene."
        },
        {
          "name": "Sara",
          "reason": "Voice-on-the-line operator presence is important here, but this recap does not establish a new hub-worthy on-screen role."
        },
        {
          "name": "Professor Tealeaf",
          "reason": "Mentioned only as an attempted contact; no active scene presence in this session."
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
          "Longmont Campaign/Campaign 2/Elderwyld_Narrative_Ledger_2.md"
        ]
      }
    ],
    "prep_pointer_proposal": {
      "prep_path": "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md",
      "recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "prep_append_line": "> Prep ↔ recap pointer: see `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md` for the played scene.",
      "recap_append_line": "> Prep ↔ recap pointer: see `Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md` for the companion reference."
    },
    "notes_for_gm": "The recap body contains one repeated paragraph from the raw notes that the ingest tool removed mechanically in the draft; the preview shown here is the de-duplicated version. The prep doc explicitly spells the bugbear family name as Brambleback and gives additional texture for Stacey, Stuart, and Marla."
  },
  "recap_write_payload_sha256_16": "f6fd7c26c51f3b50",
  "final_text_chars": 4800,
  "primary_response_id": "resp_04bbfb9a4659a6000069e3fd92deec819fa79572479b3ed37d",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.056007,
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.056007,
    "planner_cost_by_round_usd": [
      0.001502,
      0.002401,
      0.002468,
      0.011152,
      0.01701,
      0.013068,
      0.008406
    ],
    "planner_usage_totals": {
      "input_tokens": 187539,
      "cached_tokens": 183296,
      "total_tokens": 196223,
      "output_tokens": 8684
    },
    "pricing_note": "approximate public list prices; verify against billing"
  }
}
```
