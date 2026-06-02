# Activated planning corpus manifest — longmont-c2

- **schema:** `dmb_c2s23_dogfood_full_manifest_v1`
- **planning_session:** 23
- **source_sessions:** 21, 22, 23
- **entries:** 182
- **planning_live_workspace_dir:** `evals/c2_live_prep/live/session_23`

Routes are repo-relative references; this manifest inlines no corpus prose. `route_exists: false` / `admissible: false` marks an in-bounds source that is not yet materialized and must not be used for admission.

## table_notes — authority: pre_canonical_evidence

| Session | Route | Exists | Admissible | Allowed | Forbidden |
|---|---|---|---|---|---|
| 21 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_ingest_staging/session_21_raw_notes.md` | yes | yes | provenance, pre_recap_evidence | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md` | yes | yes | provenance, pre_recap_evidence | play_facts |

## play_recap — authority: canon_play

| Session | Route | Exists | Admissible | Allowed | Forbidden |
|---|---|---|---|---|---|
| 21 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 21 - Drake Nest Mirathorn Call.breadcrumbed.md` | yes | yes | play_facts, open_loops, planning_context, continuity | — |
| 21 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 21 - Drake Nest Mirathorn Call.md` | yes | yes | play_facts, open_loops, planning_context, continuity | — |
| 21 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 21 - Drake Nest Mirathorn Call.md` | yes | yes | play_facts, open_loops, planning_context, continuity | — |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 22 - Mireward Road and Lysandro.breadcrumbed.md` | yes | yes | play_facts, open_loops, planning_context, continuity | — |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md` | yes | yes | play_facts, open_loops, planning_context, continuity | — |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md` | yes | yes | play_facts, open_loops, planning_context, continuity | — |
| 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 23 - (uningested).breadcrumbed.md` | no | no | — | play_facts |
| 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - (uningested).md` | no | no | — | play_facts |
| 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 23 - (uningested).md` | no | no | — | play_facts |

## session_memory — authority: derived_memory

| Session | Route | Exists | Admissible | Allowed | Forbidden |
|---|---|---|---|---|---|
| 21 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/Session 21 - Drake Nest Mirathorn Call.records_meta.json` | yes | yes | play_facts, search, routing, evidence_support | — |
| 21 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/Session 21 - Drake Nest Mirathorn Call.records_meta.jsonl` | yes | yes | play_facts, search, routing, evidence_support | — |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/Session 22 - Mireward Road and Lysandro.records_meta.json` | yes | yes | play_facts, search, routing, evidence_support | — |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/Session 22 - Mireward Road and Lysandro.records_meta.jsonl` | yes | yes | play_facts, search, routing, evidence_support | — |
| 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/Session 23 - (uningested).records_meta.json` | no | no | — | play_facts |
| 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/Session 23 - (uningested).records_meta.jsonl` | no | no | — | play_facts |

## prep_scaffold — authority: planning_scaffold

| Session | Route | Exists | Admissible | Allowed | Forbidden |
|---|---|---|---|---|---|
| 21 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 21 - brainstorming dump.md` | yes | yes | planning_context, reusable_prep | play_facts |
| 21 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 21 - Mossford Saltfen rumor shop.md` | yes | yes | planning_context, reusable_prep | play_facts |
| 21 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 21 - prep exercise agentic trace.md` | yes | yes | planning_context, reusable_prep | play_facts |
| 21 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 21 - Session intro.md` | yes | yes | planning_context, reusable_prep | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/mireward_gate_dilemma_d6.md` | yes | yes | planning_context, reusable_prep | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_planning_anchor.md` | yes | yes | planning_context, reusable_prep | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_prep_brief.md` | yes | yes | planning_context, reusable_prep | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_travel_to_mireward_runbook.md` | yes | yes | planning_context, reusable_prep | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_campfire_d8.md` | yes | yes | planning_context, reusable_prep | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_dilemma_d12.md` | yes | yes | planning_context, reusable_prep | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_mirathorn_comms_d100.md` | yes | yes | planning_context, reusable_prep | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_night_watch_d12.md` | yes | yes | planning_context, reusable_prep | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_npc_spotlight_d12.md` | yes | yes | planning_context, reusable_prep | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_storm_weather_d20.md` | yes | yes | planning_context, reusable_prep | play_facts |
| 22 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 22 - open GM knobs.md` | yes | yes | planning_context, reusable_prep | play_facts |

