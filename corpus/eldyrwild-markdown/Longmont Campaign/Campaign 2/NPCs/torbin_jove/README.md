# Torbin Jove — Campaign 2 (table)

## Suggested reads (in order)

Use `read_corpus_file` with these paths **after** this README (corpus root = `eldyrwild-markdown/`):

1. `Longmont Campaign/Campaign 2/NPCs/torbin_jove/torbin_jove_character_dossier.md` — **primary character reference** (who he is at this table, continuity spine, disambiguators).
2. `Longmont Campaign/Campaign 2/NPCs/torbin_jove/timeline.md` — C1 + C2 recap pointers for Torbin-specific beats.
3. `Longmont Campaign/Campaign 2/NPCs/torbin_jove/torbin_jove_care_guidelines.md` — food, rest, morale, mishap rolls for running him in scenes.
4. `Elderwyld/Cities and Towns/Mirathorn/NPCs/torbin_jove/torbin_jove_statblock.md` — **CR 1/8** kid sheet (mechanical truth for AC/HP/CR).
5. `Elderwyld/Cities and Towns/Mirathorn/NPCs/torbin_jove/README.md` — Mirathorn hub (world-seed + same statblock pointer).

## Session recaps (no pinned default)

Do **not** assume a single “latest” recap for Torbin: his arc spans **Campaign 1** and **Campaign 2**. Under each campaign’s `Session Recaps/` folder, use the **corpus tree** to list `.md` recaps. For **latest played events in C2**, prefer the recap whose filename contains the **largest session number** in that folder. If `timeline.md` names specific recaps for a beat, prefer those.

## Mechanical sheets (priority — highest first)

Use this order whenever the ask touches **CR, HP, AC, attacks, saves**, or “what statblock is current?”.

| Priority | Path (corpus root = `eldyrwild-markdown/`) | Role |
|----------|--------------------------------------------|------|
| **1 — table override (if present)** | In **this folder**: any `.md` whose name starts with `torbin_jove_statblock_c2_` | **Most current for Campaign 2** when such a file exists; use the exact path from the corpus tree (no globs in `read_corpus_file`). If several exist, prefer the **highest session number** in the filename. |
| **2 — Mirathorn export** | `Elderwyld/Cities and Towns/Mirathorn/NPCs/torbin_jove/torbin_jove_statblock.md` | **Canonical kid sheet** (RulesIngestion from PDF) when no C2-only override exists. |

**Legacy path:** `Longmont Campaign/NPCs/Torbin Jove/README.md` only redirects here — do not treat it as a mechanical source.

**Campaign-local package:** dossier, care guidelines, timeline, and any future C2-only statblock exports.

| File | Role |
|------|------|
| `torbin_jove_character_dossier.md` | Voice, continuity, GM hooks. |
| `torbin_jove_care_guidelines.md` | Table-use care mechanics. |
| `timeline.md` | Recap routing for C1 + C2. |

**Setting / Mirathorn slice:** `character_seed.md` and statblock live under `Elderwyld/Cities and Towns/Mirathorn/NPCs/torbin_jove/`.
