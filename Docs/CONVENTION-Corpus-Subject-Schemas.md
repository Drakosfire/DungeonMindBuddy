# Convention: Corpus subject schemas (meta)

**Status:** Prescriptive for new or refactored hub folders in `corpus/eldyrwild-markdown/`. The NPC hub convention (`Docs/CONVENTION-NPC-Hub-Package.md`) is the prototype this meta-doc generalizes; PC and Location specializations live alongside it.
**Specializations:** `Docs/CONVENTION-PC-Hub.md`, `Docs/CONVENTION-NPC-Hub-Package.md`, `Docs/CONVENTION-Location-Hub.md`
**Cursor rule (short form):** `.cursor/rules/corpus-layout-conventions.mdc`
**Rationale and failure modes:** `Docs/Learnings/LEARNINGS-Corpus-Layout-For-LLM-Grounding.md`

---

## 1. Goals

Three goals frame every rule below; all per-class specializations should be readable as restatements of these for one subject family:

- **Easy navigation by humans and agents.** A person or planner model arriving at a folder knows what to open first because there is one cheap, well-shaped index file. The hub README is the agent's map; satellite files are the territory.
- **Easy update via append-not-regen.** State changes from a session land as **new** files (recaps) or **appended rows** (timeline), never by rewriting the bibles (dossier, seed, statblock). Conventions encode this so a writer skill or a human can stay disciplined under time pressure.
- **Easy retrieval by agents.** Frontmatter is **machine-checkable**: every hub document carries a closed-vocabulary tag set so deterministic corpus-search tools (planned, see `Backlog.md` `[READY]` engineering principle) can filter without LLM judgment. The 2026-04-21 Caelynn timeline calibration showed that hand-crawl reconstruction works because the corpus has structure; this convention is what keeps that structure recoverable as the corpus grows.

---

## 2. Subject hub — definition

A **subject hub** is exactly one folder under a typed parent directory whose immediate children belong to a single subject (one NPC, one PC, one location, etc.). The hub contains exactly one **`README.md`** (the **hub index**) plus zero or more **satellite files** that hang off it.

Vocabulary used throughout this convention and its specializations:

- **Subject** — the entity the hub is about (an NPC, a PC, a city, a sub-location, a faction). One subject per hub.
- **Hub folder** — the directory that groups all files for one subject.
- **Hub index** — the single `README.md` inside the hub folder. Always the agent's first-open file.
- **Satellite** — any other file that lives inside the hub folder and is owned by it (timeline, dossier, statblock, seed, notes aggregate, etc.).
- **Derived artifact** — a file produced by a tool (e.g. RulesIngestion statblock export) that lands as a satellite. It is still owned by the hub; the hub README must point at it.
- **Sibling hub** — another hub for the same subject in a different canonical layer (e.g. setting + campaign hubs for the same NPC).

A folder that contains files for multiple subjects (e.g. `NPCs/` itself, or `Mossford_Location_Dossiers/`) is **not** a hub; it is a **collection** and follows different rules (see §5 file-type taxonomy).

---

## 3. Frontmatter contract — closed vocabularies

Frontmatter at the top of every file is YAML between `---` delimiters. The fields below are the canonical authority; per-class specializations can mark some fields required-vs-optional, but cannot rename or replace them.

### 3.1 `document_class` — UNCHANGED

Existing closed vocabulary. **Do not add new values.** This convention does not modify how `document_class` is used in the corpus; it adds orthogonal fields instead (§3.2, §3.3).

| Value | Meaning |
|-------|---------|
| `play` | A record of what happened at the table. Session recaps. |
| `reference` | Author-curated continuity material the model reads to ground answers. Dossiers, timelines, hub READMEs, item cards. |
| `world` | World-bible / setting prose authored independent of any campaign. Gazetteers, location dossiers, faction primers, world events. |
| `planning` | Pre-session prep, brainstorming dumps, story-thread backlogs. Not yet committed to canon. |

Survey snapshot (April 2026): `world` 66, `reference` 47, `play` 38, `planning` 9. Total 160 frontmatter-bearing files.

### 3.2 `subject_class` — NEW (REQUIRED on every hub README and on every satellite under a hub)

Closed vocabulary. Identifies which subject family the document belongs to. The lint script (`scripts/lint_corpus_hubs.py`) treats this field as load-bearing.

