# Graph Memory Cross-Class Blocked Collision Diagnostics

**Status:** Diagnostic report  
**Generated:** 2026-07-01  
**Scope:** Existing checked-in dogfood / extraction diagnostics only  
**Policy:** No merge-policy changes in this report

**Purpose:** Review blocked exact-label cross-class collisions before changing merge policy.

This report is a review surface for PR 03; it does not change identity resolution, merge policy, extraction prompts, candidate graph contracts, or corpus content.

This report does not change merge policy.

## Summary

- Total blocked collision records found: 27
- Source note: Artifact roots inspected: evals/graph_memory_layer/artifacts/vocabulary_ablation_dogfood, evals/graph_memory_layer/artifacts/graph_ingest_runs, evals/graph_memory_layer/examples, out/graph_memory/runs; Missing or empty artifact roots: out/graph_memory/runs; JSON sources with blocked diagnostics: evals/graph_memory_layer/artifacts/vocabulary_ablation_dogfood/manual_review/baseline_vs_edge_and_node_manual_review.json.
- Count by bed:
  - `C1S1 Stonebridge / Glowkindle Rats`: 12
  - `Mirathorn worldbuilding`: 15
- Count by suggested review action:
  - `candidate_keep_blocked`: 3
  - `candidate_new_node_type`: 16
  - `needs_human_review`: 8
- Count by class pair:
  - `actor + collective`: 1
  - `actor + object`: 1
  - `collective + object`: 3
  - `collective + object + place`: 5
  - `object + place`: 16
  - `place + thread`: 1

## Review table

