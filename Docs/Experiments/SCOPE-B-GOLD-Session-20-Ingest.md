# Scope-B gold spec — Session 20 ingest

**Status:** frozen (decisions recorded April 2026 in [a073c164-9fc1-4c03-a888-2d71dd08bc22](a073c164-9fc1-4c03-a888-2d71dd08bc22)).
**Scope:** the **review-surface + unsure-queue layer** of the `recap-write` skill (`.cursor/skills/recap-write/SKILL.md`), evaluated against the Session 20 raw notes (`Session 20 Recap.txt`) and the campaign-2 corpus state at the time of this writing.
**Companion (Scope-A gold):** the recap file itself — `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md` (frozen byte-for-byte; the recap is graded by the simpler structural Scope-A benchmark).
**Companion (process notes):** `Docs/Plans/archive/2026-05-09/operational-notes/PROCESSING-NOTES-Session-20-Manual-Ingest.md`.

This spec is the **gold contract** a Scope-B benchmark grades against. A benchmark run is "passing" iff every §A–§F item below holds. Items in §G–§I are **findings** the run must surface, not artifacts it must produce.

---

## Conventions

- "Exact" = byte-for-byte after standard line-ending normalization.
- "Shape" = file exists at the given path, with the named frontmatter / sections / role; body content is graded by structural rules below, not byte-equal.
- "Stub" = file exists with the minimum viable shape (a single intro paragraph and a pointer); content scaffolded for human expansion.
- "Setting hub" = `Elderwyld/...` paths. "Campaign hub" = `Longmont Campaign/Campaign 2/...` paths.
- New folders implied by gold paths (e.g. `Mossford/NPCs/`, `Campaign 2/Locations/`) are part of the deliverable.

---

## §A — Frozen recap (already on disk)

| Item | Value |
|------|------|
| Path | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md` |
| Grading | **Exact** (byte-for-byte). |
| Source | `Session 20 Recap.txt` at repo root. |

Gold matches the file currently on disk: 8-field frontmatter (title `"Session 20 - Recap"`, `document_class: play`, `canon_layer: campaign`, `campaign_id: longmont-c2`, `temporal_scope: session_specific`, `session: 20`, `origin_session: 20`, `last_updated_session: 20`, `source_class: observed_session_recap`), `# Session 20 Recap` H1, then 11 paragraphs of GM prose verbatim with the duplicated paragraph from source line 10 removed.

---

## §B — Lysandra timeline append (writer-allowlisted today)

| Item | Value |
|------|------|
| Path | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/timeline.md` |
| Operation | append one row to the existing markdown table. |
| Grading | **Exact** row text. |

**Row (gold, exact):**

```markdown
| **20**  | **Mossford** is saved (forest turns east); party calls Mirathorn — Lysandra is **disoriented and shimmery-eyed** (cult-grade charm); rocky-talkie chain via **Sara** then directly to Lysandra; **Karesmine tracks** her to a half-unloaded wagon camp; she has drawn a **top-down blueprint of a tower** in the dirt — "where the voices are coming from" — and knows the location; **Caelynn's antidote tea** restores her; she remembers only voices in the dark and the smell of meat. **Tainted meat** reveal in the same camp implicates Mirathorn's supply chain. | `Session 20 - Recap.md` |
```

---

## §C — Marla Brambleback dual-hub (Mirathorn split: setting seed + campaign dossier)

### C.1 Setting hub (Mossford)

| Path | Role | Grading |
|------|------|---------|
| `Elderwyld/Cities and Towns/Mossford/NPCs/marla_brambleback/README.md` | Hub index per `Docs/CONVENTION-NPC-Hub-Package.md`. Suggested-reads list points first to `character_seed.md`, then to the C2 campaign dossier. | **Shape.** |
| `Elderwyld/Cities and Towns/Mossford/NPCs/marla_brambleback/character_seed.md` | **Pre–player-contact** framing only: who she is in Mossford before the party meets her. YAML frontmatter matches the Torbin seed pattern (`document_class: reference`, `canon_layer: world`, `source_class: seed_reference`). **No** ready-dialogue lists, **no** Session-20 “best use” prep sections. | **Exact** (byte-for-byte against the committed file on disk). |

**No statblock** in this folder yet.

**Provenance:** distilled from `Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md` (Marla section). If the prep doc is revised, update the seed and re-freeze this gold row.

### C.2 Campaign hub (Longmont C2)

| Path | Role | Grading |
|------|------|---------|
| `Longmont Campaign/Campaign 2/NPCs/marla_brambleback/README.md` | Campaign-hub index. First Suggested Read = the Mossford setting seed; second = `marla_brambleback_character_dossier.md`. | **Shape.** |
| `Longmont Campaign/Campaign 2/NPCs/marla_brambleback/marla_brambleback_character_dossier.md` | **Table-truth** dossier: what the table actually saw in S20, GM-runtime notes for next time. | **Shape** (see content rules below). |
| `Longmont Campaign/Campaign 2/NPCs/marla_brambleback/timeline.md` | Single S20 row (drafted below). | **Exact** row text. |

**Dossier content rules (graded as shape):**

- H1: `# Marla Brambleback — Campaign 2 (table)`.
- "What the table saw (Session 20)" section: slap attempt dodged by Bonogo, "smells like a circus animal" line, escalation to grappling Bonogo, defused by Caelynn's bracelet, Marla approached Caelynn afterward about "how she should deal with Bonogo" — left unresolved when party departed.
- "Open threads" section: Marla / Bonogo conflict unresolved; Marla wants accountability for Stuart-harassment narrative; she is in charge of Mossford workers and will be a power center on any party return.
- "GM voice notes" section: short pointer back to setting seed for voice/appearance; do **not** restate.
- **No** prep-doc-style "ready dialogue" lists; the prep doc stays canonical for that.

