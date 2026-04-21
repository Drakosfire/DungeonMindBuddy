# Convention: PC hub package (README + timeline + dossier)

**Status:** Prescriptive for new or refactored PC hubs in `corpus/eldyrwild-markdown/`.
**Specialization of:** `Docs/CONVENTION-Corpus-Subject-Schemas.md` §3 (subject hub definition) and §4 (frontmatter contract).
**Worked example:** `Longmont Campaign/Campaign 2/PCs/caelynn/`

---

## 1. Goals

- Give the planner a **slim continuity hub** for each player character so it can answer "what has this PC done across recaps?" without crawling every session file.
- Keep PCs explicitly **player-owned**: the corpus carries continuity (timeline, dossier, loot logs), not the live character sheet, unless the player has handed mechanics over for GM use.
- Mirror the NPC hub shape so a session planner has **one mental model** for entity hubs across both NPCs and PCs.

---

## 2. Folder and slug

- **One folder per PC**, located at `<Campaign>/Campaign N/PCs/<slug>/` (campaign-only by default).
- Slug is lowercase + underscores, matching the NPC slug rule (`captain_lysandra_ironveil` style). Examples: `caelynn/`, `bonogo/`.
- **One `README.md` per hub folder** (never merge two PCs).
- **No setting-side PC hub** by default. PCs do not live under `Elderwyld/`. Exception: a retired PC who became a recurring NPC may earn a setting-side hub, in which case follow the NPC convention's two-hub cross-link rule (§6 of the meta-doc).

---

## 3. Minimum vs recommended files

| Artifact | Status | Notes |
|----------|--------|-------|
| `README.md` | **Required** | Hub index. Slim — pointers, read order, comms call-sign / disambiguators. |
| `{slug}_character_dossier.md` | **Required** at PC inception | Continuity prose: identity, comms, relationships, items/spells **as named in recaps**, arc hooks. A PC's continuity surface is not optional — they have an identity from session 0, often with backstory the player wants treated as canonical. **Not** a statblock. Frontmatter `subject_doc_kind: dossier`. |
| `timeline.md` | **Required** at PC inception | Same hybrid-rubric beat shape as NPC timelines: Session / Beat (1–3 lines, `**minor**` permitted) / Recap pointer. Inception rows cover backstory beats the player wants canonical (Session column = `Pre-campaign` or `Backstory`); append-only after that. Frontmatter `subject_doc_kind: timeline`. |
| `{slug}_statblock*.md` | **Optional** | Only when the player has explicitly handed a sheet over for GM use (e.g. shared character sheet, NPC-conversion plan). Otherwise `(none)` in the README priority table. The corpus writer denylist still applies. |
| `character_seed.md` | **Optional** (rare) | PC seeds are unusual; usually the dossier covers backstory. Include only when there is a clean pre-campaign concept worth carrying separately. |
| `loot_*.md`, `<slug>_*_log.md`, `<slug>_*_guidelines.md` | Optional | PC-specific aggregates (loot rolls, custom item allocations). Frontmatter `subject_doc_kind: notes_aggregate`. Bonogo's `loot_geomantic_drake_nest.md` is the prototype. |

---

## 4. README sections (required order)

The same four headings the NPC convention uses, with PC-specific framing.

1. **Title** — `<Display Name> — Campaign N (PC hub)`
2. **`## Read order`** (or `## Suggested reads (in order)` — both acceptable; `Read order` is the Caelynn-shape default for PCs)
   - Numbered list of full corpus-relative paths, each annotated with one line of why it matters.
   - Order: **dossier first** (continuity surface), **timeline second** (session index), notes-aggregates and sibling NPC hubs after.
3. **`## Session recaps (no pinned default)`**
   - Same rule as NPCs: the model uses the corpus tree for "latest"; if `timeline.md` names specific recaps for a beat, prefer those.
   - PCs that miss a session (or whose row is `**minor**` only) should still have a row; the dossier can carry an "appears in every Sessions 1–N" line so absences are explicit.
4. **`## Mechanical sheets`** (only when a player-shared statblock exists; otherwise omit the heading entirely)
   - When present: same priority table as NPCs. When absent: do not write `(none)` headings; just leave the section out so the README stays honest about what the corpus owns.

A short closing paragraph ("Related" / "Cross-references") may list sibling hubs (e.g. an NPC the PC is heavily entangled with) using full corpus-relative paths.

---

## 5. `timeline.md` (PC hub)

**Purpose:** A session-by-session pointer grid showing what this PC did, so the planner can pick which recap to open for a question like "when did Caelynn first meet Lysandra off-books?". Rows are one-line beats; the recap file owns the prose.

**Required frontmatter:**

```yaml
---
title: "<PC Name> — timeline (Campaign N highlights)"
document_class: reference
subject_class: pc
subject_doc_kind: timeline
canon_layer: campaign
campaign_id: <longmont-cN>
temporal_scope: campaign_stateful
session: null
origin_session: null
last_updated_session: <N>
source_class: ledger_or_dossier
---
```

