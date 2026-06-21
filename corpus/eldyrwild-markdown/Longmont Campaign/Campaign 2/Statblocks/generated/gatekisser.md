---
schema_version: dmb_corpus_statblock_v1
document_class: statblock
source_type: generated_statblock_draft
title: Gatekisser
campaign_id: longmont-c2
campaign_number: 2
session: 23
artifact_id: statblock-draft-f97405fd-22c9-45f3-b5b0-98a0583fba31
draft_id: draft-command-board-dogfood-1781383393759
review_status: needs_dm_review
lifecycle_state: stored_artifact
storage_status: stored_draft
corpus_status: promotion_previewed
created_by: human
created_at: "2026-06-13T20:43:25.406390+00:00"
updated_at: 2026-06-13T20:43:39.304810Z
generated_by: dungeonbuddy_statblock_workbench
statblock_generator: StatBlockGenerator.generate_creature
challenge_rating: null
creature_type: aberration
source_record_path: statblock_drafts/statblock-draft-f97405fd-22c9-45f3-b5b0-98a0583fba31.json
breadcrumbs:
  - surface:statblock_workbench
  - source:http_provider
  - command:statblock.draft.generate
source_refs: []
---

# Gatekisser

> Generated statblock draft promoted from DungeonBuddy Workbench preview. Review before corpus write.

## Status

- Review status: needs_dm_review
- Source artifact: `statblock-draft-f97405fd-22c9-45f3-b5b0-98a0583fba31`
- Draft id: `draft-command-board-dogfood-1781383393759`
- Corpus status: promotion_previewed

## Combat Defaults

- AC: 16
- HP: 130
- Initiative: +2
- Passive Perception: 11
- Speed: 30 ft., climb 30 ft.
- Primary actions: Rusting Grasp, Kiss the Hinge, Borrowed Face

## Statblock

# Gatekisser
*Medium aberration, chaotic neutral*

**Armor Class** 16
**Hit Points** 130 (20d8+40)
**Speed** 30 ft., climb 30 ft.

|STR|DEX|CON|INT|WIS|CHA|
|---:|---:|---:|---:|---:|---:|
|14 (+2)|14 (+2)|14 (+2)|10 (+0)|12 (+1)|16 (+3)|

**Skills** stealth +5, deception +6, athletics +4
**Damage Resistances** acid
**Condition Immunities** frightened
**Senses** darkvision 60 ft., passive Perception 11
**Languages** Deep Speech, Common
**Challenge** 5.0 (1,800 XP)

## Actions
**Rusting Grasp.** Melee Weapon Attack: +5 to hit, reach 5 ft., one target. Hit: 10 (2d6+3) acid damage. Nonmagical metal armor or shield worn or carried by the target takes a permanent and cumulative -1 penalty to the AC it offers. The penalty worsens each time the Gatekisser hits with this attack. If the penalty drops to -5, the armor or shield is destroyed.
**Kiss the Hinge.** The Gatekisser targets a metal object within 5 feet that is part of a door, manacle, shield, or gate. It kisses the object, dealing 14 (4d6) acid damage. If the object is reduced to 0 hit points by this damage, it is destroyed.
**Borrowed Face.** The Gatekisser can use its action to assume the appearance of a missing civilian it has seen within the last 24 hours. This effect lasts for 1 minute or until the Gatekisser uses an action to revert to its true form. Any inspection reveals the illusion as false.

## Reactions
**Corrosive Sigh.** When the Gatekisser is reduced to 0 hit points within 10 feet of a metal object, it releases a corrosive sigh. All creatures within 10 feet must make a DC 13 Dexterity saving throw. On a failed save, a creature takes 10 (3d6) acid damage and nonmagical metal objects worn or carried by the creature take a permanent and cumulative -1 penalty to their AC. Objects are destroyed if their penalty reaches -5.

## Description
Gatekissers are mysterious entities resembling child-sized, smooth-faced humanoids. Their unsettling presence comes with an uncanny ability to rot and destroy metal objects with their corrosive touch, making them ideal siege infiltrators. With an affectionate touch that belies their destructive nature, they can dissolve the toughest locks and hinges, leaving gates and defenses in ruins. Their unsettling nature is compounded by their ability to mimic the visage of vanished civilians, sowing confusion and fear. When slain, they release a final corrosive sigh that threatens to ruin the weapons and armor of those around them.

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
  "generated_at": "2026-06-13T20:43:25.337131+00:00",
  "generation_info": {
    "generation_time": "2026-06-13T20:43:25.336838",
    "model_used": "gpt-4o-2024-08-06",
    "prompt_version": "1.0.0",
    "structured_outputs": true
  },
  "generator": "StatBlockGenerator.generate_creature",
  "mode": "generate_from_prompt",
  "persist_requested": false,
  "persistence_request": null,
  "request_id": "command-board-dogfood-1781383393759",
  "source_refs": []
}
```