**Timeline row (gold, exact):**

```markdown
| **20**  | First on-camera appearance in Mossford. Confronts Bonogo over Stuart-harassment (slap dodged, escalates to grapple, defused by Caelynn's bracelet); revealed as **in charge of the Mossford workers**; ends the session approaching Caelynn about "how she should deal with Bonogo" — unresolved when the party departs. | `Session 20 - Recap.md` |
```

(Header row of the timeline matches the existing Lysandra/Torbin/Dustwalker timeline column shape: `| Session | <NPC> beat (short) | Recap file |`.)

---

## §D — Mossford NPC backfill (setting-hub-only)

Once `Mossford/NPCs/` exists (created by §C.1), four additional setting-hub-only NPC entries are part of S20 gold. **No campaign-hub layer for these four** — confirmed.

### D.1 Stacey Brambleback

| Path | Role | Grading |
|------|------|---------|
| `Elderwyld/Cities and Towns/Mossford/NPCs/stacey_brambleback/README.md` | Hub index. | Shape. |
| `Elderwyld/Cities and Towns/Mossford/NPCs/stacey_brambleback/character_seed.md` | Setting seed: bugbear girl ~11–12, daughter of Marla, sharp/silent/bossy/practical, organizing kid-scale survival behavior under crisis; includes explicit note that the **west-boundary / Lysandra** prep beat did **not** surface in Session 20 recap play. | **Exact** (byte-for-byte against the committed file on disk). |

### D.2 Stuart

| Path | Role | Grading |
|------|------|---------|
| `Elderwyld/Cities and Towns/Mossford/NPCs/stuart/README.md` | Hub index. | Shape. |
| `Elderwyld/Cities and Towns/Mossford/NPCs/stuart/character_seed.md` | Setting seed: shy halfling boy, eager to please, family texture deliberately loose (gran-raised); Stacey relationship and table-vibe blocks per prep. | **Exact** (byte-for-byte against the committed file on disk). |

Slug `stuart` (no surname) is the gold default; promoted to `stuart_<surname>` only if §E.3 unsure-queue resolves with a name.

### D.3 Mayor (stub)

| Path | Role | Grading |
|------|------|---------|
| `Elderwyld/Cities and Towns/Mossford/NPCs/mayor/README.md` | Hub index, stub. | Shape (stub). |
| `Elderwyld/Cities and Towns/Mossford/NPCs/mayor/character_seed.md` | One-paragraph stub: red dragonborn, town leader, knows the trench-vs-forest history, addressed the crowd in S18 about old town policy. **Marked as awaiting canonical name.** | Shape (stub). |

Slug `mayor` is the gold default until §E.2 unsure-queue resolves.

### D.4 Sheriff (stub)

| Path | Role | Grading |
|------|------|---------|
| `Elderwyld/Cities and Towns/Mossford/NPCs/sheriff/README.md` | Hub index, stub. | Shape (stub). |
| `Elderwyld/Cities and Towns/Mossford/NPCs/sheriff/character_seed.md` | One-paragraph stub: present alongside mayor in S18/S20 town-defense beats. **Marked as awaiting canonical name.** | Shape (stub). |

Slug `sheriff` is the gold default until §E.2 unsure-queue resolves.

---

## §E — Unsure queue (the new primitive)

