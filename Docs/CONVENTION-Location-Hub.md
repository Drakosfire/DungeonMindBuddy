# Convention: Location hub package (README + sub-locations + dossiers)

**Status:** Prescriptive for new or refactored Location hubs in `corpus/eldyrwild-markdown/`.
**Specialization of:** `Docs/CONVENTION-Corpus-Subject-Schemas.md` §3 (subject hub definition) and §4 (frontmatter contract).
**Worked examples (three shapes):**
- Top-level setting hub: `Elderwyld/Cities and Towns/Mirathorn/`
- Sub-location dossier collection: `Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/`
- Named-region directory: `Elderwyld/Migrating Forest/Branchbound/`

---

## 1. Goals

- Give the planner a **map-shaped** entry point for any place a scene might land in: cities, sub-locations, regions.
- Allow nested locations (a city contains sub-locations, sub-locations contain rooms) **without** flattening every level into one folder.
- Carry **NPC affiliation** at the location level so a question like "who runs the Mossford Watch Tower?" can be answered by opening the location hub and following links.

---

## 2. Three shapes (do not collapse)

Locations in this corpus today come in **three structural shapes**. The convention covers all three rather than forcing a single mold; each shape solves a different problem and forcing one onto another loses information.

### 2.1 Top-level setting hub (`location_hub` shape)

**Pattern:** A directory under a typed parent (e.g. `Cities and Towns/Mirathorn/`) that contains:
- A **top-level orienting doc** (`<Location>_Map_Key_and_Gazetteer.md` or `The City of <Name>.md`) with `subject_doc_kind: world_primer`.
- One or more **child folders** for sub-locations (`City Council Building/`, `Sewers/`, `Stormspire Academy/`) and `NPCs/` (which itself follows the NPC convention).

**Hub index:** Today, top-level setting hubs do **not** carry a `README.md`. The world primer doc serves as the orienting file. **Going forward, new top-level location hubs MUST add a `README.md`** with `subject_class: location` + `subject_doc_kind: hub_index` that points at the world primer, the sub-location collection, and the `NPCs/` subtree. Existing locations (Mirathorn, Mossford) gain READMEs as part of their next substantive edit; the lint reports them as ISSUE rather than blocking.

### 2.2 Sub-location dossier collection (flat `location_dossiers` shape)

**Pattern:** A flat folder named `<Location>_Location_Dossiers/` containing one `.md` file per sub-location, no per-sub-location subfolder. Mossford is the prototype:

```text
Mossford/Mossford_Location_Dossiers/
  Town Hall.md          # subject_doc_kind: location_dossier
  Watch Tower.md
  Mossford Inn.md
  ...
```

**Hub index:** A `README.md` is **recommended** but optional in this shape; the parent location's hub index (§2.1) should already point here. When present, the dossier-collection README describes the collection's scope and lists the dossiers with a one-line summary each (Roads/README.md is the prototype shape).

**When to use this shape:** sub-locations are small enough to live in a single file each, and they don't need their own NPC sub-tree.

### 2.3 Named-region directory (heterogeneous `region_hub` shape)

**Pattern:** A directory under a region (`Migrating Forest/Branchbound/`) containing heterogeneous content — culture pack, encounter tables, NPCs that live there, location dossiers. There is no clean "city → sub-location" hierarchy because the region itself is the subject.

**Hub index:** A `README.md` is **required** for this shape going forward, with `subject_class: location` + `subject_doc_kind: hub_index`. The README organizes the heterogeneous contents into clear groups (region overview, encounters, NPCs, sub-areas).

### 2.4 Nested region hubs

A region hub MAY contain child region hubs. The prototype is `Elderwyld/Migrating Forest/` (parent region hub) with `Branchbound/` as a child region hub inside it. The lint correctly reports both as `location_region` candidates today; this is intended behavior, not a duplicate-detection bug.

**Contract for nested hubs:**

