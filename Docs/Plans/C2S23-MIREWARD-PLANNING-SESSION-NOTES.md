# C2S23 Mireward planning — living session notes

**Purpose:** Operator + agent scratch pad while building Mireward for Session 23 prep. Update after each planning block. This is **not canon** — promoted material lives in corpus files after preview/commit.

**Handoff:** `Docs/Plans/HANDOFF-c2s23-mireward-planning-cursor-first.md`

**Dogfood notes:** `Docs/Plans/C2S23-MIREWARD-DOGFOOD-NOTES.md`

---

## Session log

| Step | Date | What we did | CLI / skill used | Outcome | Next |
|------|------|-------------|------------------|---------|------|
| 0 | 2026-06-02 | Handoff authored; re-anchor | — | Ready to plan | Read Mireward scaffold + S22 play canon |
| A | 2026-06-06 | Phase A orientation; **DEGRADED: Cursor+CLI planning** | Cursor reads (`README`, scaffold sections, S22 recap, reach context, Mossford target shape) | Mireward hub still has README + scaffold + Lysandro seed only; S22 canon places party outside Mireward gate at ~22:00 with Lysandro identifying Lysandra; first promotion candidates are gazetteer skeleton plus gate/apron or Last Dry Bed dossier | Run manifest packets for 2–3 S23 prep questions, then pick first promotion |
| B | 2026-06-06 | Deterministic packet run + three live-query traces for `loc-01`, `town-01`, `npc-01` | `run_c2s23_manifest_context_query`; `run_live_query_telemetry_trace --no-enhancement` | 22 packets emitted; selected three traces succeeded with 12 admitted / 0 rejected and no warnings; operator chose gazetteer skeleton + Reach Gate / mud apron first | Draft promotion preview; require operator `apply` before corpus commit |
| C | 2026-06-06 | Hester / Edge / north-side opening handoff updated | Cursor planning doc edit | New direction: Edge is under siege; Mireward is preparing for a siege it knows it is not ready for; Mireward counter-festival is punkier/anarchic/free-spirit counter-programming to Mirathorn; bards in town matter; later Celtic punk battlewagon can help break/bypass siege and escort party north to Edge | Use `HANDOFF-c2s23-hester-edge-opening-combat.md` for creative planning partner session |
| D | 2026-06-06 | Dogfood notes started | Cursor planning doc edit | Created `C2S23-MIREWARD-DOGFOOD-NOTES.md` to log queries, Cursor actions, friction, and product ideas during planning | Record future planning queries/actions there as they happen |
| E | 2026-06-06 | S23 immediate narrative locked: Hester delivered Edge packet to Mireward before continuing south | Cursor planning + scaffold edit | Private Hester carried two layers: a detailed local Edge packet already delivered to Mireward, and a sealed Mirathorn tube still in hand when the party met her. Authority cluster named in scaffold: Reeve Salla Vey, Mayor Orric Tane, Nera Coalstep, Lysandro Ironveil, Delwen Rast. | Talk through combat after the immediate narrative / NPC establishment is accepted |
| F | 2026-06-06 | Lysandro captured as full NPC hub | Cursor corpus edit, following `Docs/CONVENTION-NPC-Hub-Package.md` | Added Lysandro hub README + full character dossier; revised seed/scaffold so he is a first-family artisan / merchant and wall volunteer, not merely a gate emeritus. | Use Lysandro dossier to ground the south-gate conversation, then design the north alarm / combat |
| G | 2026-06-06 | Remaining Mireward S23 NPC hubs created | Cursor corpus edit, `Docs/CONVENTION-NPC-Hub-Package.md` | Added README + character_seed hubs for Salla Vey, Orric Tane, Nera Coalstep, Delwen Rast, Maera Vell, Orin Vell, Private Hester; updated Mireward location README + scaffold §F table. | Design north-side combat; optional dossiers for authority cluster later |
| H | 2026-06-06 | Edge support refugee wave locked | Cursor planning + scaffold §F4 + `brin_holloway` hub | Civilian column sent north to Edge (guilt / sky-levy defiance); fleeing south ahead of meat-monster flank; ~half glassy-eyed; Brin Holloway named lead; on-the-fly marcher tables in scaffold | Wire into opening beat map + combat |
| I | 2026-06-06 | North-gate count and clock tightened | Cursor planning + scaffold / Brin seed edits | S23 table lock: **55 civilians**, Brin's unreliable **58 / 51 / fifty-odd** counts, meat flank **3–8 minute road clock**, Lysandro mobilizing town reaction while party handles gate / road pressure | Finish opening beat map; decide exact gate/apron tactical layout |
| J | 2026-06-06 | Siege behavior + layout packet authored from operator decisions | ChatGPT GitHub connector writes | Added `Docs/Plans/C2S23-Mireward-Siege-Behavior-Layout/` with locked anchors, authority matrix, panic model, layout/site cards, pressure interfaces, prep inventory, and table-use decisions. Operator locked: civic tithe compound, south-apron festival commons, ferry-causeway inside north gate on east-west river, emergency consensus, treatment-first glassy-eye instinct, Bell/Shrine as remembered site. | Optional next packet: refugee names / bad counts, mutual-aid roster, pressure clocks, treatment table, Bell/Shrine consensus scene card |
| K | 2026-06-06 | Siege mechanics + new monster documents captured | ChatGPT GitHub connector writes | Added `tripod_null_calf_statblock_cr5.md` and `latch_harrow_statblock_cr8.md`; updated Shepherd's Flock statblock hub; added `07-siege-mechanics-threat-inventory.md`; updated siege packet README. Operator locked: Tripod appears on-screen, north gate is focus, bardic help arrives as bagpipes out of morning mist when things get dire, glassy civilians are infected/dreaming/signal-receivers but curable, all can be cured if cure line is protected, short rest pressure is harsh. | Decide if Latch-Harrow appears in S23 or remains later-wave / cliffhanger; decide who first hears the bagpipes; optionally wire new statblocks into prep UI statblocks pane. |