The unsure queue is **distinct from the review surface**. Used **sparingly** (target: ≤ 4 items per session). Each item has:

- a **default** (what gets written if GM says "go ahead");
- a **question** (the exact shape the ingestion surfaces at end-of-run);
- **acceptable alternatives** (what answers the ingestion will accept).

**A benchmark grades the unsure queue by question shape, not by which alternative the GM eventually picks.** The default is the safe fallback; the question is the deliverable.

### E.1 Tower blueprint placement

- **Default if GM defers:** create `Longmont Campaign/Campaign 2/Locations/tower_of_voices.md` (creates new `Locations/` subfolder under C2). Stub frontmatter (`document_class: location`, `canon_layer: campaign`, `temporal_scope: enduring`, `session: 20`, `origin_session: 20`, `source_class: observed_session_recap`). Body: known facts only — drawn by charmed Lysandra in dirt, top-down tower blueprint, "where the voices are coming from", location known to Lysandra, party does not yet know location.
- **Question (gold, shape):** "The tower is the largest new plot artifact in Session 20. Default plan is to file it as a *Locations/* entry under Campaign 2 with placeholder slug `tower_of_voices.md`. Should it be promoted to the setting layer (`Elderwyld/...`), filed under a different ontology (artifact / faction / nameless-stone temple linkage), or held as recap-only?"
- **Acceptable alternatives:** setting-layer location, artifact-folder framing, recap-only (no separate file), GM-supplied in-world name (renames the file).

### E.2 Mayor + Sheriff names

- **Default if GM defers:** stub seeds with role-only slugs (`mayor/`, `sheriff/`) per §D.3 / §D.4.
- **Question (gold, shape):** "Mossford's mayor and sheriff have appeared in S18 and S20 without canonical names in the recap prose. Default is to file them as `mayor/` and `sheriff/` stubs in `Mossford/NPCs/`. Are there canonical names to use as slugs now (renames the folders), or hold off on creating stubs until they are named?"
- **Acceptable alternatives:** GM provides one or both names → slug becomes `<firstname>_<lastname>`; or GM declines stubs → no `mayor/` and/or `sheriff/` folder created.

### E.3 Stuart's surname

- **Default if GM defers:** slug `stuart` per §D.2.
- **Question (gold, shape):** "Stuart's prep doc deliberately leaves his family loose (gran-raised, parents absent / gone / seasonal). Slug `stuart` is the default. Establish a surname now (renames slug to `stuart_<surname>`), or leave the prep-doc looseness intact?"
- **Acceptable alternatives:** GM provides surname → rename slug; or GM defers → leave as `stuart/`.

---

## §F — Bidirectional prep ↔ recap pointers

Two appends; **outside** the current writer allowlist (see §H). For S20 gold, the contract is exact-string match; the implementation may be hand-edit or allowlist extension.

### F.1 Footer on the recap

| Path | Operation | Grading |
|------|-----------|---------|
| `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md` | Append at end-of-file (one trailing blank line, then this block). | **Exact text.** |

```markdown
> **Prep:** See `Session Prep/session_20_stacey_stuart_marla_reference.md`. Stuart, Stacey, and Marla Brambleback character notes; some planned beats diverged in play.
```

### F.2 Footer on the prep doc

| Path | Operation | Grading |
|------|-----------|---------|
| `Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md` | Append at end-of-file (one trailing blank line, then this block). | **Exact text.** |

```markdown
> **Played:** See `Session Recaps/Session 20 - Recap.md`. The Stacey-reveals-Lysandra-sighting clue did not fire (Bonogo went confrontational; Stacey ran home shaken). The west-stones sighting may still be canon for future use.
```

---

## §G — Backfill backlog (out of S20 gold; recorded as a finding)

A correctly-functioning ingestion run on Session 20 must **surface** these as findings (not produce them as artifacts). The benchmark grades that the finding text appears in the run's report, not that any files are created.

| NPC | First-appearance session | Expected setting-hub path (when backfilled) |
|-----|--------------------------|---------------------------------------------|
| Sara (Mirathorn operator) | S5 / S6 (rocky-talkie introduction) | `Elderwyld/Cities and Towns/Mirathorn/NPCs/sara/{README.md, character_seed.md}` |
| Frank (Mirathorn operator) | S18 (overheard with Lysandra) | `Elderwyld/Cities and Towns/Mirathorn/NPCs/frank/{README.md, character_seed.md}` |
| Professor Tealeaf | (earlier session — needs scan) | `Elderwyld/Cities and Towns/Mirathorn/NPCs/professor_tealeaf/{README.md, character_seed.md}` |

