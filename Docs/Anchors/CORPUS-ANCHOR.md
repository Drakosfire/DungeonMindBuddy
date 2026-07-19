# Corpus Anchor — Eldyrwild / Longmont Markdown

Generated: `2026-07-17T18:46:17Z` · schema `dmb_corpus_index_v1` v1.0

Regenerate:

```bash
PYTHONPATH=. python scripts/build_corpus_index.py
```

Machine-readable companion: [`corpus/CORPUS-INDEX.json`](../../corpus/CORPUS-INDEX.json)

## Purpose

Re-anchor source for **where campaign recaps and worldbuilding markdown live** in this repo.
Use before graph-memory vocabulary work, recap ingest, planning manifests, or corpus-grounded extraction.

Paths below are **repo-relative** from the DungeonMindBuddy root.

## Corpus roots

| Root | Path | Role |
|------|------|------|
| Primary markdown | `corpus/eldyrwild-markdown` | Canonical Eldyrwild + Longmont markdown corpus (read/write target for recap ingest and worldbuilding). (431 `.md` files) |
| Unprocessed pipeline | `corpus/Eldyrwild and Campaign Unprocessed` | Pipeline stage artifacts (Stage A/B surfaces, evaluation reports). Not primary markdown source. |
| Drafts | `corpus/_drafts` | Scratch / in-progress corpus drafts. |

**Read rule:** prefer `corpus/eldyrwild-markdown/` for canonical prose. Treat `_normalized`, `_breadcrumbed`, `_session_memory`, and `_archive` as **derived** ingest artifacts unless a task explicitly targets them.

## Session recaps — authority buckets

| Bucket | Meaning |
|--------|---------|
| `canonical` | GM-authored recap files at `Session Recaps/` root |
| `_normalized` | Mechanical normalized recap (graph ingest input) |
| `_breadcrumbed` | Legacy breadcrumb derivatives |
| `_archive` | Timestamped archive copies |
| `_session_memory` | Derived session-memory JSONL companions (when present) |

Path helpers: `src/corpus/session_recap_paths.py`

## Campaign 1 — Session Recaps

Base: `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps`

### _breadcrumbed (5)

- `Longmont Campaign/Campaign 1/Session Recaps/_breadcrumbed/Session 01 - Stonebridge and Glowkindle Rats.breadcrumbed.md`
- `Longmont Campaign/Campaign 1/Session Recaps/_breadcrumbed/Session 02 - Finishing the Job.breadcrumbed.md`
- `Longmont Campaign/Campaign 1/Session Recaps/_breadcrumbed/Session 03 - The Stone Bridge Flood.breadcrumbed.md`
- `Longmont Campaign/Campaign 1/Session Recaps/_breadcrumbed/Session 13 - The Meaty and the Dead.breadcrumbed.md`
- `Longmont Campaign/Campaign 1/Session Recaps/_breadcrumbed/Session 13 - The Meaty and the Dead.frontmatter_seed.md`

### _normalized (18)

- `Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 01 - Stonebridge and Glowkindle Rats.md`
- `Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 02 - Finishing the Job.md`
- `Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 03 - The Stone Bridge Flood.md`
- `Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 04 - The Grotesque Tree of Hempholm.md`
- `Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 05 - Underneath Hempholm.md`
- `Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 06 - The Road to Miraholm.md`
- `Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 07 - Passing Mirathorn Gates.md`
- `Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 08 - Captain Lysandra Quest.md`
- `Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 09 - Battle with the Meat Monsters.md`
- `Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 10 - Thraxx and the Last Warehouse.md`
- `Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 11 - Midnight Politics.md`
- `Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 12 - The Persistent Bugbear.md`
- `Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 13 - The Meaty and the Dead.md`
- `Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 14 - Into the Meat Grinder.md`
- `Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 15 - Cult Tunnels and Captain Idris.md`
- `Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 16 - Peacemaker Fiddle Meat Pile.md`
- `Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 17 - Festival Aftermath Loose Ends.md`
- `Longmont Campaign/Campaign 1/Session Recaps/_normalized/_archive/Session 02 - Stonebridge and Glowkindle Rats__20260706T023942Z.md`