## live_packet — authority: planning_scaffold

| Session | Route | Exists | Admissible | Allowed | Forbidden |
|---|---|---|---|---|---|
| 23 | `evals/c2_live_prep/live/session_23/live_packet.json` | yes | yes | active_session_orientation, planning_context | play_facts |

## live_event — authority: live_observation

| Session | Route | Exists | Admissible | Allowed | Forbidden |
|---|---|---|---|---|---|
| 23 | `evals/c2_live_prep/live/session_23/event_log.jsonl` | yes | yes | observed_play, planning_observation, audit_evidence | play_facts |

## fresh_recap — authority: pre_canonical_evidence

| Session | Route | Exists | Admissible | Allowed | Forbidden |
|---|---|---|---|---|---|
| 23 | `evals/c2_live_prep/live/session_23/recap.md` | yes | yes | planning_input | — |

## hub_evidence — authority: canon_play

| Session | Route | Exists | Admissible | Allowed | Forbidden |
|---|---|---|---|---|---|
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/baergrom/baergrom_character_dossier.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/baergrom/baergrom_statblock_dnd_beyond_level5.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/baergrom/README.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/baergrom/timeline.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/bonogo/bonogo_character_dossier.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/bonogo/bonogo_statblock_dnd_beyond_level5.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/bonogo/loot_geomantic_drake_nest.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/bonogo/README.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/bonogo/timeline.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/caelynn/caelynn_character_dossier.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/caelynn/caelynn_statblock_dnd_beyond_level5.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/caelynn/README.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/caelynn/timeline.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_character_dossier.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/lysandra_ironveil_mireward_history.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/README.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/timeline.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/dustwalker/dustwalker_character_dossier.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/dustwalker/README.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/dustwalker/timeline.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/ephanna/ephanna_character_dossier.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/ephanna/ephanna_statblock_dnd_beyond_level5.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/ephanna/README.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/ephanna/timeline.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Factions/Raucous_Saints_of_the_Rolling_Longhouse.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Factions/README.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/karsemine/karsemine_character_dossier.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/karsemine/karsemine_statblock_dnd_beyond_level5.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/karsemine/README.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/karsemine/timeline.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Plot Artifacts/boots_of_crowing_wings.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Plot Artifacts/README.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/README.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/sara_mirathorn_operator_character_dossier.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/timeline.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/stafl/README.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/stafl/stafl_character_dossier.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/stafl/stafl_statblock_dnd_beyond_level5.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/stafl/timeline.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/README.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/thrin_branchborn_character_dossier.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/timeline.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/torbin_jove/README.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/torbin_jove/timeline.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/torbin_jove/torbin_jove_care_guidelines.md` | yes | yes | planning_context, continuity, npc_grounding | — |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/torbin_jove/torbin_jove_character_dossier.md` | yes | yes | planning_context, continuity, npc_grounding | — |

## world_evidence — authority: reference_tool

