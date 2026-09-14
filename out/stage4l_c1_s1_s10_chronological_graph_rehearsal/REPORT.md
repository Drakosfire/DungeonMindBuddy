# Stage 4L — C1 chronological graph rehearsal

Generated: 2026-09-14T16:57:00Z
Sessions completed: 10/10
Paid cost recorded: $0.154333
Per-session wall total: 676.3s

Canonical contract: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4l-c1-s1-s10-chronological-graph-rehearsal-v1.md`

Execution SHA: `ee5d1fe90b170460b06c86f9446403674ee9fb7d`  
PR: [#714](https://github.com/Drakosfire/DungeonMindBuddy/pull/714)  
Isolated World: `dungeonmind_stage4l_c1_rehearsal` on `:54329` (live Eldyrwild `:54330` refused)  
Authoritative S10 head: `rev:3fc8e4e9782a6afd1b8fdfe9fa6caffc`

Model: `deepseek/deepseek-v4.1-flash` · provider pin `order=["DeepSeek"]` · `allow_fallbacks=false` · reasoning disabled · Chat Completions `json_object` + local validation.

## Revision chain

Authoritative paid chronological chain (S2–S10 receipts + DB-proven S1 child). Session 1's on-disk receipt currently records a later zero-model replay fork; see Replay proof.

- S01: `rev:d5c54ab8569139e400f0cce9ede4e60d` → `rev:1ed6387f36bb84eb9c86cf80a253d1b1` · 33 nodes / 31 edges · published edges 0/31 · node_object_partial
- S02: `rev:1ed6387f36bb84eb9c86cf80a253d1b1` → `rev:ade5e648ad6f2c3e09791e0f4f664610` · 12 nodes / 7 edges · published edges 7/7 · all
- S03: `rev:ade5e648ad6f2c3e09791e0f4f664610` → `rev:00baae206b072e5c1cf20e449c7be53a` · 34 nodes / 37 edges · published edges 0/37 · node_object_partial
- S04: `rev:00baae206b072e5c1cf20e449c7be53a` → `rev:925cc5166dd943979bc3a4a3d2a88c3c` · 34 nodes / 39 edges · published edges 0/39 · node_object_partial
- S05: `rev:925cc5166dd943979bc3a4a3d2a88c3c` → `rev:fd6ceed830a7479b11835e04f260a3a8` · 31 nodes / 27 edges · published edges 0/27 · node_object_partial
- S06: `rev:fd6ceed830a7479b11835e04f260a3a8` → `rev:c061dbafd4cb62519e7c2eeb5805b8ee` · 39 nodes / 36 edges · published edges 0/36 · node_object_partial
- S07: `rev:c061dbafd4cb62519e7c2eeb5805b8ee` → `rev:5a5c6bf48f46b3d1c7525b232004b41e` · 36 nodes / 32 edges · published edges 0/32 · node_object_partial
- S08: `rev:5a5c6bf48f46b3d1c7525b232004b41e` → `rev:d4a00d0c8d6f40bfceacdd18d50abca2` · 38 nodes / 29 edges · published edges 0/29 · node_object_partial
- S09: `rev:d4a00d0c8d6f40bfceacdd18d50abca2` → `rev:dd8c8af8d349f4ca10186b4a321491e7` · 46 nodes / 22 edges · published edges 0/22 · node_object_partial
- S10: `rev:dd8c8af8d349f4ca10186b4a321491e7` → `rev:3fc8e4e9782a6afd1b8fdfe9fa6caffc` · 28 nodes / 16 edges · published edges 0/16 · node_object_partial

## Experimental status

10/10 sessions extracted and published a truthful next head. API completion alone is not PASS.

## Cost / usage

| | |
|---|---|
| Paid semantic sessions | 10 (one per recap; S1–S5 were rerun once after checkout-contamination invalidated the first chain; superseded receipts preserved, not erased) |
| Model calls | 79 category passes |
| Input tokens | 439,077 |
| Output tokens | 166,453 |
| Cached tokens | 77,568 |
| Wall | 676.3s (11m 16s session-sum) |
| Cost | **$0.154333** |

Per session:

| S | known into N | nodes | edges | pub edges | mode | cost USD | wall s | in | out | cache |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| 1 | 0 | 33 | 31 | 0 | node_object_partial | 0.009931 | 62.6 | 29278 | 14500 | 21504 |
| 2 | 28 | 12 | 7 | 7 | all | 0.005857 | 30.3 | 19214 | 6118 | 4736 |
| 3 | 36 | 34 | 37 | 0 | node_object_partial | 0.020248 | 84.2 | 54822 | 22079 | 8320 |
| 4 | 58 | 34 | 39 | 0 | node_object_partial | 0.015568 | 72.4 | 36690 | 18496 | 7040 |
| 5 | 76 | 31 | 27 | 0 | node_object_partial | 0.013309 | 61.0 | 39934 | 14739 | 10368 |
| 6 | 96 | 39 | 36 | 0 | node_object_partial | 0.018057 | 78.5 | 46309 | 19772 | 5120 |
| 7 | 121 | 36 | 32 | 0 | node_object_partial | 0.016123 | 65.9 | 47277 | 16307 | 5120 |
| 8 | 144 | 38 | 29 | 0 | node_object_partial | 0.019362 | 82.4 | 51275 | 20706 | 5120 |
| 9 | 169 | 46 | 22 | 0 | node_object_partial | 0.020614 | 76.5 | 67827 | 18653 | 5120 |
| 10 | 194 | 28 | 16 | 0 | node_object_partial | 0.015264 | 62.4 | 46451 | 15083 | 5120 |

S2–S10 known-entity counts are World-derived from head N−1 only, plus the six Campaign 1 party anchors. Party fingerprint is stable: `3499f816c5ffdaa8507ab24ac2f2aaa3fc778b767e0ea28b49a6a42460874c26`.

## PC identity

All six roster PCs publish as DungeonMind `player_character` with stable IDs:

```text
node:baergrom
node:bonogo
node:caelynn
node:ephanna
node:karsemine
node:stafl
```

Candidate `corpus_ref.type=pc` + `proposed_action=anchor` on every session that mentions them (S2 extracted no PC nodes; S5 omitted Karsemine). No NPC-shaped duplicate of a roster PC exists on the S10 head.

## Source admission

Every session admitted the exact raw recap (`source_class: observed_session_recap`, campaign `longmont-c1`, `session-N`, SHA-256 of source bytes). No `scope_unknown` / `other` fallback in these receipts.

## C1S1 gold (evaluator-only)

Gold was not present in generation context (`generation_access: false`).

- Gold node labels represented: 12 / 27 (six PCs, Stone Bridge, River's Edge, Grishna, Glowkindle, Wizard's Tower Brewing Co, Glowkindle's excavation crew)
- Missing include cellar/rat/job-board/spider/firkin phrasing and the party-as-group node
- Gold edge endpoint pairs represented: **0 / 30** (candidate relationship IDs/endpoints do not match gold's)

## Edge funnel

| Session | extracted | published | blocker |
|---|---:|---:|---|
| 1 | 31 | 0 | predicate has no DungeonMind mapping |
| 2 | 7 | 7 | — |
| 3 | 37 | 0 | endpoint kinds not admitted for qualified predicate |
| 4 | 39 | 0 | predicate has no DungeonMind mapping |
| 5 | 27 | 0 | predicate has no DungeonMind mapping |
| 6 | 36 | 0 | endpoint kinds not admitted for qualified predicate |
| 7 | 32 | 0 | endpoint kinds not admitted for qualified predicate |
| 8 | 29 | 0 | endpoint kinds not admitted for qualified predicate |
| 9 | 22 | 0 | endpoint kinds not admitted for qualified predicate |
| 10 | 16 | 0 | predicate has no DungeonMind mapping |
| **total** | **276** | **7** | |

S2's seven published edges are `located_in` / `sublocation_of` among locations and items (hidden alchemy room, potions, gems, well). That mapping works. The rest of the vocabulary does not.

Highest-volume unpublished `relationship_type` values: `located_in` (44), `attacks` (26), `present_at` (23), `part_of` (13), `possesses` (13), `carries` (12), `knows_about` (12). Many of these look like ordinary campaign relations, not exotic new ontology.

## Cumulative S10 graph

285 objects on `rev:3fc8e4e9782a6afd1b8fdfe9fa6caffc`.

| kind | count |
|---|---:|
| mystery | 75 |
| item | 64 |
| location | 62 |
| npc | 51 |
| faction | 9 |
| group | 8 |
| player_character | 6 |
| party | 4 |
| creature | 2 |
| event | 2 |
| thread | 2 |

### Recurring identities that accumulated

- PCs: one object each, canonical IDs, kind `player_character`.
- Grishna `node:grishna`, Glowkindle `node:glowkindle` — minted in S1, not reminted later.
- Places persist as the campaign moves: Stone Bridge / Hempholm / Mirathorn families of locations.
- Known-entity context grew 0 → 28 → 36 → 58 → 76 → 96 → 121 → 144 → 169 → 194. Later sessions mostly mint **new** nodes rather than same-label remints of existing IDs.

### Fragmentation that remains

Eleven exact-label cross-kind collisions, including:

- Stone Bridge as `item:stone_bridge` and `node:stone_bridge` (already in S1)
- Hidden Alchemy Room as location and item
- Grotesque Tree of Hempholm as item and mystery (plus a creature-shaped tree)
- Caretakers as creature and faction
- Corrupted meat mound/pile/wings as item **and** npc
- Captain Lysandra split: `node:lysandra-ironveil` (S6) vs `npc:captain-lysandra` (S8)

Mystery count (75) is the noisy fact-history risk: threads, protests, promises, and fight names are stored as sibling objects rather than history on a person/place.

### Relationships

The published World is almost a node island graph. 7 published edges vs 276 extracted. Inspecting “who runs the pub”, “who hired whom”, or “who is fighting the meat” cannot be answered from published relationships.

## Replay proof

Zero-model replay of saved S1 candidate succeeded (`publication_replay.model_calls: 0`, 5.0s) but **did not reproduce the original S1 child**.

```text
paid S1 child:    rev:1ed6387f36bb84eb9c86cf80a253d1b1
replay S1 child:  rev:67862c918c5f59f9ac41bca26494f996
```

S2 then fail-closed (`saved candidate prior World revision drift`), which is the correct chronological guard. The rehearsal head was restored to the paid S10 revision for inspection. Candidates remain durable; publication package identity is not bit-stable across replay.

## Forcing-question verdict

> After ten chronological sessions, does this look like accumulated campaign memory — stable people/places/things gaining source-linked history and relationships — or like ten document parses piled into one graph?

**MIXED — useful accumulation exists but one named blocker should be isolated next.**

It is not ten disconnected parses. Roster PCs stay canonical, major S1 NPCs are not reminted, and later sessions consume a growing N−1 identity ledger. It is also not yet navigable campaign memory: almost no relationships publish, same-referent objects split across kinds, and mystery-shaped leftovers dominate the object census.

Would this graph be more useful than reopening Sessions 1–10? Only for “who are the PCs / did this name already exist?” Not for “how is this connected?” — reopen recaps still wins for continuity prep.

### Successor (exactly one)

**Relationship predicate publication slice**, using the already-paid candidates via zero-model replay. Do not widen chronological ingestion and do not rerun DeepSeek until `located_in` / `attacks` / `present_at` / `possesses` / `knows_about` (and endpoint-kind admission) can publish without pretending node-only success is a graph.

Identity fragmentation (Lysandra, Stone Bridge, meat-as-item-and-npc) is real but secondary; predicate publication is the blocker that makes the S10 World unusable as memory.
