---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: LOCAL DEMO ACCEPTED / DEMO J2 Agent backend
  - Flow: DEMO
  - Direction: PRIME activation → CODE → PRIME
  - Handoff: `Docs/Plans/HANDOFF-DEMO-universal-agent-turn-backend-v1.md`
  - Design authority: PR #790 exact accepted head `3fcc60de6159add04fe9455f5aee0a58816bfece`
  - PR topology: serial DEMO Agent backend baseline; one assigned implementation PR

  ## Verification pointer
  - Dispatch base: `ed1bf1ba0531bf9018f2397863825fa20c781bfe`
  - Review authority: pinned contract plus this ACTIVE handoff
  - Evidence: §7 owning service/route, full-route-table, no-packet, and compatibility proofs
---

# HANDOFF — DEMO: implement the universal Agent backend turn

**Created:** 2026-09-29
**Status:** ACTIVE — one bounded backend implementation capability
**Conversation/workstream:** LOCAL DEMO ACCEPTED / DEMO J2 universal Agent
**Flow / owner:** DEMO / Buddy Agent interaction
**Direction:** PRIME activation → CODE → PRIME
**Design authority:** Buddy PR #790, exact accepted design head `3fcc60de6159add04fe9455f5aee0a58816bfece`, based on `ed1bf1ba0531bf9018f2397863825fa20c781bfe`; PRIME Cycle 4 DESIGN PASS and ARCHITECTURE focused exact-head PASS. PR #790 remains a separate open design-only PR and is not merged by this handoff.
**Activation gate:** PRIME explicitly accepted and dispatched this bounded baseline on 2026-09-29; current `origin/main` was fetched and verified at `ed1bf1ba0531bf9018f2397863825fa20c781bfe`; all-open PR paths were refreshed before worktree creation.
**Dispatch base:** `ed1bf1ba0531bf9018f2397863825fa20c781bfe`
**PR topology:** `serial` within DEMO Agent implementation. This is the one assigned backend PR; shared six-surface adoption is a required successor, not part of this lease.
**PR authorization:** open/update exactly one implementation PR from this branch without another user prompt. Do not merge; PRIME owns merge coordination. No successor/repair PRs.
**PR title:** `DEMO: implement universal Agent backend turn`
**Branch / checkout:** `codex/demo-agent-turn-context-backend` / `/tmp/dmb-demo-agent-turn-context-backend`

## §1 Mission and merge-ready invariant

**Mission:** A Buddy surface can submit one bounded Agent turn request and receive a truthful answer/retrieval result bound to the independently resolved surface, owner, saved work, graph scope, temporal focus, and revisions.

**Merge-ready invariant:** The generic Agent endpoint either resolves each requested authority independently and reports exactly what it used, or returns a typed fail-closed result without silently dropping invalid scope, changing graph focus, loading a session packet for no-scope chat, calling the answer model after required retrieval fails, crossing a structured provider-continuity key, or changing legacy `/api/live/query` behavior.

This is the backend baseline only. It does not deliver universal Agent UI, all six surface publishers, user-facing visual acceptance, or end-to-end J2/J3 acceptance.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern all paths? | Yes: resolve exact per-turn context or fail closed; preserve legacy route. |
| Most likely adversarial sequence | Index/no owner → pointer store opens without packet; Plan saved revision changes during turn; selected World + campaign Plan session focus is contradicted; graph unavailable after explicit request; prior legacy pointer exists; route registration is duplicated. |
| Will §7 detect it? | Deterministic service/route tests, packet-loader failure injection, pointer-store compatibility tests, full application route table. |
| Easiest boundary to under-test | Full route composition and no-scope route accidentally depending on packet/session loading. |
| Authorized topology | Serial; one open implementation PR, exact current base, no UI successor in parallel. |
| Stop/split fact | Need for any unleased production path, schema/store, UI publisher, `main.py` registration, dependency, or external contract change. |

## §2 Context, authority, lane, and topology

The pinned design PR is the reviewed contract authority for this slice. The required meaning is restated here so implementation does not rely on mutable or unmerged branch state:

- `POST /api/live/agent/turn` is additive, nested under the existing `/api/live` router; do not modify `main.py`.
- A request independently carries surface identity, owner locator, primary saved-work locator plus expected revision, client-reported work state, graph request (`none|world|campaign`), optional exact selected node, and user message.
- Requested graph scope, optional narrative campaign anchor, and temporal focus are distinct. World reads normalize Buddy's adapter-only empty campaign representation to MIND World scope with `campaign=None`; never invent an authority ID. Exact focus campaign is carried separately and server-corroborated.
- A managed-World Plan without a target session uses World scope, no campaign anchor, and `focus=none`. A campaign-target Plan under its verified parent World may preserve its exact saved campaign anchor and target-session focus. The server must resolve and corroborate the full World/campaign/Plan/session relation.
- A graph node or session focus paired with `graph_request.mode="none"` is contradictory and is rejected, not ignored or used to upgrade to retrieval.
- `saved_dirty` is only a browser hint. Resolve the actual latest committed saved-work revision; if it differs from the expected revision, report expected and used and `changed_since_expected`. Never read local/unsubmitted draft prose.
- A valid empty result or selected-node not-found is distinct from invalid/foreign scope, unavailable graph service, or unreadable requested pin. Required retrieval failure makes no answer-model call; valid empty/not-found may answer without grounding claims.
- Generic no-scope turns may persist structured Hermes provider-continuity pointers under configured `session_dir()` as storage only. They must not call `load_session()` or require a packet. Buddy transcript remains browser-local and is not a new server transcript store.
- Generic bindings never read/adopt/rewrite legacy campaign-only pointer records. `/api/live/query` retains exact legacy behavior.
- Delivery order after this baseline: separately activated shared Agent UI/adapters on Index, Plan, Play, Build, Ingest and Combat; then owner-to-backend end-to-end witnesses. World-reference lens work consumes this authority later.

At dispatch the repository had open #790 (design only), #781 (UI-only), Rules #763 (paused; `main.py`, rules route, dependency files), #764 (Plan/UI only), #765 (Rules route and `main.py`), and UI design #760/#761. No current PR owns `routes/live.py`, the Agent services/models, or their tests. The child-router seam avoids both Rules claims on `main.py`. Refresh the open-PR collision inventory before PR creation; if `routes/live.py` or an exact leased path is newly claimed, stop and coordinate.

Runtime/state ownership: deterministic injected runtime and temporary isolated files only. Do not start/replace the user's API/UI/DB servers, modify persistent databases, issue paid provider calls, or use corpus state. No live dogfood is required for this deterministic backend baseline.

## §3 Observable paths and adverse sequences

| Path | Required behavior | Owning proof |
|---|---|---|
| Index/no owner, graph none | Ordinary conversation; no graph call, no session packet load; structured provider pointer may persist. | Route test with packet loader forced to fail and pointer store observed. |
| Managed World Plan, no target session | Exact World + saved Plan resolve independently; graph World read; focus none; no fabricated campaign/session. | Service and route tests. |
| Campaign-target Plan under World | Verify owner World, saved Plan's campaign/session, World graph scope, narrative campaign anchor, and session focus as one coherent relation. | Service mapping and adversarial mismatch tests. |
| Explicit campaign graph scope | Resolve campaign → owning World; reject unrelated owner/focus. | Service tests. |
| Saved work changed since request | Read current committed revision; return expected-vs-used and changed status; no browser draft bytes. | Service test with resolver revision changing. |
| Exact graph pin, empty/not-found, unavailable/foreign | Honor exact pin or fail closed; empty/not-found may answer ungrounded; invalid/unavailable requested retrieval does not call answer model. | Runtime spy route/service matrix. |
| Provider continuity | Reuse only exact structured owner/work/thread key; changed binding starts fresh. Legacy keys remain unchanged and inaccessible to new generic namespace. | Store tests plus live-route compatibility regression. |
| Route integration | Exactly one generic route in full app; `/api/live/query` stays one route with unchanged method/path and packet binding. | Full application route-table test and legacy regression. |

