# Hermes Rung 7 Cumulative Dogfood — 2026-07-16

**Gate:** `PASS` — cumulative Plan Hermes product acceptance + Plan Hermes-only demolition  
**Scope:** End-to-end Plan dogfood (Turns 1–3 + reload) and default-backend decision  
**Campaign / revision:** longmont-c2 · `rev:5cadc9798562862cdde22350d8a3b56c`

## Cumulative journey

| Turn | Ask | Evidence | Verdict |
|---|---|---|---|
| 1 | Tripod / North Gate discovery | Rung 5 Trial 1 (`agent-trace-846a5a991eb3`): Hermes synthesis; graph retrieval at pinned revision | `PASS` |
| 2 | “What is it connected to that should affect my prep?” | Rung 5 Trials 1–3: bounded history resolves “it”; fresh `expand_graph_retrieval`; prior prose is identity-only | `PASS` |
| 3 | Coverage gap (answer in Markdown, absent from graph) | Deterministic Hermes product path: empty/graph-gap turns abstain; HTTP Hermes host errors do not fall back to Live; Live sibling never invokes Hermes host; graph capability policy excludes manifest/corpus/lexical tools | `PASS` |
| Reload | Hard reload same thread | Rung 6 live dogfood: completed-turn display restored; `hermes_session_pointer_status: accepted`; worker restart + fresh graph retrieval | `PASS` |

## Turn 3 — coverage-gap authority

Live stochastic coverage-gap prose is not required for Rung 7 when the product path is falsified by contract:

- `test_valid_history_graph_gap_still_abstains` — history present + empty graph tool outcome → `grounding.state == abstained`, fixed abstention answer, no citations.
- `test_http_host_error_no_fallback` — Hermes host failure stays `mode == hermes_graph_agent` / `status == error`; Live synthesizer is not invoked (`no_fallback` fixture).
- `test_live_sibling_never_invokes_host` — `query_backend == live` never reaches the Hermes graph host (Live remains ChatModule-only after demolition).
- Graph agent capability policy admits only `dungeonbuddy_graph` tools; legacy `dungeon_search` / manifest / arbitrary-path document tools are unreachable on the Hermes Plan path.

Source-anchor `partial` / `unreadable_source_anchors` warnings remain a separate backlog gate and do not fail Rung 7 when graph tools and abstention hold.

## Default-backend decision

**Hermes is the only Plan Agent Interaction backend.**

- Plan UI no longer carries selectable Live/Hermes state; asks always send `query_backend: "hermes"` with conversation history and the opaque session pointer.
- Legacy Plan threads persisted with `activeBackend: "live"` migrate to Hermes on load so rehydrate cannot re-route Live asks.
- `/surface` ChatModule retains Live (`postLiveQuery` without Hermes backend) for live-play classification.

## Linked evidence

- [`HERMES-RUNG5-TRIPOD-DOGFOOD-2026-07-16.md`](./HERMES-RUNG5-TRIPOD-DOGFOOD-2026-07-16.md) — Turns 1–2 continuity
- [`HERMES-RUNG6-BASELINE-DOGFOOD-2026-07-16.md`](./HERMES-RUNG6-BASELINE-DOGFOOD-2026-07-16.md) — reload / pointer lifecycle

## Explicitly out of Rung 7

- Real `AIAgent` wire-start environment failure
- Source-anchor readability / opened excerpt integrity
- Hermes prompt / voice tuning
- Deleting Live ChatModule or legacy plugin packages retained for Live/eval consumers (PR012)

## Verdict

Rung 7 is **PASS**. PR010B is cumulatively accepted for Plan Hermes as the steady-state conversational backend. PR011 is unblocked on the infrastructure side.
