---
title: "Longmont Campaign — homebrew items"
document_class: reference
canon_layer: campaign
campaign_id: longmont-c2
temporal_scope: evergreen
session: null
origin_session: null
last_updated_session: 21
source_class: ledger_or_dossier
subject_class: null
subject_doc_kind: hub_index
table_note: "Mechanical truth for magic items. Session-born objects also have a Plot Artifacts router under Campaign 2."
---

# Homebrew Items

**Mechanical source of truth** for campaign magic items. One primary file per item; optional player copy under `Player Copies/`.

## Layout

| Path | Role |
|------|------|
| `Item_ <Name>.md` | GM item card — full statblock, lore, hooks, table rulings |
| `Player Copies/Player Copy Item_ <Name>.md` | Table-facing card (paste into CardGenerator / D&D Beyond notes) |
| `Trinkets/` | Minor trinkets without attunement |
| `../Campaign 2/Plot Artifacts/<slug>.md` | Session provenance router (when object debuted in recap) |

## Frontmatter contract (new / touched items)

```yaml
subject_class: item
subject_doc_kind: item_card
document_class: reference
canon_layer: campaign
campaign_id: longmont-c2
```

## Campaign 2 — active items

| Item | GM card | Player copy | Plot artifact |
|------|---------|-------------|---------------|
| Boots of the Crowing Wings | `Item_ Boots of the Crowing Wings.md` | `Player Copies/Player Copy Item_ Boots of the Crowing Wings.md` | `Campaign 2/Plot Artifacts/boots_of_crowing_wings.md` |
| The Slinkstone | `Item_ The Slinkstone.md` | `Player Copy Item_ The Slinkstone.md` | — |
| The Friendship Chime | `Item_ The Friendship Chime.md` | `Player Copies/Player Copy Item_ The Friendship Chime.md` | — |
