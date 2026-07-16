# Hermes Rung 5 Tripod Continuity Dogfood — 2026-07-16

**Gate:** Trial 1 `PASS`; aggregate three-trial acceptance `PENDING`  
**Scope:** Same-thread object continuity through bounded visible-prose replay  
**Question sequence:** Tripod Null-Calf discovery, followed by the pronoun-heavy prep question  
**Trace:** `agent-trace-846a5a991eb3`  
**Retrieval revision:** `rev:5cadc9798562862cdde22350d8a3b56c`

## Trial 1 result

The second turn emitted four ordered graph-tool events:

1. `expand_graph_retrieval` start — no seed nodes.
2. `expand_graph_retrieval` completion — `empty`, diagnostic
   `missing_seed_node_ids`.
3. `expand_graph_retrieval` start — retry after conversational referent resolution.
4. `expand_graph_retrieval` completion — `partial`, matching:
   - `threat:tripod-null-calf`;
   - `event:longmont-c2:session-23:mireward-gate-battle`;
   - three admitted relationships connecting the threat, event, location, and party;
   - eight source-anchor IDs.

The retrieval stayed pinned to Eldyrwild / longmont-c2 / focus session-24 at
the same revision. The retry is the important Rung 5 behavior: the initial
lexical/preflight miss did not become the final answer, and Hermes performed
fresh graph retrieval after resolving the shorthand referent.

## Verdict

| Rung 5 check | Trial 1 |
|---|---|
| Same active thread | `PASS` |
| Prior prose resolves “it” to Tripod | `PASS` |
| Prior prose used only for conversational identity | `PASS` based on the fresh retrieval events and returned graph IDs |
| Fresh graph retrieval on Turn 2 | `PASS` — two `expand_graph_retrieval` attempts |
| Fresh graph state supplies relationships/grounding | `PASS` — Tripod/Mireward objects and relationships returned at the pinned revision |
| Source excerpts opened and integrity-verified | `PENDING` — no `read_source_anchor` event |
| Aggregate three-trial gate | `PENDING` — Trials 2 and 3 not yet run |

## Source-evidence caveat

The trace reports `unreadable_source_anchors`, so the response remains
`partial` / `partial_coverage` and warns that source verification is incomplete.
This does not invalidate the Rung 5 continuity result: the graph retrieval
returned accepted graph objects and relationships, and the trace proves a fresh
Turn 2 retrieval. It does mean the trial does not yet prove the stronger
“opened source excerpt” citation path.

The warning is a coverage/evidence-chain measurement, not a continuity
measurement. Investigate it separately before using source-anchor readability
as a general Hermes acceptance gate.

## Next dogfood

Repeat the exact two-turn sequence twice more. Each trial must show:

- Turn 2 carries bounded prior visible role/content pairs;
- a fresh graph-tool completion occurs after referent resolution;
- returned objects, relationships, revision, and citations come from that turn;
- no arbitrary Markdown or ambient Hermes memory supplies campaign facts.

Record source-anchor opening as a separate evidence check until the
`unreadable_source_anchors` diagnosis is resolved.
