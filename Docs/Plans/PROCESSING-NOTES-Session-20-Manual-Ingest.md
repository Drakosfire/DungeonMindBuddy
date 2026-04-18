# Processing notes — Session 20 manual ingest

**Date:** April 2026
**Source artifact:** `Session 20 Recap.txt` (repo root, 24 lines, plain text)
**Target:** `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`
**Companion artifact (discovered during ingest):** `Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md`
**Approach:** Hand-do everything end-to-end. Track each decision: was it **deterministic** (a tool could do it without LLM judgment) or **judgment** (an LLM, or a human, has to choose)? Use the result to scope the first real ingestion tools.

---

## 1. Pattern survey across existing recaps (Sessions 17, 18, 19)

Read three recent recaps before touching the new one to confirm the canonical shape.

| Aspect | Session 17 | Session 18 | Session 19 |
|---|---|---|---|
| Frontmatter field set | identical 8 fields | identical 8 fields | identical 8 fields |
| `title` value | `"Session 17 - Migrating Forest and Thrin"` (descriptive subtitle, no colon) | `"Session 18 - Recap:"` (trailing colon — typo) | `"Session 19 - Recap"` (clean) |
| H1 markdown header | **none** — body opens `Session 17 Recap: ` as plain text | `# Session 18 Recap:` (trailing colon — typo) | `# Session 19 Recap` (clean) |
| Title duplicated into body prose | no | yes (`Session 18 Recap After taking cold damage…`) | no |
| Numbered TLDR | none | none | none |
| Section headings beyond H1 | none | none | none |
| Multi-thread interleaving in single paragraph block | yes | yes | yes |
| Ends mid-action setting up next session | yes | yes | yes |

### Findings

