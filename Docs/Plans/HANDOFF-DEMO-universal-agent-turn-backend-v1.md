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

**Mission:** Establish the first truthful universal Agent backend baseline for no-graph conversation and graph reads under a verified Buddy World owner, while preserving exact saved-work and temporal-context metadata where the existing authority proves them.

**Merge-ready invariant:** The generic Agent endpoint either resolves each supported requested authority independently and reports exactly what it used, or returns a typed fail-closed result without silently dropping invalid scope, changing graph focus, loading a session packet for no-scope chat, calling the answer model after required retrieval fails, crossing a structured provider-continuity key, or changing legacy `/api/live/query` behavior. This implementation's supported graph baseline is a verified World owner/lens plus a sessionless World Plan; no graph scope is represented by the explicit conversation-only policy.

This is the backend baseline only. It does not deliver universal Agent UI, all six surface publishers, user-facing visual acceptance, or end-to-end J2/J3 acceptance. **Campaign-owner and campaign-lens graph requests remain typed, fail-closed unavailable** until Buddy has an accepted campaign→World membership authority. They are not counted as implemented behavior or merge evidence for this baseline. This is the bounded activation clarification accepted by PRIME after architecture review; it does not rewrite the broader #790 design contract.

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
- Canonical session IDs derived from a saved Plan's server-resolved integer `target_session` use Buddy's existing `normalize_session_id(int)` encoding (`session-N`), not caller-string normalization. The generic resolver must require the submitted focus to exactly match that derived value. This encoding is not evidence that graph content exists; a valid projection may still be empty.
- A graph node or session focus paired with `graph_request.mode="none"` is contradictory and is rejected, not ignored or used to upgrade to retrieval.
- `saved_dirty` is only a browser hint. Resolve the actual latest committed saved-work revision; if it differs from the expected revision, report expected and used and `changed_since_expected`. Never read local/unsubmitted draft prose.
- A valid empty result or selected-node not-found is distinct from invalid/foreign scope, unavailable graph service, or unreadable requested pin. Required retrieval failure makes no answer-model call; valid empty/not-found may answer without grounding claims.
- Generic no-scope turns use an explicit serialized `conversation_only` runtime policy, with no graph scope, graph plugin, graph tools, or graph citations. This is distinct from graph mode with an empty/fake scope. Graph mode continues to require a fully resolved graph scope and retains its existing capability validation.
- Generic no-scope turns may persist structured Hermes provider-continuity pointers under configured `session_dir()` as storage only. They must not call `load_session()` or require a packet. Buddy transcript remains browser-local and is not a new server transcript store.
- Generic bindings never read/adopt/rewrite legacy campaign-only pointer records. `/api/live/query` retains exact legacy behavior.
- Delivery order after this baseline: separately activated shared Agent UI/adapters on Index, Plan, Play, Build, Ingest and Combat; then owner-to-backend end-to-end witnesses. World-reference lens work consumes this authority later.

At dispatch the repository had open #790 (design only), #781 (UI-only), Rules #763 (paused; `main.py`, rules route, dependency files), #764 (Plan/UI only), #765 (Rules route and `main.py`), and UI design #760/#761. No current PR owns `routes/live.py`, the Agent services/models, or their tests. The child-router seam avoids both Rules claims on `main.py`. Refresh the open-PR collision inventory before PR creation; if `routes/live.py` or an exact leased path is newly claimed, stop and coordinate.

**Implementation-discovered authority limit:** current Buddy authorities do not provide a general campaign→parent-World mapping for ordinary campaign-target Plans. `WorldContainerRecord` identifies Worlds but not campaign membership; saved Plan records carry campaign identity or World ownership, not both as a general membership relation. The generic route therefore rejects unproven campaign-owner and campaign-graph requests. It must not treat a campaign ID as a World ID or use the legacy SourceArtifact world fallback as membership authority. This means the campaign→World row in §7 remains **HOLD** pending a separately accepted Buddy-owned membership contract; no campaign graph behavior is claimed complete by this implementation.

