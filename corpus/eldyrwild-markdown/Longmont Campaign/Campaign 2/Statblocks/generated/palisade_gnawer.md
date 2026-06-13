---
schema_version: dmb_corpus_statblock_v1
document_class: statblock
source_type: generated_statblock_draft
title: "Palisade Gnawer"
campaign_id: longmont-c2
campaign_number: 2
session: 23
artifact_id: statblock-draft-9f6ae390-7387-4030-92cb-9674b6f0e1a5
draft_id: draft-command-board-dogfood-1781374651593
review_status: needs_dm_review
lifecycle_state: stored_artifact
storage_status: stored_draft
corpus_status: promotion_previewed
created_by: human
created_at: "2026-06-13T18:17:41.927714+00:00"
updated_at: 2026-06-13T19:50:29.772276Z
generated_by: dungeonbuddy_statblock_workbench
statblock_generator: StatBlockGenerator.generate_creature
challenge_rating: null
creature_type: monstrosity
source_record_path: statblock_drafts/statblock-draft-9f6ae390-7387-4030-92cb-9674b6f0e1a5.json
breadcrumbs:
  - surface:statblock_workbench
  - source:http_provider
  - command:statblock.draft.generate
source_refs: []
---

# Palisade Gnawer

> Generated statblock draft promoted from DungeonBuddy Workbench preview. Review before corpus write.

## Status

- Review status: needs_dm_review
- Source artifact: `statblock-draft-9f6ae390-7387-4030-92cb-9674b6f0e1a5`
- Draft id: `draft-command-board-dogfood-1781374651593`
- Corpus status: promotion_previewed

## Combat Defaults

- AC: 16
- HP: 140
- Initiative: +1
- Passive Perception: 14
- Speed: 30 ft., burrow 30 ft.
- Primary actions: Multiattack, Bite, Skull Ram, Foundation Gnaw

## Statblock

# Palisade Gnawer
*Large monstrosity, unaligned*

**Armor Class** 16
**Hit Points** 140 (15d10+60)
**Speed** 30 ft., burrow 30 ft.

|STR|DEX|CON|INT|WIS|CHA|
|---:|---:|---:|---:|---:|---:|
|21 (+5)|12 (+1)|18 (+4)|4 (-3)|12 (+1)|7 (-2)|

**Skills** Perception +4, Athletics +7
**Condition Immunities** charmed, frightened
**Senses** darkvision 60 ft., passive Perception 14
**Languages** understands Common but can't speak
**Challenge** 5.0 (1,800 XP)

## Traits
**Rubble Stride.** The Palisade Gnawer can move through difficult terrain made of rubble without expending extra movement.

## Actions
**Multiattack.** The Palisade Gnawer makes two attacks: one with its Bite and one with its Skull Ram.
**Bite.** Melee Weapon Attack: +7 to hit, reach 5 ft., one target. Hit: 18 (3d8 + 5) piercing damage. If the target is a structure made of wood or stone, the damage is doubled.
**Skull Ram.** Melee Weapon Attack: +7 to hit, reach 5 ft., one target. Hit: 14 (2d8 + 5) bludgeoning damage. If the target is a structure, the damage is doubled.
**Foundation Gnaw.** The Palisade Gnawer deals double damage to wooden and stone structures with its Bite and Skull Ram attacks.
**Splinter Spray (Recharge 5-6).** After damaging a barricade or structure, the Palisade Gnawer can expel sharp splinters from its teeth in a 30-foot cone. Each creature in that cone must make a DC 15 Dexterity saving throw, taking 27 (6d8) piercing damage on a failed save, or half as much damage on a successful one.

## Description
The Palisade Gnawer is a terrifying fusion of beaver and rat, engineered for siege warfare with its thick, plated skull and teeth sharp enough to saw through stone. It is a relentless force of destruction, plowing through obstacles with brute strength and devastating structures with ease. Despite its size and power, it lacks intelligence and acts purely on instinct, driven by a primal urge to gnaw and destroy.

## Review Warnings

- No draft review warnings were recorded.

## Promotion Preview Warnings

- No promotion preview warnings.

## Corpus Breadcrumbs

- `surface:statblock_workbench` — live_control
- `source:http_provider` — http_provider
- `command:statblock.draft.generate` — http_provider

## Provenance

```json
{
  "adapter_version": "0.1.0",
  "generated_at": "2026-06-13T18:17:41.878082+00:00",
  "generation_info": {
    "generation_time": "2026-06-13T18:17:41.877082",
    "model_used": "gpt-4o-2024-08-06",
    "prompt_version": "1.0.0",
    "structured_outputs": true
  },
  "generator": "StatBlockGenerator.generate_creature",
  "mode": "generate_from_prompt",
  "persist_requested": false,
  "persistence_request": null,
  "request_id": "command-board-dogfood-1781374651593",
  "source_refs": []
}
```
