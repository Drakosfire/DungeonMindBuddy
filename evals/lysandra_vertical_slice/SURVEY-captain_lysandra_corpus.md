# Corpus survey: Captain Lysandra Ironveil (as-is)

**Scope:** `corpus/eldyrwild-markdown/` **markdown** (this survey lists `.md`); **PDF statblocks** are expected under `Longmont Campaign/NPCs/` (and similar) when present on disk. **Monorepo note:** if you clone `DungeonOverMind` as the git root, root `.gitignore` used to block all `*.pdf`; it now **allows** `DungeonMindBuddy/corpus/**/*.pdf` so those files can be committed. **Standalone `DungeonMindBuddy` repo:** Buddy’s own `.gitignore` never ignored PDFs.

**Canonical naming in corpus:** “Captain Lysandra Ironveil”, “Lysandra Ironveil”, “Lysandra”, dossier title “Lieutenant Lysandra Ironveil”. **Typo:** `Session 15 - Recap.md` uses “**Lysandara**” once; `gold/corpus_policy.json` includes that string in `aliases` for retrieval recall.

---

## 1. Executive findings

| Finding | Detail |
|--------|--------|
| **Dossier is narrative, not a statblock** | `captain_lysandra_ironveil_character_dossier.md` is rich **character reference** (rank, psychology, command style). It does **not** contain 5e mechanics (no AC, HP, Challenge, class levels, stat array). |
| **No dedicated `.md` statblock sheet located** | Repo-wide search for `Lysandra` co-occurring with typical statblock headers in her dossier: **no hits**. A machine-readable “current sheet” may live **outside** this corpus, in VTT exports, or must be **authored** for the vertical slice. |
| **Strong Campaign 2 trail** | Recaps and notes track promotion to **Captain**, deputy plot, migrating forest / Mossford march; good for **temporal grounding** and dialogue seeds, poor for **parseable level**. |
| **Campaign 1 anchor** | Session 8 quest recap is a named Lysandra arc; useful for early relationship context, not “latest” canon for C2. |

---

## 2. File inventory (every `.md` with `Lysandra` / `Ironveil`)

Paths are relative to `corpus/eldyrwild-markdown/`.

| Rel path | Kind | Role re: Lysandra |
|---------|------|-------------------|
| `Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_character_dossier.md` | NPC dossier | **Primary authored reference** (C2 hub); Lieutenant/Captain framing; YAML frontmatter (`campaign_id: longmont-c2`). Same folder: `README.md`, `timeline.md`. |
| `Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/README.md` | Hub | Index for C2 Lysandra package. |
| `Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/timeline.md` | Hub | C2 session-ordered stub (fill as you write). |
| `Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/README.md` | Hub | Mirathorn setting seed index. |
| `Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/character_seed.md` | Seed | Pre–player-contact stub; expand in setting voice. |
| `Longmont Campaign/Campaign 2/Campaign 2 Notes.md` | Campaign notes | Multiple **Captain Lysandra Ironveil** bullets; long narrative + scene dialogue. |
| `Longmont Campaign/Campaign 2/Elderwyld_Narrative_Ledger_Campaign2.md` | Ledger | Section on **Captain Lysandra Ironveil** (trauma & alliance). |
| `Longmont Campaign/Campaign 2/Elderwyld_Narrative_Ledger_2.md` | Ledger | Authority line: report to Captain Lysandra Ironveil. |
| `Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md` | Prep | Plot beats: “she saw Lysandra near the west boundary stones”. |
| `Longmont Campaign/Campaign 2/Session Recaps/Session 3 - Recap.md` | Recap | Search, first contact beats. |
| `Longmont Campaign/Campaign 2/Session Recaps/Session 5 - Recap.md` | Recap | Casual Lysandra, festival / guardhouse anxiety. |
| `Longmont Campaign/Campaign 2/Session Recaps/Session 6 - Recap.md` | Recap | Charm, barn, cult; heavy Lysandra presence. |
| `Longmont Campaign/Campaign 2/Session Recaps/Session 7 - Recap.md` | Recap | Combat, grapples, Thunder Step choice involving Lysandra. |
| `Longmont Campaign/Campaign 2/Session Recaps/Session 8 - Recap.md` | Recap | Post-combat coordination. |
| `Longmont Campaign/Campaign 2/Session Recaps/Session 13 - Recap.md` | Recap | **Assigned to lead the group**; breakdown then “takes charge”. |
| `Longmont Campaign/Campaign 2/Session Recaps/Session 14 - Recap.md` | Recap | “Led by Lysandra”; recovery scene. |
| `Longmont Campaign/Campaign 2/Session Recaps/Session 15 - Recap.md` | Recap | **New uniform and new rank**; in command speech; march to Mossford. |
| `Longmont Campaign/Campaign 2/Session Recaps/Session 16 - Recap.md` | Recap | Landmarks, forest pace; Lysandra uneasy about intel. |
| `Longmont Campaign/Campaign 2/Session Recaps/Session 18 - Recap.md` | Recap | **Rocky-talkie to Lysandra**; off-screen “boundary / breached / evacuate” beats. |
| `Longmont Campaign/Campaign 1/Session Recaps/Session 8 - Captain Lysandra Quest.md` | Recap | C1 quest title; cage fight / cult body horror; early alliance stress. |
| `Longmont Campaign/Campaign 1/Session Recaps/Session 6 - The Road to Miraholm.md` | Recap | Toll protest; **Captain Lysandra Ironveil** at gate. |
| `Longmont Campaign/Campaign 1/Longmont Campaign General Notes.md` | Meta | Points to C1 Session 8 recap path. |
| `Elderwyld/UnRefined Heading into the Flesh Kaiju.md` | World draft | Council color: Lysandra reports guard disappearances. |
| `Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_statblock_cr2.md` | Statblock (RulesIngestion Stage A) | **Machine-readable sheet** at **CR 2** (Mirathorn / setting-facing). `canonical_statblock_relpath` in `corpus_policy.json`. |
| *(optional)* `captain_lysandra_ironveil_statblock_cr2.pdf` | Statblock PDF | Pair with the `.md` in the Mirathorn hub or pipeline `out/`; not required in corpus for Buddy reads. |
| `Elderwyld/Cities and Towns/Mirathorn/NPCs/torbin_jove/torbin_jove_statblock.md` | Statblock (RulesIngestion Stage A) | Kid sheet; paired PDF `torbin_jove.pdf` in same hub. |
| `Longmont Campaign/Campaign 2/NPCs/torbin_jove/README.md` | Hub | C2 table index (dossier, timeline, care guidelines). |
| `Elderwyld/Cities and Towns/Mirathorn/NPCs/torbin_jove/README.md` | Hub | Mirathorn index + `character_seed.md`. |
| `Longmont Campaign/NPCs/Torbin Jove/README.md` | Redirect | Deprecated folder — points at slug hubs above. |
| `Elderwyld/Shephards Flock/NPCs/dustwalker/dustwalker_statblock.md` | Statblock + profile | **Dustwalker** (Sorin Haldrim); CR 3 sheet + interrogation prose. |
| `Elderwyld/Shephards Flock/NPCs/dustwalker/README.md` | Hub | Shepherd’s Flock index for this NPC. |
| `Longmont Campaign/Campaign 2/NPCs/dustwalker/README.md` | Hub | C2 table index (dossier, timeline). |
| `Elderwyld/Shephards Flock/Statblocks and Tokens/DustWalker.md` | Redirect | Points at `NPCs/dustwalker/dustwalker_statblock.md`. |

