---
pr_body_template: |
  ## Summary
  Author four Session 22 travel roll tables (T-NPC d12, T-DIL d12, T-DIL-G d6, T-CF d8) and register them in the session_22 planning hub.

  ## Verification (verbatim §7)
  {{TODO: paste command outputs}}

  ## `git diff --stat` (§4 paths only)
  ```text
  {{TODO}}
  ```
---

# HANDOFF — Session 22 travel roll tables (T-NPC, T-DIL, T-DIL-G, T-CF)

**Created:** 2026-05-23 (UTC).  
**Status:** MERGED on branch `cursor/session-22-prep` (PR #70) — tables filed 2026-05-23; register synced in follow-up commit.  
**Parent agent:** Cursor agent; post-merge: bump P0 register + runbook §6.1/§12 status columns.  
**Plan anchor:** Session 22 travel prep — `session_22_travel_to_mireward_runbook.md` §6 roll registry. No PLAN YAML milestone; corpus-only slice.

---

## §1 Mission

Create **four player-rolled travel tables** for Campaign 2 Session 22 (Mireward Reach march) and register them as **ready** in the session_22 artifact index.

---

## §2 Why this slice (context for the subagent)

- **Runbook** (`session_22_travel_to_mireward_runbook.md`) defines point-crawl roll procedure: per march day → **T-NPC** → **R5** (exists) → **T-DIL** → night **R6** (exists) + **T-CF**; arrival → **T-DIL-G**.
- **R5** and **R6** already exist. This slice fills the **four missing tables** specced in runbook §6.3–§6.7.
- **Design contract:** `Event Table Design Guidance.md` (repo root), mapped in runbook §6.0.
- **This slice does NOT:** edit R5/R6 rows; write runbook encounter prose; promote Mireward to canon; touch prompts, evals, gold, or NPC dossiers; resolve Mirathorn off-screen; confirm Dustwalker/cult.

---

## §3 Authoritative inputs (read in order before writing)

1. **`.cursor/rules/external-agent-pr-loop.mdc`** — §4 allowlist / §7 verification / §9 rubric contract.
2. **`Event Table Design Guidance.md`** — weighting, action-oriented rows, beneficial mix, escalation.
3. **`corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_travel_to_mireward_runbook.md`** — **§6 entire** (registry, §6.0 authoring contract, §6.3–§6.7 specs, §7 roll order).
4. **`corpus/.../session_22/session_22_prep_brief.md`** — §3 NPC beats (Thrin mandatory omen shape, Lysandra comms).
5. **`corpus/eldyrwild-markdown/Elderwyld/Roads/mireward_reach_road_d100_encounter_table.md`** — **format mirror only** (frontmatter, band headers, numbered rows, “How to use”, escalation note). Do not duplicate R5 content.
6. **`corpus/eldyrwild-markdown/Elderwyld/Wilderness/conical_hills_night_camp_d100.md`** — secondary format mirror for “How to use” + numbered list style.
7. **`corpus/.../Session Prep/session_22/README.md`** — artifact register rows **T-NPC** through **T-CF** (currently `missing`).

**Campaign context (constraints, not prose to paste):**

| Fact | Use in tables |
|------|----------------|
| S21 end: storm edge, savory/shimmer rain, building west | Weather + magic tells in NPC/dilemma rows |
| Party presses **north** toward swamp; Mireward ~5 days | Destination pressure, refugee traffic |
| Mirathorn comms degraded; Frank hung up; Lysandra no answer | Comms dilemmas / NPC rows — **no city reveal** |
| Mireward scaffold: refugee crush, Maera/Orin, gate short-handed | Gate table + foreshadow only |
| Shepherd undertone | Ambiguous north rows — **not sermons**, no cult confirmation |

---

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|--------|------|---------|
| **Create** | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_npc_spotlight_d12.md` | **T-NPC** — mandatory NPC spotlight, d12 |
| **Create** | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_dilemma_d12.md` | **T-DIL** — travel dilemma, d12 |
| **Create** | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/mireward_gate_dilemma_d6.md` | **T-DIL-G** — gate arrival dilemma, d6 |
| **Create** | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_campfire_d8.md` | **T-CF** — campfire RP prompt, d8 |
| **Modify** | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/README.md` | Set T-NPC, T-DIL, T-DIL-G, T-CF prep status **`ready`** |
| **Modify** | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_travel_to_mireward_runbook.md` | §6.1 + §12: change four tables **To build** → **Exists** / paths unchanged |

> Expected `git diff --stat` is expressible from this table only.

---

## §5 Files explicitly OUT OF SCOPE (denylist)

| Path | Why |
|------|-----|
| `src/prompts/*.py` | Prompt edits shift benchmark behavior |
| `evals/**/gold/**` | Rubric drift |
| `corpus/**/mireward_reach_road_d100_encounter_table.md` | R5 exists — do not edit |
| `corpus/**/conical_hills_night_camp_d100.md` | R6 exists — do not edit |
| `corpus/**/Mireward_PLACE_BUILD_SCAFFOLD.md` | Town design — separate workstream |
| `corpus/**/NPCs/**/character_dossier.md`, `*_statblock*` | Bible files — read for tone, do not write |
| `session_22_travel_to_mireward_runbook.md` **except** §6.1/§12 status cells | No rewriting §6 specs or §10 arrival |
| `session_22_prep_brief.md` | Historical prep — do not sync |
| `Backlog.md`, `Docs/Plans/HANDOFF-*.md` (except this file if archiving post-merge) | Meta |
| `tests/**` | No test harness for this slice unless reviewer requests follow-up |

Stop and ask in PR description if another path seems required.

---

## §6 Implementation contract

### Shared file shape (all four tables)

Use YAML frontmatter aligned with Session 22 planning docs:

```yaml
---
title: "<table title>"
document_class: planning
canon_layer: campaign
campaign_id: longmont-c2
temporal_scope: session_specific
session: 22
origin_session: 21
last_updated_session: 21
source_class: scene_module
table_note: "<one line: die size, when rolled, pointer to runbook §6>"
---
```

Body must include:

1. **Title** (`# …`) matching frontmatter `title`.
2. **How to use** — 3–6 bullets: die size, player rolls, when in march beat (cite runbook §7), escalation-on-repeat one-liner.
3. **Thematic band headers** — `## 01–03 · Block name` (use ranges that match row counts).
4. **Numbered rows** — `1.` … `N.` only (no gaps, no duplicate numbers).

### Entry formats (required shapes)

**T-NPC (d12):** each row = four clauses separated by **` · `**

```text
{NPC name} · {trigger — sensory or weather} · {concrete ask of party} · {one action that changes the scene}
```

**T-DIL (d12):** each row =

```text
{Situation headline} · {Choice A / Choice B / Choice C} · {If ignored or on repeat}
```

**T-DIL-G (d6):** same as T-DIL but gate-scoped (queue, inn, sergeant).

**T-CF (d8):** each row = one **open question** for the table (no mechanics). Optional second line: `{Theme tag}` in italics.

### Table 1 — T-NPC `travel_npc_spotlight_d12.md`

| Field | Value |
|-------|-------|
| **Die** | d12 |
| **Rows** | **12** exactly |
| **Block order** | 01–03 Storm/land · 04–06 Comms/duty · 07–09 Magic/north · 10–12 Road/wonder |
| **NPC allocation** | Thrin **≥2** rows (one must match **omen** shape: wrong bird silence, rhythm on horizon, or shelter read — prep brief §3) · Lysandra **≥2** · Caelynn **≥1** · Ephanna **≥2** · Stafl **≥1** · Bonogo **≥1** · Karsemine **≥1** · row 12 = **party picks a PC** to spotlight |
| **Tone** | Competence wins allowed (Thrin shelter, Caelynn storm estimate). Prompts not scripts. |
| **Forbidden** | Resolve Mirathorn; confirm Dustwalker; auto-combat |

### Table 2 — T-DIL `travel_dilemma_d12.md`

| Field | Value |
|-------|-------|
| **Die** | d12 |
| **Rows** | **12** exactly |
| **Block order** | 01–03 Mercy/convoy · 04–06 Pace/storm · 07–09 Comms/south · 10–12 North/trust |
| **Tone mix** | **≥3** benign/neutral (rows 1–4 band) · ~5 pressure · ~3 ominous; **row 12** = highest-stakes north-trust (special slot per §6.0) |
| **Every row** | ≥2 real choices + credible cost if ignored |
| **Forbidden** | Auto-start combat; gate scenes (those are T-DIL-G) |

### Table 3 — T-DIL-G `mireward_gate_dilemma_d6.md`

| Field | Value |
|-------|-------|
| **Die** | d6 |
| **Rows** | **6** exactly |
| **Order** | 1–2 help queue · 3–4 wait / gossip / inn full · 5 name-drop Mirathorn · **6 wildcard** (bribe, side gate, Bonogo scout, Lysandra rank — pick one clear situation) |
| **Cast** | May reference **Sergeant Hald Voss**, **Maera Vell**, **The Last Dry Bed** (runbook §13 working names) |
| **Forbidden** | Confirm cult; resolve town crisis in one row |

### Table 4 — T-CF `travel_campfire_d8.md`

| Field | Value |
|-------|-------|
| **Die** | d8 |
| **Rows** | **8** exactly |
| **Themes (in order)** | 1 Mirathorn silence · 2 crowd/not-Mirathorn identity · 3 non-judgment · 4 forest vs road · 5 north wrongness · 6 wrong rain/shimmer · 7 festival elsewhere · 8 open — player picks whose story |
| **Forbidden** | Mechanics, saves, combat, NPC monologues |

### Escalation rule (all four tables)

Add to each **How to use**:

> If the same row is rolled twice in one journey, intensify (worse static, more witnesses, shorter decision window) — do not repeat verbatim.

### README + runbook status updates

In `session_22/README.md`, set **Prep status** to **`ready`** for T-NPC, T-DIL, T-DIL-G, T-CF.

In runbook §6.1 and §12, replace **To build** with **Exists** and the corpus-relative paths above.

---

## §7 Verification commands

Worker runs **every** command; paste output in PR body. Reviewer reruns.

```bash
cd /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy

BASE="corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22"

# Row counts — must be exactly 12, 12, 6, 8
echo "T-NPC rows:" && rg -c '^[0-9]+\.' "$BASE/travel_npc_spotlight_d12.md"
echo "T-DIL rows:" && rg -c '^[0-9]+\.' "$BASE/travel_dilemma_d12.md"
echo "T-DIL-G rows:" && rg -c '^[0-9]+\.' "$BASE/mireward_gate_dilemma_d6.md"
echo "T-CF rows:" && rg -c '^[0-9]+\.' "$BASE/travel_campfire_d8.md"

# NPC coverage (T-NPC)
echo "Thrin mentions:" && rg -ci 'thrin' "$BASE/travel_npc_spotlight_d12.md" | head -1
echo "Lysandra mentions:" && rg -ci 'lysandra' "$BASE/travel_npc_spotlight_d12.md" | head -1

# Register updated
rg 'T-NPC|T-DIL|T-CF' "$BASE/README.md" | rg 'ready'

# Allowlist-only diff stat (after commit)
git diff --stat HEAD -- \
  "$BASE/travel_npc_spotlight_d12.md" \
  "$BASE/travel_dilemma_d12.md" \
  "$BASE/mireward_gate_dilemma_d6.md" \
  "$BASE/travel_campfire_d8.md" \
  "$BASE/README.md" \
  "$BASE/session_22_travel_to_mireward_runbook.md"
```

Optional sanity (non-blocking): `rg -i 'dustwalker|confirm.*cult' "$BASE"/travel_*.md "$BASE"/mireward_gate_dilemma_d6.md` — expect **no hits** or only “do not confirm” in How to use.

---

## §8 Reporting contract

PR body must include:

1. **`git diff --stat`** filtered to §4 paths only.
2. **Verbatim §7 output** — row counts, Thrin/Lysandra counts, README `ready` lines.
3. **One paragraph “what stayed unchanged”** — R5/R6 untouched; runbook specs unchanged except status cells; no prompt/eval edits.

---

## §9 Acceptance rubric

- [ ] **T-NPC** has exactly **12** numbered rows — verified by §7 row-count command.
- [ ] **T-DIL** has exactly **12** numbered rows — verified by §7 row-count command.
- [ ] **T-DIL-G** has exactly **6** numbered rows — verified by §7 row-count command.
- [ ] **T-CF** has exactly **8** numbered rows — verified by §7 row-count command.
- [ ] **T-NPC** includes **Thrin ≥2** and **Lysandra ≥2** — verified by §7 `rg -ci` counts (≥2 each).
- [ ] **T-NPC** includes at least one **omen-shaped** Thrin row (wrong silence, horizon rhythm, or shelter/forage read) — verified by reviewer reading row text in PR diff.
- [ ] **T-DIL** rows **1–4** are benign/neutral in tone; **row 12** is highest north-trust stakes — verified by reviewer reading PR diff.
- [ ] **T-DIL-G row 6** is a distinct wildcard gate path — verified by reviewer reading PR diff.
- [ ] All four files have YAML frontmatter (`document_class: planning`, `session: 22`) — verified by reviewer reading PR diff.
- [ ] **README** register shows **`ready`** for T-NPC, T-DIL, T-DIL-G, T-CF — verified by §7 `rg` on README.
- [ ] **No files outside §4** in diff — verified by §7 `git diff --stat` scoped to allowlist.

---

## §10 Out-of-band notes

- **Player rolls at table** — tables are written for GM to read aloud after a player die roll; no GM pre-roll language in How to use.
- **PII:** Campaign corpus may contain player-linked content in dossiers — **read** dossiers for voice; do not paste long dossier excerpts into PR description or commit messages.
- **T-WX (optional d10 weather garnish)** is **out of scope** — reuse R5 21–30 or R6 21–30 per runbook §6.1.
- **Tollers Gap** keyed kit stays in runbook §9; do not author unless a dilemma row explicitly needs a name (prefer generic “abandoned hamlet”).
- If dispatching as **in-IDE subagent**, parent must still read full diff and rerun §7 (see `subagent-delegation.mdc`).

---

## Quick reference — roll order at table (for playtest smoke)

From runbook §7 — worker does not implement code; use to sanity-check table purposes:

```
Per march day:  T-NPC (d12) → R5 (d100) → T-DIL (d12) → night R6 + T-CF (d8)
Arrival:        T-DIL-G (d6) → Mireward §10
```