### canonical (18)

- `Longmont Campaign/Campaign 1/Session Recaps/Session 1 - Recap 3-27-24.md`
- `Longmont Campaign/Campaign 1/Session Recaps/Session 10 - Battle with the Meat Monsters.md`
- `Longmont Campaign/Campaign 1/Session Recaps/Session 11 - Midnight Politics.md`
- `Longmont Campaign/Campaign 1/Session Recaps/Session 12 - One Persistent Bugbear or Sneaky Fucking Bugbear.md`
- `Longmont Campaign/Campaign 1/Session Recaps/Session 13 - The Meaty and the Dead.md`
- `Longmont Campaign/Campaign 1/Session Recaps/Session 14 - Into the Meat Grinder.md`
- `Longmont Campaign/Campaign 1/Session Recaps/Session 15 - Into the Meat Grinder.md`
- `Longmont Campaign/Campaign 1/Session Recaps/Session 16 - Recap.md`
- `Longmont Campaign/Campaign 1/Session Recaps/Session 17 - Recap.md`
- `Longmont Campaign/Campaign 1/Session Recaps/Session 2 - Finishing the Job.md`
- `Longmont Campaign/Campaign 1/Session Recaps/Session 2 - Stonebridge and Glowkindle Rats.md`
- `Longmont Campaign/Campaign 1/Session Recaps/Session 3 - The Stone Bridge Flood.md`
- `Longmont Campaign/Campaign 1/Session Recaps/Session 4 - The Grotesque Tree of Hempholm.md`
- `Longmont Campaign/Campaign 1/Session Recaps/Session 5 - Underneath Hempholm.md`
- `Longmont Campaign/Campaign 1/Session Recaps/Session 6 - The Road to Miraholm.md`
- `Longmont Campaign/Campaign 1/Session Recaps/Session 7 - Passing Mirathorn Gates.md`
- `Longmont Campaign/Campaign 1/Session Recaps/Session 8 - Captain Lysandra Quest.md`
- `Longmont Campaign/Campaign 1/Session Recaps/Session 9 - Battle with the Meat Monsters.md`

## Campaign 2 — Session Recaps

Base: `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps`

### _archive (7)

- `Longmont Campaign/Campaign 2/Session Recaps/_archive/README.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_archive/Session 23 - Mireward__20260629T050000Z.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_archive/Session 23 - Session-23 Mireward Gate Battle__20260629T050000Z.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_archive/Session 23 - Session-23__20260629T050000Z.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_archive/Session 23 - ingest__20260629T050000Z.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_archive/Session 23 - session-23-mireward__20260629T050000Z.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_archive/Session 24 - 4__20260629T050000Z.md`

### _breadcrumbed (18)

- `Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 20 - Gnat Swarm Marla Lysandra.breadcrumbed.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 20 - Gnat Swarm Marla Lysandra.frontmatter_seed.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 21 - Drake Nest Mirathorn Call.breadcrumbed.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 21 - Drake Nest Mirathorn Call.frontmatter_seed.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 22 - Mireward Road and Lysandro.breadcrumbed.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 22 - Mireward Road and Lysandro.frontmatter_seed.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 23 - Mireward Gate Battle.breadcrumbed.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 23 - Mireward Gate Battle.frontmatter_seed.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 24 - Mireward Gate Battle.breadcrumbed.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 24 - Mireward Gate Battle.frontmatter_seed.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/_archive/Session 23 - Mireward Gate Battle.breadcrumbed__20260622T004132Z.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/_archive/Session 23 - Mireward Gate Battle.frontmatter_seed__20260622T004132Z.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/_archive/Session 23 - Session-23 Mireward Gate Battle.breadcrumbed__20260629T040914Z.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/_archive/Session 23 - Session-23 Mireward Gate Battle.frontmatter_seed__20260629T040914Z.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/_archive/Session 23 - session-23-mireward.breadcrumbed__20260629T040904Z.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/_archive/Session 23 - session-23-mireward.frontmatter_seed__20260629T040904Z.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/_archive/Session 24 - 4.breadcrumbed__20260629T031226Z.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/_archive/Session 24 - 4.frontmatter_seed__20260629T031226Z.md`