**Mention count (ripgrep `Lysandra` in `*.md` under this corpus root):** 19 files; per-file hit counts range from 1–11 (highest in `Campaign 2 Notes.md`). **Plus** Mirathorn statblock filename + body for mechanical hits.

---

## 3. Temporal “latest session” hint (Campaign 2)

Highest numbered recap in the inventory above that **names** Lysandra in body text is **Session 18** (radio contact + off-screen crisis). Sessions **17** and **19+** were not in the Lysandra hit list (no file or no name match in those recaps for this grep).  
**Policy implication:** `session_anchor_relpath` for “current moment” should be **explicitly chosen in gold** (e.g. Session 18), not inferred by glob alone.

---

## 4. Rank / title evolution (for later level-gates, not from statblock)

Corpus **text** supports:

- C1: Captain at the gate / quest giver.  
- C2 dossier: **Lieutenant** framing (emergency promotion, discomfort).  
- C2 Session 15+: **new rank**, command of the expedition.

Mechanical **character level** is **not** stated as an integer in the surveyed files. Any benchmark `pre_level` gold will be **benchmark-owned** until a statblock or structured sheet exists.

---

## 5. Gaps vs vertical-slice design doc

1. **Canonical statblock path:** undefined in corpus — `corpus_policy.json` marks `statblock_status` and defers `canonical_statblock_relpath` until authored.  
2. **Fingerprint:** tied to **all** `*.md` under the corpus root (`planner_cache.corpus_fingerprint`); any edit shifts gold `expected_fingerprint` — intentional drift detection.  
3. **Aliases for retrieval:** listed in `gold/corpus_policy.json` for Step 1+.

---

## 6. Refresh checklist when corpus changes

1. Re-run: `uv run python -c "from pathlib import Path; from src.agent.planner_cache import corpus_fingerprint; print(corpus_fingerprint(Path('corpus/eldyrwild-markdown')))"` from repo root.  
2. Update `evals/lysandra_vertical_slice/gold/step0_environment.json` → `expected_fingerprint`.  
3. Re-scan `rg Lysandra corpus/eldyrwild-markdown --glob '*.md'` and update this survey if new files appear.  
4. If statblock **PDFs** are added under the corpus tree (or converted to `.md`), re-run a repo-wide `*.pdf` inventory and update §2 + `gold/corpus_policy.json` (`canonical_statblock_relpath`, `statblock_status`).

---

## 7. Planner vs this survey

This file inventories **on-disk markdown**. In the running product, **which files get read** is normally chosen by the **session planner tool loop** (`read_corpus_file` + `tool_trace` in `src/agent/planner.py`). For benchmark design, see the design doc subsection **Planner alignment — one line**.

---

## 8. Related design

See `Docs/Plans/DESIGN-lysandra-statblock-vertical-slice-benchmark.md` for stepped gates G0–G8.

**Hub layout template (generalize beyond Lysandra):** `Docs/CONVENTION-NPC-Hub-Package.md`.
