<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-19T16:19:39Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: PASS | tool_trace_gates: True | payload_gates: True | primary: artifacts/runs/2026-04-19/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--PASS--2turn--20260419T161939Z--run001.md | cohort: 5 | run_index: 0 -->

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
corpus_fprint:    4f394c80b90ad672e12118e8d84230e1
corpus_dir:       /tmp/session_recap_pre_state_fzdf48rt/eldyrwild-markdown
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
  round[4] input=31814 output=3165 cached=31744
  round[5] input=35118 output=2043 cached=31744
  round[6] input=37330 output=1139 cached=36864
  scenario_estimated_cost_usd: 0.057016

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Committed the recap at **Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md**.\n\nNew corpus fingerprint: `f0a6e02e0ddaed4b77da73f109a43f51`.\n\nNo timeline-row append was run because `append_timeline_row` was not invoked in the prior structured reply and this turn only completed the approved recap commit.","unsure_queue":null,"recap_write":{"schema_version":"recap_write_v1","recap_preview":{"path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","mode":"create","confirm_token":"e7177c85a19403dd0d7cea58c8a835
...[truncated, total_chars=4602]...
d","recap_path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","prep_append_line":"> Recap: Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","recap_append_line":"> Prep reference: Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md"},"notes_for_gm":"The recap draft contains the mechanically removed duplicate paragraph only once; the preview diff surfaced the removal. The prep doc strongly supports a fuller Stacey/Stuart/Marla interpretation than the raw notes alone, but that material was not merged into the recap body."}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-19T16:19:39Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 0,
  "cohort_size": 5,
  "gates_passed": true,
  "tool_trace_gates_passed": true,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.057016,
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
  "corpus_fingerprint": "4f394c80b90ad672e12118e8d84230e1",
  "corpus_dir": "/tmp/session_recap_pre_state_fzdf48rt/eldyrwild-markdown",
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
        "paragraph_preview": "Back in town, Bonogo is being guided by Stuart down an alley to a half burned building. According to Stuart this is where they will find Stacey...",
        "recommended_action": "remove_later"
      }
    ],
    "npc_audit": {
      "timeline_append_candidates": [
        {
          "slug": "captain_lysandra_ironveil",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
          "reason": "Lysandra was located, described as shimmery-eyed and disoriented, and gave the party the tower blueprint / voice lead."
        },
        {
          "slug": "sara_mirathorn_operator",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
          "reason": "Sara relayed the call to Lysandra and reacted to the tainted-meat / trust crisis."
        },
        {
          "slug": "torbin_jove",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/torbin_jove/",
          "reason": "Tealeaf was called through the operator line and did not pick up, which is a small but real session beat for the existing hub."
        },
        {
          "slug": "thrin_branchborn",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/",
          "reason": "Thrin participated in the forest test and his secrecy around the trees remained relevant."
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
          "rationale": "Named child with clear role, continuing relevance, and a likely recurring town-side relationship."
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
          "evidence_quote": "Bonogo is being guided by Stuart down an alley to a half burned building.",
          "rationale": "Named recurring child NPC with strong emotional hooks and a likely ongoing relationship to Bonogo."
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
          "rationale": "Memorable town leader / labor authority with enough presence to recur beyond a one-scene walk-on."
        }
      ],
      "dismissed": [
        {
          "name": "Mayor of Mossford",
          "reason": "Not named in the recap with a personal identifier and functions as an office rather than a distinct NPC hub candidate."
        },
        {
          "name": "Sheriff",
          "reason": "Likewise treated as a civic role in the recap, not a uniquely named recurring individual."
        },
        {
          "name": "Professor Tealeaf",
          "reason": "Only appears as a contact the party tries to reach; no direct scene presence or new characterization in this session."
        }
      ]
    },
    "plot_artifacts": [
      {
        "name": "Tower blueprint in the dirt",
        "evidence_quote": "It appears to be a top-down blueprint of a tower and is very well done.",
        "proposed_locations": [
          "Longmont Campaign/Campaign 2/Story threads backlog.md",
          "Longmont Campaign/Campaign 2/Campaign 2 Notes.md",
          "Longmont Campaign/Campaign 2/Journey - Mireward Reach (Campaign 2).md"
        ]
      }
    ],
    "prep_pointer_proposal": {
      "prep_path": "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md",
      "recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "prep_append_line": "> Recap: Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "recap_append_line": "> Prep reference: Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md"
    },
    "notes_for_gm": "The recap draft contains the mechanically removed duplicate paragraph only once; the preview diff surfaced the removal. The prep doc strongly supports a fuller Stacey/Stuart/Marla interpretation than the raw notes alone, but that material was not merged into the recap body."
  },
  "recap_write_payload_sha256_16": "b1d7650910ac3a65",
  "final_text_chars": 4602,
  "primary_response_id": "resp_0271fffee35b3a380069e4ffb099c8819787ace22ffb88894b",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.057016,
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.057016,
    "planner_cost_by_round_usd": [
      0.001791,
      0.002345,
      0.002413,
      0.011447,
      0.016676,
      0.014105,
      0.00824
    ],
    "planner_usage_totals": {
      "input_tokens": 193570,
      "cached_tokens": 187904,
      "output_tokens": 8594,
      "total_tokens": 202164
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
