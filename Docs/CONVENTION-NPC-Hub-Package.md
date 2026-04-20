# Convention: NPC hub package (README + timeline + dossier)

**Status:** Prescriptive for new or refactored NPC hubs in `corpus/eldyrwild-markdown/`.  
**Rationale and failure modes:** `Docs/Learnings/LEARNINGS-Corpus-Layout-For-LLM-Grounding.md`  
**Cursor rule (short form):** `.cursor/rules/corpus-layout-conventions.mdc`  
**Worked example:** `Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/` plus `Elderwyld/.../Mirathorn/NPCs/captain_lysandra_ironveil/`

---

## 1. Goals

- Give the session planner a **small index** (`README.md`) it can open first and treat as the map to every other file for that entity.
- Separate **mechanical truth** (statblock files) from **table-facing character prose** (dossier) and **session ordering** (`timeline.md`).
- Avoid stale paths: **no pinned default session recap** in README; use tree + timeline pointers.
- When an NPC exists in both **setting** and **campaign** trees, **two hubs** cross-link so each README stays honest about “canonical from this hub’s perspective.”

---

## 2. Folder and slug

- **One folder per entity**, named with the **entity slug** (lowercase, underscores): e.g. `captain_lysandra_ironveil/`.
- **One `README.md` per hub folder** (never merge two entities in one hub).
- Long-form authored files use **`{entity_slug}_{document_type}_{variant}.md`** where useful; see `.cursor/rules/corpus-layout-conventions.mdc` for the full naming table.

---

## 3. Minimum vs recommended files

| Artifact | Setting hub (world bible) | Campaign hub (table) | Notes |
|----------|---------------------------|----------------------|--------|
| `README.md` | **Required** | **Required** | Index + mechanical priority + cross-link. |
| `{slug}_character_dossier.md` | Optional (short “who at contact”) | **Recommended** | Primary **non-mechanical** reference: voice, psychology, how to run scenes. **Not** a substitute for statblock for AC/HP/CR. |
| `character_seed.md` | **Recommended** | Optional | Short pre–player-contact or pre-campaign hook list. |
| `{slug}_statblock_*.md` | **Recommended** when mechanics exist | Optional; use for **C2-only overrides** (e.g. `*_statblock_c2_post_sessNN.md`) | Planner must **read** the highest-priority statblock file before quoting CR/HP/AC/saves. |
| `timeline.md` | Usually omit | **Recommended** for recurring campaign NPCs | Pointer grid to session recaps; see §5. |

**Torbin-style legacy layout** (flat `NPCs/Torbin Jove/` with spaces in folder names) is **not** the target shape for new work; new hubs should use a single slug folder under the campaign’s `NPCs/` tree when you refactor.

---

## 4. README sections (required order)

Use the same **heading names** in both hubs so planner prompts and human authors stay aligned.

1. **Title** — `Display Name — {Mirathorn | Campaign N} ({setting seed | table})`  
2. **`## Suggested reads (in order)`**  
   - Numbered list. Each line: **full path from corpus root** (e.g. `Longmont Campaign/...`) + em dash + one-line **why open this next**.  
   - State explicitly that paths are for `read_corpus_file` **after** this README.  
   - Order: most universally useful for *this* hub first (often dossier or seed, then timeline, then statblocks, then sibling README).  
3. **`## Session recaps (no pinned default)`**  
   - Instruct: list recaps from the **corpus tree**; for “latest,” use the **largest session number in filenames**; if `timeline.md` names specific recaps for a beat, prefer those.  
   - Do **not** embed a single default `Session N - Recap.md` path that goes stale.  
4. **`## Mechanical sheets (priority — highest first)`**  
   - Markdown **table**: Priority (rank + short label), Path, Role.  
   - Describe filename families in **prose** (e.g. “any `.md` whose name starts with `{slug}_statblock_c2_`”). **Never** put shell globs (`*`, `?`) in strings the model might copy into tools.  
5. **Short prose “package” blurb** — bullet table or paragraph: what lives **in this folder** vs the **sibling hub** (cross paths once each).

**Cross-link:** each README must link to the other hub with **full paths** and say which statblock is authoritative **from that README’s perspective** (Mirathorn export vs table override).

---

## 5. `timeline.md` (campaign hub)

**Purpose:** Curated **chronology pointers** for this NPC at **this** table—not a full recap. The model uses it to choose **which** `Session Recaps/*.md` files to open.