The exact session encoding is independently grounded in `src/graph_memory/session_graph_context.py::_session_id_from_number()` and `tests/test_graph_memory_session_graph_context.py` (e.g. integer 99 → `session-99`), plus `apps/live_control_server/services/recap_artifacts.py::normalize_session_id()` and `tests/test_recap_artifacts.py::test_normalize_session_id`. This implementation uses the normalizer only on the integer `target_session` read from the resolved saved Plan record, then requires any submitted session focus to match that exact derived ID and campaign. It does not parse caller-supplied free text or treat the derived ID as proof that graph evidence exists.

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
| Modify | `apps/live_control_server/services/hermes_agent_runtime.py` | Map no-scope conversation turns to the existing Hermes runtime without constructing graph authority or graph tools. |
| Modify | `apps/live_control_server/services/pydantic_ai_agent_runtime.py` | Map no-scope conversation turns to the existing PydanticAI runtime without graph authority, graph tools, or scoped tool arguments. |
| Modify | `apps/live_control_server/services/hermes_graph_agent.py` | Dispatch the explicit conversation-only worker mode without graph-specific scope, prompt, retrieval, or tool registration. |
| Modify | `apps/live_control_server/services/hermes_graph_agent_contract.py` | Discriminated worker-wire mode: graph mode has its required scope; conversation-only has none and rejects contradictory graph authority. |
| Modify | `src/graph_memory/hermes_graph_plugin.py` | Represent conversation-only capability separately from graph-read policy; do not relax graph-policy scope requirements. |
| Modify | `apps/live_control_server/services/agent_context_assembler.py` | Assemble independent surface, owner, work and graph channels. |
| Modify | `tests/test_agent_context_assembler.py` | Prove no-graph assembly creates no World scope or retrieval packet and preserves local conversation metadata. |
| Modify | `apps/live_control_server/services/agent_world_graph_query_context.py` | Preserve mode, campaign anchor, exact focus, pin and resolved graph evidence. |
| Modify | `apps/live_control_server/services/agent_surface_context.py` | Keep legacy v1 adapter unchanged; add no silent surface rewrite. |
| Modify | `apps/live_control_server/services/hermes_session_store.py` | Structured provider-continuity namespace alongside untouched legacy pointers. |
| Modify | `apps/live_control_server/services/hermes_graph_query.py` | Optional graph dispatch and truthful statuses without changing legacy route semantics. |
| Create | `tests/test_agent_turn_service.py` | Deterministic service/resolver/runtime matrix. |
| Create | `tests/test_agent_turn_route.py` | Route owning-boundary and failure/no-call behavior. |
| Modify | `tests/test_live_query_hermes_graph.py` | Prove legacy packet-bound behavior unchanged. |
| Modify | `tests/test_hermes_session_store.py` | Structured pointer continuity and legacy compatibility. |
| Modify | `tests/test_hermes_agent_runtime.py` | Exercise the actual Hermes adapter mapping and no-graph tool/capability boundary. |
| Modify | `tests/test_pydantic_ai_agent_runtime.py` | Exercise the actual PydanticAI adapter mapping and no-graph tool/capability boundary. |
| Modify | `tests/test_hermes_graph_agent.py` | Exercise worker mode validation, conversation-only dispatch/tool surface, and preserved graph-policy rejection behavior. |
| Modify | `tests/test_hermes_graph_agent_host.py` | Exercise conversation-only mode through the existing host serialization/worker seam. |
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
| New provider/runtime engine, model selection or fallback, dependency/SDK change, graph writes/actions | Forbidden. Reuse the selected runtime and existing process-isolated Hermes host; conversation-only means no graph tools/authority, not a new capability surface. |

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
| World Plan focus | Resolver/service | Verified World Plan resolves current committed revision, no target session means focus none, and any target session uses the canonical ID derived from the server-resolved integer record and rejects mismatches. | Guessing from caller data or broadening owner. |
| Campaign-owner and campaign-lens graph requests | Explicit accepted authority dependency | Typed fail-closed unavailable; no answer model call; campaign→World membership is not supplied by this baseline. This row is **deferred/HOLD**, not a PASS. | Treating a campaign ID, legacy SourceArtifact fallback, URL, or client map as its parent World. |
| Saved work freshness | Service | Current revision differs from expected; actual committed revision returned with `changed_since_expected`; no draft/body access. | Answer mislabeled at older revision. |
| Graph outcomes and answer-call policy | Runtime/service/route | Valid empty/not-found may call ungrounded; foreign/unavailable/unreadable pin does not call answer model. | Any fallback to another lens/head. |
| Structured provider pointer isolation | Pointer store/service | Same key reuse; changed owner/work fresh; legacy pointer bytes untouched/no generic read. | Cross-key continuity or legacy auto-adoption. |
| Legacy compatibility | `/api/live/query` route | Existing tests still enforce packet/campaign/session equality, pointer key and response behavior. | Any behavior change. |
| Full route composition | Full application | Exactly one `POST /api/live/agent/turn`; exactly one unchanged `/api/live/query`; no `main.py` change. | Duplicate/missing route or registration in excluded file. |
| Lease and authority sync | Cumulative PR diff | Only §4 paths; root/mirror byte-identical; #789 recorded truthful; no visual PASS claimed. | Unleased path or stale/overclaimed state. |

