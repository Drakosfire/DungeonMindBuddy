# DEMO handoff — successful Agent turn trace emission

**Status:** ACTIVE
**Owner:** DEMO steward, authorized by PRIME
**Repository:** Drakosfire/DungeonMindBuddy
**Base:** main@ea1badba8e433db78029aee7e0ca0f809907eeda
**Branch:** codex/demo-agent-trace-emission
**Topology:** parallel-independent from the checked open PRs #810 and #811. PRIME approved the bounded service/test lease. Neither open PR includes the service or test paths below.

## User-visible outcome

A successful graphless Plan Agent turn returns its answer.trace and emits exactly one sanitized dmb_agent_turn_trace event with the same trace ID. The current service calls AgentTurnTraceBuilder.finalize(), which constructs the trace but does not emit it. The existing finalize_and_log() uses the established privacy-filtered logger.

RAKE DUTY confirmed this source behavior read-only on main@ea1bad... after #814. The three witness requests returned HTTP 200; response bodies and provider receipts were not preserved, so request IDs, usage, cost, and attempt count remain unknown. The missing event is not evidence of provider failure.

## Invariants and exclusions

- Preserve the returned answer.trace unchanged and use the existing privacy-filtered event emitter.
- Emit one event for each finalized runtime result, with the same trace ID returned to the caller.
- Never add raw prompt, response, or tool-result bodies to logs.
- Keep graphless Plan behavior, runtime selection, response schema, routes, UI, and failure response behavior unchanged.
- Do not touch #810 or #811 leased paths.

## ACTIVE write allowlist

- Docs/Plans/HANDOFF-DEMO-agent-turn-trace-emission.md — this authority record.
- apps/live_control_server/services/agent_turn_service.py — call the existing log-aware finalizer.
- tests/test_agent_turn_service.py — prove a successful graphless Plan turn returns and logs the same sanitized trace.

The active roadmap is part of #810's lease and is intentionally excluded from this write set. Reconcile the result into the roadmap after that lease settles.

## Re-anchor and collision check

- Buddy main is ea1badba8e433db78029aee7e0ca0f809907eeda; #814 is merged at that SHA.
- Open #810 is at a20e14518ebdb24a5e1790c2486dfad8758c7920; its changed files cover World Play/context, Runbook APIs, and the roadmap, not the two code/test paths.
- Open #811 is at ae1e3aaff746aee8ad630ffa58f7e22d79d3997e; its changed files are its handoff, Alembic setup, and migration logging test.
- No shared runtime, database, provider, or generated output is used by this slice.

## Verification and completion

Run the focused service and trace suites, scoped Ruff, Python compilation, and cumulative diff checks. The owning-boundary regression must assert one successful Plan trace event, a matching trace ID in the returned and logged trace, and absence of a prompt-secret sentinel. PRIME owns independent review and merge coordination; no merge is authorized here.