### _normalized (32)

- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 01 - Let the Games Begin.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 02 - Steel Fangs Colosseum.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 03 - Storms Torbin and Shepherd.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 04 - Wolf Manor Mage Duel.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 05 - Lysandra Tea Guardhouse.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 06 - Barn Fleshborn Shepherd Wake.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 07 - Portals Tentacles Barn.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 08 - Dustwalker Cellar Barin Party.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 09 - Costume Contest Temple Aspitome.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 10 - Festival Crafting Elementals.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 11 - Coliseum Finals Tealeaf Tea.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 12 - Dustwalker Globe Duel.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 13 - Council Curfew Swamp March.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 14 - Supplies Wolf Crypt Letter.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 15 - Ride Out Mossford Ale.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 16 - Thinking Tree Sneaking Forest.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 17 - Migrating Forest and Thrin.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 18 - Wyvern Mother Fallen Spine.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 19 - Mossford Plans Stuart Inn.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 20 - Gnat Swarm Marla Lysandra.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 21 - Drake Nest Mirathorn Call.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - Mireward Gate Battle.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 24 - Mireward Gate Battle.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/_archive/Session 23 - Mireward Gate Battle__20260622T004132Z.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/_archive/Session 23 - Mireward Gate__20260629T125358Z.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/_archive/Session 23 - Mireward__20260622T004132Z.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/_archive/Session 23 - Session-23 Mireward Gate Battle__20260629T040914Z.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/_archive/Session 23 - Session-23__20260629T040904Z.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/_archive/Session 23 - ingest__20260622T000343Z.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/_archive/Session 23 - session-23-mireward__20260629T040904Z.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/_archive/Session 24 - 4__20260629T031226Z.md`

### canonical (25)

- `Longmont Campaign/Campaign 2/Session Recaps/Session 1 - Let the Games Begin.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 10 - Recap.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 11 - Recap.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 12 - Recap.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 13 - Recap.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 14 - Recap.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 15 - Recap.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 16 - Recap.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 17 - Migrating Forest and Thrin.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 18 - Recap.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 19 - Recap.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 2 - Recap.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 21 - Drake Nest Mirathorn Call.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 23 - Mireward Gate Battle.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 23 - Mireward Gate.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 24 - Mireward Gate Battle.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 3 - Recap.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 4 - Recap.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 5 - Recap.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 6 - Recap.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 7 - Recap.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 8 - Recap.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 9 - Recap.md`

## Longmont Campaign directories

### Campaign 1

- `Longmont Campaign/Campaign 1/Locations/` — 10 markdown files
- `Longmont Campaign/Campaign 1/NPCs/` — 40 markdown files
- `Longmont Campaign/Campaign 1/PCs/` — 18 markdown files
- `Longmont Campaign/Campaign 1/Session Recaps/` — 41 markdown files
- `Longmont Campaign/Campaign 1/_ingest_staging/` — 1 markdown files

### Campaign 2

- `Longmont Campaign/Campaign 2/Factions/` — 2 markdown files
- `Longmont Campaign/Campaign 2/NPCs/` — 17 markdown files
- `Longmont Campaign/Campaign 2/PCs/` — 25 markdown files
- `Longmont Campaign/Campaign 2/Plot Artifacts/` — 2 markdown files
- `Longmont Campaign/Campaign 2/Session Prep/` — 19 markdown files
- `Longmont Campaign/Campaign 2/Session Recaps/` — 82 markdown files
- `Longmont Campaign/Campaign 2/Statblocks/` — 4 markdown files
- `Longmont Campaign/Campaign 2/_ingest_staging/` — 5 markdown files

### Shared (outside Campaign 1/2 folders)

- `Longmont Campaign/Cards/` — 3 markdown files
- `Longmont Campaign/Character Docs/` — 1 markdown files
- `Longmont Campaign/Homebrew Items/` — 22 markdown files
- `Longmont Campaign/NPCs/` — 1 markdown files

## Worldbuilding — Elderwyld

Root: `corpus/eldyrwild-markdown/Elderwyld/`

### Top-level markdown (4)

- `Elderwyld/# _Campaign Summary_ Mirathorn Post-Cultist Battle_.md`
- `Elderwyld/Stonebridge and The Wizard Tower Brewing Co.md`
- `Elderwyld/The Stonebridge Flood.md`
- `Elderwyld/UnRefined Heading into the Flesh Kaiju.md`