The focused cohort below uses the pinned reviewer environment at `/tmp/pr791-prime-review/.venv`; the repository-root `.venv` was not used because its installed DungeonMind package was stale. `httpx.ASGITransport` exercises the complete `create_app()` HTTP routing stack without starting the Hermes worker lifespan; every test injects a deterministic fake runtime and makes no model/provider call.

### Implementation verification record

The exact candidate source passed the bounded request/service/adapter and legacy-route cohorts:

```bash
PYTHONPATH=src:. /tmp/pr791-prime-review/.venv/bin/pytest -q \
  tests/test_agent_turn_route.py \
  tests/test_agent_turn_service.py \
  tests/test_agent_context_assembler.py \
  tests/test_hermes_agent_runtime.py \
  tests/test_hermes_session_store.py \
  tests/test_hermes_graph_agent.py \
  tests/test_hermes_graph_agent_host.py \
  tests/test_pydantic_ai_agent_runtime.py
# 167 passed

PYTHONPATH=src:. /tmp/pr791-prime-review/.venv/bin/pytest -q \
  tests/test_live_query_hermes_graph.py
# 65 passed

/tmp/pr791-prime-review/.venv/bin/ruff check \
  apps/live_control_server/routes/agent.py \
  apps/live_control_server/services/agent_runtime.py \
  apps/live_control_server/services/agent_surface_context.py \
  apps/live_control_server/services/agent_turn_service.py \
  apps/live_control_server/services/hermes_agent_runtime.py \
  apps/live_control_server/services/hermes_graph_agent.py \
  apps/live_control_server/services/hermes_session_store.py \
  apps/live_control_server/services/pydantic_ai_agent_runtime.py \
  tests/test_agent_turn_route.py \
  tests/test_agent_turn_service.py \
  tests/test_hermes_session_store.py \
  tests/test_hermes_graph_agent.py \
  tests/test_pydantic_ai_agent_runtime.py
# All checks passed!

git diff --check
# clean
```

The two full-application route tests assert exactly one `POST /api/live/agent/turn` and one legacy `POST /api/live/query`; one sends a no-graph request through the complete HTTP route, and the other publishes an in-memory DungeonMind revision and verifies the returned World projection reaches the injected runtime. The prior TestClient attempt stalled because AnyIO's sync worker threads cannot run in the restricted sandbox (a minimal FastAPI route reproduced the same issue); the ASGITransport HTTP proof passed outside that sandbox. The exact candidate also passes the unchanged 65-test legacy route suite. No provider call, live database write, persistent state mutation, or UI edit was used.

No paid/live smoke: deterministic fake runtime and isolated temp files are sufficient for this backend baseline. No model calls, live DB writes, or browser UI changes.

## §8 Required review handback

The implementation PR must hand back exact branch/base/head, declared topology and refreshed open-PR path inventory, changed paths against §4, focused and route-table evidence, base/head failures, no provider/DB side effects, commit story, unresolved visual acceptance, and the required next six-surface adoption lane. PRIME owns final merge coordination. Do not mark J2 or LOCAL DEMO ACCEPTED complete from this backend PR.
