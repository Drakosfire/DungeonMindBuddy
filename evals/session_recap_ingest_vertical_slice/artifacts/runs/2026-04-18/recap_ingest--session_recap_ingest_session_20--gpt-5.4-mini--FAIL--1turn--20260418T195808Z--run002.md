<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-18T19:58:08Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: FAIL | tool_trace_gates: False | payload_gates: True | primary: artifacts/runs/2026-04-18/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--FAIL--1turn--20260418T195808Z--run002.md | cohort: 5 | run_index: 1 -->

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
corpus_fprint:    533f1ab2bf4f36baad5bc312c39e8d3f
corpus_dir:       /tmp/session_recap_pre_state_8ye3lqv5/eldyrwild-markdown
hit_tool_limit:   False
tool_trace rows:  6

========================================================================
§ Prompt payload sizes
========================================================================
instructions:  {'chars': 22309, 'bytes': 24495, 'sha256_16': 'e90c1800676d4da1'}
user_line:     {'chars': 26894, 'bytes': 27006, 'sha256_16': 'd8211a736b03fb36'}

========================================================================
§ Token usage (per round)
========================================================================
  round[0] input=17031 output=24 cached=16896
  round[1] input=17362 output=212 cached=16896
  round[2] input=26667 output=3375 cached=17408
  scenario_estimated_cost_usd: 0.027485

