---
title: "Session 22 — planning package (hub index)"
document_class: planning
canon_layer: campaign
campaign_id: longmont-c2
temporal_scope: session_specific
session: 22
origin_session: 21
last_updated_session: 21
source_class: scene_module
table_note: "Planning hub only — not table canon. After Session 22 play, promote facts via recap + timeline rows; do not treat this README as chronology."
---

# Session 22 — planning package

**Campaign:** Longmont Campaign 2 (Questionable Company)  
**Prep target:** Session **22** (travel north on the Mireward Reach after Session 21 drake nest / Mirathorn comms)  
**Table canon through:** `Session Recaps/Session 21 - Drake Nest Mirathorn Call.md`

This folder is the **GM-facing index** for everything produced while planning Session 22: what exists, what is still missing, and where decided facts should land after play.

---

## 1. Suggested reads (in order)

1. `Longmont Campaign/Campaign 2/Session Recaps/Session 21 - Drake Nest Mirathorn Call.md` — **table canon** for party end-state.
2. `Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_travel_to_mireward_runbook.md` — **primary runnable plan** (T-WX, travel beats, dilemmas, Mireward arrival toolkit).
3. `Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_planning_anchor.md` — where-we-are snapshot (read stack, Mireward state, drift notes).
4. `Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_prep_brief.md` — runnable Session 22 plan + proof ledger.
5. `Longmont Campaign/Campaign 2/Session Prep/Session 22 - open GM knobs.md` — unresolved GM decisions (not lore until written elsewhere).
6. `Longmont Campaign/Campaign 2/Journey - Mireward Reach (Campaign 2).md` — distances, terrain; **update during play** for clock / weather / comms.
7. `Longmont Campaign/Campaign 2/Mirathorn — While You Were Away.md` — if party turns back or calls Mirathorn again.
8. `Longmont Campaign/Campaign 2/Mirathorn — rockie-talkie comms timeline.md` — full wire log + city-day / march-day comms tables.
8. `Elderwyld/Cities and Towns/Mireward/Mireward_PLACE_BUILD_SCAFFOLD.md` — design scaffold (not table canon).
9. `Longmont Campaign/Campaign 2/Session Prep/session_22/README.md` — **this file** (artifact register, promotion rules, **§2 notes table**).

**Repo-only (agents):** `DungeonMindBuddy/Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-s22-live-play-agent.md` — live-play index, retrieval vs corpus search, **§11 notes discipline**.

---

## 2. Authority (what becomes canon)

| Layer | Rule |
|-------|------|
| **Play** | After Session 22, one canonical recap: `Session Recaps/Session 22 - <slug>.md` (via recap-write). **Recap wins** on facts of play. |
| **Planning** | Files under `Session Prep/` and this README are **not canon**. Tone and intent only until promoted. |
| **Reference** | Hubs, journey tracker, item cards, d100 tables — canon for **world/mechanics**; update when planning decisions land (e.g. Mireward town content). |
| **Derived** | `_session_memory/*.records_meta.jsonl` — retrieval index; re-materialize after recap or breadcrumb changes. |

**Promotion rule:** When a knob in `Session 22 - open GM knobs.md` is decided, write the answer into the **Canon target** column below (or in the register), then remove or update the knob row. Do not leave table decisions only in chat or in the prep brief.

### Where to keep notes (Session 22)

Full agent runbook: `DungeonMindBuddy/Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-s22-live-play-agent.md` **§11**.

| When | Where | Canon? |
|------|-------|--------|
| **Travel clock / weather / comms** | `Journey - Mireward Reach (Campaign 2).md` (**R1**) | Reference scratch; recap wins on story |
| **Must-decide before payoff** | `Session Prep/Session 22 - open GM knobs.md` (**P1**) | Promote to target column when decided |
| **Raw paste before recap** | `_ingest_staging/session_22_raw_notes.md` (**S22-staging**) | Staging only → feeds recap-write |
| **After play — what happened** | `Session Recaps/Session 22 - <slug>.md` (**C3**) | **Yes — table canon** |
| **Unrefined GM ideas** | `Session Prep/Session 21 - brainstorming dump.md` | **No** — north-star only |
| **Roll prompts** | **T-*** / **R5** / **R6** table files | Prompts & intent — **not** a roll log |
| **Agent chat, eval JSON** | — | **Never** canon |

**Convention:** Read roll rows from table files at table; **do not** append roll outcomes to those files or leave table decisions only in chat. Promote facts via **C3 recap** (and timeline rows / R1 as appropriate).

**Do not** store session facts in dossiers, statblocks, roll-table files, or prep docs instead of C3.

---

## 3. Artifact register

