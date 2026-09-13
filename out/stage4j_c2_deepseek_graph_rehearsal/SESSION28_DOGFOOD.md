# Session 28 dogfood — Stage 4J C2 DeepSeek graph rehearsal

**Generated:** 2026-09-13  
**Rehearsal DB:** `postgresql://dungeonmind@127.0.0.1:54329/dungeonmind_stage4j_rehearsal` (not live `:54330`)  
**World head:** `rev:edfe97d69fab1aaad7a6a0f9633e3f7f`  
**Model:** `deepseek/deepseek-v4.1-flash` via OpenRouter (DeepSeek pin)

## Pipeline summary

| Phase | Result |
|---|---|
| Census | 27/27 normalized C2 recaps present |
| Extract | 27/27 sessions produced reviewable candidate graphs |
| Promote | 24/27 sessions committed (non-edge fallback after select-all edge qualification failures) |
| Promote gaps | Sessions **15**, **20**, **22** — v6 materialization / unmapped node kind (`entity`) |

Promote mode for all successful sessions: **`non_edge_fallback`** (select-all attempted first; edges dropped because DungeonMind edge predicate / endpoint admission blocked full confirm).

## Graph queryability

**Direct World read (rehearsal DB):** yes — head resolves, **720 objects** at `rev:edfe97d69fab1aaad7a6a0f9633e3f7f`.

**Lexical retrieval search (`search_campaign_graph`):** returns **`outcome: empty`** for all Session 28 prep probes (see `session_28_retrieval_probe.json`). The graph is populated but search did not surface nodes for Mireward / Thrin / warehouse queries in this rehearsal environment.

## Sample graph evidence (direct payload scan, not retrieval)

Honest labels returned from published object payloads — not invented lore:

| Topic | Sample object labels in graph |
|---|---|
| **Mireward** | Mireward, Mireward Reach, Mireward Gate, Mireward Gate Defenders, Battle at Mireward Reach's north gate against meat monsters |
| **Thrin** | Thrin, Thrin's Forest People, Ambush and Recruitment of Thrin, Tendrils Under Thrin's Shoulder |
| **Refugees** | Refugees, Refugees from Edge, Refugee Infection Sorting at South Gate, Refugees split open to reveal hybrid creatures |
| **Meat creatures** | Swarm of Meat Monsters, Tainted Meat, Meatwings, Key Rattle Matches Meat Monster Seed |
| **Orik / Orric** | Orik Tane, Orik — **no Orric label hit** |
| **Warehouse** | Ironveil Warehouse, Ironveil Warehouse Wall, Ironveil Warehouse inner wall collapse and monster breach, Warehouse Guards |
| **Tripods** | Tripod Creatures, Tripod Spike Impale and Blindness |
| **Lysandro** | Lysandro (single node label hit) |

## Forcing question

> **Would I prep Session 28 from this graph, or reopen twenty-seven recaps?**

**Verdict: MIXED → lean REOPEN RECAPS**

**Why not GRAPH-only:**
- Retrieval search returned empty for all prep-shaped queries; GM workflow would still require direct DB/object spelunking or recap reopen.
- Edges were not published (experiment fallback dropped all `relationship` assertions); companionship, location adjacency, and thread carry-forward are mostly node islands.
- Three sessions (15, 20, 22) never landed on the head; Session 22 includes an unmapped `entity` node kind.
- Identity fragmentation visible (e.g. multiple Thrin-related nodes, separate Mireward / Mireward Reach / gate nodes) without published relationships to disambiguate.

**Why not full REOPEN:**
- 720 promoted objects include many Session 25–27 anchors (warehouse collapse, gate battle aftermath, tripod/meats/refugees) with table-usable descriptions when located by keyword scan.
- DeepSeek extract path is functional (27/27 reviewable graphs); cost was paid and artifacts exist under `out/stage4j_c2_deepseek_graph_rehearsal/`.

## Cost / wall

- Full extract wall clock: ~68 minutes for sessions 1–27 (OpenRouter paid).
- Per-session token/cost receipts were not aggregated in this runner; see individual run dirs under `session_NN/<run_id>/` and APP-STATE extraction runs for detailed usage if needed.

## Artifacts

- Census: `out/stage4j_c2_deepseek_graph_rehearsal/census.json`
- Receipts: `out/stage4j_c2_deepseek_graph_rehearsal/receipts/session_NN.json`
- Retrieval probe: `out/stage4j_c2_deepseek_graph_rehearsal/session_28_retrieval_probe.json`
- Checklist template: `out/stage4j_c2_deepseek_graph_rehearsal/session_28_dogfood_checklist.md`

## Blockers for a future GRAPH win

1. Edge qualification / vocabulary mapping must pass select-all confirm (or rehearsal must accept edges).
2. Retrieval search must return campaign-scoped hits for prep queries against the published head.
3. Unmapped extractor node types (`entity`, `warning`) need kernel kind mapping or extract profile tightening.
4. Sessions 15/20 materialization failures need investigation (duplicate object ids / v6 validation).
