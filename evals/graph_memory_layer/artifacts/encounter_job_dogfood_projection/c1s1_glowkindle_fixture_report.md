# Encounter/Job Dogfood Projection Report — Glowkindle Rat Job Fixture

## Status

This is a deterministic fixture dogfood report. It does not call an LLM, scan corpus files, mutate corpus files, write graph memory, connect `/plan`, approve facts, promote canon, or change runtime behavior.

## Scope

Eval-only, fixture-only candidate graph projection for review. The source fixture is synthetic and not campaign canon.

## Fixture summary

- Fixture ID: `synthetic-glowkindle-rat-job-v0`
- Source spans: `spref:glowkindle:001` through `spref:glowkindle:004`.
- Scenario: Glowkindle asks the party to clear rats from the cellar beneath the brewery; the party fights a rat swarm and the cellar becomes safe enough to reopen.

## Extraction configuration

- `enable_encounter_job_pass`: `True`
- `enable_party_participation_attachment`: `True`
- `enable_encounter_job_edge_guidance`: `True`
- `enable_dynamic_node_vocabulary_packet`: `True`

## Review checklist

- [x] One quest node exists.
- [x] One combat encounter node exists.
- [x] Heroes / party pursues the quest.
- [x] Heroes / party participates in the combat encounter.
- [x] Encounter is located in the cellar.
- [x] Rat swarm participates in the encounter.
- [x] Quest targets the rat swarm.
- [x] Quest focuses on the cellar.
- [x] Dynamic node vocabulary packet was used.
- [x] Encounter/job edge guidance was enabled.
- [x] No invalid predicate issues.
- [x] No dropped edges.
- [x] No corpus mutation.

## Nodes of interest

- `npc_glowkindle` — Glowkindle (`character`)
- `creature_rat_swarm` — Rat swarm (`character`)
- `loc_glowkindle_brewery` — Glowkindle's brewery (`location`)
- `loc_glowkindle_cellar` — Glowkindle's cellar (`location`)
- `node:heroes-party` — Heroes / party (`character`)
- `quest_clear_glowkindle_rats` — Clear rats from Glowkindle's cellar (`quest`)
- `enc_glowkindle_cellar_rats` — Glowkindle cellar rat fight (`combat_encounter`)

## Edges of interest

- `enc_glowkindle_cellar_rats` → `loc_glowkindle_cellar` — `located_in` (location_hierarchy)
- `creature_rat_swarm` → `enc_glowkindle_cellar_rats` — `participates_in` (participation)
- `quest_clear_glowkindle_rats` → `creature_rat_swarm` — `mission_targets` (hook_relation)
- `quest_clear_glowkindle_rats` → `loc_glowkindle_cellar` — `mission_focus` (hook_relation)
- `node:heroes-party` → `enc_glowkindle_cellar_rats` — `participates_in` (participation)
- `node:heroes-party` → `quest_clear_glowkindle_rats` — `pursues` (hook_relation)

## Diagnostics summary

- `dynamic_node_vocabulary_packet`: enabled=True
- `node_vocabulary_ablation`: enabled=True
- `encounter_job_pass`: {'enabled': True, 'raw_node_count': 2, 'kept_node_count': 2, 'dropped_invalid_node_type_ids': []}
- `party_participation_attachment`: {'enabled': True, 'subject_node_ids': ['node:heroes-party'], 'combat_encounter_node_ids': ['enc_glowkindle_cellar_rats'], 'quest_node_ids': ['quest_clear_glowkindle_rats'], 'inserted_edge_ids': ['edge:heroes-party-participates-in-enc-glowkindle-cellar-rats', 'edge:heroes-party-pursues-quest-clear-glowkindle-rats'], 'inserted_edge_count': 2, 'skipped_reason': None}
- `encounter_job_edge_guidance`: {'enabled': True, 'guidance_added': True, 'quest_node_ids': ['quest_clear_glowkindle_rats'], 'combat_encounter_node_ids': ['enc_glowkindle_cellar_rats']}
- `edge_predicate_issues`: []
- `dropped_edges_missing_endpoints`: []
- Checks: `{'has_quest': True, 'has_combat_encounter': True, 'has_party_pursues_quest': True, 'has_party_participates_in_encounter': True, 'has_encounter_location_edge': True, 'has_rat_participation_edge': True, 'has_quest_target_edge': True, 'has_quest_focus_edge': True, 'has_duplicate_pc_nodes': False, 'has_invalid_predicate_issues': False, 'has_dropped_edges': False}`

## Known limitations

This fixture proves pipeline shape and projection review structure. It does not prove live LLM extraction quality. A later manual dogfood run must compare real model output against this expected shape.

## Non-goals

- No LLM calls.
- No corpus scanning.
- No corpus mutation.
- No graph memory writes, fact approval, canon promotion, runtime wiring, or `/plan` integration.

## Next review step

Use this report as the stable review shape for a later explicit LLM-backed C1S1/C2S23 dogfood run.