| Bed | Variant | Label | Classes | Node IDs | Suggested review action | Human decision | Notes |
|---|---|---|---|---|---|---|---|
| C1S1 Stonebridge / Glowkindle Rats | baseline | job board | collective, object | organization_jobs_board, item_3 | needs_human_review | TBD | Exact-label cross-class collision requires human review before any policy change. |
| C1S1 Stonebridge / Glowkindle Rats | baseline | river s edge pub | collective, object, place | loc_rivers_edge_pub, organization_rivers_edge_pub, item_2 | needs_human_review | TBD | Exact-label cross-class collision requires human review before any policy change. |
| C1S1 Stonebridge / Glowkindle Rats | baseline | room full of broken alchemical tools | place, thread | loc_room_of_broken_alchemical_tools, mystery_broken_alchemical_tools_004 | candidate_keep_blocked | TBD | Narrative thread or phenomenon labels can overlap concrete entities; keep blocked unless reviewed. |
| C1S1 Stonebridge / Glowkindle Rats | baseline | stone bridge | collective, object, place | loc_stone_bridge, faction_town_stone_bridge, item_1 | needs_human_review | TBD | Exact-label cross-class collision requires human review before any policy change. |
| C1S1 Stonebridge / Glowkindle Rats | baseline | trapped mosaic | object, place | loc_trapped_mosaic, item_8 | candidate_new_node_type | TBD | Object/place collisions often indicate structure or establishment modeling pressure; do not merge blindly. |
| C1S1 Stonebridge / Glowkindle Rats | edge_and_node_packet | enormous boulder | object, place | loc_enormous_boulder, item_enormous_boulder | candidate_new_node_type | TBD | Object/place collisions often indicate structure or establishment modeling pressure; do not merge blindly. |
| C1S1 Stonebridge / Glowkindle Rats | edge_and_node_packet | excavation crew | collective, object | group_excavation_crew, item_excavation_crew | needs_human_review | TBD | Exact-label cross-class collision requires human review before any policy change. |
| C1S1 Stonebridge / Glowkindle Rats | edge_and_node_packet | flaming magma infused spider monstrosity | actor, object | npc:spider-monstrosity, item_flaming_magma_spider | candidate_keep_blocked | TBD | Actor-involved exact-label collisions are high-risk false-merge candidates. |
| C1S1 Stonebridge / Glowkindle Rats | edge_and_node_packet | river s edge pub | collective, object, place | loc_rivers_edge_pub, organization_rivers_edge_pub, item_rivers_edge_pub | needs_human_review | TBD | Exact-label cross-class collision requires human review before any policy change. |
| C1S1 Stonebridge / Glowkindle Rats | edge_and_node_packet | stone bridge | collective, object, place | loc_stone_bridge, faction_stone_bridge, item_stone_bridge | needs_human_review | TBD | Exact-label cross-class collision requires human review before any policy change. |
| C1S1 Stonebridge / Glowkindle Rats | edge_and_node_packet | troupe of gnomes | actor, collective | npc:the-wizard-s-tower-brewing-company-gnomes, group_gnome_brewing_troupe | candidate_keep_blocked | TBD | Actor-involved exact-label collisions are high-risk false-merge candidates. |
| C1S1 Stonebridge / Glowkindle Rats | edge_and_node_packet | wizard s tower brewing company | collective, object | faction_wizard_tower_brewing_co, item_wizards_tower_brewing_company | needs_human_review | TBD | Exact-label cross-class collision requires human review before any policy change. |
| Mirathorn worldbuilding | baseline | broken blade inn | object, place | loc_8, item_011 | candidate_new_node_type | TBD | Object/place collisions often indicate structure or establishment modeling pressure; do not merge blindly. |
| Mirathorn worldbuilding | baseline | festival of expansion | object, place | loc_18, item_013 | candidate_new_node_type | TBD | Object/place collisions often indicate structure or establishment modeling pressure; do not merge blindly. |
| Mirathorn worldbuilding | baseline | grand market | object, place | loc_5, item_008 | candidate_new_node_type | TBD | Object/place collisions often indicate structure or establishment modeling pressure; do not merge blindly. |
| Mirathorn worldbuilding | baseline | lake mirathorn docks | object, place | loc_7, item_010 | candidate_new_node_type | TBD | Object/place collisions often indicate structure or establishment modeling pressure; do not merge blindly. |
| Mirathorn worldbuilding | baseline | stormspire academy | object, place | loc_6, item_009 | candidate_new_node_type | TBD | Object/place collisions often indicate structure or establishment modeling pressure; do not merge blindly. |
| Mirathorn worldbuilding | baseline | temple of the nameless goddess | object, place | loc_9, item_012 | candidate_new_node_type | TBD | Object/place collisions often indicate structure or establishment modeling pressure; do not merge blindly. |
| Mirathorn worldbuilding | edge_and_node_packet | altar of sacrifice | object, place | loc_11, item_023 | candidate_new_node_type | TBD | Object/place collisions often indicate structure or establishment modeling pressure; do not merge blindly. |
| Mirathorn worldbuilding | edge_and_node_packet | broken blade inn | object, place | loc_8, item_030 | candidate_new_node_type | TBD | Object/place collisions often indicate structure or establishment modeling pressure; do not merge blindly. |
| Mirathorn worldbuilding | edge_and_node_packet | grand market | object, place | loc_5, item_027 | candidate_new_node_type | TBD | Object/place collisions often indicate structure or establishment modeling pressure; do not merge blindly. |
| Mirathorn worldbuilding | edge_and_node_packet | great hall | object, place | loc_10, item_022 | candidate_new_node_type | TBD | Object/place collisions often indicate structure or establishment modeling pressure; do not merge blindly. |
| Mirathorn worldbuilding | edge_and_node_packet | lake mirathorn docks | object, place | loc_7, item_029 | candidate_new_node_type | TBD | Object/place collisions often indicate structure or establishment modeling pressure; do not merge blindly. |
| Mirathorn worldbuilding | edge_and_node_packet | reflection pool | object, place | loc_12, item_024 | candidate_new_node_type | TBD | Object/place collisions often indicate structure or establishment modeling pressure; do not merge blindly. |
| Mirathorn worldbuilding | edge_and_node_packet | sanctuary | object, place | loc_13, item_025 | candidate_new_node_type | TBD | Object/place collisions often indicate structure or establishment modeling pressure; do not merge blindly. |
| Mirathorn worldbuilding | edge_and_node_packet | stormspire academy | collective, object, place | loc_6, organization:stormspire-academy, item_028 | needs_human_review | TBD | Exact-label cross-class collision requires human review before any policy change. |
| Mirathorn worldbuilding | edge_and_node_packet | temple of the nameless goddess | object, place | loc_9, item_021 | candidate_new_node_type | TBD | Object/place collisions often indicate structure or establishment modeling pressure; do not merge blindly. |

