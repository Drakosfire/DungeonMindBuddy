<!-- benchmark_artifact: recap_ingest_run_report_v1 | iso_utc: 2026-04-19T16:20:22Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | gates: PASS | tool_trace_gates: True | payload_gates: True | primary: artifacts/runs/2026-04-19/recap_ingest--session_recap_ingest_session_20--gpt-5.4-mini--PASS--2turn--20260419T162022Z--run002.md | cohort: 5 | run_index: 1 -->

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
corpus_fprint:    497a9a2f33beb1035c811b142e2f4bfd
corpus_dir:       /tmp/session_recap_pre_state_pmeh_3vf/eldyrwild-markdown
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
  round[3] input=27595 output=2014 cached=27136
  round[4] input=31802 output=3037 cached=31232
  round[5] input=34978 output=2037 cached=31232
  round[6] input=37175 output=846 cached=36864
  scenario_estimated_cost_usd: 0.05555

========================================================================
§ Final assistant text (preview)
========================================================================
{"user_intent":"status_or_recap_request","message":"Committed the recap successfully at `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`.\n\nCorpus fingerprint: `34ed514744cb186086fb0462c754e2a5`.\n\nNo timeline rows were drafted because `npc_audit.timeline_append_candidates` was empty in the prior structured payload.","unsure_queue":null,"recap_write":{"schema_version":"recap_write_v1","recap_preview":{"path":"Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md","mode":"create","confirm_token":"959df16cedceab2219ca87575348e850"},"duplicate_paragraphs":[{"sourc
...[truncated, total_chars=3459]...
ampaign/Campaign 2/Session Recaps/Session 20 - Recap.md","prep_append_line":"> See recap: `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`","recap_append_line":"> See prep: `Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md`"},"notes_for_gm":"The assembled recap includes the mechanically removed duplicate paragraph in the source notes; the draft body reflects the de-duplicated version. The prep packet is specifically about Stacey, Stuart, and Marla Brambleback, and it suggests a richer reading of that trio than the recap alone captures."}}
```

## Sidecar JSON

```json
{
  "schema": "recap_ingest_run_report_v1",
  "iso_utc": "2026-04-19T16:20:22Z",
  "scenario_id": "session_recap_ingest_session_20",
  "model_id": "gpt-5.4-mini",
  "run_index": 1,
  "cohort_size": 5,
  "gates_passed": true,
  "tool_trace_gates_passed": true,
  "payload_gates_passed": true,
  "scenario_estimated_cost_usd": 0.05555,
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
  "corpus_fingerprint": "497a9a2f33beb1035c811b142e2f4bfd",
  "corpus_dir": "/tmp/session_recap_pre_state_pmeh_3vf/eldyrwild-markdown",
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
          10
        ],
        "paragraph_preview": "Back in town, Bonogo is being guided by Stuart down an alley to a half burned building. According to Stuart this is where they will find Stacey. As soon as they step inside the large warehouse...",
        "recommended_action": "remove_later"
      }
    ],
    "npc_audit": {
      "timeline_append_candidates": [],
      "new_hub_proposals": [],
      "dismissed": [
        {
          "name": "Stacey Brambleback",
          "reason": "A named first-appearance child NPC, but the current turn only drafts the recap and does not create new hubs."
        },
        {
          "name": "Stuart",
          "reason": "A named first-appearance child NPC, but the current turn only drafts the recap and does not create new hubs."
        },
        {
          "name": "Marla Brambleback",
          "reason": "A named first-appearance town adult NPC, but the current turn only drafts the recap and does not create new hubs."
        },
        {
          "name": "Sara",
          "reason": "An already-known operator voice in the call scene, but the recap alone does not justify a hub proposal here."
        },
        {
          "name": "Professor Tealeaf",
          "reason": "Mentioned only as an off-screen contact; not enough session-specific material for a hub proposal."
        },
        {
          "name": "Lysandra",
          "reason": "Already established in prior campaign material and should be handled by separate NPC/timeline work, not this recap draft."
        },
        {
          "name": "Thrin",
          "reason": "Existing NPC, but no timeline or hub action is being proposed in this recap-write turn."
        },
        {
          "name": "Bonogo",
          "reason": "PCs are skipped silently for hub/audit purposes."
        },
        {
          "name": "Caelynn",
          "reason": "PCs are skipped silently for hub/audit purposes."
        },
        {
          "name": "Ephanna",
          "reason": "PCs are skipped silently for hub/audit purposes."
        },
        {
          "name": "Karesmine",
          "reason": "PCs are skipped silently for hub/audit purposes."
        },
        {
          "name": "Stafl",
          "reason": "PCs are skipped silently for hub/audit purposes."
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
      "prep_append_line": "> See recap: `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`",
      "recap_append_line": "> See prep: `Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md`"
    },
    "notes_for_gm": "The assembled recap includes the mechanically removed duplicate paragraph in the source notes; the draft body reflects the de-duplicated version. The prep packet is specifically about Stacey, Stuart, and Marla Brambleback, and it suggests a richer reading of that trio than the recap alone captures."
  },
  "recap_write_payload_sha256_16": "da85bd1dbdbf56ce",
  "final_text_chars": 3459,
  "primary_response_id": "resp_06bb5bcf63646b360069e500c1dfe481a3ad19a00004c004cf",
  "telemetry_cost": {
    "planner_estimated_cost_usd": 0.05555,
    "statblock_tool_estimated_cost_usd": 0,
    "scenario_estimated_cost_usd": 0.05555,
    "planner_cost_by_round_usd": [
      0.001791,
      0.002345,
      0.002413,
      0.011442,
      0.016436,
      0.014318,
      0.006805
    ],
    "planner_usage_totals": {
      "input_tokens": 193263,
      "cached_tokens": 186880,
      "output_tokens": 8166,
      "total_tokens": 201429
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
