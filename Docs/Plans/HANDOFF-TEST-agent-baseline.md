# Agent service regression baseline

Status: ACTIVE. PRIME owns this serial slice under the operator's 2026-10-19 Execute instruction. Base: 2eb3156a0f3d97c1d50011ffe7ecf47661ca3a6c. Reuse buddy-context-loop checkout; no new worktree/environment. Open PR inventory checked: no active competing Agent service test repair; historical ACTIVE handoffs do not grant concurrent writes.

## Invariant and scope

Restore a trustworthy complete tests/test_agent_turn_service.py baseline: reproduce inherited failures, distinguish stale fixtures from product defects, retain meaningful boundary assertions. No skips, weaker validation, production contract changes or unrelated suite cleanup. A valid fixture must satisfy the current frozen policy, native graph revision and evidence authority; synthetic provider tests must not call real providers or mutate retained campaign state.

## Exclusive expected paths

This handoff, tests/test_agent_turn_service.py, Docs/Roadmaps/ROADMAP-demo.md. Inspect owning service read-only; if a genuine product defect needs a production path, amend this steward-owned lease with its concrete failure and owning-boundary verification before editing. Single PR, independent Architecture exact-head review before PRIME merge. No port/service/database/data writes; test-owned isolated fixtures only. No provider requests. A test-only change needs no 5202 restart.

## Verification and completion

Run full owning file on current base and repaired head, preserve failures and stack traces in established private evidence location, examine cumulative diff and relevant adjacent tests. Repeat owning file to check stability. Commit, push, PR, independent review, merge, re-anchor and settle this lease. Roadmap may record the specific green baseline; broader J1–J6 acceptance remains open.

## Reproduced causes and verification

Base run: 157 passed, seven failed. All seven are stale test setup, not product defects:

- Two reconciled-turn cases lacked four currently required APP adapter methods. Each is still bound to no_dispatch, preserving the no-mutation/no-provider invariant and allowing the runtime inspection to execute.
- The 96,000-character recap quota case expected an unpaged top-level content field. It now checks the exact content record in the parent page, complete exposure and no continuation; all eight-read totals, ninth-call rejection and no-extra-IO assertions remain.
- Four lifecycle variants injected fabricated raw results without parent presentation registration. They now supply relationship/source records consistent with the event and register exact bytes through the real presenter. Unregistered whitespace-altered bytes still fail before authorization. Repeated registered bytes succeed with one event binding. The previously unreachable finite-policy exhaustion scenario now explicitly selects four attempts/eight operations; default uncapped-budget assertions remain unchanged.

Focused seven cases pass. Complete owning file: 164 passed, one existing CitationFreshnessResponse schema-shadowing warning. Repeat of the full owning file plus graph tool presentation, transport, evidence bundle and Agent graph policy suites: 245 passed, same one warning. Review and merge remain pending. Evidence logs retained in the existing private jev-evidence-loop-20261016 directory under agent-baseline-*; no story payload or provider requests used. Ruff reports four pre-existing findings (three E702 and one F401) on both base and head, unchanged apart from line shifts; no new lint findings. git diff --check passed. No runtime restart is necessary for test/document-only changes.