## Records by bed

### C1S1 Stonebridge / Glowkindle Rats

- Blocked records: 12
- `baseline` / `job board` / `collective, object` / `needs_human_review`
- `baseline` / `river s edge pub` / `collective, object, place` / `needs_human_review`
- `baseline` / `room full of broken alchemical tools` / `place, thread` / `candidate_keep_blocked`
- `baseline` / `stone bridge` / `collective, object, place` / `needs_human_review`
- `baseline` / `trapped mosaic` / `object, place` / `candidate_new_node_type`
- `edge_and_node_packet` / `enormous boulder` / `object, place` / `candidate_new_node_type`
- `edge_and_node_packet` / `excavation crew` / `collective, object` / `needs_human_review`
- `edge_and_node_packet` / `flaming magma infused spider monstrosity` / `actor, object` / `candidate_keep_blocked`
- `edge_and_node_packet` / `river s edge pub` / `collective, object, place` / `needs_human_review`
- `edge_and_node_packet` / `stone bridge` / `collective, object, place` / `needs_human_review`
- `edge_and_node_packet` / `troupe of gnomes` / `actor, collective` / `candidate_keep_blocked`
- `edge_and_node_packet` / `wizard s tower brewing company` / `collective, object` / `needs_human_review`

### Mirathorn worldbuilding

- Blocked records: 15
- `baseline` / `broken blade inn` / `object, place` / `candidate_new_node_type`
- `baseline` / `festival of expansion` / `object, place` / `candidate_new_node_type`
- `baseline` / `grand market` / `object, place` / `candidate_new_node_type`
- `baseline` / `lake mirathorn docks` / `object, place` / `candidate_new_node_type`
- `baseline` / `stormspire academy` / `object, place` / `candidate_new_node_type`
- `baseline` / `temple of the nameless goddess` / `object, place` / `candidate_new_node_type`
- `edge_and_node_packet` / `altar of sacrifice` / `object, place` / `candidate_new_node_type`
- `edge_and_node_packet` / `broken blade inn` / `object, place` / `candidate_new_node_type`
- `edge_and_node_packet` / `grand market` / `object, place` / `candidate_new_node_type`
- `edge_and_node_packet` / `great hall` / `object, place` / `candidate_new_node_type`
- `edge_and_node_packet` / `lake mirathorn docks` / `object, place` / `candidate_new_node_type`
- `edge_and_node_packet` / `reflection pool` / `object, place` / `candidate_new_node_type`
- `edge_and_node_packet` / `sanctuary` / `object, place` / `candidate_new_node_type`
- `edge_and_node_packet` / `stormspire academy` / `collective, object, place` / `needs_human_review`
- `edge_and_node_packet` / `temple of the nameless goddess` / `object, place` / `candidate_new_node_type`

## Suggested human review actions

- `needs_human_review`: default for cases where the diagnostic is not enough to classify safely.
- `candidate_merge_policy`: possible future policy case, only after human confirmation.
- `candidate_keep_blocked`: likely safer as a visible duplicate than a false merge.
- `candidate_new_node_type`: may indicate taxonomy/pass design pressure rather than merge-policy pressure.
- `insufficient_context`: blocked row exists, but node details were not available for review enrichment.

## Manual review checklist

- [ ] For each `candidate_merge_policy` row, confirm that the same label truly refers to one entity rather than two related concepts.
- [ ] For each `candidate_keep_blocked` row, confirm that blocked duplication is preferable to false merge.
- [ ] For each `candidate_new_node_type` row, decide whether the failure belongs to taxonomy/pass design rather than merge policy.
- [ ] For every row involving an actor class, prefer keeping blocked unless there is explicit reviewed evidence.
- [ ] Before PR 03, choose a tiny allowlist of policy cases; do not generalize from one attractive example.

## Non-goals

This report does not authorize:
- changing `should_merge_cross_class_label_collision`;
- changing `_CROSS_CLASS_TYPE_PRIORITY`;
- changing node taxonomy;
- changing extraction prompts;
- mutating corpus files;
- promoting graph memory to canon.

## Next step

PR 03 may use this report to implement a conservative cross-class merge-policy v0, but only for reviewed cases. False merges are worse than visible duplicates.