| Value | Meaning | Hub examples |
|-------|---------|--------------|
| `npc` | Non-player character | `NPCs/captain_lysandra_ironveil/` |
| `pc` | Player character | `PCs/caelynn/` |
| `location` | A named place at any scale (city, sub-location, region) | `Cities and Towns/Mirathorn/` |
| `faction` | A bounded organization, cult, or fellowship | `Factions/Raucous_Saints_of_the_Rolling_Longhouse.md` (no hub yet) |
| `item` | A specific magic / homebrew item | `Homebrew Items/Item_ The Slinkstone.md` (no hub yet) |
| `event` | A bounded in-world event (festival, election, battle) | `Events/The Festival of Expansion/` (no hub yet) |
| `world` | Setting-wide primers not bound to a single subject | `Elderwyld/The Stonebridge Flood.md` |
| `null` | The file is not bound to any single subject (collection indexes, ledgers spanning many subjects) | `Campaign 2 Notes.md`, `Factions/README.md` |

`null` is permitted for documents that are intentionally cross-cutting; it is **not** an escape hatch for "I haven't decided yet." If you cannot pick a value, the file probably belongs in a different folder.

### 3.3 `subject_doc_kind` — NEW (REQUIRED on every doc inside a hub folder)

Closed vocabulary. Identifies the structural role of the document so deterministic search can filter ("show me every NPC's timeline" without an LLM call).

| Value | Meaning |
|-------|---------|
| `hub_index` | The `README.md` of a hub folder. Always exactly one per hub. |
| `timeline` | `timeline.md` — append-only chronology pointer table for a subject. |
| `dossier` | `*_character_dossier.md` — character voice / psychology / GM bullets for an NPC or PC. **Not** a statblock. |
| `statblock` | `*_statblock*.md` — mechanical 5e numbers (AC, HP, CR, attacks). Source of truth for combat. |
| `seed` | `character_seed.md` — short pre–player-contact concept, usually setting-side. |
| `recap` | `Session N - <slug>.md` under `Session Recaps/`. `document_class: play`. |
| `prep` | Files under `Session Prep/`. `document_class: planning`. |
| `world_primer` | Top-level setting prose that orients a region or city before any sub-hub (e.g. `The City of Mirathorn.md`, `Mossford_Map_Key_and_Gazetteer.md`). |
| `location_dossier` | One file describing a single sub-location inside a location hub (e.g. `Mossford_Location_Dossiers/Town Hall.md`). |
| `item_card` | One file describing a single magic / homebrew item. |
| `faction_brief` | One file describing a single faction. |
| `notes_aggregate` | Heterogeneous content that does not fit the above and lives inside (or alongside) a hub: loot logs, care guidelines, ledgers, brainstorming dumps. Use sparingly; prefer a more specific kind when one fits. |
| `null` | The file is not part of a hub and does not fit any structural kind above (rare; usually means the file belongs somewhere else). |

### 3.4 Existing fields (unchanged in this pass)

Per-class specializations document required-vs-optional. The list below is the canonical field set; this convention pass adds three new/promoted fields — `subject_class`, `subject_doc_kind`, and `table_note` — and otherwise leaves everything unchanged. Do not invent additional "core" fields beyond these without amending this doc.

| Field | Description | Typical values |
|-------|-------------|----------------|
| `title` | Display title for the document. | Free-form string. Optional but recommended on every file. |
| `canon_layer` | Which canon layer the file belongs to. | `world` (setting-side) or `campaign` (table-side). |
| `temporal_scope` | How time-bound the contents are. | `evergreen`, `campaign_stateful`, `session_specific`. |
| `session` | The session number this file primarily covers (if any). | Integer or `null`. |
| `origin_session` | The session number this file was first authored for. | Integer or `null`. |
| `last_updated_session` | The most recent session whose state is reflected. | Integer or `null`. |
| `source_class` | Provenance of the prose. | `authored_dossier`, `observed_session_recap`, `seed_reference`, `ledger_or_dossier`, `planning_document`, `faction_module`, `scene_module`, `process_log`, `thread_backlog`, `brainstorming_unrefined`, `other`. (Twelve values observed in April 2026.) |
| `campaign_id` | Which table this file is bound to, if any. | `longmont-c1`, `longmont-c2`, `null`. |
| `table_note` | **Optional** for all subject classes. Free-form one-line annotation surfacing a non-mechanical disambiguator the model should respect when reading the file — e.g. "this is continuity, not a statblock"; how to handle a player-facing epithet vs the canonical name; usage rules for a random table; provenance of an imported draft. Read by humans and the planner; not parsed by the lint. | Short prose string, ideally one sentence. Eleven files use it as of April 2026. |

Files predating this convention are valid as-is; they keep their current frontmatter and gain `subject_class` / `subject_doc_kind` only when they are next touched substantively. The lint reports stragglers; migration is not automatic.

---

## 4. File-type taxonomy