## §4 Files in scope — ACTIVE write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-DEMO-universal-agent-turn-backend-v1.md` | This ACTIVE implementation authority, PR contract, evidence, and exact post-dispatch base. |
| Create | `apps/live_control_server/routes/agent.py` | Generic additive Agent turn route. |
| Modify | `apps/live_control_server/routes/live.py` | Include the Agent child router only; preserve `/api/live/query`; do not edit `main.py`. |
| Create | `apps/live_control_server/models/agent_turn.py` | Strict request/result and explicit typed resolution/status objects. |
| Create | `apps/live_control_server/services/agent_turn_service.py` | Per-turn authority resolution, graph policy, context assembly and runtime dispatch. |
| Modify | `apps/live_control_server/services/agent_runtime.py` | Optional graph capability/result semantics without fabricating scope. |
| Modify | `apps/live_control_server/services/agent_context_assembler.py` | Assemble independent surface, owner, work and graph channels. |
| Modify | `apps/live_control_server/services/agent_world_graph_query_context.py` | Preserve mode, campaign anchor, exact focus, pin and resolved graph evidence. |
| Modify | `apps/live_control_server/services/agent_surface_context.py` | Keep legacy v1 adapter unchanged; add no silent surface rewrite. |
| Modify | `apps/live_control_server/services/hermes_session_store.py` | Structured provider-continuity namespace alongside untouched legacy pointers. |
| Modify | `apps/live_control_server/services/hermes_graph_query.py` | Optional graph dispatch and truthful statuses without changing legacy route semantics. |
| Create | `tests/test_agent_turn_service.py` | Deterministic service/resolver/runtime matrix. |
| Create | `tests/test_agent_turn_route.py` | Route owning-boundary and failure/no-call behavior. |
| Modify | `tests/test_live_query_hermes_graph.py` | Prove legacy packet-bound behavior unchanged. |
| Modify | `tests/test_hermes_session_store.py` | Structured pointer continuity and legacy compatibility. |
| Modify | `Docs/Roadmaps/ROADMAP-demo.md` | Backward sync #789; record backend status/evidence, current visual rejection, and mandatory all-six-surface successor. |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-demo.md` | Byte-identical roadmap mirror. |
| Modify | `Docs/Plans/HANDOFF-DEMO-J2-world-plan-canvas-composition-v1.md` | Record #789 complete from accepted review/head/merge while preserving visual judgment as unaccepted. |

No bounded-discovery exception. Any production path outside this exact lease is a stop/coordination report. Documentation changes are limited to this handoff and the named backward-looking #789/current-workflow sync.

## §5 Explicitly out of scope and collision boundary

| Path/capability | Boundary |
|---|---|
| `apps/live_control_server/main.py` | Explicitly forbidden; open Rules PRs #763 and #765 both claim it. |
| `pyproject.toml`, `uv.lock` | Forbidden; #763 has a dependency lease. |
| All six UI surfaces, shared Agent UI, publishers, `agentInteractionHistory.ts`, `api/types.ts` | Successor UI/adoption lease only; no UI/provider context mutation here. |
| New server transcript/history store | Buddy history remains browser-local. |
| WorldKeeper, DungeonMind/MIND APIs or schemas | Reuse the accepted existing graph path; external contract gap is routed to owner, not invented here. |
| Plan edits, graph writes, extraction, tool/action execution, generation tools | Generic endpoint is conversation/retrieval only. |
| Plan canvas styling and visual redesign | Explicit product-owner rejection remains open and separate; this implementation does not claim visual acceptance. |
| Persistent DBs, C1/C2/Of Conks corpus, live providers/API credentials | Not needed; tests use deterministic fakes and disposable temp roots only. |

PR #790 remains open and design-only. This implementation PR is authorized from current `main` with the exact reviewed decisions copied into this handoff; it is not a Git-stacked branch on #790. The semantic dependency is explicit and PRIME owns coordination of the two PRs. Do not merge either PR autonomously.

## §6 Implementation contract

**Input:** strict bounded user message and client IDs plus surface/work/owner/graph locators. Locators are re-resolved server-side each turn. Never accept ambient prose, source excerpts, local filesystem paths, URL-derived IDs, or client-asserted resolved status.

