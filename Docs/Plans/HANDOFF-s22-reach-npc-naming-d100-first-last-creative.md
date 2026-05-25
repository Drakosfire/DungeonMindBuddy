---
pr_body_template: |
  ## Summary
  Author **T-NAME-F** and **T-NAME-L** — paired d100 first- and last-name tables for ephemeral Mireward Reach NPCs, plus a regional naming-conventions reference. Register in session_22 hub and wire into runbook roll registry.

  ## Verification (verbatim §7)
  {{TODO: paste command outputs}}

  ## `git diff --stat` (§4 paths only)
  ```text
  {{TODO}}
  ```
---

# HANDOFF — Mireward Reach NPC naming d100 (first + last, creative writing)

**Created:** 2026-05-23 (UTC).  
**Status:** ACTIVE — dispatch to **creative writing agent** with git access. One PR (two tables + conventions reference). Parent agent may update **`canvases/session-22-planning.canvas.tsx`** after merge (out of scope for worker).  
**Parent agent:** Cursor agent (DungeonMindBuddy).  
**Plan anchor:** Session 22 travel prep — scaffold ephemeral NPCs rolled from road/comms/gate beats before full hub promotion. Pairs with **T-COMMS** guard overhear rows and **R5** stranger traffic. Dogfood: `Backlog.md` → `[READY] Tooling — d-table generator workflow`.

---

## §1 Mission

Author **two player-rolled d100 tables** (100 numbered rows each) for **first names** and **last names** on the **Mireward Reach** corridor, plus one **regional naming-conventions reference** doc. Rows must encode **south→north cultural drift** (Mirathorn → Mossford → Mireward → Edge/fen) and carry a **scaffold** so the GM can promote a rolled stranger to a hub without re-deriving voice or trade.

**This slice does NOT:** create NPC hubs, dossiers, or statblocks; resolve Edge-of-the-World map position; edit recaps; touch prompts/evals; update canvas.

---

## §2 Why this slice

- **Road/comms tables name roles, not people:** T-COMMS guard overhear, R5 convoys, Mireward gate dilemmas need **instant names** that feel **regional**, not generic fantasy filler.
- **Cultural transition is table-visible:** Party left **Mirathorn** (city, academy, festival gravity), passed **Mossford** (river agriculture, moss-craft labor), marches toward **Mireward** (garrison charter town, refugee crush), with **Edge of the World** music rumors farther north (`Session 21` Marr warning).
- **Build-out path:** Rolled name + scaffold → on-the-fly scene → optional promotion to `Elderwyld/Cities and Towns/<place>/NPCs/<slug>/` per `Docs/CONVENTION-NPC-Hub-Package.md`.
- **Naming is world reference, not session-only:** Tables live under `Elderwyld/Roads/` (evergreen, like `mireward_reach_road_d100_encounter_table.md`); Session 22 README registers them for travel prep.

---

## §3 Authoritative inputs (read in this order)

### 3.1 Workflow & format

1. **`.cursor/rules/external-agent-pr-loop.mdc`** — §4 allowlist / §7 verification / §9 rubric.
2. **`Event Table Design Guidance.md`** (repo root) — weighted bands, beneficial mix, escalation on repeat.
3. **`corpus/.../Elderwyld/Roads/mireward_reach_road_d100_encounter_table.md`** — **format mirror**: frontmatter, band headers, numbered rows, “How to use”.
4. **`Docs/Plans/HANDOFF-s22-mirathorn-comms-d100-creative.md`** — sibling creative slice (comms); **do not edit**; note guard overhear rows need **attachable names**.

### 3.2 Geography & culture (required reads)

