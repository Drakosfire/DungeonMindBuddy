# HANDOFF — APP-STATE: safe completion rejection classifications

**Status:** ACTIVE — PRIME authorized one bounded internal classification slice on 2026-10-07 after the Source A+B deployment surfaced a Graph completion validation failure.
**Base and lane:** `main@5411faceb5a96bca61dbd02c9c68907b3914e67b`; branch `codex/appstate-completion-rejection-classification` in the managed worktree `appstate-safe-completion-rejections`. One serial implementation PR to `main`; PRIME owns independent review and merge.
**Primary question:** Can APP-STATE preserve the current Graph-completion predicates and `ValueError` compatibility while exposing a closed, safe internal code for the exact fixed invariant that rejected completion?
**Write lease:** `src/application_state/agent_conversation/types.py`; `tests/application_state/test_agent_conversation_postgres.py` (pure validator tests only; no database fixture); this handoff. No migration, schema, public response, SERVER mapper, parser, provider, runtime, or live-state changes.

## Contract and limits

Add an internal closed set of rejection codes at the existing completion validators in `types.py`. Every rejection must remain a `ValueError` (a subclass is acceptable), retain its fixed existing message and predicate, and expose only a fixed invariant category. Codes must never contain completion/user/provider text, IDs, or exception details. The new code is for a later SERVER-owned safe diagnostic mapper; this slice does not change any API or public response.

Do not alter status/evidence semantics, citation membership, receipt binding, producing-attempt requirements, or event-to-claim support. No raw provider answer is retained or added to telemetry. No runtime/provider call is authorized.

## Re-anchor and coordination

Created the isolated worktree from `5c606458a5fd5b4a09bf140add3756e00a692ecf`, then fetched current `origin/main` at `5411faceb5a96bca61dbd02c9c68907b3914e67b` before PR preparation. The intervening merge is UI-only and does not touch the leased paths. Open PR #979 is UI-only; merged #983 is docs-only. Open PR #939 concerns Plan Ask history projection; it also edits `types.py` but not these validator functions. This lease is limited to the validator region, the focused tests in the existing PostgreSQL test module, and this handoff; the PR #939 branch is not modified or stacked.

## Acceptance evidence

The focused test `tests/application_state/test_agent_conversation_postgres.py::test_completion_validation_codes_are_closed_safe_and_valueerror_compatible` covers successful controls, representative fixed rejection categories, unchanged fixed messages, `ValueError` compatibility, and absence of IDs from codes across both completion validators. It passes when isolated from the repository-root autouse PostgreSQL fixture. Changed-file Ruff and `git diff --check` pass. The ordinary pytest invocation stops during root fixture setup because PostgreSQL is unavailable at `127.0.0.1:54329`; no test body runs in that invocation. `ruff format --check` reports existing formatting drift in both touched files; unrelated formatting was not rewritten. No live ask, provider, or database mutation was run.

The reported production failure is only coarsely captured in `/tmp/prime-reservation-turn-proof.json`; it does not include included-ID sets or the claim/event binding map, so this handoff does not claim a specific failed predicate or repair. SERVER owns the separate binder diagnosis and mapper.