**Required table columns:**

| Column | Content |
|--------|---------|
| Session | Session number or range (e.g. `7–8`). For pre-campaign / backstory rows, accept non-numeric values: `Pre-campaign` or `Backstory`. |
| Beat (1–3 lines) | What this PC did. Telegraphic OK. Prefix `**minor**` for low-signal rows so the planner can de-weight without skipping. |
| Recap / prep | **Literal filename** as played (e.g. `Session 6 - Recap.md`) or, when no recap exists, the prep doc that covers the bridge (e.g. `Session Prep/session_21_intro.md`). For backstory rows the cell may be `—` (no recap exists) or point at a backstory dossier section. |

**Maintenance:** A PC timeline is created at PC inception with at minimum (a) one row per pre-campaign backstory beat the player wants treated as canonical (`Session` column = `Pre-campaign` or `Backstory`), and (b) one row at the PC's first actual session marking introduction. Append on each new session after that. Update `last_updated_session` in frontmatter. Never rewrite a row already covered by an existing recap.

---

## 6. Dossier and statblock boundaries

- **PC dossier owns:** identity, comms call-sign(s), party role, relationships, recurring items / spells **as named in recaps**, arc hooks. **Disambiguators** belong here (e.g. "Not Karsemine — different PC").
- **PC dossier does NOT own:** AC, HP, spell-slot accounting, full spell list, feat choices. Those live on the **player's character sheet** at the table. Add a frontmatter `table_note` line that says so explicitly (the Caelynn dossier is the prototype).
- **PC statblock**, if present, follows NPC rules (`source of truth for mechanical numbers`) but is rare and should never be silently authored — only ingested when the player has handed it over.

---

## 7. Discovery hooks

- For PCs referenced obliquely in recaps ("the storm caster," "Danielle's character"), the dossier opening paragraph should carry the **stable disambiguator** (player name + role + display name) the same way the NPC convention recommends.
- Aliases (e.g. comms call-signs like "The Storm" for Caelynn) belong in the dossier under a `## Disambiguators` or `## Comms` heading so a search by call-sign lands on the right hub.

---

## 8. Workflow (when does a PC hub get created or extended?)

- **New PC at session 1:** create a slim README + dossier stub. Timeline waits until session 3 (after which append-not-regen kicks in).
- **Existing PC, after session N:** the `recap-write` skill emits the recap and a structured follow-up payload. If the payload's timeline-append candidates include this PC, append the row to `timeline.md` (manual today; future `recap-timeline-append` skill).
- **Player hands over a sheet:** add the statblock file under the PC hub. Do not paraphrase it into the dossier.

---

## 9. Checklist (new PC hub)

- [ ] Slug folder under `<Campaign>/Campaign N/PCs/<slug>/`.
- [ ] `README.md` with frontmatter (`subject_class: pc`, `subject_doc_kind: hub_index`) and the four sections in §4.
- [ ] Dossier file (`{slug}_character_dossier.md`) at hub creation; `subject_doc_kind: dossier`. Required regardless of appearance count.
- [ ] `timeline.md` at hub creation; `subject_doc_kind: timeline`; seeded with backstory rows (`Pre-campaign` / `Backstory`) and/or the PC's first session row; append-only afterward.
- [ ] No statblock unless the player has shared one explicitly.
- [ ] After corpus edits: fingerprint per `.cursor/rules/corpus-layout-conventions.mdc` if your eval pins `expected_fingerprint`.

---

## 10. Reference layout

```
Longmont Campaign/Campaign 2/PCs/caelynn/
  README.md                       # subject_class: pc, subject_doc_kind: hub_index
  caelynn_character_dossier.md    # subject_class: pc, subject_doc_kind: dossier
  timeline.md                     # subject_class: pc, subject_doc_kind: timeline

Longmont Campaign/Campaign 2/PCs/bonogo/
  README.md                       # slim hub — LEGACY shape (predates this convention)
  loot_geomantic_drake_nest.md    # subject_class: pc, subject_doc_kind: notes_aggregate
```

The Caelynn hub is the canonical full-shape example. The Bonogo hub is **legacy shape** (predates this convention) — kept here as the canonical "slim hub with notes-aggregate satellite" pattern, but **any new PC hub must include both dossier and timeline from inception**, not gated on appearance count.

---

## 11. Silent gap reminder (do not silently fix here)

`Longmont Campaign/Campaign 1/PCs/` does **not** exist on disk. The Campaign 1 PC hubs (Caelynn-C1, Bonogo-C1, etc.) have not been created. This convention does not authorize a subagent to create them; the parent's `Backlog.md` is the right place to capture the work item. If the lint reports `Campaign 1` PC absences, that is the expected signal — don't migrate as a side effect.