**Recommended backfill action (separate task, not S20 deliverable):** run the ingestion flow against Sessions 5, 6, and 18 (and any other recap that names unhubbed Mirathorn NPCs) so each NPC's first-appearance recap creates the setting-hub entry it should have created at the time.

---

## §H — Writer allowlist gaps S20 surfaces

A benchmark run must surface each of these as a finding. Until the allowlist extends, the affected paths require hand-edit (or the writer rejects with `path not in allowlist`).

| Path pattern | Why current writer rejects | Extension needed |
|--------------|----------------------------|------------------|
| `Elderwyld/Cities and Towns/<town>/NPCs/<slug>/README.md` | Setting-hub NPC creation not in `_CREATE_ALLOWED_RE`. | Add. (Used by §C.1, §D.) |
| `Elderwyld/Cities and Towns/<town>/NPCs/<slug>/character_seed.md` | Same. | Add. (Used by §C.1, §D.) |
| `<campaign>/NPCs/<slug>/<slug>_character_dossier.md` | Dossier-class file is in the **deny** list (Lesson 11) — but **only post-creation**; first-create is the gap. | Add **for create-only**; preserve immutability after first commit. (Used by §C.2.) |
| `<campaign>/NPCs/<slug>/README.md` (when slug is brand-new) | README append is allowlisted, but README **create** for a never-before-seen slug is ambiguous in the current rules. | Clarify create vs append for README; allow create when the slug folder is being introduced this session. (Used by §C.2, §D.) |
| `<campaign>/Locations/<slug>.md` | New `Locations/` subfolder pattern; no allowlist entry. | Add. (Used by §E.1 default.) |
| `<campaign>/Session Prep/*.md` (append, footer-pointer only) | Prep doc append not in allowlist. | Add for **footer-pointer append only** (no body edits). (Used by §F.2.) |

These do not block the **deliverable** (hand-edit covers everything); they block clean **two-phase commits** for §C–§F and are the natural next allowlist iteration.

---

## §I — Confirmed no-action

A benchmark run **must not** produce files for the following. Surfacing them is fine; writing files is gold-violating.

- Forest-east turn → recap prose only.
- Storm / shimmer-rain approach → recap prose only (carries to S21).
- Tainted meat reveal → covered by Lysandra timeline row (§B) + recap prose; no separate Mirathorn supply-chain file.
- PCs (Ephanna, Karesmine, Caelynn, Thrin, Bonogo, Stafl) → never get NPC hubs.
- "Players' Frank" / "the cult" / "the voices" — faction/group references → no faction file unless §E queue is extended.

---

## §J — Pass / fail summary

A Scope-B benchmark run on the Session 20 ingest **passes** iff all of the following hold:

1. §A recap is byte-equal to the existing on-disk file.
2. §B Lysandra row is appended exactly.
3. §C.1: `marla_brambleback/README.md` satisfies hub-index shape rules; `marla_brambleback/character_seed.md` is **byte-equal** to the committed canonical on disk. §C.2 (when executed): campaign-hub files at named paths with named shapes; **timeline row appended exactly**.
4. §D.1–D.2: `stacey_brambleback` and `stuart` **character_seed.md** files are **byte-equal** to the committed canonicals; each `README.md` satisfies hub-index shape. §D.3–D.4 mayor/sheriff stubs exist **only if** §E.2 resolves to “create stubs”; otherwise absent-by-design.
5. §E unsure queue contains exactly the three items, with question shape matching gold (alternative wording allowed; intent must be clear).
6. §F footer pointers appended verbatim to both files.
7. §G backfill backlog is surfaced as findings (Sara, Frank, Tealeaf).
8. §H allowlist gaps are surfaced as findings.
9. §I no-action set has no spurious files created.

Any mismatch is a fail. A run can be partially-passing; gold requires all 9.

---

## Author note

Frozen from a manual ingest pass; see `PROCESSING-NOTES-Session-20-Manual-Ingest.md` for the deterministic-vs-judgment bucket analysis that drove the design. The unsure-queue primitive (§E) was introduced during Section-6 walkthrough and is **new to this skill** — this spec is its first use; the SKILL.md needs a corresponding update once we have a second artifact to validate the shape against.

**Update (same pass):** §C.1 and §D.1–§D.2 `character_seed.md` files were authored on disk under `Elderwyld/Cities and Towns/Mossford/NPCs/`; Scope-B grading for those three bodies is now **exact** (byte-for-byte) per §J item 3–4.
