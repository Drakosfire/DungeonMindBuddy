# HANDOFF — DEMO Plan Agent thread continuity

**Status:** ACTIVE — one bounded runtime continuity repair

**Owner:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`

**Pinned base:** Buddy `main@9a8e0a7782252e297467cfe63826e40a85fd9b23`, independently re-anchored through GitHub on 2026-09-30

**Branch / checkout:** `codex/demo-plan-continuity` / `/tmp/dmb-demo-plan-continuity`

**PR title:** `DEMO: restore scoped Plan Agent conversation continuity`
**PR topology:** parallel-independent, one implementation PR to `main`; PRIME owns review and merge.

## Failure and user-visible outcome

In a fresh managed-World Plan witness, the first saved Plan conversation turn returned three planning questions. The next turn in the same visible thread could not see those questions and asked the user to paste them again. The saved Plan remained at revision 3 and was unchanged. The witness used `graph_request: none`, did not read Plan Markdown, and stopped at this first broken transition. Provider model, per-turn request IDs, usage, and cost were not observable and remain unknown.

The browser sends the current message and stable `client_thread_id`, not prior transcript turns. The server resolves a structured pointer for the exact verified World + saved Plan + client-thread key and forwards its Hermes session ID. The Hermes adapter constructs a fresh `AIAgent` each request and calls `run_conversation` with no history. Hermes' pinned turn context therefore starts with an empty message list. The process host also gives each worker an ephemeral home, and the per-turn runner creates and removes a separate Hermes home. The pointer proves identity reuse; it does not restore model-visible history.

## Authorized capability

For an exact active structured pointer, resume the same Hermes-native session across worker/process restarts so a saved World Plan conversation can use prior user-visible turns. On a first turn, start an empty Hermes session and bind it only after a successful turn. On a valid later turn, load prior messages from that exact Hermes-native session and pass them through the runtime's single native restore path.

Buddy continues to own the visible transcript in browser storage. Do not add, accept, or send Buddy `conversation_history`; do not create a Buddy-side transcript store; do not read saved Plan prose; do not change graph behavior, Plan editing, UI request shape, or provider/model configuration.

The server resolves one typed `plan_continuity_turn` decision from the exact work owner and active surface: true only when the resolved work kind is `plan` and the current surface is `plan`. Carry that boolean in the harness-neutral `AgentRuntimeInvocation`, through the Hermes adapter, and over the bounded host IPC request. The Hermes worker gates persistent profiles and the seven-day sliding TTL only on that typed flag. Descriptive rendered surface prose never grants continuity; other Agent surfaces keep their existing per-turn Hermes home and pointer behavior. The browser request shape remains unchanged.

Keep native Hermes profiles under the configured `session_dir()` in a dedicated `hermes_agent_profiles/` root, keyed by an opaque server-generated Hermes session handle. Never derive a path from a client thread token, document ID, URL, or caller-supplied path. Structured pointer bindings expire after a **7-day sliding idle TTL**, measured from the last successful persisted turn. Failed/rejected turns do not renew the TTL. On expiry, mark the binding expired before cleanup and remove profile bytes only inside the dedicated profile root.

If a bound Hermes profile is missing, expired, malformed, inconsistent, or cannot be decoded, fail closed without an answer-model call, revoke/expire that binding, and return an explicit continuity-unavailable message directing the user to the existing **New conversation** action. Do not silently answer under an empty reused pointer or label it reused/recovered. A new thread starts a fresh Hermes session and makes the reset visible through the existing error/new-conversation flow.

## Exclusive expected write set

- `Docs/Plans/HANDOFF-DEMO-plan-agent-continuity.md` — this bounded authority and evidence record.
- `apps/live_control_server/services/agent_runtime.py` — add the internal typed continuity decision to the harness-neutral invocation, defaulting false.
- `apps/live_control_server/services/agent_turn_service.py` — derive that decision from resolved saved-work kind and active surface, then pass it to the runtime.
- `apps/live_control_server/services/hermes_agent_runtime.py` — forward the typed decision into the Hermes request.
- `apps/live_control_server/services/hermes_graph_agent_contract.py` — serialize and strictly decode the decision in the bounded internal host wire contract.
- `apps/live_control_server/services/hermes_graph_agent.py` — gate native profile behavior on the typed decision; resolve and validate Hermes-native prior turns; use one restore path; retain no new Buddy transcript.
- `apps/live_control_server/services/hermes_graph_agent_host.py` — provide a stable per-session Hermes profile root across worker restarts and serialize access through the owning host.
- `apps/live_control_server/services/hermes_session_store.py` — exact structured identity, 7-day sliding TTL, expiry/revocation, and confined cleanup for structured Plan profiles only; preserve legacy campaign-only binding behavior.
- `tests/test_hermes_graph_agent_host.py` — real pinned Hermes Agent with an offline local Responses stub, sequential turns separated by worker restart, profile isolation, and no network attempts.
- `tests/test_hermes_session_store.py` — TTL, exact key isolation, expiry/revocation and confined profile cleanup.
- `tests/test_agent_turn_service.py` — prove only a server-resolved saved Plan on the Plan surface sets the invocation flag; preserve pointer, failed-continuity, and fresh-thread recovery regressions.
- `tests/test_hermes_agent_runtime.py` — prove the adapter forwards the typed flag into the Hermes request.

If the implementation requires a path or contract outside this list, stop and return the exact reason to PRIME before editing.

## Parallel lease and runtime boundary

At activation, current open Buddy PRs were refreshed:
- #810 C1 at `a1f3f8e4cf3800d29b3543911dbab645b598ecac`, based on `a8b0d5c29feaf451b4a7b562302272bc02fdad2a`.
- #811 RAKE at `ae1e3aaff746aee8ad630ffa58f7e22d79d3997e`, based on the same base.

The continuity write set is disjoint from both leases. #810 owns its C1 handoff/roadmap, typed World Play paths and C1 suites; #811 owns its migration logger handoff, Alembic environment and migration logger test. Do not modify `Docs/Roadmaps/ROADMAP-demo.md`, C1 paths, #811 paths, schemas/migrations, other owners' work, or shared runtime state.

All implementation tests use disposable temporary directories and the pinned local Hermes runtime with a stubbed local Responses transport. The existing `7865/5177` Plan witness is read-only. Do not start a patched build against it; PRIME will coordinate a separate isolated patched-build witness after local verification.

## Owning-boundary verification

1. Through the actual process host and pinned Hermes `AIAgent`, send a first turn that introduces a harmless unique fact, stop/restart the host, then send a second turn with the same server session handle. The offline model request must include the prior visible user/assistant exchange and answer from it. No real provider/network call is allowed.
2. A different Hermes session handle receives no prior exchange. Service/store tests prove changed World, Plan, or client-thread identity resolves a different/fresh structured binding and cannot read the prior profile.
3. Same-session concurrent turns are serialized by the host or explicitly rejected before either can corrupt native history. Preserve the existing host concurrency regression.
4. Expired (older than seven idle days), missing, malformed, or mismatched native state fails closed, does not call the answer model, expires/revokes the binding, and cleans only its hashed profile path after status is recorded. A subsequent new client thread starts clean.
5. A successful turn updates the sliding TTL; failures do not. Existing legacy campaign pointer lookup/write behavior remains unchanged.
6. The generic Plan request remains `graph:none` with no graph selection, browser history, Plan body, or document mutation. The response/error remains honest, and the saved Plan revision does not change.

Run the focused host, store, and Agent turn service suites; any additional check must answer a concrete failure risk. Review the exact cumulative `main@9a8e0a7... → head` diff before PR creation. No live provider acceptance is part of local implementation verification; PRIME owns the separate patched-build witness and merge review.

## Review update — 2026-09-30

PRIME reviewed #817 at `4339d500cadd575b081157c255405e3b2680a702` and found that the worker selected persistent profiles by searching an English sentence in descriptive surface prose. The service's authority decision is already typed (`work_kind == "plan"` and `surface_id == "plan"`), so prose and authorization could diverge. This slice now carries `plan_continuity_turn` through the harness-neutral invocation, Hermes adapter, and strict host wire contract; only that flag enables persistent profiles. The browser contract remains unchanged. PRIME authorized the added invocation/adapter/wire paths and focused tests in this same PR.

At the updated working tree: Agent turn service + Hermes adapter tests **26 passed**; session-store suite **13 passed**; Hermes graph-agent suite **51 passed**; focused host/wire/continuity cases **6 passed**. Ruff, compileall, and cumulative `git diff --check` passed. The full host suite was not rerun; the earlier full run stalled after 40 dots and was interrupted. No live provider call or patched-runtime witness is claimed here.

## Authority

PRIME explicitly authorized this single parallel-independent implementation from `main@9a8e0a7782252e297467cfe63826e40a85fd9b23` after the read-only RAKE diagnosis and ARCHITECTURE's runtime/session-lifecycle ruling. PRIME selected the 7-day sliding idle TTL and restricted cleanup to the dedicated hashed profile root. During exact-head review, PRIME expanded this same slice's lease to the typed invocation, adapter, wire-contract, and service paths listed above; no second capability or PR was added. PRIME owns the post-test live witness, review, and merge.