---

## Authority ledger (per promoted section)

When copying scaffold → gazetteer/dossier, record source role:

| Promoted chunk | Source (scaffold §) | Target path | Authority after promote | Play-fact risk? |
|----------------|---------------------|-------------|-------------------------|-----------------|
| | | | `reference_tool` / world | |

**Rule:** Scaffold and S22 prep are **not** proof that something happened in play. S22 recap + session memory are play canon for gate/Lysandro beats only.

---

## Retrieval packets reviewed

Log each manifest query run before answering a prep question batch:

| Question (operator ask) | Packet artifact path | Admitted roles | Rejected / gaps | Full-doc reads after packet |
|-------------------------|----------------------|----------------|-----------------|----------------------------|
| `loc-01` — where S22 ended and which location hubs ground the scene | `evals/c2_live_prep/artifacts/runs/2026-06-06/c2s23_manifest_query_context_packet_loc-01.json` | `play_recap` / `canon_play`; `session_memory` / `derived_memory`; `prep_scaffold` / `planning_scaffold`; `world_evidence` / `reference_tool` | No rejected evidence; scaffold/prep admitted only for planning, not play facts | `Session 22 - Mireward Road and Lysandro.md`; Mireward `README.md`; Mireward scaffold §§A–F; Mossford README + gazetteer shape |
| `town-01` — next settlement and economy hooks for S23 opening | `evals/c2_live_prep/artifacts/runs/2026-06-06/c2s23_manifest_query_context_packet_town-01.json` | `world_evidence` / `reference_tool`; `hub_evidence` / `canon_play`; `prep_scaffold` / `planning_scaffold`; `live_packet` / `planning_scaffold`; `live_event` / `live_observation` | No rejected evidence; includes non-canon planning surfaces, so separate confirmed end state from economy prep | Mireward `README.md`; `Mireward_PLACE_BUILD_SCAFFOLD.md`; `mireward_reach_road_d100_encounter_table.md`; `Journey - Mireward Reach (Campaign 2).md` |
| `npc-01` — Lysandra state into S23 | `evals/c2_live_prep/artifacts/runs/2026-06-06/c2s23_manifest_query_context_packet_npc-01.json` | `hub_evidence` / `canon_play`; `play_recap` / `canon_play`; `session_memory` / `derived_memory`; `world_evidence` / `reference_tool`; `live_packet` / `planning_scaffold` | No rejected evidence; statblocks admitted as reference only, not needed for current non-mechanics prep | S22 recap; Lysandra Mireward history; Lysandro seed |
| live trace — Mireward opening location | `evals/c2_live_prep/artifacts/runs/2026-06-06/live_query_loc_01_mireward_opening.json` | 12 admitted / 0 rejected; answer accepted | Minor generated-answer typo in suggested path text (`Elderwywyld`), do not copy into promoted corpus | Same as `loc-01` packet |
| live trace — town/economy opening | `evals/c2_live_prep/artifacts/runs/2026-06-06/live_query_town_01_mireward_opening.json` | 12 admitted / 0 rejected; answer accepted | Uses scaffold as planning support; do not cite as play facts | Same as `town-01` packet |
| live trace — Lysandra S23 state | `evals/c2_live_prep/artifacts/runs/2026-06-06/live_query_npc_01_lysandra_state.json` | 12 admitted / 0 rejected; answer accepted | Includes live/pre-canon surfaces among admitted evidence; play facts still need S22 recap / campaign hub support | Same as `npc-01` packet |
| | | | | |