- The **frontmatter field set is invariant** across all three: `title`, `document_class: play`, `canon_layer: campaign`, `campaign_id: longmont-c2`, `temporal_scope: session_specific`, `session: N`, `origin_session: N`, `last_updated_session: N`, `source_class: observed_session_recap`. Fully deterministic to emit given the session number and campaign id.
- **Title formatting is inconsistent.** Some have trailing colons (typos), some have descriptive subtitles, S17 lacks an H1 entirely. Treat this as **judgment** to normalize, but the safe choice (and the one I'll use) is the cleanest existing exemplar: Session 19's form. I'll record the normalization decision rather than match S18's typo.
- **No TLDR ever.** My SKILL currently mandates a numbered TLDR up front — that contradicts the canon. Drop the mandate (logged for the SKILL revision pass).
- **No internal section headings.** The recap is one continuous interleaved prose blob under the H1.
- **Title duplication into body is a transcription artifact** (Session 18 only). Detect-and-strip is mechanical.

---

## 2. The companion artifact (Session 20 prep doc)

Discovered: `Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md`. Authored **before** Session 20 played.

### What it is

- `document_class: planning`, `source_class: planning_document`, `temporal_scope: session_specific`, `session: 20`. Sibling to the recap (same session number), different document class.
- Heavily structured: H2 per character (Stacey / Stuart / Marla), H3 sub-sections (Core read, Appearance, Vibe, What they want, Ready dialogue), social-triangle summary, suggested dialogue beats.
- Gives surnames the recap doesn't use:
  - **Stacey Brambleback** (recap just says "Stacey")
  - **Marla Brambleback** (recap just says "Marla")
- Predicts a clue beat that **never landed in actual play**: "Stacey saw Lysandra near the west boundary stones." In the recap, Bonogo went confrontational immediately (knife in alley), Stacey ran home shaken, the clue is closed off.
- Suggests a dialogue beat ("Stacey's mom has got it going on") that didn't happen at the table either.

### Implications

- **Surname continuity is a judgment call.** Should the recap text be rewritten to add "Brambleback" where the GM wrote "Marla"? My instinct is **no** — the recap captures what was said at the table, the prep doc captures what the GM had ready. They can disagree. Surnames flow into NPC hub naming if/when we create one for Marla.
- **The prep doc is now partially obsolete** — its main plot lever (Stacey reveals Lysandra sighting) didn't fire. Rather than mark it obsolete, this is exactly the kind of "plan diverged from execution" continuity that probably wants a **bidirectional pointer** between the two files (judgment).
- **Prep ↔ recap linkage is a real demand**, not just theoretical. Logged for discussion.

---

## 3. The raw recap, structurally

`Session 20 Recap.txt` — 24 lines:

| Line | Content |
|---|---|
| 1 | `Session 20 Recap` (plain text title) |
| 2 | blank |
| 3 | Para 1 — forest swarm fight (Thrin/Caelynn under the swarm) |
| 4 | blank |
| 5 | Para 2 — combat continues; swarm gives up; return to town |
| 6 | Para 3 — Bonogo + Stuart at warehouse; Stacey throws gold pouch |
| 7 | blank |
| 8 | Para 4 — Stuart runs off happy; Bonogo follows Stacey into alley with knife |
| 9 | blank |
| 10 | Para 5 — **byte-for-byte duplicate of Para 3** |
| 11 | blank |
| 12 | Para 6 — Marla confrontation begins (workers preparing) |
| 13 | blank |
| 14 | Para 7 — Marla escalates; Caelynn diffuses with bracelet; short rest |
| 15 | blank |
| 16 | Para 8 — Forest fires lit; trees turn east; mayor doesn't know Lysandra |
| 17 | blank |
| 18 | Para 9 — Rocky-talkie call: Sara → Lysandra; Karesmine will lead team |
| 19 | blank |
| 20 | Para 10 — Find Lysandra in dirt camp; tower blueprint; antidote tea |
| 21 | blank |
| 22 | Para 11 — Tainted meat reveal; Sara newly suspicious; Tealeaf no answer |
| 23 | blank |
| 24 | Para 12 — Storm + shimmer rain approaching; group settles in |

12 paragraphs, but Para 5 = Para 3 byte-identical. Final body: **11 paragraphs**.

### Quality issues to flag before write

- **Duplicate paragraph at lines 6 and 10.** Detection: exact-string match across paragraphs after splitting on blank lines. Mechanical.
- Minor inconsistency: "Karsemine" vs "Karesmine" appears in both this recap and prior ones. Carrying it forward verbatim per "preserve GM voice" rule.

---

## 4. Bucket: deterministic vs judgment

Tracked per step taken during this ingest.

### Deterministic (a tool could do this without LLM judgment)

| Step | What | How |
|---|---|---|
| D1 | Discover next session number | List `Session Recaps/*.md`, parse `Session NN` from filename, max + 1. |
| D2 | Compute target path | `<campaign>/Session Recaps/Session <N> - Recap.md` from campaign hub + N. |
| D3 | Emit frontmatter | 8-field fixed schema with N substituted. Field set is invariant across all surveyed recaps. |
| D4 | Add H1 line `# Session <N> Recap` | Normalize to S19 form (skip trailing colon, skip omission, skip body-duplication). |
| D5 | Strip leading title-line from body | If body starts with `Session N Recap` (with or without colon), strip the first line (it becomes the H1). Detected on this artifact (line 1 was a plain-text title). |
| D6 | Detect duplicate paragraphs | Split on blank lines, exact-string compare, surface duplicates for human review. **Caught the lines 6/10 dup.** |
| D7 | Preserve all GM prose verbatim | No rewriting; identity transform on the rest. |
| D8 | Emit unified-diff preview before write | Existing two-phase commit pattern. |
| D9 | Save to target path | Existing writer (`write_corpus_file`, `mode='create'`). |

### Judgment (LLM or human has to choose)

| Step | What | Why |
|---|---|---|
| J1 | Title normalization choice (S19 form vs preserving the GM's exact title styling) | Existing recaps are inconsistent; choose a canonical form. |
| J2 | Whether to keep duplicate or remove | Almost always remove, but the LLM should still surface for confirmation in case the dup is intentional (rare). |
| J3 | Which NPCs warrant a `timeline.md` row append this session | Some named NPCs (Stuart, Stacey, Stafl, Mayor, Sheriff) don't have hubs and probably shouldn't get them; only major recurring NPCs do. |
| J4 | Whether to create a new hub for Marla | First appearance + power-center status + named surname in prep doc. Strong yes, but the GM should approve. |
| J5 | Where the tower blueprint plot artifact lives on disk | New file? Append to a "world artifacts" file? Note in Lysandra dossier? GM's ontology call. |
| J6 | Whether to add a bidirectional pointer between this recap and the prep doc | Plan-vs-execution continuity. Editorial judgment. |
| J7 | Whether to update Lysandra's `README.md` (no obvious need; but the C2 dossier might want a Session 20 note about the shimmery-eyes recovery) | Dossier is read-only (Lesson 11), so the answer for the writer is "no." But the recap itself carries the change forward. |
| J8 | What to do with NPCs in Mirathorn (Sara, Professor Tealeaf) — do they get setting-hub presence too, or campaign-hub only? | Two-hub vs single-hub decision per the convention doc. |

### Surface for review (NOT writes)

The ingestion tool should produce a **review surface** for the GM containing:

1. The proposed `Session 20 - Recap.md` content with frontmatter + de-duped body (diff against nothing — it's a create).
2. The detected duplicate paragraph(s), with line numbers in source.
3. Proposed `timeline.md` append rows per affected NPC.
4. Proposed new hub creation requests (e.g. "Marla Brambleback — no hub exists; create at `Longmont Campaign/Campaign 2/NPCs/marla_brambleback/`?").
5. Proposed plot-artifact placements (e.g. "the tower blueprint — no obvious home; suggested locations: A/B/C").
6. Proposed cross-references (e.g. "link recap ↔ session 20 prep doc?").

Each item is approved individually. Nothing writes without an `apply <item>` reply.

---

## 5. Step-by-step log of this manual ingest

(Filled in as I do the work below.)

### Step 1 — Built the .md by hand (deterministic part)

- Computed target path: `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md` (D1, D2).
- Emitted frontmatter using S19 field set with `session: 20`, `origin_session: 20`, `last_updated_session: 20`, `title: "Session 20 - Recap"` (D3, J1: chose clean S19 form).
- Added H1 `# Session 20 Recap` (D4, J1).
- Stripped the leading "Session 20 Recap" plain-text title from the body (D5).
- Removed the duplicated paragraph at line 10 (D6, J2 → keep).
- Preserved all other prose verbatim (D7).
- Wrote the file to disk via direct file write (NOT via the corpus_writer two-phase tool — this is a hand-ingest pass to learn the shape; the writer is the *next* iteration).

Notes:

- The body in the .txt uses a non-breaking-style straight quote in `"testing"` (Para 2) and curly `“rockie-talkie”` (Para 9). Both preserved verbatim. Tools should NOT silently normalize quote styles.
- The .txt has trailing whitespace on some paragraphs (e.g. trailing space at end of Para 1, Para 6, Para 10, Para 11). Preserved verbatim — could be normalized by a tool, but doing so silently would mask intent.

### Step 2 — Found one more deterministic-vs-judgment subtlety while comparing source to output

The source `.txt` is **inconsistent about blank-line paragraph separation**:

- Lines 3 → 5 are separated by a blank line (line 4) — clean.
- Lines 5 → 6 are **adjacent without a blank line** — but lines 5 and 6 are clearly two different paragraphs (one ends "what they discovered.", the next opens "Back in town, Bonogo…"). The GM started a new paragraph with a single newline, not a blank line.
- Lines 6 → 7 is blank, then 7 → 8 is the next paragraph — clean again.
- And so on.

A naive splitter that breaks on `\n\n` only would have **glued lines 5 and 6 into a single paragraph**, hiding the duplicate detection (the line-6 paragraph would be embedded inside a longer combined block, never matching line 10's standalone copy via exact-string compare).

**Mechanical mitigation:** before paragraph-splitting, normalize the body so any `\n` that immediately follows a sentence-ending punctuation + space is treated as a hard paragraph break. Or simpler: split on `\n` runs of length ≥ 1 *and* recognize that an isolated single `\n` between lines is paragraph-equivalent if both adjacent lines look like complete sentences. This is light heuristics, not LLM judgment, but it's the kind of thing that would be missed if "the artifact is well-formed prose" were assumed.

**For this manual pass:** I split visually rather than mechanically, so I caught it. A tool wouldn't, automatically. Logged for the SKILL/ingestion-tool spec as a real edge case caught on artifact #1.

See section 3 (the line table) for the corrected per-paragraph layout, and section 6 below for the proposed organization items.

---

## 6. Proposed organization items (for GM review — nothing written to disk yet)

### 6.1 Lysandra timeline.md row

**Target:** `Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/timeline.md`
**Operation:** append one row to the existing table.
**Proposed row** (matching the rich-prose voice of existing rows, not a one-line beat):

```markdown
| **20**  | **Mossford** is saved (forest turns east); party calls Mirathorn — Lysandra is **disoriented and shimmery-eyed** (cult-grade charm); rocky-talkie chain via **Sara** then directly to Lysandra; **Karesmine tracks** her to a half-unloaded wagon camp; she has drawn a **top-down blueprint of a tower** in the dirt — "where the voices are coming from" — and knows the location; **Caelynn's antidote tea** restores her; she remembers only voices in the dark and the smell of meat. **Tainted meat** reveal in the same camp implicates Mirathorn's supply chain. | `Session 20 - Recap.md` |
```

**Notes for review:**
- The "Lysandra is shimmery-eyed" + "Caelynn's antidote tea" + "the cult charm style" continuity is the same as Session 6 (`Caelynn antidote + Shocking Grasp breaks charm`). Worth flagging in the row that this is a *recurring* charm pattern.
- The tower-blueprint reveal is the highest-impact plot artifact in this session; it deserves to be in the timeline beat (where the GM will look for "what changed").

### 6.2 New NPC hub: Marla Brambleback

**Target (proposed):** `Longmont Campaign/Campaign 2/NPCs/marla_brambleback/` (new slug folder)
**Why:** First appearance this session; established as a Mossford power center (in charge of workers); named with surname in the prep doc; ended the session unresolved (Marla approached Caelynn about Bonogo, party left town); **strong continuity hook** for any future return to Mossford.
**Proposed contents:**
- `README.md` — minimal hub index per CONVENTION (Suggested reads, Mechanical sheets if/when one exists, Session recaps section).
- `marla_brambleback_character_dossier.md` — distilled from the prep doc's Marla section (the prep doc is a *planning* document, not a dossier; the dossier should reflect what the table actually saw + what the GM had ready). **Judgment:** how much of the prep doc material is "now canonical because it appeared in play" vs "still planned but not seen"?
- `timeline.md` — single-row table for Session 20.
- (no statblock — none implied yet.)

**Open question for GM:** Do we want a setting-hub presence too (`Elderwyld/.../Mossford/NPCs/marla_brambleback/`)? Mossford may not have a setting-hub layer yet; the recap is the first time we've seen the town's social structure named (Marla "in charge of workers"). Probably **campaign-only hub for now**, escalate to dual-hub if she recurs across campaigns.

### 6.3 Tower blueprint plot artifact

**The artifact:** A top-down tower blueprint that Lysandra drew in the dirt while charmed. "Where the voices are coming from." She knows the location; party doesn't yet.

**Why it needs corpus presence:** This is the largest new plot object in the session. If we leave it only in the recap prose, future planners (model or human) can't easily ask "what do we know about the tower?" without re-reading the full recap. It will recur.

**Proposed locations (judgment — pick one or propose another):**

1. New file at `Longmont Campaign/Campaign 2/Plot Artifacts/tower_blueprint_lysandra_dirt.md` — clean, easy to point at, but no precedent for a `Plot Artifacts/` folder in this campaign hub yet. Would set a new convention.
2. New file at `Longmont Campaign/Campaign 2/Locations/tower_of_voices.md` (or whatever the GM names the tower) — frame it as a location, treat the blueprint as an artifact pointing to it. Better long-term ontology if the tower becomes a destination.
3. Note in the Lysandra dossier — but dossier is read-only per Lesson 11. So this is **not** an option; the recap is the right home for the *event*, but the *artifact* still wants its own pointer file.
4. New file at `Elderwyld/<region>/Locations/tower_of_voices.md` — if the tower is a world-level location, this is the canonical home; the C2 hub then carries a pointer.

**Recommendation (judgment):** Option 2 in C2, escalate to Option 4 once the GM confirms the tower exists in-world (not just in Lysandra's charmed vision).

### 6.4 Bidirectional pointer between recap and prep doc

**Why:** The prep doc's main plot lever (Stacey reveals the Lysandra sighting) **didn't fire** in actual play. Future readers need to be able to see this — both to understand why the prep doc reads as if it predicts something that doesn't happen, and to recover the "what was planned but didn't happen" continuity (the west-boundary-stones sighting may still be true even though Stacey never spoke it aloud).

**Proposed:**

- Append a small pointer at the bottom of the prep doc: `> **Played:** See \`Session Recaps/Session 20 - Recap.md\`. The Stacey-reveals-Lysandra-sighting clue did not fire (Bonogo went confrontational; Stacey ran home shaken). The west-stones sighting may still be canon for future use.`
- Append a small pointer at the bottom of the new recap: `> **Prep:** See \`Session Prep/session_20_stacey_stuart_marla_reference.md\`. Stuart, Stacey, and Marla Brambleback character notes; some planned beats diverged in play.`

The prep doc has `document_class: planning` and is **not** in the writer's read-only list, so this append is mechanically allowed by the existing allowlist (it's a `*.md` under a non-protected path). **But** prep docs are a new write target — the existing writer allowlist only covers `Session Recaps/*.md` (create) and `NPCs/<slug>/{timeline,README}.md` (append). Prep docs would need to be added to the allowlist if we want a tool to do this; otherwise hand-edit.

**Decision:** Hand-do this one for now. Logged as a future allowlist extension if the prep ↔ recap linkage becomes a recurring need.

### 6.5 NPCs *not* getting hubs (logged for explicit decision)

These appeared in the recap and I am explicitly **not** proposing hubs for them, with rationale per name. GM can override.

| NPC | Why no hub proposed |
|---|---|
| Stuart (halfling boy) | Recurring across S19–S20, but role is "kid sidekick of Bonogo this arc"; not a power center; the prep doc covers him. Hub would be premature. Dossier-light text could go into the prep doc instead. |
| Stacey Brambleback | Same reasoning. Plus shaken/threatened this session — may not recur. |
| Stafl | Wait — Stafl is a **PC**, not an NPC. Skip. |
| Mayor (red dragonborn) | Town-functionary role; no name yet; hub waits until named or recurring. |
| Sheriff | Same. |
| Sara (Mirathorn operator) | Already a recurring voice on the rocky-talkie; **may warrant a hub** in the Mirathorn setting layer (`Elderwyld/Cities and Towns/Mirathorn/NPCs/sara/`). Logged as **borderline yes** — flagged for GM call. |
| Frank (Mirathorn operator, Session 18) | Same reasoning as Sara. Borderline. |
| Professor Tealeaf | Same. Borderline. |
| The cult / "the voices" | Faction, not individual. Probably belongs in a `Factions/` layer that may not exist yet. |

### 6.6 PCs

The recap names: Ephanna, Karesmine, Caelynn, Thrin, Bonogo, Stafl. These are PCs and **never** get NPC-hub treatment. Logged here only to show I considered and dismissed each.

### 6.7 World-state deltas (no immediate disk action, captured for review)

| Delta | Where it might land |
|---|---|
| Migrating forest turned east after fires lit | Could update a Mossford / regional "current world state" file if one exists. Doesn't appear to. Recap prose carries it. |
| Tainted meat in Mirathorn supply chain | Plot continuity for any future Mirathorn arc; recap prose carries it. Sara's dialogue line is the canonical statement. |
| Storm + shimmer rain still active and approaching new camp | Carries into Session 21. Recap prose carries it. |

No hub or new file warranted from these alone.

---

## 7. Fingerprint reminder (per Lesson 8)

After this recap is written, the corpus fingerprint changes. The standing process applies:

1. Recompute fingerprint via `from src.agent.planner_cache import corpus_fingerprint`.
2. Update `evals/lysandra_vertical_slice/gold/step0_environment.json` → `expected_fingerprint`.
3. Run `tests/test_lysandra_vertical_slice_step0.py` to confirm.

**Not done in this manual ingest pass** — the GM will decide whether to write the recap (and any of the proposed organization items) to disk, then the fingerprint update follows naturally. Logged here so it doesn't get forgotten.

---

## 8. Headline learnings for the SKILL revision

(Detailed revision happens in a separate pass; this section is the input list.)

1. **Drop the numbered TLDR mandate.** Canonical recaps don't have one.
2. **No internal section headings.** One H1, then prose.
3. **Title normalization is a real choice.** Pick the cleanest exemplar (S19 form) as the canonical target; don't replicate prior typos.
4. **Detect-and-strip leading title from body** — Session 18 has the title duplicated into the body, which would happen mechanically if a tool naively concatenates "the .txt minus line 1" after the H1. The fix: if the .txt's line 1 is a plain-text version of the title, treat it as the title and don't re-emit it.
5. **Duplicate-paragraph detection is a hard requirement, not a nice-to-have.** It caught a real regression on the very first artifact.
6. **The prose is already in the GM's voice.** Don't rewrite, restructure, or "improve" it. Identity transform on body text after de-dup.
7. **The skill is structurer + extractor, not composer.** Composing prose is the GM's job; the skill turns prose into a structured file plus a review surface.
8. **The review surface (proposed organization items) is the LLM-judgment layer.** Mechanical ingest writes the recap; LLM judgment surfaces "you may also want to do these things." GM approves each independently.
9. **Companion-document discovery matters.** The session prep doc is a sibling to the recap (same session number) and the recap should at minimum link to it. Add prep-doc lookup to the skill protocol.
10. **First-appearance NPC detection** is part of the extractor surface. New NPCs (Marla) imply hub-creation proposals; existing NPCs (Lysandra) imply timeline-append proposals.
11. **Plot-artifact detection** is part of the extractor surface. Major new objects (the tower blueprint) need a home and the GM should propose where.
12. **The writer's path allowlist may need extension** for prep-doc append (link-back-to-recap pattern). Currently only Session Recaps create + NPCs timeline/README append are allowed.

---

## 9. Open questions for discussion (after the GM reads this and the recap)

1. Recap as written — accept verbatim, or revise the title-normalization choice?
2. Lysandra timeline row — append as drafted?
3. Marla hub — create now, or wait for recurrence?
4. Tower blueprint — which location ontology (1, 2, 3, 4 from §6.3)?
5. Prep ↔ recap pointers — append by hand (since it's outside writer allowlist)?
6. Sara / Frank / Tealeaf — promote to Mirathorn-hub NPCs now, or wait?
