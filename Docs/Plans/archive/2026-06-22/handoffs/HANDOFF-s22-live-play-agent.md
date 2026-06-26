# HANDOFF — Session 22 live play agent (resources, retrieval, corpus search)

**Created:** 2026-05-23 (UTC).  
**Status:** ACTIVE — dispatch to any agent assisting **live play**, **between-scene lookup**, or **mid-session prep** for Campaign 2 Session 22.  
**Campaign:** Longmont C2 — Questionable Company.  
**Table canon through:** Session **21** (`Session 21 - Drake Nest Mirathorn Call.md`).  
**Branch / PR:** `cursor/session-22-prep` (PR #70) — corpus prep + roll tables filed.

**Mission:** Give a zero-context agent a **complete map** of where materials live, **when to use retrieval** vs **when to read/search the corpus directly**, and **how to run the tools** without inventing plot or duplicating d100 rows in chat.

---

## §0 Re-anchor (read first)

| Field | Value |
|-------|--------|
| **Session shape** | Travel north on **Mireward Reach** → session ends at **Mireward** gate or first night in town |
| **Party position (S21 end)** | Conical-hill camp **north of Mossford** |
| **Distances** | ~**3 days** south to Mirathorn · ~**5 days** north to Mireward · ~**10 days** rough to swamp objective |
| **Weather** | Western storm front — **player T-WX (d20)** each march day (`travel_storm_weather_d20.md`); runbook §3.3 optional GM fallback only if not rolling |
| **Route intent** | **Press north**; Mirathorn turnaround only if table reopens comms |
| **Primary at-table doc** | `corpus/.../Session Prep/session_22/session_22_travel_to_mireward_runbook.md` |
| **Notes discipline** | **§11** — where to keep travel clock, knobs, staging, recap, roll logs |
| **Session memory indexed** | **S20 + S21 only** (170 records) — **not** S1–S19, **not** hubs, **not** d100 tables |
| **Corpus root** | `corpus/eldyrwild-markdown/` (all paths below are relative to this unless noted) |

**Corpus PII:** Real-player notes live in corpus files. Do not paste long recap excerpts into web tools or external services. See `.cursor/rules/corpus-pii-and-llm-payloads.mdc`.

---

## §1 Three agent modes

| Mode | Goal | Primary tools | Avoid |
|------|------|-------------|--------|
| **Live play assist** | Answer GM/player lookup mid-scene | **Read roll-table files**, runbook §2.1/§7, journey tracker | Re-running full retrieval for every question; inventing d100 rows; GM-scripting T-WX |
| **Between-scene prep** | Refresh NPC beat, continuity, “what do we know about X?” | **Retrieval packet** → **hub README** → dossier/timeline | Treating retrieval snippets as full canon without opening cited recap |
| **Post-session** | Recap-write, journey update, register | `.cursor/skills/recap-write/SKILL.md`, **§11** notes discipline, P0 README promotion rules | Editing dossiers/statblocks as session writeup |

---

## §2 At-table read order (GM — not for provisioning to players)

Use this order when **running** Session 22. Agents **open these files** when asked; do not paste multi-step runbooks into player-facing chat.

| # | Path | Role |
|---|------|------|
| 1 | `Longmont Campaign/Campaign 2/Session Recaps/Session 21 - Drake Nest Mirathorn Call.md` | **Table canon** — end state |
| 2 | `Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_travel_to_mireward_runbook.md` | **Runnable plan** — runtime §2.1 (3+ hr), T-WX §3.3, rolls §6–§7, Mireward §10 |
| 3 | `Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_prep_brief.md` | NPC depth, Saints ladder, proof ledger |
| 4 | `Longmont Campaign/Campaign 2/Journey - Mireward Reach (Campaign 2).md` | Distances, weather rows — **update after long rests** |
| 5 | Roll tables (§4) — **read row from file after player roll** | Encounters, dilemmas, camp |
| 6 | `Longmont Campaign/Campaign 2/Session Prep/Session 22 - open GM knobs.md` | Decide-before-payoff only |
| 7 | `Elderwyld/Cities and Towns/Mireward/Mireward_PLACE_BUILD_SCAFFOLD.md` | Town depth beyond runbook §10 |

**Skip at table:** `Docs/Plans/HANDOFF-*.md` (except this doc for agents), `evals/**` JSON traces, `Backlog.md`.

---

## §3 Complete material index

Paths relative to `corpus/eldyrwild-markdown/` unless noted. Repo-only paths prefixed with `DungeonMindBuddy/`.

### 3.1 Session 22 planning package (`Session Prep/session_22/`)

| ID | File | Status | Use |
|----|------|--------|-----|
| **P0** | `README.md` | draft hub | Artifact register, phases, promotion rules |
| **P1** | `../Session 22 - open GM knobs.md` | draft | Unresolved GM decisions |
| **P2** | `session_22_prep_brief.md` | ready | NPC threads, pressure clocks, retrieval command |
| **P2a** | `session_22_planning_anchor.md` | ready | Where-we-are snapshot |
| **P2b** | `session_22_travel_to_mireward_runbook.md` | ready | **Primary runbook** |
| **T-NPC** | `travel_npc_spotlight_d12.md` | ready | Mandatory NPC beat — **player d12** |
| **T-DIL** | `travel_dilemma_d12.md` | ready | Travel dilemma — **player d12** |
| **T-DIL-G** | `mireward_gate_dilemma_d6.md` | ready | Gate dilemma — **player d6** |
| **T-CF** | `travel_campfire_d8.md` | ready | Campfire RP — **player d8** |
| **T-WX** | `travel_storm_weather_d20.md` | ready | Storm weather — **player d20** (1×/march day) |
| **T-WATCH** | `travel_night_watch_d12.md` | ready | Night watch — **on-duty player d12** (1×/watch) |

**Staging (pre-recap paste):** `_ingest_staging/session_22_raw_notes.md` (**S22-staging**) — not canon until C3; see **§11**.

### 3.2 World / travel reference (evergreen)

| ID | Path | Use |
|----|------|-----|
| **R1** | `Longmont Campaign/Campaign 2/Journey - Mireward Reach (Campaign 2).md` | Journey clock |
| **R5** | `Elderwyld/Roads/mireward_reach_road_d100_encounter_table.md` | Road encounter — **player d100** (beat bands in runbook §6.2) |
| **R6** | `Elderwyld/Wilderness/conical_hills_night_camp_d100.md` | Night camp depth — **optional 1× d100/night** (T-WATCH is per-watch primary) |
| — | `Elderwyld/Roads/README.md` | Roads index |
| — | `Elderwyld/Wilderness/pre_era_conical_hills_d20_find.md` | Optional hill detour |
| — | `Elderwyld/Wilderness/geomantic_drake_nest_loot_d100.md` | Drake nest (S21 done; reference) |

### 3.3 Locations & place-build

| ID | Path | Canon |
|----|------|-------|
| **R3** | `Elderwyld/Cities and Towns/Mireward/README.md` | Hub index (scaffold) |
| **R3b** | `Elderwyld/Cities and Towns/Mireward/Mireward_PLACE_BUILD_SCAFFOLD.md` | **Planning only** until promoted |
| **R4** | `Elderwyld/Cities and Towns/Edge of the World/README.md` | Far-north rumor stub |
| **R2** | `Longmont Campaign/Campaign 2/Mirathorn — While You Were Away.md` | Turn-back / comms (timeline **GM TODO**) |

### 3.4 Table canon & memory index

| ID | Path | Role |
|----|------|------|
| **C1** | `Longmont Campaign/Campaign 2/Session Recaps/Session 21 - Drake Nest Mirathorn Call.md` | **Promoted play recap** |
| **C2** | `.../Session Recaps/_session_memory/Session 20 - Gnat Swarm Marla Lysandra.records_meta.jsonl` | Retrieval index |
| **C2** | `.../Session Recaps/_session_memory/Session 21 - Drake Nest Mirathorn Call.records_meta.jsonl` | Retrieval index |
| — | `.../_normalized/Session 21 - Drake Nest Mirathorn Call.md` | Normalized recap (pipeline) |
| — | `.../_breadcrumbed/Session 21 - *.breadcrumbed.md` | Breadcrumb artifact |
| **S22 staging** | `Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md` | **Pre-recap paste only** — not canon until C3 (create when ingesting) |

**Not indexed for retrieval:** Session recaps **S1–S19** (markdown may exist; no `_session_memory` JSONL for C2 except S20–S21).

### 3.5 PCs & active NPCs (hub-first)

| Entity | Hub path |
|--------|----------|
| **Thrin Branchborn** | `Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/README.md` |
| **Captain Lysandra Ironveil** | `Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/README.md` |
| **Caelynn** | `Longmont Campaign/Campaign 2/PCs/caelynn/` |
| **Ephanna, Stafl, Bonogo, Karsemine** | `Longmont Campaign/Campaign 2/PCs/<slug>/` |
| **Frank / Sara (Mirathorn ops)** | `Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/` |
| **Dustwalker** | `Longmont Campaign/Campaign 2/NPCs/dustwalker/README.md` |

**Convention:** Open hub `README.md` → follow **Suggested reads** → statblock before citing CR/AC/HP.

### 3.6 Factions, music, north pressure

| Topic | Path |
|-------|------|
| **Raucous Saints** (Celtic-punk misdirection) | `Longmont Campaign/Campaign 2/Factions/Raucous_Saints_of_the_Rolling_Longhouse.md` |
| **Shepherd / cult pressure** | `Elderwyld/Shephards Flock/` (world layer — **not in session memory**) |
| **C2 narrative ledger** | `Longmont Campaign/Campaign 2/Elderwyld_Narrative_Ledger_Campaign2.md` |

### 3.7 Loot & props (S21)

| Item | Path |
|------|------|
| **Boots of Crowing Wings** | `Longmont Campaign/Campaign 2/Homebrew Items/Item_ Boots of the Crowing Wings.md` |
| Player copy | `.../Player Copies/Player Copy Item_ Boots of the Crowing Wings.md` |
| Bonogo loot log | `Longmont Campaign/Campaign 2/PCs/bonogo/loot_geomantic_drake_nest.md` |
| Plot artifact stub | `Longmont Campaign/Campaign 2/Plot Artifacts/boots_of_crowing_wings.md` |

### 3.8 Repo-only (agents, not table canon)

| Path | Role |
|------|------|
| `DungeonMindBuddy/Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-s22-live-play-agent.md` | **This file** |
| `DungeonMindBuddy/Docs/Plans/HANDOFF-session-22-travel-north-active-NPCs.md` | Legacy path index |
| `DungeonMindBuddy/Docs/Plans/HANDOFF-s22-travel-roll-tables.md` | Roll-table build handoff (done) |
| `DungeonMindBuddy/Docs/Plans/HANDOFF-prep-agent-c2-ingest-s21-plan-s22-cursor-first.md` | Ingest + retrieval pipeline deep dive |
| `DungeonMindBuddy/Event Table Design Guidance.md` | Table authoring principles |
| `DungeonMindBuddy/Making Travel Sessions Memorable and Fun in TTRPGs.md` | Travel design source for P2b |
| `DungeonMindBuddy/evals/c2_live_prep/` | Retrieval smoke harness + artifacts |

---

## §4 Roll procedure at table (player dice)

From **P2b §7**. **Players roll everything** in the daily stack — including weather (**T-WX**). Do not GM-narrate a fixed five-day weather spine unless the table explicitly opts into runbook §3.3 fallback (compressed arc, no T-WX).

**Session length (~3+ hr):** runbook **§2.1** — typical shape is beat 0 + **2 march days** + arrival, with **2× (4 T-WATCH + T-CF)** night blocks. Merge march beats if time is tight; **still roll — don't GM-pick rows**.

**Per march day (beats 1–3):**

```
1. Player — T-WX (d20)  → travel_storm_weather_d20.md
2. Player — T-NPC  (d12)  → travel_npc_spotlight_d12.md
3. Player — R5     (d100, beat band §6.2) → mireward_reach_road_d100_encounter_table.md
4. Player — T-DIL  (d12)  → travel_dilemma_d12.md
5. Night — assign 4 watches; each on-duty player — T-WATCH (d12); once at fire — T-CF (d8); optional 1× R6
```

**Arrival (beat 4):** **T-WX (d20)** *or* §3.7 gate layer (pick one) → **T-DIL-G (d6)** → runbook §10 Mireward reveal.

### Roll lookup discipline

**Read the row from the markdown file** — do not paraphrase from memory or regenerate in chat.

**Two file shapes:**

| Tables | Format | Lookup |
|--------|--------|--------|
| **T-NPC, T-DIL, T-CF, T-WX, T-WATCH, T-DIL-G** | Markdown pipe rows `\| N \| … \|` | `rg -n '^\| 16 \|' "<file>"` |
| **R5, R6** | Band headings + paragraph entries (not `\| N \|` or `N.`) | Open the **band section** for the rolled number (e.g. roll 28 → read **§21–30 Weather** in R5) |

```bash
# Session 22 tables (pipe rows)
rg -n '^\| 16 \|' "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_storm_weather_d20.md"
rg -n '^\| 10 \|' "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_dilemma_d12.md"

# R5 — find band header, then read entries in that section
rg -n '^## 21–30' "corpus/eldyrwild-markdown/Elderwyld/Roads/mireward_reach_road_d100_encounter_table.md"
```

**T-WX + R5 overlap:** If R5 lands in band **21–30** the same day as a T-WX roll, treat **T-WX as macro weather** and R5 as **road encounter texture** — do not re-read duplicate weather flavor from both (`travel_storm_weather_d20.md` footer rule).

**R5 beat bands** (reroll once if outside window): beat 1 → 01–30 · beat 2 → 11–60 · beat 3 → 11–40 or 31–70 (pick one for session; log in R1).

**T-DIL row 10 (ransacked hamlet rumor):** The **tanner is an in-row NPC only** — no dossier, no map pin. The **hamlet is unnamed** until the party commits to a detour. If they verify → runbook **§9 Tollers Gap** kit or R5 §31–40 texture; **name in recap**. If they press north → gossip may reach Mireward harder. Read `travel_dilemma_d12.md` **Row 10 grounding** before play.

---

## §5 Authority layers (what wins)

| Layer | Wins for | Examples |
|-------|----------|----------|
| **Session recap** | Facts of play | S21 recap > prep brief if they disagree |
| **Hub README + dossier/timeline/statblock** | Entity truth | Lysandra timeline, Thrin dossier |
| **World Eldyrwyld refs** | Setting evergreen | Road d100, conical hill camp d100 |
| **Session Prep / scaffold** | Intent, not yet played | Mireward scaffold, open GM knobs, runbook |
| **Session memory retrieval** | **Hints + unit_ids** — open recap for full prose | Snippets in smoke JSON |
| **Brainstorm / HANDOFF** | GM tone only | `Session 21 - brainstorming dump.md` |

---

## §6 What retrieval indexes — and what it does **not**

### Indexed today (C2 live prep)

| Surface | Scope | Record count (2026-05-23) |
|---------|--------|---------------------------|
| **Session memory JSONL** | **S20 + S21** recap units only | **170** records |
| **Retrieval mode** | `prior_only` — no oracle/support cards for C2 | |
| **Stack** | PR58–67 lane routing → query variants → budgeted admission | |

**Source files:**

```
Longmont Campaign/Campaign 2/Session Recaps/_session_memory/
  Session 20 - Gnat Swarm Marla Lysandra.records_meta.jsonl
  Session 21 - Drake Nest Mirathorn Call.records_meta.jsonl
```

### **Not** in retrieval index (must use corpus search / full read)

| Content | Why | What to do instead |
|---------|-----|-------------------|
| **Sessions 1–19** recaps | No C2 `_session_memory` materialized | Read `Session Recaps/Session NN - *.md` directly |
| **NPC/PC hub dossiers, timelines, statblocks** | Hub chunk index is **C1 allowlist only** | Hub README → suggested reads |
| **All d100 / d12 / d8 roll tables** | Not ingested | Read file after roll |
| **Mireward scaffold, journey doc, runbook** | Planning markdown | Read path from §3 |
| **Shepherd's Flock deep lore** | World corpus, sparse in S20–S21 memory | `Elderwyld/Shephards Flock/`, Dustwalker hub |
| **Raucous Saints module** | Faction doc | `Factions/Raucous_Saints_of_the_Rolling_Longhouse.md` |
| **Mirathorn away timeline** | Stub — GM TODO | `Mirathorn — While You Were Away.md` + S20–S21 recaps |
| **Eval gold / harness JSON** | Forbidden in planner-visible text | Never inject into player/GM prompts |

### Known retrieval gaps (documented smoke)

| Gap | Symptom | Fix |
|-----|---------|-----|
| **Thrin under-ranked** | Thrin questions return Caelynn/Lysandra/location meta | Read `NPCs/thrin_branchborn/` + **T-NPC** table |
| **Storm / travel tables** | Low admitted count for weather questions | **T-WX** roll table + P2b §3; R5 band 21–30 for encounter texture only |
| **Shepherd / swamp** | Weak or absent in S20–S21 memory | Corpus read: ledger §1/§8, Sheriff Marr beat in S21 recap |
| **Mireward town detail** | Not in memory | Scaffold + runbook §10 |

---

## §7 Retrieval tools — how to run

### 7.1 Batch smoke (pre-built questions)

Runs **6 default prep questions**; writes JSON + markdown report.

```bash
cd DungeonMindBuddy
uv run python evals/c2_live_prep/smoke_retrieval_packets.py
```

**Default output:** `evals/c2_live_prep/artifacts/runs/YYYY-MM-DD/`

| Output | Contents |
|--------|----------|
| `c2s22_smoke_report.md` | Human-readable admitted snippets |
| `c2s22_smoke_summary.json` | Per-question admit counts |
| `{question_id}.json` | Full packet: `admitted_context`, `rendered_context_packet`, `source_derived_context_gaps` |
| `c2s22_probe_index.json` | Index of extra probes (Lysandra, Thrin, storm) |

**Pre-built question IDs:** `active_npcs_thrin_lysandra`, `mirathorn_turnaround`, `travel_north_mireward`, `raucous_saints_dustwalker`, `boots_crowing_wings`, plus probes in probe index.

### 7.2 Ad-hoc question (single packet)

Reuse the harness module (same as smoke script):

```python
# Run from repo root: uv run python -c '...'
from evals.c2_live_prep.smoke_retrieval_packets import (
    build_live_prep_packet,
    load_c2_combined_records,
)
import json

combined, by_id, sources = load_c2_combined_records((20, 21))
q = "YOUR NATURAL LANGUAGE QUESTION HERE"
packet = build_live_prep_packet(
    question=q,
    question_id="live_adhoc",
    combined_records=combined,
    records_by_unit_id=by_id,
)
print(packet["rendered_context_packet"][:4000])
print("--- gaps ---", packet.get("source_derived_context_gaps"))
```

**Review order:** `admitted_context` → `source_derived_context_gaps` → open recap paths cited by `unit_id` → hub README if entity-focused.

### 7.3 Planner REPL (`dmb plan`) — optional

```bash
cd DungeonMindBuddy
uv run python -m src.cli
# REPL: plan --corpus-dir corpus/eldyrwild-markdown
```

Tools: `read_corpus_file`, `load_context_markdown`, `query_session_memory` (when env configured).

**Session memory env:** `DUNGEONMIND_SESSION_MEMORY_RECORDS_JSONL` points to **one** JSONL file. Live prep smoke **merges S20+S21** in Python — for `dmb plan` either:

- Point env at S21 JSONL only (recent bias), or  
- Concatenate S20+S21 into a temp combined JSONL for the REPL session.

**Prefer** §7.1–§7.2 in Cursor for bounded prep packets; use REPL when simulating full planner discovery.

### 7.4 What to do with a packet

1. Read **`rendered_context_packet`** — bounded prior memory.  
2. Check **`source_derived_context_gaps`** — flags missing corpus classes.  
3. For each important **`unit_id`**, open the **Session 20/21 recap** prose (retrieval gives snippets, not authority).  
4. If gaps mention entities/locations, open **hub README** next.  
5. **Never** treat retrieval alone as sufficient for mechanical stats or full NPC voice — read dossier/statblock.

---

## §8 Corpus search when retrieval is the wrong tool

Use this ladder when the question is **not** “what happened in S20–S21 recap units.”

```
1. SymDex symbol/outline (if index fresh) — hub README, known modules
2. Hub README first — NPCs/<slug>/README.md, location README
3. rg / Grep — exact strings, roll rows, names
4. Read — dossier, timeline, statblock, full recap
5. Retrieval (§7) — only for S20–S21 continuity compression
```

### 8.1 SymDex / repo navigation (Cursor agent)

Per `AGENTS.md` / `.cursor/rules/token-efficient-navigation.mdc`:

1. Symbol search for known functions or file names when debugging **code**.  
2. **File outline** before full read on large files.  
3. **Literal grep** for NPC names, place names, d100 row numbers, `Session NN`.  
4. **Semantic search** when exact string unknown.  
5. **Read** smallest relevant region.

### 8.2 Grep patterns (corpus)

```bash
CORPUS="corpus/eldyrwild-markdown"
CAMPAIGN="$CORPUS/Longmont Campaign/Campaign 2"

# NPC hub
rg -l "thrin" "$CAMPAIGN/NPCs"

# All Session 21 mentions in campaign tree
rg -n "Session 21" "$CAMPAIGN"

# Shepherd / meat / hymn (north pressure)
rg -n -i "shepherd|dustwalker|hymn|choir" "$CORPUS/Elderwyld" "$CAMPAIGN"

# Roll row — Session 22 pipe tables
rg -n '^\| 7 \|' "$CORPUS/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_night_watch_d12.md"

# R5 — band section (roll 57 → open ## 51–60 or nearest band header)
rg -n '^## [0-9]+' "$CORPUS/Elderwyld/Roads/mireward_reach_road_d100_encounter_table.md"
```

### 8.3 Hub navigation contract

From `.cursor/rules/corpus-layout-conventions.mdc`:

1. **`README.md`** in entity folder — suggested reads, statblock priority table.  
2. **Statblock** before citing CR/HP/AC.  
3. **`timeline.md`** for session pointers — opens correct recap file.  
4. **No globs** in paths copied to tools — exact paths from README only.

### 8.4 Corpus tree entry points

| Entry | Path |
|-------|------|
| Campaign 2 root | `Longmont Campaign/Campaign 2/` |
| Session recaps | `Longmont Campaign/Campaign 2/Session Recaps/` |
| Session prep | `Longmont Campaign/Campaign 2/Session Prep/` |
| NPCs | `Longmont Campaign/Campaign 2/NPCs/` |
| PCs | `Longmont Campaign/Campaign 2/PCs/` |
| Eldyrwyld roads | `Elderwyld/Roads/` |
| Eldyrwyld wilderness | `Elderwyld/Wilderness/` |
| Towns | `Elderwyld/Cities and Towns/` |

---

## §9 Topic → where to look (decision matrix)

| Question type | First open | If insufficient |
|---------------|------------|-----------------|
| **Where is party / distances / weather clock** | S21 recap + R1 journey + P2a anchor | — |
| **What to run this scene (travel)** | P2b runbook §7 + roll table file | P2 prep brief |
| **Thrin beat today** | **T-NPC d12** + Thrin hub README + dossier | S21 recap (shelter, rainbow) |
| **Lysandra / Caelynn / comms** | S21 recap + Lysandra hub + smoke `lysandra_state_probe.json` | `Mirathorn — While You Were Away.md` |
| **Storm / shimmer rain** | **T-WX** (player d20) + P2b §3.3 | R5 band 21–30 only if encounter roll lands there — don't double-stack with T-WX |
| **Road encounter** | **R5** (player roll, band §6.2) | — |
| **Night camp** | **T-WATCH** (4×/night) + **T-CF** | optional **1× R6**/night; pre_era d20 if probing cone |
| **T-DIL 10 detour / empty hamlet** | `travel_dilemma_d12.md` row 10 note | P2b §9 Tollers Gap kit — **only if party commits** |
| **Mireward at gate** | **T-DIL-G** + P2b §10 + R3b scaffold | — |
| **Music / Saints / cult rumor** | S21 recap (Marr) + Raucous Saints module + Dustwalker hub | Shepherd corpus — **not retrieval** |
| **Boots flight / loot** | R7 item card + Bonogo loot log | — |
| **Mirathorn if turnaround** | S21 recap + R2 stub + smoke `mirathorn_turnaround.json` | Sara hub |
| **Swamp objective / Lysandra brief** | S13 recap (full read) + ledger | Session memory weak — **read recap** |
| **Continuity “what happened last session”** | **C1 S21 recap** | Retrieval optional |

---

## §10 During-play agent rules

1. **Discovery, not provisioning** — do not dump corpus paths or roll procedures into player-facing messages (`.cursor/rules/llm-context-discovery.mdc`).  
2. **Roll tables:** player rolls → agent/GM **reads row from file** (§4) — pipe-row tables and R5 band sections use **different grep shapes**; wrong pattern ≠ missing file.  
3. **Weather is rolled, not scripted** — **T-WX (d20)** each march day unless table opts into §3.3 GM fallback. Storm is normal meteorology and is **not following the party** (table copy).  
4. **Night watches are rolled** — **T-WATCH (d12)** per watch (default 4/night); **R6** at most once per night for extra cone weirdness, not per watch.  
5. **In-row NPCs ≠ keyed locations** — dilemma/encounter NPCs (e.g. T-DIL 10 tanner) exist **only in that table row** until play promotes them. Optional kits (Tollers Gap §9, Mireward scaffold) are **not pre-selected canon**.  
6. **Retrieval:** use for **between-scene** continuity compression, not every rules lookup.  
7. **Do not confirm** Dustwalker, cult canon, or Mirathorn off-screen truth unless table invests investigation time (runbook + prep brief).  
8. **Mireward scaffold** is planning — table facts after play go to **Session 22 recap**, not scaffold edits mid-session. See **§11** for all note surfaces.  
9. **Update R1** after long rests: days elapsed, camp, last **T-WX** row + front position, comms state (runbook §3.6).  
10. **Pace knob:** merge march days if time is short — **still player-roll** every table in the compressed stack; never substitute GM-chosen outcomes for dice.  
11. **Notes go to the right file** — never log roll outcomes in T-* / R5 / R6 table files or treat agent chat as canon (**§11**).

---

## §11 Notes discipline — where to keep and leave notes

Agents and GMs need a single rule: **facts of play live in recaps and their promotion targets; everything else is intent, scratch, or pipeline.**

**At-table quick reference** (GM — corpus paths relative to `Longmont Campaign/Campaign 2/`):

| When | Where |
|------|-------|
| Travel clock / weather / comms | `Journey - Mireward Reach (Campaign 2).md` (**R1**) |
| Must-decide before payoff | `Session Prep/Session 22 - open GM knobs.md` (**P1**) |
| Raw notes before ingest | `_ingest_staging/session_22_raw_notes.md` |
| What actually happened | `Session Recaps/Session 22 - <slug>.md` (**C3**) after play |
| Unrefined ideas | `Session Prep/Session 21 - brainstorming dump.md` — **never canon** |
| Roll prompts | **T-*** / **R5** / **R6** files — **not** a session log |

**Convention:** Read roll rows from table files at table; **do not** append outcomes to those files or leave table decisions only in chat. Promote facts via **C3 recap** (and timeline rows / R1 as appropriate).

Corpus mirror: `Session Prep/session_22/README.md` **§2** (compact table + register row **S22-staging**).

### 11.1 Authority quick rule

| If the note is… | Put it here | Becomes canon when… |
|-----------------|-------------|---------------------|
| **What happened at the table** | Post-play → **C3 recap** only | recap-write commits `Session 22 - <slug>.md` |
| **Travel clock mid-session** | **R1** journey tracker | Reference bookkeeping — recap still wins on narrative facts |
| **Unresolved GM choice before payoff** | **P1** open GM knobs | You write the answer to the knob’s **Canon target** column and clear the row |
| **Raw unrefined GM ideas** | `Session Prep/Session <N> - brainstorming dump.md` | **Never** — tone/north-star only (`source_class: brainstorming_unrefined`) |
| **Runnable prep / roll procedures** | P2b runbook, T-* tables, P2 brief | Table **outcomes** are not logged in these files — only in recap |
| **Town/location design not yet played** | Mireward **scaffold** (R3b) | After play → scaffold §J promotion → gazetteer/dossiers |
| **Mirathorn off-screen beats** | **R2** `Mirathorn — While You Were Away.md` § Timeline | When decided or when recap confirms on-call beats |
| **NPC session pointer** | Hub `timeline.md` row | After recap (timeline-append skill / manual row with recap filename) |
| **Pre-recap paste buffer** | `_ingest_staging/session_22_raw_notes.md` | **Staging only** — input to recap-write, not chronology |
| **Retrieval / eval traces** | `evals/c2_live_prep/artifacts/` | **Never canon** — hints only |

**Recap wins:** If R1, prep brief, or agent chat disagrees with a committed Session 22 recap, the recap is table canon.

### 11.2 During live play — allowed scratch surfaces

Use these **during** Session 22; none replace the post-play recap.

| Surface | Path | What belongs here | What does **not** belong |
|---------|------|-------------------|-------------------------|
| **Journey tracker** | `Journey - Mireward Reach (Campaign 2).md` | Days elapsed, camp location, **T-WX** row + front position, comms `clear/static/dead`, R5 beat-3 band choice for this session, optional hours-traveled | Full scene prose, NPC dialogue, “canon” lore edits |
| **Open GM knobs** | `Session Prep/Session 22 - open GM knobs.md` | Decisions you **must** fix before a beat pays off (e.g. Lysandra’s city contact) | Outcomes that already happened at table — those go to recap |
| **Physical / voice scratch** | *(off corpus)* | OK at table | Must be pasted to staging or recap input **before close-out** — chat alone is lost |
| **Agent chat** | Cursor / Discord | Lookup, read row, continuity compression | **Do not** treat as canonical record; do not leave table decisions only here |

**Do not mid-session edit:** hub dossiers, statblocks, seeds, T-* roll table rows (outcomes aren’t “corrections” to the table), or Mireward scaffold as a substitute for “what the party did.”

**In-row table NPCs** (e.g. T-DIL 10 tanner): exist only in the table until play names or confirms them — **name and promote in recap**, not by editing the dilemma file.

### 11.3 Pre-play and planning-only (intent, not facts of play)

| Surface | Path | Role |
|---------|------|------|
| **Planning hub** | `Session Prep/session_22/README.md` | Register, phases, promotion rules — not a session log |
| **Planning anchor** | `session_22_planning_anchor.md` | Snapshot at prep time; may drift — re-read S21 recap + R1 at table |
| **Prep brief** | `session_22_prep_brief.md` | NPC depth, proof ledger — superseded by **C3** for chronology |
| **Runbook** | `session_22_travel_to_mireward_runbook.md` | Procedure + optional kits — checklist ticks OK; don’t append play-by-play |
| **Brainstorm dump** | `Session Prep/Session 21 - brainstorming dump.md` | GM north-star (pressure, swamp pit vision) — **NOT CANON** |
| **Agent handoffs** | `Docs/Plans/HANDOFF-*.md` | Dispatch and tooling — repo-only, not player/GM lore |
| **Roll tables T-*** | `session_22/travel_*.md` | Row text is **prompt**, not a log of what you rolled last Tuesday |

### 11.4 Post-play promotion pipeline (order matters)

```
1. Paste raw notes (optional) → Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md
2. recap-write → Session Recaps/Session 22 - <slug>.md          (C3 — table canon)
3. normalize → breadcrumb → materialize session memory           (C4 — retrieval index)
4. Update R1 journey tracker (final camp, distances, weather end-state)
5. For each decided P1 knob → write target file; remove/update knob row
6. NPC timeline rows (Thrin, Lysandra, …) → point at C3 recap filename
7. Mireward: promote scaffold §J blocks actually used at table → hub/gazetteer
8. Update P0 README register (C3/C4 status, `played`, `last_updated_session`)
```

**Staging convention:** `{campaign_hub}/_ingest_staging/session_{N}_raw_notes.md` — same pattern as S20/S21 ingest. Recap-write reads staging via `assemble_recap_draft`; do not treat staging as promoted canon.

**Pipeline artifacts — leave in place, do not edit for lore:**

| Path | Role |
|------|------|
| `Session Recaps/_normalized/` | Normalized recap (pipeline) |
| `Session Recaps/_breadcrumbed/` | Breadcrumb artifact |
| `Session Recaps/_session_memory/*.jsonl` | Derived retrieval index — rebuild after C3 |

### 11.5 Forbidden note locations (writer + convention)

| Never store session **facts of play** in… | Why |
|-------------------------------------------|-----|
| `*_character_dossier.md`, `character_seed.md`, `*_statblock*.md` | Static bible — writer denied; session status belongs in recap + timeline |
| Brainstorming dump | Unrefined ideas only |
| Prep brief / runbook alone | Planning docs — recap required |
| T-* / R5 / R6 table files | Prompts, not session logs |
| `evals/**` JSON / smoke reports | Tooling artifacts |
| Agent HANDOFF bodies | Operational, not chronology |

### 11.6 Agent-specific

- **Between scenes:** retrieval + hub reads OK; **do not** write corpus files mid-session unless GM explicitly runs recap-write or updates R1.
- **After session:** follow `.cursor/skills/recap-write/SKILL.md` — one recap create, structured follow-ups in payload (timeline candidates, plot artifacts as **proposals** only).
- **Discovery:** do not paste multi-file promotion runbooks into player-facing chat (`.cursor/rules/llm-context-discovery.mdc`).

---

## §12 Post-session close-out

| Step | Action |
|------|--------|
| 1 | Recap-write → `Session Recaps/Session 22 - <slug>.md` |
| 2 | Normalize → breadcrumb → `scripts/materialize_session_memory.py` for C4 |
| 3 | Update R1 journey tracker |
| 4 | Promote P1 knob rows; update P0 register (C3/C4, `played`) |
| 5 | Mireward: promote scaffold §J blocks used at table |
| 6 | NPC timeline rows for Thrin, Lysandra, Bonogo as needed |

See **§11** and P0 `session_22/README.md` §2–§3 for promotion rules.

---

## §13 Related handoffs & docs

| Doc | When |
|-----|------|
| `HANDOFF-prep-agent-c2-ingest-s21-plan-s22-cursor-first.md` | Full retrieval stack architecture, Phase A/B ingest |
| `DEMO-ARCHITECT-AGENT-MANUAL-c2s21-s22.md` | Packet review rubric, demo readiness |
| `HANDOFF-session-22-travel-north-active-NPCs.md` | Legacy comprehensive path list |
| `HANDOFF-s22-travel-roll-tables.md` | Roll table build spec (completed) |
| `.cursor/skills/recap-write/SKILL.md` | Post-session recap protocol |

---

## §14 Quick verification (agent sanity check)

```bash
cd DungeonMindBuddy

# Session 22 tables — pipe-row format (NOT "N." numbered lists)
BASE="corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22"
declare -A EXPECT=( [travel_npc_spotlight_d12]=12 [travel_dilemma_d12]=12 [mireward_gate_dilemma_d6]=6 \
  [travel_campfire_d8]=8 [travel_storm_weather_d20]=20 [travel_night_watch_d12]=12 )
for f in "${!EXPECT[@]}"; do
  n=$(rg -c '^\| [0-9]+ \|' "$BASE/$f.md" 2>/dev/null || echo 0)
  echo "$f: $n (expect ${EXPECT[$f]})"
done

# R5 — band headers present (paragraph entries, not pipe rows)
rg -c '^## [0-9]+' "corpus/eldyrwild-markdown/Elderwyld/Roads/mireward_reach_road_d100_encounter_table.md"

# Session memory sources
ls "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/"Session\ 2*.jsonl

# Smoke artifacts present
ls evals/c2_live_prep/artifacts/runs/2026-05-23/c2s22_smoke_report.md
```

Expected pipe-row counts: **T-NPC 12 · T-DIL 12 · T-DIL-G 6 · T-CF 8 · T-WX 20 · T-WATCH 12**.

---

## §15 Lessons learned (2026-05-23 prep iteration)

Captured during Session 22 prep review — apply when assisting live play or extending tables.

| Lesson | What we learned | Where it lives |
|--------|-----------------|----------------|
| **Weather must be rollable** | A GM-narrated five-day weather spine reads as preplanned. **T-WX (d20)** gives one unique storm texture per march day; §3.3 fallback is optional compression only. | `travel_storm_weather_d20.md`, P2b §3.3 |
| **Night needs per-watch play** | One R6 d100 per watch is too heavy and too random for 3+ hr sessions. **T-WATCH (d12)** ×4 + **T-CF (d8)** at fire; **R6** optional 1×/night. | `travel_night_watch_d12.md`, P2b §6.4 |
| **Table grep shapes differ** | Sanity check `^[0-9]+\.` returns **0** for Session 22 tables — they use `\| N \|` pipe rows. R5/R6 use **band headings + paragraphs**, not numbered lines. | §4, §14 |
| **In-row NPCs aren't keyed** | T-DIL 10's tanner has **no dossier**; the hamlet has **no name** until detour play. Don't invent backstory from retrieval gaps — read row grounding note. | `travel_dilemma_d12.md`, P2b §9 |
| **Optional kits ≠ canon** | Tollers Gap, Mireward scaffold, open GM knobs are **planning until recap promotes**. Agent must not treat them as facts of play. | P2b §9, §10; P1 knobs |
| **T-WX + R5 21–30** | Same-day double weather is redundant. T-WX = macro; R5 band = encounter on the road. | T-WX footer rule |
| **3+ hr session shape** | Beat 0 + 2 march days + arrival ≈ minimum bar; ~45–60 min/march day, ~25–35 min/night. Full five-day arc needs 4+ hr or merged beats. | P2b §2.1, §11 checklist |
| **Retrieval gaps are expected** | Thrin, storm tables, Shepherd lore, Mireward detail — **read corpus**, don't expect S20–S21 memory to cover prep tables. | §6 |
| **Notes discipline** | Roll outcomes, scene facts, and NPC beats belong in **R1 scratch + C3 recap** — not in T-* table files, prep brief, dossiers, or agent chat. Staging → recap-write → C4 memory. | §11; P0 README §2 |
