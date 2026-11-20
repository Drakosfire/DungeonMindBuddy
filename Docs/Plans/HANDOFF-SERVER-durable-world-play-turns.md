# HANDOFF — SERVER durable World Play turns

**Status:** ACTIVE implementation lease from PRIME on 2026-10-10. Merge and rollout remain PRIME decisions.

**Authority:** Buddy `main@a7d89a0986e2727388ead4d60928f37beecc5876`, including APP-STATE #1059's Play Run V1 reference codec and #1060's Core `b789ddc207a0a5a820a11f85e18d203d355d8f53` pin. [PRIME's exact lease](https://github.com/Drakosfire/DungeonMindBuddy/pull/927#issuecomment-6094490524) owns this scope. Branch: `codex/server-durable-world-play-turns`; base is `main`, independent of held SERVER #1014 and queued DEMO #927.

## Primary question

Can the durable World Agent turn route admit a question about the exact current World-owned Play Run, preserve its accepted Runbook/Beat/Scene during a pending retry after progress changes, and return a completed retry without reading mutable Play state or redispatching the provider?

## Bounded lease

Expected paths: `apps/live_control_server/models/agent_turn.py`, `apps/live_control_server/routes/agent.py`, `apps/live_control_server/services/agent_turn_service.py`, `apps/live_control_server/services/agent_play_surface_context.py` for a narrow shared snapshot adapter, `tests/test_agent_turn_route.py`, `tests/test_agent_conversation_world_retry.py`, `tests/test_agent_play_surface_context.py`, and this handoff. Reuse the existing World Play admission resolver and APP-STATE V1 reference codec. The API owns request validation, World/Run authorization, historical Runbook reconstruction, and response/history projection. APP-STATE owns immutable storage and codec validation.

Keep Graph off for Play Run turns. Preserve Plan Ask/edit/Graph behavior. No new persistence, producer/schema/codec changes, UI, #1014 files, production runtime, corpus, or paid provider execution.

## Stop conditions

Stop and return to PRIME if the V1 tuple cannot prove the original Beat/Scene and exact Runbook without reading current Run progress; if a new durable contract or path outside this lease is required; or if a provider can dispatch before stale/foreign context rejection.

## Acceptance witness

Focused route/service tests with unique disposable APP-STATE PostgreSQL prove fresh Play Run admission; stale/foreign rejection before provider dispatch; pending retry from the original Runbook/Beat/Scene after current Run progress moves; rejection when a stored Scene belongs to a different Beat; completed exact replay with zero Run/Runbook/provider calls; altered-intent conflict; and mixed Plan/Play World history retaining each turn's original provenance. Run relevant focused tests, lint, locked dependency check, and inspect the cumulative base-to-head diff. Record exact head and deviations below before review.

## Implementation and evidence

Implementation commit: `b86a65606fc9b39293f94382a6547fb53ce463f4`. Exact base: `a7d89a0986e2727388ead4d60928f37beecc5876`.

- Prepared the exact pinned Hermes source and ran `uv sync --locked` in this isolated worktree. The resulting environment installed Core `b789ddc207a0a5a820a11f85e18d203d355d8f53`; no shared environment was used as dependency proof.
- Focused Play resolver, route, and World retry gate: **38 passed** with unique disposable PostgreSQL databases on port 54329. The owning HTTP tests cover fresh Play admission, stale/foreign rejection before runtime, a pending retry from the frozen Beat/Scene after mutable Run progress changes, cross-Beat Scene rejection before dispatch, completed replay with no Run/Runbook/provider reads, altered-intent conflict, and mixed Plan/Play history.
- Scoped Ruff check passed. `git diff --check` passed.
- Full `tests/test_agent_turn_route.py`: **48 passed, 1 failed**. The sole failing Graph policy assertion (`test_policy_resolver_reads_real_pinned_native_graph_with_distinct_managed_id`, expected `AgentTurnServiceError` not raised) was reproduced unchanged in a clean worktree at exact base `a7d89a09` with its own locked environment and disposable database. It is outside this Play slice; no Graph policy behavior was changed.

The only departure from the initial expected path list is that the accepted tests live entirely in `tests/test_agent_turn_route.py`; no APP-STATE or schema files changed. Acceptance is limited to the API/durable-history boundary. No runtime rollout or provider call occurred.