| Session | Route | Exists | Admissible | Allowed | Forbidden |
|---|---|---|---|---|---|
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Migrating Forest/Branchbound/branchbound_culture_pack.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Migrating Forest/Branchbound/branchbound_indirect_help_encounters_ash_in_the_canopy.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Migrating Forest/Branchbound/README.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Migrating Forest/Branchbound/The Witness Seed.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Migrating Forest/Branchbound/Threnn-of-Second-Bloom.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_statblock_cr2.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_statblock_cr4.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/character_seed.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/README.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/City Council Building/Battle with The Wolf and Aftermath.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/City Council Building/The City Council.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/City Council Building/The Council Room.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/City Council Building/The Emergency Council Meeting.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Events/The Festival of Expansion/Schedule and Event Details/Day Four/Bardic Storytelling Circle.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Events/The Festival of Expansion/Schedule and Event Details/Day Three/Cultural Ceremonies at the Temple of the Aspitome.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Events/The Festival of Expansion/Schedule and Event Details/Day Three/Festival Crafting Chaos.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Events/The Festival of Expansion/Schedule and Event Details/Day Two /Day Two Notes.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Shephards Flock/NPCs/dustwalker/character_seed.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Shephards Flock/NPCs/dustwalker/dustwalker_statblock.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Shephards Flock/NPCs/dustwalker/README.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Edge of the World/README.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/# _Campaign Summary_ Mirathorn Post-Cultist Battle_.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Stonebridge and The Wizard Tower Brewing Co.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/The Stonebridge Flood.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/UnRefined Heading into the Flesh Kaiju.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Stonebridge/NPCs/grishna/character_seed.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Stonebridge/NPCs/grishna/README.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Inns and Shops/The Copper & Quartz Inn.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Item Cards/Untitled document.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Upriver River Route/NPCs/kirfan/character_seed.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Upriver River Route/NPCs/kirfan/README.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mireward/NPCs/lysandro_ironveil/character_seed.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/NPCs/marla_brambleback/character_seed.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/NPCs/marla_brambleback/README.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Migrating Forest/HEX KEY_ THE MIGRATING FOREST BOARD.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Migrating Forest/migrating_forest_d_100_universal_encounter_table.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Migrating Forest/migrating_forest_hex_expansion.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Migrating Forest/README.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Migrating Forest/the_migrating_forest_executive_dm_summary.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/README.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/The City of Mirathorn.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mireward/Mireward_PLACE_BUILD_SCAFFOLD.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mireward/README.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Copper Moss Brewery & Waterwheel Mill.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Dense Worker Housing.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Drying Barns.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Market Square.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Moldyards.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Mossford Inn.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Southern Road.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Stone Bridge.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Stoneweir Dam.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Temple of the Nameless Stone.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Town Hall.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Watch Tower.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/Mossford_Map_Key_and_Gazetteer.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/README.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Roads/mireward_reach_road_d100_encounter_table.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Roads/reach_npc_first_names_d100.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Roads/reach_npc_last_names_d100.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Roads/reach_npc_naming_conventions.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Roads/README.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Events/The Festival of Expansion/Schedule and Event Details/Event Posters & Pamphlets.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Events/The Festival of Expansion/Schedule and Event Details/Festival of Expansion Schedule.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Sewers/allies_hideout.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Sewers/loot_room.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Sewers/Mirathorn Sewers.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Sewers/nameless_goddess_temple.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Sewers/path_to_temple.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Sewers/ritual_chamber.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Sewers/Sewer Traps.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Shephards Flock/The cult of the Great  Shephard.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/NPCs/sheriff_roderic_marr/character_seed.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/NPCs/sheriff_roderic_marr/README.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/NPCs/stacey_brambleback/character_seed.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/NPCs/stacey_brambleback/README.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Shephards Flock/Statblocks and Tokens/DustWalker.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/README.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/Stormspire Academy.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/What the Wolf knows.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/Wynna Mossglade _ Clerk.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/NPCs/stuart/character_seed.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/NPCs/stuart/README.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Events/The Festival of Expansion/Events Mechanics.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Events/The Festival of Expansion/The Festival of Expansion.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Events/The Hearthbound Bake-Off/Bakeoff Mechanics.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Events/The Hearthbound Bake-Off/Forageables.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Events/The Hearthbound Bake-Off/Other Teams.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Events/The Hearthbound Bake-Off/The Baked Goods.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Events/The Hearthbound Bake-Off/The Hearthbound Bake-Off.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Events/The Hearthbound Bake-Off/Tilly TuffCrust and Harland Broadquill_.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Shephards Flock/Statblocks and Tokens/Tokens/Cultist and Corrupted Meat Token Sheet.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Shephards Flock/Statblocks and Tokens/Tokens/Shephards Flock Tokens.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/NPCs/torbin_jove/character_seed.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/NPCs/torbin_jove/README.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/NPCs/torbin_jove/torbin_jove_statblock.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Wilderness/conical_hills_night_camp_d100.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Wilderness/geomantic_drake_juvenile_statblock.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Wilderness/geomantic_drake_nest_loot_d100.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Wilderness/pre_era_conical_hills_d20_find.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
| 21, 22, 23 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Wolf Manor/Wolf_s Manor Architectural description_.md` | yes | yes | setting_context, mechanical_reference, npc_grounding | play_facts |
