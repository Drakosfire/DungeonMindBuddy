<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-19T16:03:10Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: PASS | tool_trace_gates: True | payload_gates: True | primary: artifacts/runs/2026-04-19/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--PASS--2turn--20260419T160310Z--run001.md | cohort: 5 | run_index: 0 -->

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
corpus_fprint:    72ff078527b06b141b750101a6d9fac1
corpus_dir:       /tmp/session_recap_pre_state_9frcm1rw/eldyrwild-markdown
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
  round[2] input=25472 output=54 cached=17920
  round[3] input=27595 output=2014 cached=25088
  round[4] input=31802 output=3092 cached=29184
  round[5] input=35033 output=2014 cached=31232
  round[6] input=39240 output=1000 cached=36864
  scenario_estimated_cost_usd: 0.077677

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Commit preview returned unchanged and is now awaiting the actual write phase. I have not yet received a commit response from the corpus writer, so the recap file is still in preview state.","unsure_queue":null,"recap_write":{"schema_version":"recap_write_v1","recap_preview":{"path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","mode":"create","confirm_token":"959df16cedceab2219ca87575348e850"},"duplicate_paragraphs":[{"source_lines":[6,6],"paragraph_preview":"Stuart is so happy with the outcome that he runs out the door,
...[truncated, total_chars=4169]...
 the resolved playthrough.","recap_append_line":"> Companion prep note: see [session 20 stacey stuart marla reference](../Session Prep/session_20_stacey_stuart_marla_reference.md) for the prepped NPC details."},"notes_for_gm":"The draft preserves the duplicated Bonogo/Stacey scene exactly as the assembler emitted it except for the mechanically removed repeated paragraph; the preview shows one duplicate paragraph catch only. I did not surface append_timeline_row calls because this skill's contract is recap-only, but the NPC audit lists the obvious timeline candidates for downstream handling."}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-19T16:03:10Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 0,
  "cohort_size": 5,
  "gates_passed": true,
  "tool_trace_gates_passed": true,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.077677,
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
  "corpus_fingerprint": "72ff078527b06b141b750101a6d9fac1",
  "corpus_dir": "/tmp/session_recap_pre_state_9frcm1rw/eldyrwild-markdown",
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
        "paragraph_preview": "Stuart is so happy with the outcome that he runs out the door, racing off to tell his mom the good news.",
        "recommended_action": "remove_later"
      }
    ],
    "npc_audit": {
      "timeline_append_candidates": [
        {
          "slug": "captain_lysandra_ironveil",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
          "reason": "Lysandra was found traveling alone, disoriented by the forest, and revealed a tower blueprint plus strange shimmery eyes tied to the cult."
        },
        {
          "slug": "dustwalker",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/dustwalker/",
          "reason": "Thrin took part in the forest tests, revealed more of his capabilities, and remains a significant recurring forest-linked NPC."
        },
        {
          "slug": "sara_mirathorn_operator",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
          "reason": "Sara directly relayed Caelynn to Lysandra and handled the report about the tainted meat and Lysandra's condition."
        },
        {
          "slug": "torbin_jove",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/torbin_jove/",
          "reason": "Torbin is not active in this recap and did not materially appear."
        }
      ],
      "new_hub_proposals": [],
      "dismissed": [
        {
          "name": "Stacey",
          "reason": "Named first-appearance child, but the prep packet frames her as a one-session local figure rather than a hub-worthy recurring NPC from the recap alone."
        },
        {
          "name": "Stuart",
          "reason": "Named child side character whose role is localized to this session's Mossford side scene."
        },
        {
          "name": "Marla Brambleback",
          "reason": "Important local adult, but the prep doc already anchors her as Stacey's mother and the recap does not establish wider recurrence beyond Mossford."
        },
        {
          "name": "Stafl",
          "reason": "NPC already used as a session-facing town helper, but no hub evidence is present in the corpus during this turn."
        },
        {
          "name": "Professor Tealeaf",
          "reason": "Referenced only as a contact; no appearance or hub evidence in the opened files."
        },
        {
          "name": "Mayor",
          "reason": "Unnamed town official in this recap, not a named hub candidate."
        },
        {
          "name": "Sheriff",
          "reason": "Unnamed town official in this recap, not a named hub candidate."
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
      "prep_append_line": "> Companion prep note: see [Session 20 - Recap](../Session Recaps/Session 20 - Recap.md) for the resolved playthrough.",
      "recap_append_line": "> Companion prep note: see [session 20 stacey stuart marla reference](../Session Prep/session_20_stacey_stuart_marla_reference.md) for the prepped NPC details."
    },
    "notes_for_gm": "The draft preserves the duplicated Bonogo/Stacey scene exactly as the assembler emitted it except for the mechanically removed repeated paragraph; the preview shows one duplicate paragraph catch only. I did not surface append_timeline_row calls because this skill's contract is recap-only, but the NPC audit lists the obvious timeline candidates for downstream handling."
  },
  "recap_write_payload_sha256_16": "b04d75a5f43663c3",
  "final_text_chars": 4169,
  "primary_response_id": "resp_0e6700c247805a930069e4fcb81d8481969f5287e4f63a7e9a",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.077677,
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.077677,
    "planner_cost_by_round_usd": [
      0.013541,
      0.00269,
      0.007251,
      0.012825,
      0.018066,
      0.014256,
      0.009047
    ],
    "planner_usage_totals": {
      "output_tokens": 8352,
      "input_tokens": 195383,
      "total_tokens": 203735,
      "cached_tokens": 157696
    },
    "pricing_note": "approximate public list prices; verify against billing"
  },
  "scope_b_extras": {
    "write_corpus_file_phases": {
      "calls": 2,
      "previews": 2,
      "commits": 0,
      "phases": "preview→preview"
    },
    "write_corpus_file_soft_observations": [
      "[scope_b_grader:session_recap_ingest_session_20] commit_observed=false: the model produced 2 preview call(s) but did not issue a dry_run=false commit on this turn (HITL-by-design — informational, not a failure)."
    ],
    "preview_required": true,
    "commit_required": false
  }
}
```
