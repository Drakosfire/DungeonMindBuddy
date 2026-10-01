# HANDOFF — DEMO: typed World Play Runbook and Agent context V2

**Status:** ACTIVE — PRIME explicitly activated C1
**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Base:** Buddy `main@2da16c35e1902468451910a44550ff2db20a5bbe` (after RAKE PR #811 merge)
**Branch / checkout:** `codex/demo-world-play-c1` / `/home/drakosfire/.codex/worktrees/8b2b/DungeonMindBuddy`
**Topology:** Serial. C1 is one implementation PR; C2 remains BLOCKED until C1 merges and its PostgreSQL owning-boundary witness passes.
**PR title:** `DEMO: add typed World Play Runbook and context V2`

PRIME activated C1 after re-anchoring Buddy main, open PRs, and active leases.
The paths below are an exclusive write lease. Stop and return to PRIME if a
schema migration, another path, another repository, or a runtime/product-state
change is needed. The ACTIVE Phase B implementation lease ended at #809 merge.

## Capability and authority

Expose the existing World-owned Runbook Content capability through a narrow,
typed World API: list, create, read, snapshot, TipTap prepare, and TipTap commit.
The managed World identity and the exact immutable Content revision/SHA remain
the authorities consumed by World PlayRun V2. A World ID is never sent as
`campaign_id`; generic workspace-document APIs retain their existing campaign
contract.

Add a specialized read-only Play context V2 request for `/api/live/query`.
It carries explicit `world_id`, `run_id`, and `run_revision`, with no
`campaign_id`. Before admission, the route verifies the same managed World,
World PlayRun V2 detail, independent Run revision, and exact pinned Runbook
artifact/revision/SHA. The global active-Run pointer is only a hint and must be
validated through World V2 detail. Never silently switch Worlds.

Preserve `dmb_agent_surface_context_request_v1` exactly, including its required
fields and campaign behavior. Add an explicit V2 discriminator for the typed
World Play context. Keep the `/api/live/query` outer packet/session contract,
campaign path, graph request and response semantics unchanged. Admit nested
V2 only for managed World Ask after validating the same World V2 Run and exact
pin. The specialized context reader remains read-only; this does not authorize
the generic `/api/live/agent/turn` resolver, Play Agent UI, provider, turn, or
prompt changes.

## C1 exclusive write lease

Only these paths may be edited:

~~~text
Docs/Plans/HANDOFF-DEMO-world-play-surface-v2.md
Docs/Plans/HANDOFF-DEMO-world-owned-play-runs.md
Docs/Roadmaps/ROADMAP-demo.md
Docs/Plans/HANDOFF-DEMO-world-owned-runbook-foundation.md
Docs/Plans/HANDOFF-DEMO-world-play-run-v2-backend.md
Docs/Plans/HANDOFF-DEMO-universal-agent-turn-backend-v1.md
apps/live_control_server/routes/workspace_documents.py
apps/live_control_server/routes/live.py (only typed World Runbook routes and nested managed-World context V2 admission/transport)
apps/live_control_server/services/workspace_document_registry.py
apps/live_control_server/services/tiptap_markdown_write.py
apps/live_control_server/services/agent_surface_context.py
apps/live_control_server/services/agent_play_surface_context.py
apps/live_control_server/services/live_agent_loop.py (only the surface_context request union annotation)
tests/test_world_play_runs_v2.py
tests/test_workspace_document_registry.py
tests/test_live_tiptap_markdown_write.py
tests/test_agent_surface_context.py
tests/test_agent_play_surface_context.py
tests/test_live_query_hermes_graph.py
tests/test_live_control_server.py
~~~

The last three handoff paths are limited to truthful predecessor settlement.
Do not expand runtime scope based on those documentation edits. Do not edit
`routes/agent.py`, `main.py`, a generic Agent Run resolver, UI files, provider
code, schemas/migrations, dependencies, or any other repository.

PRIME explicitly accepted `services/live_agent_loop.py` as a narrow lease
amendment: only its `surface_context` parameter annotation carries the
existing V1 request or typed World Play V2 request. No runtime behavior in
that service is otherwise changed.

## Owning-boundary witness

Against PRIME's fresh disposable PostgreSQL 16 tmpfs container
`prime-demo-c1-pg-20260930-b` at `127.0.0.1:55454` (PRIME owns the container;
DEMO owns only the databases created and dropped by test fixtures). The
previously named `prime-demo-phase-c1-pg-20260930` at `127.0.0.1:32768` is
retired and must not be used. Prove:

- Create a managed World A Runbook through the typed API, list/read it only in
  World A, then obtain its Content snapshot and immutable committed revision.
- Prepare and commit TipTap edits through the typed World route; the returned
  revision and SHA are exactly those consumed when a World V2 Run is started.
- World B cannot list/read/mutate World A's Runbook. A World ID equal to an
  unrelated Campaign string grants no access. Missing/foreign World identity,
  wrong Run, stale `run_revision`, and any artifact/revision/SHA pin mismatch
  fail closed before dependent work.
- Typed context V2 resolves only the selected World's exact V2 Run and
  retained pin. Missing/invalid World, mismatched or stale Run revision,
  damaged pin, and legacy unbound Run are rejected. It never derives authority
  from `campaign_id` or the active pointer.
- V1 context request parsing, resolution, campaign Play behavior and existing
  managed World Plan behavior remain unchanged. No context read mutates Run,
  Runbook, or manifest state.

Run these seven C1 suites with `DMB_APPLICATION_STATE_TEST_DATABASE_URL` set
to `postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:55454/postgres`:

~~~text
tests/test_world_play_runs_v2.py
tests/test_workspace_document_registry.py
tests/test_live_tiptap_markdown_write.py
tests/test_agent_surface_context.py
tests/test_agent_play_surface_context.py
tests/test_live_query_hermes_graph.py
tests/test_live_control_server.py
~~~

PRIME owns container `prime-demo-c1-pg-20260930-b`; the test fixtures
create/drop their own uniquely named databases. Do not start or modify any
container, touch other containers or persistent demo state, or use the retired
32768 target. PRIME will retire its container after verification. Preserve test
failures.

Run scoped Ruff, Python compilation, `git diff --check`, and the named tests.
Inspect the exact cumulative `2da16c35...HEAD` diff. Commit and push this
bounded branch, update the assigned PR #810, and return its URL, exact head,
tests and failure dispositions to PRIME. PRIME owns review and merge; PRIME
retires the test container after verification.

## Implementation verification — 2026-09-30

The pre-fix seven-suite PostgreSQL invocation on the previous C1 base collected
242 tests: 240 passed and two Hermes trace-capture assertions failed in the
combined run: `test_product_trace_aggregates_model_calls_and_keeps_tool_events`
and `test_invalid_history_logs_failure_trace_once` in
`tests/test_live_query_hermes_graph.py`. Both expected one
`dmb.agent.turn_trace` record and observed zero. PRIME traced this to
`src/application_state/migrations/env.py:15` calling `logging.config.fileConfig`
without `disable_existing_loggers=False`, which disables the trace logger when
the migration environment loads. PRIME activated RAKE DUTY's separate repair
lane from `main@a8b0d5c29feaf451b4a7b562302272bc02fdad2a`, branch
`codex/rake-alembic-preserve-loggers`, under
`Docs/Plans/HANDOFF-RAKE-alembic-preserve-loggers.md`. Its exclusive paths were
that handoff, `src/application_state/migrations/env.py`, and
`tests/test_application_state_migration_logging.py`; RAKE was authorized to open
one PR and PRIME retained review and merge.

Buddy [PR #811](https://github.com/Drakosfire/DungeonMindBuddy/pull/811) merged
at Buddy main `2da16c35e1902468451910a44550ff2db20a5bbe` from reviewed head
`619c11998a7bc17bc0fd740791352e1b275cdf84` (original head
`ae1e3aaff746aee8ad630ffa58f7e22d79d3997e`). The offline regression is at
`tests/test_application_state_migration_logging.py`, outside the nested
PostgreSQL fixture path. RAKE reported the offline Alembic SQL-mode regression
passed 1/1 and the ordered regression plus both C1 Hermes trace tests passed
3/3 in 8.48 seconds. That run used an unusable port-1 URL for the offline test
and a temporary source archive of pinned DungeonMind commit
`7c69e447f6d4acc963ac09c6fb9cb48cc1c5b9cc` for imports; it made no database
connection or dependency sync. Eleven existing Pydantic `schema` shadow
warnings were emitted. Scoped Ruff and `git diff --check origin/main...HEAD`
passed against the then-current main `efadc41019e39ca53d19bca85cd7e2a560763049`;
the cumulative RAKE diff contained only its three leased paths. PRIME
independently reran the offline regression (1 passed) before merging #811.

C1 was rebased onto `main@2da16c35e1902468451910a44550ff2db20a5bbe`; the
implementation code head at the fresh witness was
`561513a8a2ca2099380e4f891ec1012f37e1f21d`. PRIME designated fresh disposable
PostgreSQL 16 tmpfs container `prime-demo-c1-pg-20260930-b` at
`127.0.0.1:55454`, with admin DSN
`postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:55454/postgres`. PRIME owns
the container; DEMO owns only test-fixture databases. The previous target
`prime-demo-phase-c1-pg-20260930` at `127.0.0.1:32768` is retired.

The exact seven-suite PostgreSQL witness passed: 242 passed, 11 existing
Pydantic `schema`-field shadow warnings, in 106.39 seconds. It ran against the
rebased implementation code head above with
`DMB_APPLICATION_STATE_TEST_DATABASE_URL` set to the designated admin DSN. The
post-run cleanup query found no `dungeonbuddy_app_state_test_*` databases.
Scoped Ruff passed on the nine changed Python files; Python `compileall`,
`git diff --check origin/main...HEAD`, and the worktree `git diff --check`
passed. ARCHITECTURE confirmed the merged logger repair requires no C1 contract
or witness changes. PRIME will retire the disposable container after
verification. This passing witness supersedes the prior 240-pass, 2-failure
run. Do not absorb RAKE's repair into C1. C2 remains blocked pending C1 merge.
All C1 behavior tests passed, including the focused PostgreSQL World Runbook,
context, ownership, and pin-boundary run (29 passed, 11 existing warnings).

Scoped Ruff, Python `compileall`, and `git diff --check` passed. The Pydantic
shadow warnings are pre-existing. These results do not authorize C2 or claim
the C1 witness is fully green.

## C2 remains blocked

C2 is a separate serial UI enablement lease, not part of this PR. It may start
only after C1 merges and its owner-boundary witness passes. It must separately
audit and migrate World Runbook selection, Start Run, active selection, reload,
resume, progress and same-World rebase in the mounted Play surface. It must
preserve campaign compatibility and fail closed on cross-World selection,
campaign-string matches, unbound legacy Runs and damaged pins. No C2 UI path is
authorized here.

The six-surface Agent UI adoption, generic Agent Run resolution, J1–J6,
rejected visual acceptance, J3 retrieval and operator acceptance remain open.
