# Hermes Rung 6 Baseline and Dogfood Report

**Date:** 2026-07-16  
**Scope:** Durable Hermes session-pointer boundary, deterministic contracts, and live Plan-surface dogfood  
**Verdict:** PASS — Rung 6 session-pointer / reload / process lifecycle gate accepted

## What is proven

### Deterministic contract layer

- The first Hermes graph turn creates a server-issued opaque `hptr-*` pointer.
- The pointer binds to `(campaign_id, agent_thread_id)` in durable local server storage.
- A valid pointer resolves to the internal Hermes session ID without exposing that ID to the UI.
- Cross-thread or cross-campaign reuse is rejected.
- Unknown and expired pointers recover to a fresh session and rotate the pointer.
- Every turn still dispatches against the server-resolved graph revision.
- Legacy client-supplied `hermes_session_id` continuity remains rejected.
- UI thread persistence and rehydration retain the server-issued pointer.
- Hermes follow-up requests send the pointer, while conversation history remains role/content-only.
- Worker-PID change telemetry reports correctly when the host worker PID differs across turns.

The parent host contract also proves process isolation, worker reuse, replacement after failure, timeout handling, and no post-accept replay in the stubbed host suite.

### Live Plan-surface dogfood

- Browser reload preserved Thread A, its turns, and status-only trace telemetry.
- After full server shutdown, startup, and hard reload, a Thread A follow-up showed:
  - `hermes_session_pointer_status: accepted`
  - `worker_pid_changed: yes`
  - `fresh_graph_revision_used: yes`
- A subsequent factual follow-up after restart issued `expand_graph_retrieval` at the pinned revision (fresh graph authority, not prose-as-truth).
- Thread B isolation dogfood passed: Thread B does not reuse Thread A's conversation history or pointer binding.
- Invalid/expired pointer recovery is accepted via deterministic contract tests, not UI dogfood — the opaque pointer is intentionally not exposed in the Plan surface.

## Verification evidence

Managed backend contract suite (pointer lifecycle):

```text
uv run pytest -q tests/test_live_query_hermes_graph.py -k 'pointer or session_pointer'
6 passed
```

Full Hermes graph-query suite:

```text
uv run pytest -q tests/test_live_query_hermes_graph.py
42 passed
```

Focused worker-restart telemetry regression:

```text
uv run pytest -q tests/test_live_query_hermes_graph.py -k 'pointer_trace_reports_worker_pid_change or first_turn_issues_opaque_pointer or follow_up_accepts_bound_pointer'
3 passed
```

Frontend pointer / Plan regressions (including prep-thread switcher close-on-select):

```text
npx vitest run src/planSurface/PlanSurfaceShell.test.tsx
54 passed
```

## Explicitly out of Rung 6 acceptance

These remain open but do **not** block the Rung 6 lifecycle gate:

- Real `AIAgent` wire-start environment failure:
  `test_host_executes_real_aiagent_tool_turn_through_wire` → `hermes_worker_start_failed`.
  Stubbed host lifecycle tests remain green; this is an environment/runtime availability
  issue, not a failed pointer-contract assertion.
- Hermes prompt / voice tuning (including steering away from thread-isolation meta-narration)
  — parked on `Backlog.md` as separate IDEAs.
- Copy-trace clipboard browser verification — observability nicety only.

## Acceptance checklist

1. Thread A first turn: `hermes_session_pointer_status=absent` — **PASS**
2. Thread A follow-up after reload / process restart: `accepted`, fresh graph revision — **PASS** (live traces after full shutdown + hard reload)
3. Thread B: no reuse of Thread A's pointer or conversation history — **PASS** (dogfood)
4. Worker restart: pointer survives, `worker_pid_changed=true`, graph retrieval remains fresh — **PASS** (live traces)
5. Invalid/expired pointer: `recovered`, fresh internal session, rotated pointer — **PASS** (deterministic tests; not UI dogfood)

## Verdict

Rung 6 is **PASS** for the durable Hermes session-pointer and reload/process lifecycle gate.
This remains distinct from Rung 4C display persistence and Rung 5 same-thread prose continuity.
Rung 5 same-thread continuity is separately accepted (DONE); Rung 7 cumulative product acceptance remains DOING.