---

## Corpus writes (preview → apply)

| Phase | Path | Mode | Preview ok? | Committed? | Notes |
|-------|------|------|-------------|------------|-------|
| S23 siege monsters | `corpus/eldyrwild-markdown/Elderwyld/Shephards Flock/Statblocks and Tokens/tripod_null_calf_statblock_cr5.md` | create | yes | yes | CR 5 large three-limbed alien scout; appears on-screen; can mark north gate. |
| S23 siege monsters | `corpus/eldyrwild-markdown/Elderwyld/Shephards Flock/Statblocks and Tokens/latch_harrow_statblock_cr8.md` | create | yes | yes | CR 8 later-wave siege breaker; north-gate breach-clock monster. |
| S23 siege monsters | `corpus/eldyrwild-markdown/Elderwyld/Shephards Flock/Statblocks and Tokens/README.md` | update | yes | yes | Indexed Tripod Null-Calf and Latch-Harrow. |
| S23 siege mechanics | `Docs/Plans/C2S23-Mireward-Siege-Behavior-Layout/07-siege-mechanics-threat-inventory.md` | create | yes | yes | Captures Cure Line, bagpipe escalation, harsh rest pressure, threat ladder, and table handling. |
| S23 siege mechanics | `Docs/Plans/C2S23-Mireward-Siege-Behavior-Layout/README.md` | update | yes | yes | Added locked decisions and new packet file. |

---

## Current S23 siege locks — mechanics layer

- **North gate focus:** North gate remains the central tactical object. The Latch-Harrow can redirect toward Bell / Shrine, tithe barn, or ferry chain only if the party is not challenged enough.
- **Tripod reveal:** Tripod Null-Calf appears on-screen as a large three-limbed alien scout / geometry-breaker.
- **Tripod → Latch chain:** Tripod's `Mark the Gate` can make the Latch-Harrow's later `Siege Adaptation` feel earned.
- **Glassy truth:** Glassy civilians are infected, dreaming, and receiving a signal. They are curable and should not be default enemies.
- **Cure Line:** Track curing as a 0–6 shared clock. The dramatic question is whether the party protects the cure process under pressure.
- **Bardic escalation:** Bardic counter-music arrives late, when things get dire: bagpipes out of the morning mist.
- **Rest:** Short rest pressure is harsh. Rest before cure/gate stabilization advances siege clocks and causes visible cost.

## Remaining small decisions

- Decide whether Latch-Harrow appears in Session 23 or is held as a later-wave cliffhanger.
- Decide who first hears the bagpipes: Stafl, Lysandra, Thrin, or a newly cured civilian.
- Decide exact cure flavor at table: magic, medicine, song, purge, name-recognition, or combined ritual.
- Decide how the Tripod exits if driven off: reflection, mud, wall-crawl, or impossible geometry.