**Prep status:** `missing` · `draft` · `ready` · `played`  
**Canon status:** `n/a` (planning-only) · `reference` (already world canon) · `promote_after_play` · `promoted`

| ID | Artifact | Path | Prep status | Canon status | After Session 22 |
|----|----------|------|-------------|--------------|------------------|
| **P0** | Planning hub (this file) | `Session Prep/session_22/README.md` | draft | n/a | Update register; archive or bump `last_updated_session` |
| **P1** | Open GM knobs | `Session Prep/Session 22 - open GM knobs.md` | draft | promote_after_play | Promote each decided row; empty file → delete or mark done |
| **P2** | Prep brief | `Session Prep/session_22/session_22_prep_brief.md` | **ready** | n/a | Superseded by recap for chronology; keep as historical prep if useful |
| **P2a** | Planning anchor | `Session Prep/session_22/session_22_planning_anchor.md` | **ready** | n/a | Where-we-are snapshot |
| **P2b** | **Travel → Mireward runbook** | `Session Prep/session_22/session_22_travel_to_mireward_runbook.md` | **ready** | n/a | Roll registry §6 + §7 procedure; player rolls R5/R6 + tables below |
| **P3** | Retrieval smoke report | `evals/c2_live_prep/artifacts/runs/2026-05-23/c2s22_smoke_report.md` | ready | n/a | Repo artifact; optional link in proof ledger |
| **P3b** | Targeted probes (Lysandra, Thrin, storm) | `evals/c2_live_prep/artifacts/runs/2026-05-23/{lysandra_state_probe,thrin_foreground,storm_travel}.json` | ready | n/a | Follow-on smoke; index in `c2s22_probe_index.json` |
| **P4** | Agent live-play handoff | `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-s22-live-play-agent.md` | **ready** | n/a | Primary agent entry for S22 play + lookup |
| **P4b** | Legacy agent index | `Docs/Plans/HANDOFF-session-22-travel-north-active-NPCs.md` | draft | n/a | Superseded by P4 for retrieval/corpus ladder |
| **R1** | Journey tracker | `Journey - Mireward Reach (Campaign 2).md` | draft | promote_after_play | Update distances / camp location after play |
| **R2** | Mirathorn away + comms + **dual-front arc** | `Mirathorn — While You Were Away.md`, `Mirathorn — rockie-talkie comms timeline.md`, `Campaign 2 — Dual Front Shepherd Arc (GM planning).md` | **ready** | promote_after_play | Promote wire beats + any **proven** truths to recap |
| **R3** | Mireward hub | `Elderwyld/Cities and Towns/Mireward/` + `Mireward_PLACE_BUILD_SCAFFOLD.md` | **scaffold** | planning → reference | Promote via checklist in scaffold §J |
| **R4** | Edge of the World hub | `Elderwyld/Cities and Towns/Edge of the World/README.md` | draft | promote_after_play | Expand if sheriff rumor pays off |
| **R5** | Travel d100 (road) | `Elderwyld/Roads/mireward_reach_road_d100_encounter_table.md` | ready | reference | Use at table; do not duplicate rows in prep |
| **R6** | Night camp d100 | `Elderwyld/Wilderness/conical_hills_night_camp_d100.md` | ready | reference | Same |
| **T-NPC** | NPC spotlight d12 | `Session Prep/session_22/travel_npc_spotlight_d12.md` | **ready** | n/a | Mandatory 1×/day — P2b §6.3 |
| **T-DIL** | Travel dilemma d12 | `Session Prep/session_22/travel_dilemma_d12.md` | **ready** | n/a | P2b §6.5 |
| **T-DIL-G** | Gate dilemma d6 | `Session Prep/session_22/mireward_gate_dilemma_d6.md` | **ready** | n/a | P2b §6.6 |
| **T-CF** | Campfire prompt d8 | `Session Prep/session_22/travel_campfire_d8.md` | **ready** | n/a | P2b §6.7 |
| **T-WX** | Storm weather d20 | `Session Prep/session_22/travel_storm_weather_d20.md` | **ready** | n/a | **1×/march day** before T-NPC — P2b §3.3, §7 |
| **T-WATCH** | Night watch d12 | `Session Prep/session_22/travel_night_watch_d12.md` | **ready** | n/a | **1×/watch** (4/night) — P2b §6.4 |
| **T-COMMS** | Mirathorn retry d100 | `Session Prep/session_22/travel_mirathorn_comms_d100.md` | **ready** | n/a | Roll on explicit Mirathorn retry / T-DIL 7 / T-WATCH 1 or 7 / Lysandra comms beat |
| **—** | Table authoring guide | `Event Table Design Guidance.md` (repo root) | reference | n/a | P2b §6.0 maps principles → Session 22 tables |
| **R7** | Boots / nest loot | `PCs/bonogo/loot_geomantic_drake_nest.md` + printed card / `Homebrew Items/Item_ Boots of the Crowing Wings.md` | **done** | reference | Synced to CardGenerator card 2026-05-23 |
| **R8** | Raucous Saints module | `Factions/Raucous_Saints_of_the_Rolling_Longhouse.md` | ready | reference | Seed/ladder in prep brief; not in session memory yet |
| **C1** | Session 21 recap | `Session Recaps/Session 21 - Drake Nest Mirathorn Call.md` | ready | **promoted** | Input only |
| **C2** | Session 21 memory | `Session Recaps/_session_memory/Session 21 - …records_meta.jsonl` | ready | derived | Rebuild if S21 recap edits |
| **C3** | Session 22 recap | `Session Recaps/Session 22 - <slug>.md` | **missing** | promote_after_play | **Create after play** (recap-write); see §2 notes table |
| **C4** | Session 22 memory | `Session Recaps/_session_memory/Session 22 - …jsonl` | **missing** | derived | normalize → breadcrumb → materialize after C3 |
| **S22-staging** | Raw notes (pre-recap) | `_ingest_staging/session_22_raw_notes.md` | **ready** | n/a | Paste buffer only — not canon until C3 |

