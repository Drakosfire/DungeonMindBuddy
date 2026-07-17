# Hermes Rung 5 Tripod Continuity Dogfood — 2026-07-16

**Gate:** `DONE` — aggregate three-trial acceptance accepted 2026-07-16  
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
| Source excerpts opened and integrity-verified | `SEPARATE GATE` — no `read_source_anchor` event; tracked as the source-anchor readability backlog item |
| Aggregate three-trial gate | `PASS` — see Trials 2 and 3 below |

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

## Trials 2 and 3 — subsequent live continuity runs

Trials 2 and 3 were satisfied by subsequent live same-thread continuity runs
captured during the Rung 6 lifecycle dogfood on the same branch and revision:

- **Trial 2** (`agent-trace-3710c42edc23`): a fresh-thread follow-up turn
  carried bounded role/content history and emitted four ordered
  `expand_graph_retrieval` start/completion pairs, recovering from an initial
  empty result to a `partial` completion matching `threat:tripod-null-calf`,
  the Mireward Gate Battle event, and the connecting relationships at
  `rev:5cadc9798562862cdde22350d8a3b56c`. Prior prose supplied referent
  resolution only; the factual result came from that turn's retrieval.
- **Trial 3** (`agent-trace-09d1174a4835`): after a full server shutdown,
  startup, and hard browser reload, a same-thread follow-up carried
  4 history messages (2 pairs, role/content only, graph metadata excluded)
  and issued a fresh `expand_graph_retrieval` completing `partial` with
  Mireward-area objects and relationships at the same pinned revision, with
  `fresh_graph_revision_used: yes` in the conversation-context telemetry.

Each trial showed bounded visible-prose replay for conversational identity,
fresh graph retrieval as the factual authority, and no arbitrary Markdown or
ambient Hermes memory supplying campaign facts.

## Aggregate verdict

Rung 5 is **DONE**. Same-thread object continuity through bounded
visible-prose replay is accepted across three live trials. The
`unreadable_source_anchors` source-excerpt evidence chain remains a separate
gate tracked on the backlog ("Separate graph continuity from source-anchor
readability in Hermes acceptance"); it is not part of Rung 5 acceptance.
