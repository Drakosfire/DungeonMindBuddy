# HANDOFF — SERVER Play World Graph turns

**Status:** ACTIVE implementation lease from PRIME on 2026-10-10. PRIME owns independent review and merge.

**Authority:** Buddy `origin/main@0063aae23149c165dd9cffb94206c8d1c24392da`, after APP-STATE #1064. [PRIME's exact SERVER lease](https://github.com/Drakosfire/DungeonMindBuddy/pull/1061#issuecomment-6096729339) and `HANDOFF-APP-STATE-play-graph-binding-receipt.md` define this consumer contract. Branch `codex/server-play-world-graph-turn`, serial PR against `main`. Held #1014 and active DEMO #1065 have no file overlap with this lease.

## Primary question

Can a GM ask about a verified World-owned Play Run using read-only selected-World Graph context, with the exact Runbook/Beat/Scene, native binding, and Graph revision independently frozen for durable retry and history?

## Bounded implementation

Expected writes: `apps/live_control_server/models/agent_turn.py`, `apps/live_control_server/routes/agent.py`, `apps/live_control_server/services/agent_turn_service.py`, `tests/test_agent_turn_route.py`, `tests/test_agent_conversation_world_retry.py`, and this handoff. PRIME's [narrow extension](https://github.com/Drakosfire/DungeonMindBuddy/pull/1061#issuecomment-6096810581) additionally authorizes `apps/live_control_server/services/managed_world_graph_projection.py` for a private expected-binding guard before native projection. The bounded envelope adapter remains reuse-only. APP-STATE owns the typed `PlayGraphBindingReceiptV1` codec and durable references; SERVER owns current authorization, ordered reads, dispatch, and response projection.

Play Graph requires an exact World Run and a World-only Graph request for the same managed owner. Campaign/session focus, Graph selection, and a caller-supplied revision pin are excluded. Fresh Run admission precedes native Graph reads. Pending retries compare the stored native ID and binding version with the current verified managed binding **before** native projection, then read the stored Graph revision. The projection adapter checks the expected binding again before its native read, closing a rebind between route precheck and projection. Completed retries replay immutable provenance without Run, Runbook, Graph, or provider reads. New turns observe current Run and Graph heads. No Plan-policy reuse, Graph mutation, source admission, binding change, UI, deployment, paid provider, or private corpus work.

## Stop conditions

Stop if a new APP-STATE/Core contract or a path outside this lease is needed; if a missing/changed binding can reach the native Graph or provider on retry; or if historical Runbook/Beat/Scene or Graph cannot be reconstructed from the stored pins.

## Acceptance witness

Run the owning HTTP and durable retry suites with unique disposable PostgreSQL. The synthetic in-memory native Graph fixture must use a native World ID different from the managed ID. Prove invalid Run and missing binding block Graph/provider calls; unavailable Graph blocks provider; a pending same-ID retry retains original Runbook/Beat/Scene and native Graph revision after both heads move; a new turn uses current heads; binding version or native ID changes block native Graph/provider before dispatch, including a rebind between route precheck and projection; completed replay performs no mutable reads; history retains independent pins and altered intent conflicts. Check locked dependencies, scoped Ruff, and cumulative `origin/main..HEAD` diff. Record exact implementation SHA and any inherited failures before PRIME review.

## Implementation and evidence

Implementation base: `0063aae23149c165dd9cffb94206c8d1c24392da`. Exact review head is recorded in the PR handback because the commit containing this note cannot name itself.

- Fresh isolated `uv sync --locked` succeeded with the pinned DungeonMind, WorldKeeper, GenerationEngine, and prepared Hermes sources. The prepared Hermes manifest verified its exact source, patch, and tree identity.
- Owning route, durable retry, service, managed Graph projection, and context assembler suites: **130 passed**, 11 existing Pydantic schema-name warnings. The tests used unique disposable PostgreSQL databases. The synthetic native Graph and managed World had distinct IDs; the provider was a fake runtime.
- The HTTP witness covers stale/foreign Run before native read, missing binding before native read, unavailable Graph before provider, frozen pending retry after Graph head and Run progress move, new-turn current head, completed replay with no mutable reads, altered-intent conflict, history reloaded through a new service instance, native binding version/identity changes before Graph read, and a rebind between precheck and projection.
- The fake runtime receives bounded native Graph context containing the synthetic tavern fact. It returns a simple answer; no provider-produced citation claim is made. The existing Graph context contract explicitly marks Graph as navigation/memory, not corpus citation authority.
- Scoped Ruff and `git diff --check` passed. Cumulative changed paths match PRIME's original lease plus its one authorized managed projection extension. No production runtime, paid provider, or private corpus was used. No inherited failure was observed in the focused suites.

No rollout performed. PRIME owns independent exact-head review and merge.