This is the authoritative table for "what goes where" — the direct response to the **hub scope creep** risk surfaced in the 2026-04-21 Caelynn calibration. If a file does not match a row here, prefer changing the file to fit (split, rename, or relocate) over inventing a new role.

| `subject_doc_kind` | Filename pattern | Typical `document_class` | Typical contents |
|--------------------|------------------|--------------------------|------------------|
| `hub_index` | `<hub>/README.md` | `reference` | Suggested-reads list, mechanical-priority table (when applicable), session-recaps note, cross-link to sibling hubs. **Not** prose about the subject. |
| `timeline` | `<hub>/timeline.md` | `reference` | One short header paragraph + a Session / Beat / Recap table. Append-only. **Pointers**, not recap prose. |
| `dossier` | `<hub>/{slug}_character_dossier.md` | `reference` | Voice, psychology, relationships, how to run scenes, GM bullets. **Never** the source of truth for AC/HP/CR. |
| `statblock` | `<hub>/{slug}_statblock*.md` | `world` (setting export) or `reference` (campaign override) | RulesIngestion export or authored sheet. **The** source of truth for mechanical numbers. Server-side denylist from writes. |
| `seed` | `<hub>/character_seed.md` | `reference` (setting hub) or `world` | Short pre–player-contact concept; expand over time. Server-side denylist from writes. |
| `recap` | `<campaign>/Session Recaps/Session N - <slug>.md` | `play` | What happened at the table. Two-phase commit on create. |
| `prep` | `<campaign>/Session Prep/session_<N>_<slug>.md` | `planning` | One per session; the `recap-write` resolver raises if more than one matches. |
| `world_primer` | Top-level location/region prose (`<location>/<Name>.md`, `<location>/<location>_Map_Key_and_Gazetteer.md`) | `world` | Orienting overview for a region before any sub-hub; not a single-room dossier. |
| `location_dossier` | `<location>/<Sub-location Collection>/<Name>.md` (flat) or `<location>/<Sub-location>/<Name>.md` | `world` | One sub-location described in detail (rooms, exits, NPCs that pin to it). |
| `item_card` | `Homebrew Items/Item_ <name>.md`, `Player Copies/Player Copy Item_ <name>.md` | `reference` | Stats, attunement, lore for a single item. |
| `faction_brief` | `Factions/<Faction_Name>.md` | `world` or `reference` | One faction module. |
| `notes_aggregate` | `<hub>/loot_*.md`, `<hub>/<slug>_care_guidelines.md`, top-level `Campaign N Notes.md` | `reference` or `planning` | Heterogeneous append-friendly material. |

**Rules of thumb.** If it is mechanical 5e numbers, that is a `statblock`, not a `dossier`. If it is voice/psychology/run-scenes, that is a `dossier`, not a `hub_index`. If the README starts having paragraphs about who the subject is, those paragraphs belong in the `dossier` and the README should shrink back to pointers. Hub indexes earn their cheapness by **not** carrying prose; the moment they do, the planner stops paying its own opening cost in tokens.

---

## 5. Hub lifecycle

Three states, two promotion gates. NEVER hard-delete a canonical hub.

### 5.1 `draft`

A hub that lives under `corpus/_drafts/` (preferred) or carries an explicit `draft_provenance` line in frontmatter (acceptable for in-place experiments). Drafts are excluded from normal corpus search and from the `document_class: world | reference` retrieval baseline. The Caelynn regenerated timelines under `corpus/_drafts/caelynn_timeline_REGENERATED_2026-04-21.md` are the prototype example.

### 5.2 `canonical`

A hub committed under `corpus/eldyrwild-markdown/...` with no `draft_provenance` and no `_drafts/` parent. The planner treats canonical files as authoritative.

**Promotion `draft → canonical`:** GM review. Move the file (`git mv`), add it to a hub README's suggested-reads, recompute the corpus fingerprint per the cursor rule, and update `expected_fingerprint` in any pinned eval gold.

### 5.3 `retired`

A hub that has been superseded but must not be forgotten. Move the entire hub folder (or single file) to a `_retired/` sibling directory with a one-line **forward pointer** stub left in place if external bookmarks still refer to it. The legacy `Longmont Campaign/NPCs/Torbin Jove/README.md` is the prototype: a single file pointing at the new hub locations.

**Promotion `canonical → retired`:** explicit forward pointer + a one-line reason in the stub. Never silent. Never `rm`.

---

## 6. Cross-link rules

When a subject exists in both a setting tree and a campaign tree (the Lysandra pattern), there are **two hubs**. Each hub README must:

1. Link to the sibling hub by its **full corpus-relative README path** (no abbreviations, no globs).
2. State which sheet is **authoritative from this hub's perspective** (e.g. "Mirathorn export `*_statblock_cr4.md` is the table-side default until a `*_statblock_c2_*` override exists in this folder").
3. Surface the cross-link in the hub README's body, not only in `Suggested reads`.

The full table-style spec for cross-links is `Docs/CONVENTION-NPC-Hub-Package.md` §4 (the four-section README contract). PCs that have a setting-side appearance (e.g. retired PC who became an NPC) follow the same rule. Locations inherit it for sub-locations that also appear in a campaign-side play log.

---

## 7. Specialization pointer

Every per-class specialization restates §1–§6 in concrete terms for one subject family. Read this meta-doc first, then the relevant specialization.

| Subject family | Specialization doc | Worked example |
|----------------|--------------------|----------------|
| NPC | `Docs/CONVENTION-NPC-Hub-Package.md` | `Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/` + `Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/` |
| PC | `Docs/CONVENTION-PC-Hub.md` | `Longmont Campaign/Campaign 2/PCs/caelynn/` |
| Location | `Docs/CONVENTION-Location-Hub.md` | `Elderwyld/Cities and Towns/Mirathorn/`, `Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/`, `Elderwyld/Migrating Forest/Branchbound/` |

---

## 8. NPC registry artifact (per campaign)

The **NPC registry** is the canonical "known NPCs in this campaign" lookup, distinct from the per-hub READMEs that describe individual NPCs. It exists because Stage C (NPC candidate identification) and Stage D (entity resolution) need a cheap, structured "here are the tracked NPCs" surface — re-deriving it from filesystem traversal on every run was wasteful and prone to drift.

- **Path:** `<campaign>/_npc_registry.json` — one file per campaign, colocated with the campaign folder. The leading underscore signals "machine-maintained metadata," matching the convention used elsewhere in this repo for `_archive/`-style names.
- **Schema:** `schemas/v0.1/npc_registry.schema.json` — array of records. Sibling to `event_record.schema.json`. Pydantic mirror at `src/contracts/npc_registry.py` exposes `NpcRegistryRecord` and `load_npc_registry()`.
- **Lint:** `uv run python scripts/lint_npc_registry.py` — schema validation + cross-ref check (each `slug` must match an actual folder under `hub_path` or `setting_hub_path`) + duplicate-slug check + null-hub-for-non-candidate check + `first_session ≤ last_session` check. Exit 0 clean, 1 with issues. Mirrors the output style of `scripts/lint_corpus_hubs.py`.
- **Status enum** (4 values, closed): `tracked` (has a hub README, GM-curated, regularly appears) · `background` (has a hub README but minor/setting figure) · `dormant` (was tracked, hasn't appeared in recent sessions; flagged not removed) · `candidate` (named in recaps but no hub yet; awaits GM curation). Only `candidate` may carry `hub_path: null`.
- **Distinct from `FactStore.entities`.** The `FactStore` `entities` table is per-run extraction provenance and has a different lifecycle. The registry is GM-curated campaign canon and survives across runs.

**Today's coverage.** Campaign 2 is seeded (9 NPCs: 5 Longmont-C2 hubs + 4 Mossford/Elderwyld hubs heavily played in C2). Campaign 1 has zero `NPCs/<slug>/README.md` hubs in the corpus today and is a separate cold-start problem (tracked in `Backlog.md`). New campaigns get a registry the moment they have one tracked NPC.

---

## 9. Out of scope (this pass)

Captured here so the boundary is unambiguous:

- **No Faction convention.** `Factions/` exists with one canonical entry; flag for follow-up after PC/Location stabilize.
- **No Event convention.** `Events/The Festival of Expansion/` and `Events/The Hearthbound Bake-Off/` are large nested structures that deserve their own pass.
- **No Item convention.** `Homebrew Items/` has 21 files in mixed shapes (`Item_*.md`, `Player Copies/`, `Trinkets/`); treat as a future spec.
- **No JSON-Schema or Pydantic file-body validation.** The lint script reads frontmatter only and reports state. Body shape is enforced by prose conventions and human review, not by runtime validators.
- **No CI lint wiring.** `scripts/lint_corpus_hubs.py` is informational by default. `--strict` exits non-zero only when explicitly invoked.
- **No corpus refactor.** The existing NPC convention's body is unchanged (one-line specialization pointer added, nothing else). Existing files keep their current frontmatter; the lint reports stragglers but does not migrate them.
- **No Campaign-1 PC-tree creation.** `Longmont Campaign/Campaign 1/PCs/` does not exist on disk; backlog tracks creating it.

Future work pointers belong in `Backlog.md` (parent owns).
