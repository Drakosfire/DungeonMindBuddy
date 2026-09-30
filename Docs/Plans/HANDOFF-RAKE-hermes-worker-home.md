# HANDOFF — RAKE: keep Hermes logging home with its worker

**Status:** ACTIVE — PRIME authorized one bounded backend repair on 2026-09-30
**Repository:** `Drakosfire/DungeonMindBuddy`
**Base at activation:** exact Buddy `main@3494b8f4561b2ec465af42bf4fb55bac3f42ee3c`
**Refreshed base:** exact Buddy `main@92b55241f2736853c4e18182b963dd086ed6314e`
**Branch:** `codex/rake-hermes-worker-home`
**Topology:** `parallel-independent` from open Buddy #810 and #811; one PR to `main`. PRIME owns review and merge.

## Failure and capability

Two ordinary saved Plan UI turns on the same thread/session returned HTTP 200.
API output also reported `FileNotFoundError` for Hermes' per-turn
`/tmp/dmb-hermes-graph-home-*/logs/agent.log` and `errors.log`. The runtime
creates a fresh `HERMES_HOME` for each turn and removes it in `finally` at
`apps/live_control_server/services/hermes_graph_agent.py:1197`, while
`HermesGraphAgentHost` reuses one spawned process. Hermes 0.18.2 caches
`run_agent._hermes_home` and keeps asynchronous file handlers for the worker's
lifetime. A handler and its queue can therefore outlive the turn home they
target. This is a logger-home lifetime mismatch and cleanup race, not absent
logger initialization or a failed provider response.

Keep a private logger home for the reused worker. Pin Hermes' cached logger
home to it before the first per-turn profile is installed; retain fresh
per-turn profiles for turn configuration. Drain and stop the Hermes logging
queue before the worker exits, then let the host remove the private home only
after the worker process has exited. No route, provider, model, schema, or
dependency changes are in scope.

## Exclusive write lease

Only these paths may change:

~~~text
Docs/Plans/HANDOFF-RAKE-hermes-worker-home.md
apps/live_control_server/services/hermes_graph_agent_host.py
apps/live_control_server/services/hermes_graph_agent.py
tests/test_hermes_graph_agent_host.py
~~~

No provider/model calls, database access, live routes, schemas, UI, external
service, dependency, or lockfile changes are authorized. Do not edit the
separate #810 or #811 leases.

## Acceptance and verification

- Two fake turns execute on the same spawned worker without a provider call.
- The fake Agent emits INFO and WARNING records on both turns. Before private
  home cleanup, `agent.log` and `errors.log` contain all expected records and
  worker stderr contains no `FileNotFoundError`.
- The worker drains and stops file logging; the parent joins the worker before
  deleting its private home. The regression observes the log files and drain
  marker at the exact cleanup boundary.
- If forced termination prevents drain confirmation after log files exist,
  preserve that private home for diagnosis rather than deleting unflushed logs.
- The real-AIAgent host test uses locally synthesized Responses events. A
  socket-level tripwire blocks and counts network attempts; the test asserts
  zero attempts and exactly two calls to the local Responses stream stub.
- Run both relevant test files only with provider/model transports locally
  stubbed, no network access, and explicit zero-network assertions. The
  TestClient lifespan hang is tracked separately below.
- Review the cumulative diff from the exact base before opening one PR.

## Collision check

At activation, #810 is open at `a20e14518ebdb24a5e1790c2486dfad8758c7920` and
touches World Play Runbook/context routes, services, tests, roadmap, and DEMO
handoffs; it does not touch this lease. #811 is open at
`ae1e3aaff746aee8ad630ffa58f7e22d79d3997e` and is limited to Alembic logging,
its test, and its own handoff. Neither changed-path set overlaps this lease.
After the requested refresh, Buddy `main` is
`92b55241f2736853c4e18182b963dd086ed6314e`. #810 and #811 remain open at those
same heads and still have no changed-path overlap. #813 is merged at this base;
its head `046b9a7ccfa064e3a1865e32cf999a3a54a81ba3` changed only the Plan trace
receipt handoff and Plan UI conversation/test files, with no overlap here.

## Verification record

The first broad run was not safely isolated and does **not** establish zero
provider/network calls. Preserve its exact failure evidence:

- The failing host test was
  `test_host_executes_real_aiagent_tool_turn_through_wire`; the named
  `test_real_worker_executes_rung3_entry_for_validation_error` passed. The
  fake test client supplied Chat Completions responses while pinned Hermes
  selected `codex_responses`. Captured result:

  ~~~text
  ⚠️  API call failed (attempt 1/3): RuntimeError
     🔌 Provider: openai-api  Model: gpt-5.3-codex
     🌐 Endpoint: https://api.openai.com/v1
     📝 Error: Codex Responses stream did not emit a terminal response
     ⏱️  Elapsed: 0.03s  Context: 2 msgs, ~1,211 tokens
  ⏳ Retrying in 2.6s (attempt 1/3)...
  ⚠️  API call failed (attempt 2/3): RuntimeError
     🔌 Provider: openai-api  Model: gpt-5.3-codex
     🌐 Endpoint: https://api.openai.com/v1
     📝 Error: Codex Responses stream did not emit a terminal response
     ⏱️  Elapsed: 2.64s  Context: 2 msgs, ~1,211 tokens
  ⏳ Retrying in 5.0s (attempt 2/3)...
  ⚠️  API call failed (attempt 3/3): RuntimeError
     🔌 Provider: openai-api  Model: gpt-5.3-codex
     🌐 Endpoint: https://api.openai.com/v1
     📝 Error: Codex Responses stream did not emit a terminal response
     ⏱️  Elapsed: 7.85s  Context: 2 msgs, ~1,211 tokens
  ❌ API failed after 3 retries — Codex Responses stream did not emit a terminal response
     💀 Final error: Codex Responses stream did not emit a terminal response
  🧾 Request debug dump written to: /tmp/dmb-hermes-graph-home-obr4vm3p/sessions/request_dump_sess-host-tool_20260930_073519_398087.json
  Captured stderr: Failed to fetch model metadata from OpenRouter: HTTPSConnectionPool(host='openrouter.ai', port=443): Max retries exceeded with url: /api/v1/models (Caused by NameResolutionError("HTTPSConnection(host='openrouter.ai', port=443): Failed to resolve 'openrouter.ai' ([Errno -2] Name or service not known)"))
  ~~~

- `tests/test_hermes_graph_agent.py::test_pinned_hermes_auto_selects_responses_for_policy_model`
  failed during `AIAgent` logging setup, before its conversation path:

  ~~~text
  OSError: [Errno 30] Read-only file system: '/home/drakosfire/.hermes/logs/agent.log'
  ~~~

- `tests/test_hermes_graph_agent.py::test_real_aiagent_dispatches_provider_tool_call_through_registry`
  also failed before returning an Agent result:

  ~~~text
  AssertionError: ('hermes_agent_init_error', 'Hermes graph-agent construction failed.')
  Failed to fetch model metadata from OpenRouter: HTTPSConnectionPool(host='openrouter.ai', port=443): Max retries exceeded with url: /api/v1/models (Caused by NameResolutionError(...))
  ~~~

  This test is outside the four leased paths and was not rerun. Its
  transport/client setup needs owner authorization before any edit or safe
  replay can be completed.

After the failure was identified, the leased host integration test was changed
to return two local Responses event streams. Both it and the two-turn logging
regression now install socket tripwires and record model-catalog requests as
local stubs. Safe verification completed:

- `tests/test_hermes_graph_agent_host.py -k 'not test_app_lifespan_shuts_down_global_host'`:
  **51 passed, 1 deselected**. The guarded Responses test asserted two local
  stream requests and zero socket-level network attempts.
- `tests/test_hermes_graph_agent.py -k 'not test_real_aiagent_dispatches_provider_tool_call_through_registry'`:
  **50 passed, 1 deselected**, with the offline pytest guard and a writable
  temporary Hermes home. This includes a passing policy-selection test; the
  out-of-lease real-Agent dispatch test remains unverified.
- After consolidating the worker network guard, the focused logging and local
  Responses host tests passed: **2 passed in 7.05s**.
- `ruff check` on the three leased Python files and `git diff --check`: pass.

The `TestClient.__enter__` hang in
`test_app_lifespan_shuts_down_global_host` was independently reproduced on the
exact pinned base `3494b8f4561b2ec465af42bf4fb55bac3f42ee3c`. A baseline run
timed out after 25 seconds (exit 124); a faulthandler capture located the main
thread waiting at `starlette.testclient.TestClient.__enter__` and the test call
site. It is inherited and was deselected from the safe host suite.

## Handback

Return the exact base and head, PR URL, changed paths, owning-boundary test
results, cumulative diff review, and any inherited failures. Do not merge.
