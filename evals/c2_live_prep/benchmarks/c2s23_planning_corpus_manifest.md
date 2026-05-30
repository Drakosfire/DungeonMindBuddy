# Activated planning corpus manifest — longmont-c2

- **schema:** `dmb_c2s23_planning_corpus_manifest_v0`
- **planning_session:** 23
- **source_sessions:** 21, 22
- **entries:** 44

Routes are repo-relative references; this manifest inlines no corpus prose. `route_exists: false` marks an in-bounds source that is not yet materialized.

## table_notes — authority: pre_canonical_evidence

| Session | Route | Exists | Allowed | Forbidden |
|---|---|---|---|---|
| 21 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_ingest_staging/session_21_raw_notes.md` | yes | provenance, pre_recap_evidence | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md` | yes | provenance, pre_recap_evidence | — |

## play_recap — authority: canon_play

| Session | Route | Exists | Allowed | Forbidden |
|---|---|---|---|---|
| 21 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 21 - Drake Nest Mirathorn Call.breadcrumbed.md` | yes | play_facts, open_loops, planning_context, continuity | — |
| 21 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 21 - Drake Nest Mirathorn Call.md` | yes | play_facts, open_loops, planning_context, continuity | — |
| 21 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 21 - Drake Nest Mirathorn Call.md` | yes | play_facts, open_loops, planning_context, continuity | — |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 22 - (uningested).breadcrumbed.md` | no | play_facts, open_loops, planning_context, continuity | — |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - (uningested).md` | no | play_facts, open_loops, planning_context, continuity | — |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 22 - (uningested).md` | no | play_facts, open_loops, planning_context, continuity | — |

## session_memory — authority: derived_memory

| Session | Route | Exists | Allowed | Forbidden |
|---|---|---|---|---|
| 21 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/Session 21 - Drake Nest Mirathorn Call.records_meta.json` | yes | play_facts, search, routing, evidence_support | — |
| 21 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/Session 21 - Drake Nest Mirathorn Call.records_meta.jsonl` | yes | play_facts, search, routing, evidence_support | — |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/Session 22 - (uningested).records_meta.json` | no | play_facts, search, routing, evidence_support | — |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/Session 22 - (uningested).records_meta.jsonl` | no | play_facts, search, routing, evidence_support | — |

## prep_scaffold — authority: planning_scaffold

| Session | Route | Exists | Allowed | Forbidden |
|---|---|---|---|---|
| 21 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 21 - brainstorming dump.md` | yes | planning_context, reusable_prep | play_facts |
| 21 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 21 - Mossford Saltfen rumor shop.md` | yes | planning_context, reusable_prep | play_facts |
| 21 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 21 - prep exercise agentic trace.md` | yes | planning_context, reusable_prep | play_facts |
| 21 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 21 - Session intro.md` | yes | planning_context, reusable_prep | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_planning_anchor.md` | yes | planning_context, reusable_prep | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_prep_brief.md` | yes | planning_context, reusable_prep | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_travel_to_mireward_runbook.md` | yes | planning_context, reusable_prep | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_mirathorn_comms_d100.md` | yes | planning_context, reusable_prep | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 22 - open GM knobs.md` | yes | planning_context, reusable_prep | play_facts |

## roll_table — authority: reference_tool

| Session | Route | Exists | Allowed | Forbidden |
|---|---|---|---|---|
| 22 | `corpus/eldyrwild-markdown/Elderwyld/Roads/mireward_reach_road_d100_encounter_table.md` | yes | table_use, table_patch | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/mireward_gate_dilemma_d6.md` | yes | table_use, table_patch | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_campfire_d8.md` | yes | table_use, table_patch | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_dilemma_d12.md` | yes | table_use, table_patch | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_night_watch_d12.md` | yes | table_use, table_patch | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_npc_spotlight_d12.md` | yes | table_use, table_patch | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_storm_weather_d20.md` | yes | table_use, table_patch | play_facts |
| 22 | `corpus/eldyrwild-markdown/Elderwyld/Wilderness/conical_hills_night_camp_d100.md` | yes | table_use, table_patch | play_facts |

## live_packet — authority: planning_scaffold

| Session | Route | Exists | Allowed | Forbidden |
|---|---|---|---|---|
| 22 | `evals/c2_live_prep/live/session_22/live_packet.json` | yes | active_session_orientation, planning_context | play_facts |

## live_event — authority: live_observation

| Session | Route | Exists | Allowed | Forbidden |
|---|---|---|---|---|
| 22 | `evals/c2_live_prep/live/session_22/event_log.jsonl` | yes | observed_play, planning_observation, audit_evidence | play_facts |

## hub_evidence — authority: canon_play

| Session | Route | Exists | Allowed | Forbidden |
|---|---|---|---|---|
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/baergrom/README.md` | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/bonogo/README.md` | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/caelynn/README.md` | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/README.md` | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/dustwalker/README.md` | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/ephanna/README.md` | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Factions/README.md` | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/karsemine/README.md` | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Plot Artifacts/README.md` | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/README.md` | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/stafl/README.md` | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/README.md` | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/torbin_jove/README.md` | yes | planning_context, continuity, npc_grounding | — |