| Order | Path (under `corpus/eldyrwild-markdown/`) | Why |
|-------|-------------------------------------------|-----|
| 1 | `Longmont Campaign/Campaign 2/Journey - Mireward Reach (Campaign 2).md` | Anchor distances Mirathorn → Mossford → Mireward → Edge |
| 2 | `Elderwyld/Roads/mireward_reach_road_d100_encounter_table.md` | Road tone, traffic types, Reach insult-names |
| 3 | `Elderwyld/Cities and Towns/Mirathorn/The City of Mirathorn.md` | City scale, Lundayell refugee origin, trade hub |
| 4 | `Elderwyld/Cities and Towns/Mirathorn/README.md` + `Stormspire Academy/Wynna Mossglade _ Clerk.md` | Academy polish vs civic names |
| 5 | `Elderwyld/Cities and Towns/Mossford/Mossford_Map_Key_and_Gazetteer.md` | River town, moss economy, labor ethos |
| 6 | `Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Town Hall.md` | Marr, Rusk, Mosscale voice samples |
| 7 | `Elderwyld/Cities and Towns/Mossford/NPCs/sheriff_roderic_marr/character_seed.md` | Reach-warden backstory; music-as-signal |
| 8 | `Elderwyld/Cities and Towns/Mireward/Mireward_PLACE_BUILD_SCAFFOLD.md` | §A2 identity, §F2 Maera/Orin Vell, garrison thin, refugee stack |
| 9 | `Elderwyld/Cities and Towns/Mireward/README.md` | Last walled town before fen |
| 10 | `Elderwyld/Cities and Towns/Edge of the World/README.md` | Music rumor stub; liminal north |
| 11 | `Longmont Campaign/Campaign 2/Session Recaps/Session 21 - Drake Nest Mirathorn Call.md` | Marr + Edge rumor table canon |
| 12 | `Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_travel_to_mireward_runbook.md` | §6 roll registry — add T-NAME rows |
| 13 | `Longmont Campaign/Campaign 2/Session Prep/session_22/README.md` | Artifact register |

### 3.3 Existing names — phonology seed (do not duplicate)

Use these as **pattern anchors**, not rows to copy:

| Region | Given | Surname | Pattern |
|--------|-------|---------|---------|
| **Mirathorn** | Lysandra, Merril, Wynna, Torbin, Sara, Frank | Ironveil, Tealeaf, Jove, Mossglade | Classical or soft given + **virtue/trade/compound** surname; academy elven influence |
| **Mossford** | Roderic, Sareth, Meret, Hen, Stuart, Stacey, Siv | Marr, Mosscale, Rusk, Clow, Brambleback | **River/labor** given; **moss·river·plant** compounds or **blunt one-syllable** surnames |
| **Mireward** | Maera, Orin *(working)* | Vell | Shorter, charter-plain; **fewer syllables** than city; garrison/stink-trade hints |
| **Edge / fen** | *(sparse — author)* | *(sparse — author)* | Wary, liminal; **fen·reed·verge** morphemes; hymn-adjacent **without** cult proper nouns |

**Reserved (never use as table rows):** Sara, Frank, Lysandra, Ironveil, Tealeaf, Merril, Torbin, Jove, Roderic, Marr, Mosscale, Rusk, Maera, Vell, Orin, Dustwalker, Haldrim, Thrin, Baergrom, Karsemine, Stafl, Bonogo, Caelynn, Ephanna, Pippa, Grishna, Glowkindle — party, anchor NPCs, and working Mireward inn family.

---

## §3.4 Regional phonology (binding — encode in conventions doc + bands)

South→north = **density → labor → charter → liminal**. Names should **sound** different when read aloud in sequence.

### Mirathorn band (rows **01–25**)

- **Feel:** Cosmopolitan trade city; Lundayell refugee legacy (**formal but not aristocratic**).
- **Given:** 2–3 syllables; classical or soft (Lysandra, Merril, Wynna); human/dwarf/elven mix acceptable.
- **Surname:** Compound **virtue·trade·landmark** (Ironveil, Tealeaf, Stormwright); occasional simple (Jove).
- **Scaffold roles:** clerk, guild factor, academy adjacency, city guard transfer, festival labor, operator-adjacent **not** Sara/Frank.

### Mossford band (rows **26–50**)

- **Feel:** River agriculture, moss-craft, **plainspoken**; temple modest; mayor’s consensus politics.
- **Given:** Shorter, practical (Hen, Siv, Stuart, Meret); less elven polish.
- **Surname:** **Moss-** compounds (Mosscale, Mossglade), **plant·water** (Brambleback, Reedwash), or **blunt** (Rusk, Clow, Marr-class — **not** Marr itself).
- **Scaffold roles:** dam crew, moldyard, brewery hand, ferryman, watch auxiliary, field hand, inn second.

### Mireward band (rows **51–75**)

- **Feel:** **Sky not spires**; garrison pension culture; stink-trades downwind; refugee crush **now**.
- **Given:** Charter-plain; gender-neutral OK; fewer fancy vowels.
- **Surname:** Short (**Vell-class**, one syllable or harsh two); **trade-honest** (Ashkettle, Limegrit, Tannerford — invent, don’t genericize); retired spear **epithet** surnames rare (≤5 rows).
- **Scaffold roles:** gate sergeant-emeritus, tithe clerk, ferry guard, tanner, refugee with bundle, apron inn, patrol widow.