### Directory tree (depth ≤ 3)

- `Elderwyld/Cities and Towns/` — 73 `.md` (recursive); subdirs: Edge of the World, Mirathorn, Mireward, Mossford, Stonebridge, Upriver River Route
- `Elderwyld/Cities and Towns/Edge of the World/` — 1 `.md` (recursive); subdirs: —
- `Elderwyld/Cities and Towns/Mirathorn/` — 25 `.md` (recursive); subdirs: City Council Building, NPCs, Sewers, Stormspire Academy, Wolf Manor
- `Elderwyld/Cities and Towns/Mireward/` — 21 `.md` (recursive); subdirs: NPCs
- `Elderwyld/Cities and Towns/Mossford/` — 22 `.md` (recursive); subdirs: Mossford_Location_Dossiers, NPCs
- `Elderwyld/Cities and Towns/Stonebridge/` — 2 `.md` (recursive); subdirs: NPCs
- `Elderwyld/Cities and Towns/Upriver River Route/` — 2 `.md` (recursive); subdirs: NPCs
- `Elderwyld/Events/` — 14 `.md` (recursive); subdirs: The Festival of Expansion, The Hearthbound Bake-Off
- `Elderwyld/Events/The Festival of Expansion/` — 8 `.md` (recursive); subdirs: Schedule and Event Details
- `Elderwyld/Events/The Hearthbound Bake-Off/` — 6 `.md` (recursive); subdirs: —
- `Elderwyld/Inns and Shops/` — 1 `.md` (recursive); subdirs: —
- `Elderwyld/Item Cards/` — 1 `.md` (recursive); subdirs: —
- `Elderwyld/Migrating Forest/` — 10 `.md` (recursive); subdirs: Branchbound
- `Elderwyld/Migrating Forest/Branchbound/` — 5 `.md` (recursive); subdirs: —
- `Elderwyld/Roads/` — 5 `.md` (recursive); subdirs: —
- `Elderwyld/Shephards Flock/` — 16 `.md` (recursive); subdirs: NPCs, Statblocks and Tokens
- `Elderwyld/Shephards Flock/NPCs/` — 3 `.md` (recursive); subdirs: dustwalker
- `Elderwyld/Shephards Flock/Statblocks and Tokens/` — 12 `.md` (recursive); subdirs: Tokens
- `Elderwyld/Wilderness/` — 4 `.md` (recursive); subdirs: —

## Related tooling

| Module | Path |
|--------|------|
| Session recap path helpers | `src/corpus/session_recap_paths.py` |
| C2 planning corpus manifest | `src/live_play/planning_corpus_manifest.py` |
| Batch corpus ingest | `tools/batch_ingest_corpus.py` |

## Re-anchor checklist (corpus scope)

1. Confirm you are reading from `corpus/eldyrwild-markdown/`, not unprocessed pipeline output.
2. For play facts, prefer canonical recaps or `_normalized` (ingest input), not `_breadcrumbed`.
3. For setting vocabulary, start at Elderwyld location hubs (`README.md` indexes under `Elderwyld/Cities and Towns/`).
4. Re-run `scripts/build_corpus_index.py` after adding sessions or major worldbuilding hubs.
