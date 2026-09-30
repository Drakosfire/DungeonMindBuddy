# HANDOFF — DEMO: typed World Play Runbook and Agent context V2

**Status:** ACTIVE — PRIME explicitly activated C1
**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Base:** Buddy `main@a8b0d5c29feaf451b4a7b562302272bc02fdad2a` (Phase B PR #809)
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

Against PRIME's disposable PostgreSQL 16 tmpfs target
`prime-demo-phase-c1-pg-20260930` at `127.0.0.1:32768` (database `postgres`,
user `dungeonmind`), prove:

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

Run the named C1 suite against the designated database. The test fixtures
create/drop their own uniquely named databases. The target is disposable; do
not start or modify a container or touch persistent demo state. Sandbox
loopback requires running the owning tests with per-command escalation for
`127.0.0.1:32768`; use the DSN supplied by PRIME and preserve test failures.

~~~sh
postgresql://dungeonmind@127.0.0.1:32768/postgres
~~~

Run scoped Ruff, Python compilation, `git diff --check`, and the named tests.
Inspect the exact cumulative `a8b0d5c2...HEAD` diff. Commit and push this
bounded branch, open exactly one PR, and return its URL, exact head, tests and
failure dispositions to PRIME. PRIME owns review and merge. Retire the
designated C1 test database after the tests complete.

## Implementation verification — 2026-09-30

The final seven-suite PostgreSQL invocation collected 242 tests: 240 passed
and two Hermes trace-capture assertions failed in the combined run:
`test_product_trace_aggregates_model_calls_and_keeps_tool_events` and
`test_invalid_history_logs_failure_trace_once` in
`tests/test_live_query_hermes_graph.py`. Both expected one
`dmb.agent.turn_trace` log record and observed zero. PRIME traced this to
`src/application_state/migrations/env.py:15` calling `logging.config.fileConfig`
without `disable_existing_loggers=False`, which disables the trace logger when
the migration environment loads. RAKE DUTY owns a separate, narrowly leased
infrastructure repair; do not absorb it into C1. Hold this PR until that repair
merges, then rebase and rerun all seven suites against a fresh disposable
PostgreSQL target. Rerunning just the two tests passed (2 passed, 11 existing
Pydantic `schema`-field shadow warnings), but the combined suite is not green.
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