- The **parent acts as the index.** Its README lists and links to each child region hub in §5 (Sub-locations), with a one-line summary per child. The parent's region-level material (encounters that span the whole region, gazetteer-like prose, parent-region NPCs) lives directly under the parent hub.
- The **child is the leaf.** Its README is the operational hub for that named region's content (culture pack, encounters, anchor NPCs, sub-locations).
- **Both must satisfy the standard hub-README requirements** (frontmatter with `subject_class: location` + `subject_doc_kind: hub_index`, plus the four sections in §5).

**Rule of thumb — when to nest vs promote:**

- Don't create a parent region hub purely to wrap a single child. If the only resident is one named region, promote that region to its own top-level hub and skip the wrapper.
- Nest only when there are **≥2 child region hubs** (the parent earns its keep as an index) **OR** the parent has its own region-level material that doesn't fit cleanly inside any child (the parent earns its keep as a peer of its children).

---

## 3. Closed-vocabulary choice (defended)

The meta-doc (`§3.3`) keeps `subject_doc_kind` deliberately small. Rather than introduce three new values (`location_hub_index`, `region_hub_index`, `sub_location_dossier`) we reuse:

- `hub_index` — the README of any location hub, regardless of shape (top-level, dossier collection, or region).
- `world_primer` — the top-level orienting doc inside a setting hub (`<Location>_Map_Key_and_Gazetteer.md`, `The City of <Name>.md`).
- `location_dossier` — one file describing one sub-location.
- `notes_aggregate` — heterogeneous in-region material (culture packs, indirect-help encounter sheets, "what the wolf knows" notes).

`subject_class: location` is the same value for all three shapes; the structural difference is encoded in the directory layout, not in the frontmatter. This keeps deterministic search ("show me every location dossier") simple at the cost of the lint needing path-pattern judgment to decide which shape a hub follows. That trade is intentional.

---

## 4. When does a place warrant its own hub?

Suggested threshold (use judgment; this is a heuristic, not a gate):

- **Standalone hub** (top-level or region shape) when the place has **≥ 3 sub-locations** *or* **≥ 2 NPCs** that pin to it *or* a top-level orienting doc longer than ~300 lines.
- **`location_dossier` inside a parent collection** when the place is one room / one shop / one civic building with no sub-areas of its own.
- **No hub** when the place is mentioned only in passing across recaps; the recap text owns it. Promote to a `location_dossier` once it shows up in 3+ recaps.

Do not pre-emptively split. A flat dossier file under `Mossford_Location_Dossiers/` is cheaper to maintain than a near-empty subfolder.

---

## 5. README sections (when a Location hub README exists)

Same four-section spirit as NPC and PC hubs, with location framing.

1. **Title** — `<Location Display Name> — <Region | World> (location hub)`
2. **`## Suggested reads (in order)`**
   - Numbered list, full corpus-relative paths.
   - Order: world primer first (the gazetteer / top-level overview), then the sub-location collection or named sub-locations of highest play relevance, then the NPCs subtree.
3. **`## Sub-locations`**
   - Markdown table or bullet list. Columns: **Name** | **Path** | **One-line summary** | **Anchor NPC(s)** (with full corpus-relative path to NPC hub README, if any).
   - For the **dossier-collection shape (§2.2)**, this section *is* the index; list every dossier.
4. **`## NPCs anchored here`**
   - Bullet list or table linking each NPC hub README that names this location as primary.
   - For NPCs that span multiple locations, list the NPC under the location they are most strongly associated with; cross-link from secondary locations.
   - **Evidence boundary:** this section is an affiliation/navigation index only. It may help a planner decide which NPC hub to open next, but it does not make the location hub a source of NPC continuity evidence. NPC continuity, relationship state, motivation, and behavior must be read from the linked NPC hub, timeline, dossier, or observed play recap.

A **Cross-references** section may follow if the location is connected to others by road, river, sewer, etc.

### 5.1 Name, slug, and alias handling

Use the folder name as the stable filesystem slug: lowercase, underscores, and one subject per folder. The display title may preserve table spelling, punctuation, or typography.