### Edge / fen band (rows **76–100**)

- **Feel:** Last named-town threshold; **music-rumor** undertone; fen displacement; **wrong-quiet** hamlets.
- **Given:** Older, wary; occasional **renamed** folk (escaped south — note in *Notes*).
- **Surname:** **Fen·reed·verge·bell** morphemes (Reedmantle, Vergeborn); ambiguous hymn echoes — **never** Dustwalker, Maelthor, Shepherd as surnames.
- **Scaffold roles:** reed-cutter, hymn-hearer, hamlet evacuee, causeway toll, night singer **ambiguous**, crown rider from north.

### Reach-generic (≤10 rows **total across both tables**, any band)

- Drover/pilgrim **could be from anywhere** — tag `Reach-generic`; scaffold says “accent from south” or “no fixed origin.”

---

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|--------|------|---------|
| **Create** | `corpus/eldyrwild-markdown/Elderwyld/Roads/reach_npc_naming_conventions.md` | Regional phonology + promotion scaffold card |
| **Create** | `corpus/eldyrwild-markdown/Elderwyld/Roads/reach_npc_first_names_d100.md` | **T-NAME-F** — d100 first names |
| **Create** | `corpus/eldyrwild-markdown/Elderwyld/Roads/reach_npc_last_names_d100.md` | **T-NAME-L** — d100 last names |
| **Modify** | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/README.md` | Register **T-NAME-F**, **T-NAME-L**, conventions ref |
| **Modify** | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_travel_to_mireward_runbook.md` | §6 roll registry — when to roll names (one subsection, ≤15 lines) |
| **Modify** | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mireward/Mireward_PLACE_BUILD_SCAFFOLD.md` | §E anchor NPC table — one-line pointer to naming tables (no rewrites) |
| **Modify** | `corpus/eldyrwild-markdown/Elderwyld/Roads/mireward_reach_road_d100_encounter_table.md` | “Related tables” cross-link only (≤5 lines) |

> Expected `git diff --stat` expressible from this table only.

---

## §5 Files explicitly OUT OF SCOPE (denylist)

| Path | Why |
|------|-----|
| `canvases/session-22-planning.canvas.tsx` | Parent agent post-merge |
| `src/prompts/*.py`, `evals/**`, `tests/**` | No code |
| `corpus/**/Session Recaps/**` | Read only |
| `corpus/**/NPCs/**/` hub creation | No dossiers/statblocks/hubs |
| `travel_mirathorn_comms_d*.md`, other `travel_*.md` | Sibling slices |
| `HANDOFF-s22-mirathorn-comms-d100-creative.md` | Do not edit |
| `Backlog.md`, other `HANDOFF-*.md` | Meta |

---

## §6 Implementation contract

### 6.1 File: `reach_npc_naming_conventions.md`

**Frontmatter:**

```yaml
---
title: "Mireward Reach — NPC naming conventions"
document_class: reference
canon_layer: world
campaign_id: null
temporal_scope: evergreen
session: null
origin_session: 22
last_updated_session: null
source_class: seed_reference
table_note: "Phonology and promotion scaffold for T-NAME-F / T-NAME-L. World reference — not table canon for specific NPCs until promoted to hubs."
---
```

**Body (required sections):**

1. **How to roll** — roll **d100 first** + **d100 last** independently; optional **region bias**: if party is within 2 days of a anchor, reroll once if row region mismatches (GM discretion).
2. **South→north map** — one table: Mirathorn / Mossford / Mireward / Edge-fen with 1-line phonology each (expand §3.4).
3. **Reserved names** — bullet list from §3.3.
4. **Promotion scaffold card** — copy-paste template for when a rolled NPC gets a second scene:

```markdown
### {First} {Last} — ephemeral → hub candidate
- **Rolled from:** T-NAME-F {n} + T-NAME-L {n} · Region: {tag}
- **Role bucket:** {from row scaffold}
- **Voice:** {from row scaffold}
- **Want:** {GM fills after one scene}
- **Promote to:** `Elderwyld/Cities and Towns/{place}/NPCs/{slug}/` when they recur
```

5. **Cross-links** to both d100 files and `mireward_reach_road_d100_encounter_table.md`.

---

### 6.2 File: `reach_npc_first_names_d100.md`

**Frontmatter:**

```yaml
---
title: "d100 First Names — Mireward Reach"
document_class: world
canon_layer: world
campaign_id: null
temporal_scope: evergreen
session: null
origin_session: 22
last_updated_session: null
source_class: roll_table
table_id: T-NAME-F
dice: d100
table_note: "Ephemeral NPC given names — regional bands south→north. Pair with T-NAME-L. Planning/world reference until promoted to NPC hubs."
---
```

**Body sections:**

1. **Title** + **How to use** (6–8 bullets): pair with last-name table; region bands; reserved names; repeat rule (same name twice → add nickname or scar); tie to R5 strangers / gate / comms overhear.
2. **Band map** — compact table mirroring §3.4 row ranges.
3. **Ten band headers** — `## 01–25 · Mirathorn given`, `## 26–50 · Mossford given`, etc.
4. **100 numbered rows** — `1.` through `100.` exactly once.