---

## 4. Planning phases (this session’s workstream)

| Phase | Goal | Status | Evidence |
|-------|------|--------|----------|
| **A** | Ingest Session 21 → recap + session memory | done | S21 recap + JSONL on disk; `--check` OK |
| **B-smoke** | PR58–67 retrieval over S20+S21 memory | done | `evals/c2_live_prep/artifacts/runs/2026-05-23/` |
| **B-prep** | Prep brief + proof ledger | **done** | P2 `session_22_prep_brief.md` |
| **B-comms** | T-COMMS Mirathorn retry d100 | **done** | `travel_mirathorn_comms_d100.md` |
| **Play** | Run Session 22 at table | pending | C3 missing |
| **Post** | Recap, timeline rows, journey update, register | pending | — |

---

## 5. Active prep themes (from GM intent)

Track in prep brief (P2) when written; pointers only here.

| Theme | Corpus anchors | Register |
|-------|----------------|----------|
| **Thrin foreground** | `NPCs/thrin_branchborn/` | One beat per session in P2 §3 |
| **Lysandra weird week** | `NPCs/captain_lysandra_ironveil/` | P1 knob: city investigation target |
| **Mirathorn if turnaround** | `Mirathorn — While You Were Away.md`, S21 open loops, `travel_mirathorn_comms_d100.md` | R2 / T-COMMS |
| **Travel north + storm** | `Journey - Mireward Reach…`, d100 R5–R6 | R1 |
| **Music / Saints vs Dustwalker** | `Factions/Raucous_Saints…`, S21 sheriff beat | R8; not in retrieval index alone |
| **Boots of Crowing Wings** | Bonogo loot log + item card | R7, P1 |

---

## 6. Conventions for future sessions (`session_<N>/`)

Reuse this package shape for Session 23+:

```
Session Prep/session_<N>/
  README.md                 ← hub index (this pattern)
  session_<N>_prep_brief.md ← single runnable prep doc (optional until written)
```

- Keep **one** `session_<N>_prep_brief.md` per session (recap-write resolver convention).
- Keep **GM knobs** as sibling `Session <N> - open GM knobs.md` or fold into README §3 when small.
- **Do not** store table outcomes only in prep — recap + timeline promotion is the close-out.
- **Do not** store table outcomes in roll-table files or agent chat — see §2 notes table and HANDOFF §11.
- Agent/dispatch indexes stay in `Docs/Plans/HANDOFF-*.md`; this README links them but lives in corpus for GM + planner discovery.

---

## 7. Quick checklist before running Session 22

- [x] P2b travel runbook `ready` (primary at-table doc)
- [x] P2 prep brief `ready` (NPC / Saints detail)
- [x] T-NPC, T-DIL, T-DIL-G, T-CF, **T-WX**, **T-COMMS** roll tables `ready` (player rolls per P2b §7)
- [ ] P1 knobs reviewed — any must-decide before play?
- [ ] **S22-staging** ready if pasting raw notes (`_ingest_staging/session_22_raw_notes.md`)
- [ ] R5–R6 travel tables open at table (read rows from file, not from memory; **do not log outcomes in table files**)
- [ ] R1 journey tracker matches S21 end-state (~3 days south to Mirathorn, ~5 to Mireward)
- [ ] After play: C3 recap → C4 memory → update R1 → promote P1 rows → update this register