When an existing world/prep source and an observed campaign recap use different spellings for the same place — for example `Stonebridge` in older setting material versus `Stone Bridge` in a campaign recap — do not silently create two canon entities. Pick the hub slug from the authoritative layer being created, preserve known spelling variants as aliases/retrieval keywords, and add a note explaining that the variants are aliases unless a later canon decision deliberately splits them.

Do not add new core frontmatter fields for aliases unless `Docs/CONVENTION-Corpus-Subject-Schemas.md` is amended first; the frontmatter vocabulary is closed. Use body notes and full corpus-relative paths until an alias field is formally introduced.

---

## 6. Frontmatter requirements

For a location hub README:

```yaml
---
title: "<Location Name> — location hub"
document_class: reference        # hub indexes are reference; world_primer files use document_class: world
subject_class: location
subject_doc_kind: hub_index
canon_layer: world               # campaign for table-only locations (rare)
campaign_id: null                # set to longmont-cN only when the location exists only at one table
temporal_scope: evergreen
session: null
origin_session: null
last_updated_session: null
source_class: seed_reference
---
```

For a `location_dossier`:

```yaml
---
title: "<Sub-location Name>"
document_class: world
subject_class: location
subject_doc_kind: location_dossier
canon_layer: world
campaign_id: null
temporal_scope: evergreen
session: null
origin_session: null
last_updated_session: null
source_class: seed_reference
---
```

For a `world_primer` (top-level orienting doc inside a setting hub): same as `location_dossier` but with `subject_doc_kind: world_primer`.

The lint script does **not** require frontmatter on `location_dossier` files yet (the existing Mossford dossiers already have it; the cross-validation is on hub READMEs). When a dossier is touched substantively, add `subject_class` + `subject_doc_kind` then.

---

## 7. NPCs inside a location

Setting-side NPCs that live in a location follow the **NPC convention** (`Docs/CONVENTION-NPC-Hub-Package.md`) and live under `<Location>/NPCs/<slug>/`. The location hub README §5.4 surfaces them by full path; it does **not** duplicate any NPC content. The NPC hub remains the source of truth for that NPC.

When a campaign-side NPC is bound to a setting-side location (the Lysandra pattern), the campaign NPC hub cross-links to the location's setting-side NPC hub, not directly to the location. The chain is **Location hub → Setting NPC hub → Campaign NPC hub**.

For retrieval evaluation, lane assignment, and gold matching, a location hub may satisfy location/worldbuilding context only. It must not satisfy NPC-continuity requirements merely because it links or names an NPC. NPC-continuity requirements must be satisfied by `subject_class: npc` artifacts or observed play records admitted into the NPC/character continuity lane.

---

## 8. Workflow (when does a Location hub get created or extended?)

- **New named place referenced in 3+ recaps:** add a `location_dossier` under the appropriate parent collection (or create the collection if it doesn't exist).
- **Existing location grows a 3rd sub-area or 2nd anchor NPC:** promote it from a single dossier to a hub (§2.1 or §2.3). Move the existing dossier text into the hub's `world_primer` doc; create the README; link sub-areas.
- **Existing top-level setting hub gains a README:** during any substantive edit pass; lint reports as ISSUE until done.

---

## 9. Checklist (new Location hub)

- [ ] Choose the shape (§2.1, §2.2, or §2.3) based on actual sub-area / NPC count.
- [ ] Create or rename the hub folder.
- [ ] For shapes §2.1 and §2.3: write a `README.md` with frontmatter (`subject_class: location`, `subject_doc_kind: hub_index`) and the four sections in §5.
- [ ] For shape §2.1: ensure the world primer file exists and carries `subject_doc_kind: world_primer`.
- [ ] For shape §2.2: dossier files carry `subject_doc_kind: location_dossier`.
- [ ] Cross-link any setting-side NPCs anchored here.
- [ ] Confirm any `NPCs anchored here` section is navigational only and does not duplicate NPC continuity content.
- [ ] Record known spelling variants in body notes/retrieval keywords without creating duplicate canon entities.
- [ ] After corpus edits: fingerprint per `.cursor/rules/corpus-layout-conventions.mdc`.