**Row format (required — four fields):**

```text
{N}. **{FirstName}** · *Region:* {Mirathorn|Mossford|Mireward|Edge-Fen|Reach-generic} · *Scaffold:* {role bucket}; {one voice adjective} · *Notes:* {gender hint if useful; phonetic or culture tag — one clause}
```

**Creative constraints:**

- **Unique** first names within the table — no duplicates.
- **No reserved names** (§3.3).
- **Speakable** at table without explanation.
- **≥15 rows** with scaffold role **beneficial** (helpful stranger, witness, trade) not only threat.
- **Edge-Fen band:** ≥3 rows tagged `renamed-fleeing` in *Notes*.
- **Avoid** real-world celebrity names and modern anachronisms.

---

### 6.3 File: `reach_npc_last_names_d100.md`

**Frontmatter:** same shape as first-name file with `table_id: T-NAME-L`, title `d100 Last Names — Mireward Reach`.

**Row format (required — four fields):**

```text
{N}. **{Surname}** · *Region:* {Mirathorn|Mossford|Mireward|Edge-Fen|Reach-generic} · *Scaffold:* {family trade, origin story, or social slot — one clause} · *Notes:* {pairing hint — e.g. "Mirathorn given + this"; compound morpheme gloss}
```

**Creative constraints:**

- **Unique** surnames within the table.
- **No reserved surnames** (§3.3).
- **Compound surnames** should **decode** in *Notes* (Ironveil = iron + veil pattern) at least once per regional band.
- **Mossford band:** ≥8 rows with **moss·river·plant** morpheme visible.
- **Mireward band:** ≥5 **one-syllable** surnames.
- **Edge-Fen band:** ≥5 with **fen·reed·verge** morpheme; **zero** explicit cult titles.

### Band allocation (both tables — same row ranges)

| Band | Rows | Primary region tag |
|------|------|-------------------|
| **01–25** | 25 | Mirathorn |
| **26–50** | 25 | Mossford |
| **51–75** | 25 | Mireward |
| **76–100** | 25 | Edge-Fen |

**Reach-generic:** ≤10 rows **total per table**, distributed — not a separate band.

### Escalation rule (in both How to use sections)

> Same **first + last pair** rolled twice on one journey → add **distinguisher** (nickname, limp, uniform patch, smell, or “the younger”) — never identical NPC twice.

### Pointer updates

- `session_22/README.md`: two register rows **T-NAME-F**, **T-NAME-L** + conventions ref → **`ready`**, `reference`.
- `session_22_travel_to_mireward_runbook.md` §6: when stranger needs a name (R5 row, gate, overhear, refugee) → roll both tables.
- `Mireward_PLACE_BUILD_SCAFFOLD.md` §E: footnote “name pool: `reach_npc_*_d100.md`”.
- `mireward_reach_road_d100_encounter_table.md`: Related → naming tables.

---

## §7 Verification commands

Worker runs **every** command; paste output in PR body. Reviewer reruns.