**Output:** one truthful result with surface generation/owner snapshot, independently resolved work status and actual revision, graph status/scope/anchor/focus/requested pin/actual head and selection result, conversation pointer outcome, answer text/status/warnings, and no implication of grounding when graph is absent/empty.

**Trust boundary:**
- Verify every non-null identity against its owning authority; malformed/foreign/removed is typed failure, not absence.
- Verify graph request is compatible with resolved owner and saved-work relation; graph focus is exact context, not authorization.
- Exact graph pin must be readable or fails; do not substitute head.
- Work expected revision is freshness expectation, not content pin; use actual current committed content and report change.
- Empty/not-found graph is not an outage and does not authorize citations.
- Structured Hermes IDs are provider continuation only, never product transcript/scope authority.

**Failure behavior:**
- Invalid or unavailable required graph request → typed result/failure, no answer-model call.
- Valid empty/not-found graph → explicit empty retrieval context, answer may run without grounding claim.
- No graph requested → answer may run without graph tools/citations.
- Missing optional owner/work → explicit absent only when truly absent; invalid supplied locator never downgrades.
- Any pointer mismatch → fresh provider continuity; never read a different key.
- Legacy request/pointer behavior remains unchanged.

**Replay:** identical IDs under the same exact structured key may reuse only that provider continuation; changed owner/work/thread identity starts fresh. Do not migrate, overwrite or delete legacy records from the generic namespace.

## §7 Evidence required to merge

| Guarantee | Owning boundary | Required evidence | Stop condition |
|---|---|---|---|
| Strict request shape and independent statuses | Pydantic model/service | Unknown/oversized/malformed values rejected; null distinct from malformed. | Silent default or field coercion. |
| No-scope Index does not load packet | API route + service | Force `load_session()`/packet loader to raise; ordinary fake-runtime answer succeeds and pointer persistence still works under temp `session_dir()`. | Any packet/session dependency. |
| World Plan and campaign Plan focus | Resolver/service | Managed World Plan focus none/no campaign anchor; verified parent-World campaign Plan preserves exact saved campaign/session; mismatch rejected. | Guessing session, alias or campaign, or broadening owner. |
| Saved work freshness | Service | Current revision differs from expected; actual committed revision returned with `changed_since_expected`; no draft/body access. | Answer mislabeled at older revision. |
| Graph outcomes and answer-call policy | Runtime/service/route | Valid empty/not-found may call ungrounded; foreign/unavailable/unreadable pin does not call answer model. | Any fallback to another lens/head. |
| Structured provider pointer isolation | Pointer store/service | Same key reuse; changed owner/work fresh; legacy pointer bytes untouched/no generic read. | Cross-key continuity or legacy auto-adoption. |
| Legacy compatibility | `/api/live/query` route | Existing tests still enforce packet/campaign/session equality, pointer key and response behavior. | Any behavior change. |
| Full route composition | Full application | Exactly one `POST /api/live/agent/turn`; exactly one unchanged `/api/live/query`; no `main.py` change. | Duplicate/missing route or registration in excluded file. |
| Lease and authority sync | Cumulative PR diff | Only §4 paths; root/mirror byte-identical; #789 recorded truthful; no visual PASS claimed. | Unleased path or stale/overclaimed state. |

Exact focused commands must be added in the implementation PR after inspecting repository conventions. At minimum run the four named Python test modules, scoped Ruff for changed Python files, relevant full application route tests, and `git diff --check`; report inherited base failures by same-command base/head comparison.

No paid/live smoke: deterministic fake runtime and isolated temp files are sufficient for this backend baseline. No model calls, live DB writes, or browser UI changes.

## §8 Required review handback

The implementation PR must hand back exact branch/base/head, declared topology and refreshed open-PR path inventory, changed paths against §4, focused and route-table evidence, base/head failures, no provider/DB side effects, commit story, unresolved visual acceptance, and the required next six-surface adoption lane. PRIME owns final merge coordination. Do not mark J2 or LOCAL DEMO ACCEPTED complete from this backend PR.