========================================================================
§ Violations
========================================================================
  scope_b: [scope_b_grader:session_recap_ingest_session_20] get_recap_context must be called with no arguments (do not pin campaign_id or target_session for this scenario); got arguments={'campaign_id': 'longmont-c2'}.
  scope_b_tool: [scope_b_grader:session_recap_ingest_session_20] get_recap_context must be called with no arguments (do not pin campaign_id or target_session for this scenario); got arguments={'campaign_id': 'longmont-c2'}.

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Drafted the Session 20 recap and surfaced the mechanical preview below. The new file is `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`.\n\n```diff\n--- /dev/null\n+++ b/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md\n@@ -0,0 +1,45 @@\n+---\n+title: \"Session 20 - Recap\"\n+document_class: play\n+canon_layer: campaign\n+campaign_id: longmont-c2\n+temporal_scope: session_specific\n+session: 20\n+origin_session: 20\n+last_updated_session: 20\n+source_class: observed_session_recap\n+---\n+# Session 20 Recap
...[truncated, total_chars=14355]...
ampaign 2/Session Recaps/Session 20 - Recap.md","prep_append_line":"> Companion recap: [Session 20 - Recap](../Session Recaps/Session 20 - Recap.md)","recap_append_line":"> Companion prep: [session_20_stacey_stuart_marla_reference](../Session Prep/session_20_stacey_stuart_marla_reference.md)"},"notes_for_gm":"The raw notes contain one exact duplicate paragraph, which was removed mechanically by the ingest tool. I did not commit any corpus writes yet; this is still the dry-run preview. The recap body preserves the note spelling and punctuation as ingested, including the source’s rough edges."}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-18T19:58:08Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 1,
  "cohort_size": 5,
  "gates_passed": false,
  "tool_trace_gates_passed": false,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.027485,
  "tool_trace_rows": 6,
  "tool_trace_tools": [
    "get_recap_context",
    "read_corpus_file",
    "read_corpus_file",
    "read_corpus_file",
    "read_corpus_file",
    "assemble_recap_draft"
  ],
  "violation_counts": {
    "scope_b_tool": 1,
    "scope_b": 1
  },
  "violations": {
    "scope_b_tool": [
      "[scope_b_grader:session_recap_ingest_session_20] get_recap_context must be called with no arguments (do not pin campaign_id or target_session for this scenario); got arguments={'campaign_id': 'longmont-c2'}."
    ],
    "scope_b": [
      "[scope_b_grader:session_recap_ingest_session_20] get_recap_context must be called with no arguments (do not pin campaign_id or target_session for this scenario); got arguments={'campaign_id': 'longmont-c2'}."
    ]
  },
  "corpus_fingerprint": "533f1ab2bf4f36baad5bc312c39e8d3f",
  "corpus_dir": "/tmp/session_recap_pre_state_8ye3lqv5/eldyrwild-markdown",
  "recap_write_payload": {
    "schema_version": "recap_write_v1",
    "recap_preview": {
      "path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "mode": "create",
      "confirm_token": "7a0ff5d0c2b3b4dd"
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
          "reason": "Lysandra is contacted, reported missing/disoriented, and recovered from an apparent compulsion with a new tower blueprint clue."
        },
        {
          "slug": "dustwalker",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/dustwalker/",
          "reason": "The session references the tainted meat thread and the camp cleanup pressure that likely intersects the existing dustwalker hub's ongoing crisis role."
        },
        {
          "slug": "torbin_jove",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/torbin_jove/",
          "reason": "Torbin is not in the raw notes, so no timeline row is proposed for him this session."
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
          "rationale": "Stacey is named, memorable, and clearly positioned to recur as a local child with useful crisis knowledge."
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
          "rationale": "Stuart gets a substantial first-appearance scene, has a defined relationship web, and seems likely to recur in Mossford."
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
          "rationale": "Marla is a named town power figure with authority over workers and a clear likely future role."
        }
      ],
      "dismissed": [
        {
          "name": "Stafl",
          "reason": "Already a party PC / major known character, so no NPC hub proposal is needed here."
        },
        {
          "name": "Ephanna",
          "reason": "Already a party PC / major known character, so no NPC hub proposal is needed here."
        },
        {
          "name": "Caelynn",
          "reason": "Already a party PC / major known character, so no NPC hub proposal is needed here."
        },
        {
          "name": "Karesmine",
          "reason": "Already a party PC / major known character, so no NPC hub proposal is needed here."
        },
        {
          "name": "Bonogo",
          "reason": "Already a party PC / major known character, so no NPC hub proposal is needed here."
        },
        {
          "name": "Thrin",
          "reason": "Already established in prior recaps as a recurring companion rather than a new hub-worthy first appearance."
        },
        {
          "name": "Sara",
          "reason": "Support-contact operator; named but not first-appearance hub-worthy from this recap alone."
        },
        {
          "name": "Professor Tealeaf",
          "reason": "Only mentioned as a failed contact and not materially present in the scene."
        },
        {
          "name": "the mayor",
          "reason": "Functionary role without a unique personal name in the recap."
        },
        {
          "name": "the sheriff",
          "reason": "Functionary role without a unique personal name in the recap."
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
        "name": "Tower sighting clue",
        "evidence_quote": "She says it is a tower where the voices are coming from and she knows where it is.",
        "proposed_locations": [
          "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
          "Longmont Campaign/Campaign 2/Elderwyld_Narrative_Ledger_2.md",
          "Longmont Campaign/Campaign 2/Campaign 2 Notes.md"
        ]
      }
    ],
    "prep_pointer_proposal": {
      "prep_path": "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md",
      "recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "prep_append_line": "> Companion recap: [Session 20 - Recap](../Session Recaps/Session 20 - Recap.md)",
      "recap_append_line": "> Companion prep: [session_20_stacey_stuart_marla_reference](../Session Prep/session_20_stacey_stuart_marla_reference.md)"
    },
    "notes_for_gm": "The raw notes contain one exact duplicate paragraph, which was removed mechanically by the ingest tool. I did not commit any corpus writes yet; this is still the dry-run preview. The recap body preserves the note spelling and punctuation as ingested, including the source’s rough edges."
  },
  "recap_write_payload_sha256_16": "1cc938b14cef18e3",
  "final_text_chars": 14355,
  "primary_response_id": "resp_03349d39144ffef70069e3e241642c819ebc70bad988dacd68",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.027485,
    "planner_cost_by_round_usd": [
      0.001476,
      0.002571,
      0.023437
    ],
    "planner_usage_totals": {
      "input_tokens": 61060,
      "output_tokens": 3611,
      "total_tokens": 64671,
      "cached_tokens": 51200
    },
    "pricing_note": "approximate public list prices; verify against billing",
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.027485
  }
}
```
