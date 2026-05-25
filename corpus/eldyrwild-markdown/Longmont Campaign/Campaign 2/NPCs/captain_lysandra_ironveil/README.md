---
title: "Captain Lysandra Ironveil — Campaign 2"
document_class: reference
canon_layer: campaign
campaign_id: longmont-c2
temporal_scope: campaign_stateful
session: null
origin_session: null
last_updated_session: null
source_class: ledger_or_dossier
subject_class: npc
subject_doc_kind: hub_index
---

# Captain Lysandra Ironveil — Campaign 2 (table)

## Suggested reads (in order)

Use `read_corpus_file` with these paths **after** this README (corpus root = `eldyrwild-markdown/`):

1. `Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_character_dossier.md` — primary **character reference** (psychology, command style, GM-sourced ledger bullets).
2. `Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/lysandra_ironveil_mireward_history.md` — **Mireward upbringing, Ironveil family soap, gate/homecoming beats** (read when she is on Reach soil).
3. `Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/timeline.md` — C2 beats + which recap to open next.
3. `Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_statblock_cr4.md` — **CR 4** leveled mechanical sheet (Mirathorn export; current default for combat numbers).
4. `Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_statblock_cr2.md` — **CR 2** baseline sheet (earlier tier).
5. `Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/README.md` — Mirathorn hub (seed + statblock pointers); optional if you already opened those files.

## Session recaps (no pinned default)

Do **not** assume a fixed recap file (no default “Session N” in this README). Under `Longmont Campaign/Campaign 2/Session Recaps/`, use the **corpus tree** to list `.md` recaps. For **latest played events**, open the recap whose filename contains the **largest session number**. If `timeline.md` names specific recaps for a beat, prefer those. Open more than one recap when the question spans multiple sessions.

## Mechanical sheets (priority — highest first)

Use this order whenever the ask touches **CR, HP, AC, attacks, saves**, or “which statblock is current for this table?”.

| Priority | Path (corpus root = `eldyrwild-markdown/`) | Role |
|----------|--------------------------------------------|------|
| **1 — table override (if present)** | In **this folder**: any `.md` whose name starts with `captain_lysandra_ironveil_statblock_c2_` | **Most current for Campaign 2** when such a file exists. Use the exact path from the corpus tree (no globs in `read_corpus_file`). If several exist, prefer the **highest session number** in the filename. |
| **2 — Mirathorn leveled export** | `Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_statblock_cr4.md` | **CR 4** current mechanical default from the setting hub when no C2-only override exists. |
| **3 — Mirathorn baseline** | `Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_statblock_cr2.md` | **CR 2** earlier export — comparison or historical runs. |
| **4 — archive / draft** | Other `*_statblock_*.md` under either hub | Older drafts — only when the user asks for comparison or history. |

Avoid opening `Longmont Campaign/Campaign 2/Campaign 2 Notes.md` unless you need **non–Lysandra** campaign-wide threads; Lysandra-specific prose lives in this folder and in recaps.

**Campaign-local package:** continuity at the table, dossier, and any C2-specific mechanical exports.

| File | Role |
|------|------|
| `captain_lysandra_ironveil_character_dossier.md` | Character reference (voice, psychology, how to run her in scenes). |
| `lysandra_ironveil_mireward_history.md` | Mireward roots, Ironveil family cast, soapy timeline, gate/homecoming. |
| `timeline.md` | Session-ordered beats for **this** campaign (curated from recaps + historical `Campaign 2 Notes.md` pulls). |

**Setting / pre-contact:** Mirathorn seed and the statblock exports (**CR 4** current, **CR 2** baseline) live under  
`Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/`.

**Level-up statblocks** for C2 only: add here with names like `captain_lysandra_ironveil_statblock_c2_post_sessNN.md` when they exist; they automatically become **priority 1** for this table per the table above.
