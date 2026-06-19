---
title: "Markdown Theme Fixture"
fixture_kind: markdown_theme_visual_test
---

# Mireward Theme Fixture

Lead paragraph with **bold**, *italic*, `inline code`, and a [relative Markdown link](../../../../Docs/Plans/PLAN-configurable-markdown-rendering-and-tiptap-styling.md).

## Tactical Summary

- First bullet with a short phrase.
- Second bullet with **strong emphasis**.
- Third bullet with `inline code`.

1. First ordered item.
2. Second ordered item.
3. Third ordered item.

> Read-aloud-ish prose goes here. This is not semantic syntax yet; it is only a blockquote fixture.

## Semantic Callout Fixtures

> [!READ-ALOUD]
> The rain hisses against the crystal road. Something massive moves beneath the swampwater.

> [!GM-NOTE]
> If the party hesitates, advance the breach clock by 1.

> [!RULES]
> Treat this as difficult terrain. Fire damage suppresses regeneration until the end of the next round.

> [!WARNING]
> The gate will fail in 3 rounds unless reinforced.

## Typed Reference Chip Fixtures

Runbook refs should stay readable as Markdown while rendering as inline chips in Command Board prose.

If the players push toward the refugees, use [Gate Dilemma d12](#dmb-ref:roll-table:gate-dilemma-d12). If combat starts, launch [North Gate Combat](#dmb-action:combat:north-gate-combat).

Active threats: [Sewer Meat Creature](#dmb-ref:statblock:sewer-meat-creature), [Aberrant Meatwing](#dmb-ref:statblock:aberrant-meatwing), [Corrupted Meat Golem](#dmb-ref:statblock:corrupted-meat-golem).

Key people: [Lysandro Ironveil](#dmb-ref:npc:lysandro-ironveil), [Brin Holloway](#dmb-ref:npc:brin-holloway), [Captain Lysandra Ironveil](#dmb-ref:npc:captain-lysandra-ironveil).

Location context: [North Reach Gate](#dmb-ref:location:north-reach-gate), [Mireward Wall](#dmb-ref:location:mireward-wall). Source: [Session 22 ending](#dmb-ref:citation:c2s22-ending).

## Table Fixture

| Creature | Role | CR | Notes |
|---|---:|---:|---|
| Sewer Meat Creature | Baseline pressure | 3 | Poison-resistant, fire-vulnerable |
| Tripod Null-Calf | Alien geometry | 5 | High HP, positional threat |
| Latch-Harrow | Breach clock | 8 | Late-wave crisis |

## Code Fence

```json
{
  "theme": "statblock",
  "surface": "fixture",
  "parserChanged": false
}
```

---

## Final Section

A closing paragraph after a horizontal rule.
