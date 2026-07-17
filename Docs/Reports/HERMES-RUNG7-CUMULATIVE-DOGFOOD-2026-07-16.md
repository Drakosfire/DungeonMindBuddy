# Hermes Rung 7 Cumulative Dogfood — 2026-07-16

**Gate:** `DOING` — Plan Hermes-only demolition present; cumulative acceptance open  
**Scope:** End-to-end Plan dogfood (Turns 1–3 + reload) and default-backend decision  
**Campaign / revision:** longmont-c2 · `rev:5cadc9798562862cdde22350d8a3b56c`

## Cumulative journey

| Turn | Ask | Evidence | Verdict |
|---|---|---|---|
| 1 | Tripod / North Gate discovery | Rung 5 Trial 1 (`agent-trace-846a5a991eb3`): Hermes synthesis; graph retrieval at pinned revision | `PASS` |
| 2 | “What is it connected to that should affect my prep?” | Rung 5 Trials 1–3: bounded history resolves “it”; fresh `expand_graph_retrieval`; prior prose is identity-only | `PASS` |
| 3 | Coverage gap (answer in Markdown, absent from graph) | Deterministic Hermes product path: empty/graph-gap turns abstain; HTTP Hermes host errors do not fall back to Live; Live sibling never invokes Hermes host; graph capability policy excludes manifest/corpus/lexical tools | `PASS` (contract proof; live stochastic turn optional per amended tracker gate) |
| Reload | Hard reload same thread | Rung 6 live dogfood: completed-turn display restored; `hermes_session_pointer_status: accepted`; worker restart + fresh graph retrieval | `PASS` |

## Turn 3 — coverage-gap authority

The tracker’s required dogfood originally called for a live graph-gap ask. That
gate is **explicitly amended**: live stochastic coverage-gap prose is optional.
Coverage-gap authority is accepted when the product path is falsified by
deterministic contract:

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
- CI-backed / workflow-run verification provenance (current evidence is local/manual)

## Verdict

Rung 7 remains **DOING**. Demolition and journey evidence are real, and the
coverage-gap criterion is amended to deterministic contracts, but cumulative
acceptance stays open until remaining merge gates clear and current-head
confidence is recorded. PR010B remains `DOING`. PR011 remains `BLOCKED`.
