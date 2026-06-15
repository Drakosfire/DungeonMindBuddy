---
schema_version: dmb_corpus_statblock_v1
document_class: statblock
source_type: generated_statblock_draft
title: "Generated Obsidian Thornling"
campaign_id: longmont-c2
campaign_number: 2
session: 23
artifact_id: statblock-draft-ca2e6c0d-11f4-4f72-bba9-2e1c26166fb3
draft_id: mock-generated-obsidian-thornling
review_status: needs_dm_review
lifecycle_state: stored_artifact
storage_status: stored_draft
corpus_status: promotion_previewed
created_by: human
created_at: "2026-06-12T20:30:32.889472+00:00"
updated_at: 2026-06-12T21:27:42.787981Z
generated_by: dungeonbuddy_statblock_workbench
statblock_generator: mock-statblock-generator
challenge_rating: 2
creature_type: plant
source_record_path: statblock_drafts/statblock-draft-ca2e6c0d-11f4-4f72-bba9-2e1c26166fb3.json
breadcrumbs:
  - surface:statblock_workbench
  - source:mock_provider
  - command:statblock.draft.generate
source_refs:
  - sample-source-obsidian-thornling
---

# Generated Obsidian Thornling

> Generated statblock draft promoted from DungeonBuddy Workbench preview. Review before corpus write.

## Status

- Review status: needs_dm_review
- Source artifact: `statblock-draft-ca2e6c0d-11f4-4f72-bba9-2e1c26166fb3`
- Draft id: `mock-generated-obsidian-thornling`
- Corpus status: promotion_previewed

## Combat Defaults

- AC: 14
- HP: 45
- Initiative: +3
- Passive Perception: 12
- Speed: 35 ft., climb 20 ft.
- Primary actions: Splinter Thorn, Root Snare

## Statblock

## Generated Obsidian Thornling
*Small plant, unaligned*

**Armor Class** 14 (glassy bark)
**Hit Points** 45 (10d6 + 10)
**Speed** 35 ft., climb 20 ft.

### Actions
**Splinter Thorn.** Ranged Weapon Attack: +6 to hit, one target.

**Root Snare.** The thornling lashes obsidian roots around a creature.

## Review Warnings

- WARNING `generated_mock_needs_dm_review`: Review root restraint wording before table use.

## Promotion Preview Warnings

- No promotion preview warnings.

## Corpus Breadcrumbs

- `surface:statblock_workbench` — live_control
- `source:mock_provider` — mock_provider
- `command:statblock.draft.generate` — mock_provider

## Provenance

```json
{
  "generated_at": "2026-06-09T00:00:00Z",
  "generation_info": {
    "generated": true,
    "provider": "MockStatBlockGeneratorProvider",
    "sample": true
  },
  "generator": "mock-statblock-generator",
  "mode": "generate_from_prompt",
  "persistence_request": null,
  "request_id": "live-control-statblock-workbench-generate",
  "source_refs": [
    {
      "excerpt": null,
      "id": "sample-source-obsidian-thornling",
      "kind": "prompt_seed",
      "label": "Obsidian thornling generated mock prompt",
      "metadata": {},
      "page": null,
      "path": "workbench/mock/generate-prompt",
      "reason": "Mock generate provenance only; not read or written by endpoint.",
      "source_id": null,
      "source_type": null,
      "title": null,
      "uri": null
    }
  ]
}
```