```bash
cd /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy

ROADS="corpus/eldyrwild-markdown/Elderwyld/Roads"
FIRST="$ROADS/reach_npc_first_names_d100.md"
LAST="$ROADS/reach_npc_last_names_d100.md"
CONV="$ROADS/reach_npc_naming_conventions.md"
S22="corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22"

# Row counts — must be exactly 100 each
echo "T-NAME-F rows:" && rg -c '^[0-9]+\.' "$FIRST"
echo "T-NAME-L rows:" && rg -c '^[0-9]+\.' "$LAST"

# Band headers — expect 10 per table
echo "T-NAME-F bands:" && rg -c '^## [0-9]{2}–[0-9]{2}' "$FIRST"
echo "T-NAME-L bands:" && rg -c '^## [0-9]{2}–[0-9]{2}' "$LAST"

# Frontmatter
rg '^table_id: T-NAME-F' "$FIRST" && rg '^table_id: T-NAME-L' "$LAST" && rg '^dice: d100' "$FIRST" "$LAST"

# Conventions file exists + scaffold card
test -f "$CONV" && echo "conventions: OK"
rg 'Promotion scaffold card' "$CONV"

# Reserved name spot-check — must NOT appear as row names (adjust rg if false positive on Notes)
for NAME in Ironveil Tealeaf Mosscale Marr Vell; do
  rg "^\d+\. \*\*${NAME}\*\*" "$FIRST" "$LAST" && echo "RESERVED HIT $NAME: FAIL"
done
echo "reserved spot-check done"

# Register
rg 'T-NAME-F' "$S22/README.md" && rg 'T-NAME-L' "$S22/README.md"

# Runbook wired
rg -i 'T-NAME|reach_npc_first|reach_npc_last' "$S22/session_22_travel_to_mireward_runbook.md"

# Allowlist-only diff
git diff --stat HEAD -- \
  "$CONV" \
  "$FIRST" \
  "$LAST" \
  "$S22/README.md" \
  "$S22/session_22_travel_to_mireward_runbook.md" \
  "corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mireward/Mireward_PLACE_BUILD_SCAFFOLD.md" \
  "$ROADS/mireward_reach_road_d100_encounter_table.md"
```

---

## §8 Reporting contract

PR body must include:

1. **`git diff --stat`** filtered to §4 paths only.
2. **Verbatim §7 output** — row counts **100+100**, band headers **10+10**, register `ready`.
3. **Band distribution** — self-reported region-tag counts per band (both tables).
4. **Six sample rows** — one full row from each region band (first + last = 8 rows) + **one promoted scaffold card** filled with a sample roll.
5. **Phonology summary** — 3–5 sentences on what makes each region **sound** different (worker-authored).
6. **What stayed unchanged** — recaps, NPC hubs, canvas, T-COMMS, other travel tables.

---

## §9 Acceptance rubric

- [ ] **Exactly 100** numbered rows in **each** table — verified by §7 row-count commands.
- [ ] **Ten band headers** per table spanning 01–100 — verified by §7 band-header counts.
- [ ] Frontmatter `table_id` **T-NAME-F** / **T-NAME-L**, `dice: d100` — verified by §7 `rg`.
- [ ] **`reach_npc_naming_conventions.md`** exists with promotion scaffold card — verified by §7.
- [ ] **Every row** includes *Region*, *Scaffold*, *Notes* — reviewer spot-check **10 random rows per table** in PR diff.
- [ ] **No reserved names** as row primary names — verified by §7 spot-check + reviewer skim.
- [ ] **README** lists both tables + conventions as **`ready`** / **`reference`** — verified by §7.
- [ ] **Runbook §6** mentions when to roll — verified by §7 `rg`.
- [ ] **No cult proper nouns** in Edge-Fen surnames — reviewer read of rows 76–100 in last-name table.
- [ ] **No files outside §4** in diff — verified by §7 scoped `git diff --stat`.

---

## §10 Out-of-band notes

- **Canvas:** Parent may add T-NAME roll hook beside R5 / gate / comms on planning canvas **after** merge — worker **must not** edit canvas.
- **Pair with T-COMMS:** Guard overhear rows that need a name → roll T-NAME-F + T-NAME-L; corruption stays on comms row, identity from naming tables.
- **Mireward §E TBD slots:** Tables supply **pool**; Maera/Orin Vell remain **working anchors** — do not overwrite scaffold names.
- **PII:** Read corpus for phonology; do not paste long dossier excerpts in PR.
- **Branch:** `cursor/s22-reach-npc-naming-d100` or similar; open PR against current integration branch when done.

---

## §11 Dispatch pairing

This HANDOFF is **independent** of `HANDOFF-s22-mirathorn-comms-d100-creative.md` — may run **parallel** (separate PRs) or **sequential**. If parallel, worker must not touch T-COMMS files.

**Suggested dispatch order:** Either order works; naming tables unblock road/gate improv immediately; comms d100 unblocks Mirathorn retry beats.
