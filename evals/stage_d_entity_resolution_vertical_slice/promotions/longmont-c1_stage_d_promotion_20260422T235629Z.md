<!-- benchmark_artifact: stage_d_promotion_v1 | iso_utc: 2026-04-22T23:56:29.664793+00:00 | campaign: longmont-c1 | model: gpt-5.4-mini | cost_usd: 0.013748 -->

# Stage D promotion review — longmont-c1

- **generated_at:** `2026-04-22T23:56:29.664793+00:00`
- **model:** `gpt-5.4-mini`
- **llm_enabled:** True
- **cost:** $0.0137 USD over 12 call(s)
- **sources:** 13 file(s)
- **registry size at review:** 3

## proposed_new_records (4)

| slug | recommendation | confidence | rationale | evidence | flags |
|---|---|---|---|---|---|
| `glowkindle` | accept | high | The proposal is a clear single entity with consistent sightings of the exact same descriptor "Glowkindle" across sessions 1 and 2, and there is no slug collision or PC roster collision. The evidence shows multiple appearances/events supporting a stable NPC record rather than noise or an ambiguous duplicate. | sessions=[1, 2]; descriptors=['Glowkindle'] | none |
| `grishna` | accept | high | Grishna appears as a single named entity across sessions 1 and 3 with repeated direct descriptors and no slug or PC roster collision. The evidence is consistent enough to promote as a new candidate rather than defer. | sessions=[1, 3]; descriptors=['Grishna'] | none |
| `kirfan` | accept | high | Kirfan appears to be a single named entity with consistent evidence across session 3 and no registry slug or PC roster collision. The name is specific rather than generic, and there is no sign it is a fragment or duplicate of an existing registered NPC. | sessions=[3]; descriptors=['Kirfan'] | none |
| `pippa` | accept | high | The proposal has a clean, non-colliding slug and no PC roster conflict, and the evidence consistently shows the same named entity "Pippa" across session 3 events. The name is specific rather than generic, and there is no indication it matches an existing registry sibling. | sessions=[3]; descriptors=['Pippa'] | none |

## proposed_aliases (0)

(none)

## unresolvable (8) — advisory

| descriptor | recommendation | confidence | rationale | proposed_canonical |
|---|---|---|---|---|
| a flaming, magma-infused spider monstrosity | leave_unresolvable | high | This looks like a purely descriptive monster phrase with no evidence of a specific named entity or alias in the registry. The sample reason and empty evidence trail both support keeping it generic rather than canonicalizing it. | — |
| a magma-infused spider monstrosity | leave_unresolvable | high | This is a generic creature description with no named-entity evidence or registry substring match. The sampled siblings do not provide any linkage to a specific existing entry, so it should remain unresolved unless the GM later introduces a proper name or alias. | — |
| a mysterious cat owl | leave_unresolvable | high | This is a generic creature description with no named-entity evidence, and the provided registry siblings do not match it in any meaningful way. There is no strong basis to canonicalize it to an existing slug, so it should remain unresolvable unless future evidence ties it to a specific entity. | — |
| cat owl | leave_unresolvable | high | “cat owl” reads as a generic creature descriptor, and the provided evidence does not show any linkage to a named registry entity or alias. The sample registry siblings are unrelated, so there is no strong basis to canonicalize this into an existing slug. | — |
| flaming, magma-infused spider monstrosity | leave_unresolvable | high | This is a purely descriptive creature phrase with no named-entity evidence in the item or nearby registry context. The sibling samples do not suggest any plausible match, so it should remain unresolved unless the GM later ties it to a specific canonical monster. | — |
| magma-infused spider monstrosity | leave_unresolvable | high | This is a generic creature description with no named-entity evidence or alias overlap to any registry sibling. The sample reason also indicates Stage D found no substring match, so there is no strong basis to canonicalize it. | — |
| mysterious cat owl | leave_unresolvable | high | This looks like a purely descriptive creature phrase with no name evidence, alias, or registry linkage. The nearby registry siblings are unrelated named entities, so there is no strong basis to canonicalize it to an existing slug. | — |
| the mysterious cat owl | leave_unresolvable | high | This looks like a purely descriptive phrase with no evidence of a specific named entity or registry alias match. The sampled siblings do not provide any meaningful substring or identity link to justify canonicalizing it into an existing slug. | — |

## sources

- `/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/evals/stage_d_entity_resolution_vertical_slice/proposals/longmont-c1_stage_d_proposals_20260422T225721Z.json`
- `/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/evals/stage_d_entity_resolution_vertical_slice/proposals/longmont-c1_stage_d_proposals_20260422T233536Z.json`
- `/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/evals/stage_d_entity_resolution_vertical_slice/proposals/longmont-c1_stage_d_proposals_20260422T233537Z.json`
- `/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/evals/stage_d_entity_resolution_vertical_slice/artifacts/runs/2026-04-22/stage_d--stage_d_live_from_c_session1_c1--deterministic-v0--PASS--20260422T233536Z.json`
- `/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/evals/stage_d_entity_resolution_vertical_slice/artifacts/runs/2026-04-22/stage_d--stage_d_live_from_c_session2_c1--deterministic-v0--PASS--20260422T233536Z.json`
- `/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/evals/stage_d_entity_resolution_vertical_slice/artifacts/runs/2026-04-22/stage_d--stage_d_live_from_c_session3_c1--deterministic-v0--PASS--20260422T233537Z.json`
- `/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/evals/stage_d_entity_resolution_vertical_slice/artifacts/runs/2026-04-22/stage_d--stage_d_session1_c1--deterministic-v0--PASS--20260422T225716Z.json`
- `/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/evals/stage_d_entity_resolution_vertical_slice/artifacts/runs/2026-04-22/stage_d--stage_d_session3_c1--deterministic-v0--PASS--20260422T225717Z.json`
- `/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/evals/stage_d_entity_resolution_vertical_slice/artifacts/runs/2026-04-22/stage_d--stage_d_session3_c1--deterministic-v0--PASS--20260422T225721Z--run001.json`
- `/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/evals/stage_d_entity_resolution_vertical_slice/artifacts/runs/2026-04-22/stage_d--stage_d_session3_c1--deterministic-v0--PASS--20260422T225721Z--run002.json`
- `/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/evals/stage_d_entity_resolution_vertical_slice/artifacts/runs/2026-04-22/stage_d--stage_d_session3_c1--deterministic-v0--PASS--20260422T225721Z--run003.json`
- `/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/evals/stage_d_entity_resolution_vertical_slice/artifacts/runs/2026-04-22/stage_d--stage_d_session3_c1--deterministic-v0--PASS--20260422T225721Z--run004.json`
- `/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/evals/stage_d_entity_resolution_vertical_slice/artifacts/runs/2026-04-22/stage_d--stage_d_session3_c1--deterministic-v0--PASS--20260422T225721Z--run005.json`
