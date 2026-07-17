# Hermes Rung 7 Cumulative Dogfood — 2026-07-16

**Gate:** `PASS` — Plan Hermes-only demolition complete; cumulative acceptance closed 2026-07-17 (see Merge addendum)  
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

## Verdict (original, 2026-07-16)

Rung 7 remains **DOING**. Demolition and journey evidence are real, and the
coverage-gap criterion is amended to deterministic contracts, but cumulative
acceptance stays open until remaining merge gates clear and current-head
confidence is recorded. PR010B remains `DOING`. PR011 remains `BLOCKED`.

## Merge addendum (2026-07-17)

The remaining merge gate closed: `agent/pr010b5-plan-hermes-thread-continuity`
merged into `main` as `129a4c40` (GitHub PR #356). Before merge, three rounds
of external critique review requested and received fixes on the same branch,
so they are included in the merged evidence:

1. **`2db5da67` — close claim authority escape hatches.** Removed the
   zero-tool-call implicit-trust path (no graph calls + no explicit scope
   declaration now abstains, not accepts model prose); removed the
   missing-provenance → `gm_authored_accepted_assertion` default (now
   `"unknown"`); rejected claims whose `revision_id` does not match the
   session's current revision.
2. **`293fdf43` — keep natural answers with coarse graph authority.**
   Restored `model_prose` as the frontstage answer text when factual claims
   exist, labeled `answer_authority: graph_context_synthesis` (not
   sentence-level validated prose), moved the deterministic claim-bullet
   ledger to a new `support_claim_ledger_text` support/debug field, and made
   an explicit `declare_conversation_context` tool call win over any
   preflight-seeded graph claims.
3. **`09898467` / `6db1e18a` / `c92e5a02` — expand-tool, hydration, and
   pointer-store honesty.** `ExpansionOperation` reduced to
   `object`/`neighborhood`/`search`/`support` (dropped `compare`/`path`/
   `timeline`/`coverage` aliases); `ExpandTarget.kind` restricted to `node`
   and `relationFamilies`/`claimPredicates`/`bounds` removed from the
   model-visible schema (the executor never implemented them); targetless
   `neighborhood` now fails closed with `ambiguous_target` instead of
   silently running `search`; per-operation target cardinality is enforced
   (`object`/`support` exactly one effective target, `neighborhood` 1–8,
   `search` 0–8) with `effective_targets` recorded alongside the raw request
   in the operation trace; `hydrate_session_from_packet` now validates
   claims through `GraphClaim.model_validate` and fails closed instead of
   inventing `revision_id`/`claim_kind`/`authority_class` for malformed IPC
   claims; `HermesSessionPointerStore`'s concurrency contract is documented
   as same-process-only (path-scoped shared `RLock`, unique temp filenames;
   no cross-process guarantee).

**Updated verdict:** Rung 7 is **PASS**. PR010B is `DONE`. PR011 is `READY`.
Verification provenance remains local/manual `pytest`/`vitest` (this repo has
no CI status checks attached to PRs) — a standing, accepted limitation, not a
Rung 7 blocker. Items still explicitly out of scope (see above) are unchanged:
real `AIAgent` wire-start environment failure, source-anchor readability, and
Hermes prompt/voice tuning remain separate backlog items.