**Required front matter (prose, top of file):**

- Display name + campaign id.
- **Primary chronology:** path to the session recap folder (corpus-relative).
- **Aggregated digests** (if any): e.g. `Campaign 2 Notes.md` — one line stating that timeline rows are pointers, not replacements for recap text.

**Required table columns:**

| Column | Content |
|--------|---------|
| Session | Session number or range (e.g. `7–8`). |
| Beat (short) | One cell: what happened for **this NPC** (telegraphic OK). |
| Recap file | **Literal filename** as played (e.g. `Session 6 - Recap.md`) so paths can be resolved under the recap folder from the tree. |

**Optional subsection** (after the table): “How to use this with prep / statblock bumps” — emotional spine, combat touchpoints, **remote** tension lines. Keeps voice-upgrade and prep questions grounded without inventing sessions.

**Maintenance:** On new sessions, **append** a row; keep recap filenames **literal** and consistent with on-disk names.

---

## 6. Dossier and statblock boundaries

- **Dossier:** ranks, relationships, voice, GM bullets — **no** 5e stat array as the source of truth for AC/HP/CR unless you explicitly duplicate (still: planner should read the **statblock file** for mechanics).  
- **Statblock:** RulesIngestion export or authored sheet — **source of truth** for numbers.  
- If rank in prose **lags** the statblock (promotion arc), say so in dossier or timeline; do not assume the model reconciles them without both files.

---

## 7. Discovery and eval hooks (optional but useful)

For NPCs used in benchmarks or vague player phrasing (“the kid,” “the guard captain”):

- Maintain **`aliases` / role hints** in eval-owned policy JSON (e.g. `evals/lysandra_vertical_slice/gold/corpus_policy.json`) **or** a future corpus-level manifest—keep **one** source of truth documented per slice.  
- In dossier **opening paragraph**, prefer **stable disambiguators** (role + affiliation + name) so retrieval and tree search land on the hub.

---

## 8. Session-recap workflow (corpus writes)

When a session ends and the GM has notes/transcript ready, route through the
**`recap-write` skill** (`.cursor/skills/recap-write/SKILL.md`) rather than hand-editing the recap file. It enforces:

- **Numbered next recap** at `Session Recaps/Session <N> - <slug>.md` with the same YAML frontmatter shape as recent recaps (`title`, `document_class: play`, `canon_layer: campaign`, `campaign_id`, `session: N`, `origin_session: N`, `last_updated_session: N`, `source_class: observed_session_recap`).
- **Structured follow-up payload** (timeline-append candidates, new-hub proposals, etc.) emitted with the recap; **append-only timeline rows** in each affected campaign-hub `NPCs/<slug>/timeline.md` are a separate per-NPC step (future `recap-timeline-append` skill, or manual follow-up using `append_timeline_row`).
- **No edits to dossier / seed / statblock** (`*_character_dossier.md`, `character_seed.md`, `*_statblock*.md`). These are the static character/world bible. State changes from the session live in the recap; the timeline row carries the pointer.

`write_corpus_file` and `append_timeline_row` register only when the planner is launched with `--allow-corpus-writes` (or `DUNGEONMIND_PLANNER_ALLOW_WRITES=1`). Both use a **two-phase commit**: `dry_run=true` returns a unified-diff preview plus a short `confirm_token`; the operator must see the diff and reply `apply` before the second call commits with the matching token. Token mismatches (file changed between phases) abort the write. The `recap-write` skill uses `write_corpus_file` for the recap only; timeline appends are not part of that skill's contract.

After commit, the writer reports a `fingerprint_reminder`. Run the fingerprint update steps in §9 (or the `## Fingerprint hygiene` section in `.cursor/rules/corpus-layout-conventions.mdc`).

## 9. Checklist (new NPC hub)

- [ ] Slug folder under correct `NPCs/` path.  
- [ ] `README.md` with all four sections in §4; paths are full corpus-relative strings.  
- [ ] Mechanical priority table present if any `*_statblock_*.md` exists.  
- [ ] If campaign + setting both exist: both READMEs cross-linked.  
- [ ] `timeline.md` if the NPC spans multiple recaps and planners need recap routing.  
- [ ] After corpus edits: fingerprint per `.cursor/rules/corpus-layout-conventions.mdc` if your eval pins `expected_fingerprint`.
