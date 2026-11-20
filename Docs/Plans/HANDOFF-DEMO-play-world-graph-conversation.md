# HANDOFF — DEMO selected World Graph in the shared Play conversation

**Status:** ACTIVE bounded UI adoption for PRIME review. **Base:** Buddy `75014e62935fa9745dc5f702271e834077ca9809`, including producer #1066. **Authority:** [PRIME lease comment 6096857221](https://github.com/Drakosfire/DungeonMindBuddy/pull/1066#issuecomment-6096857221). **Lane:** `codex/demo-play-world-graph-conversation`, isolated checkout `/tmp/demo-multiedge-verdict-order`. **Topology:** one independent PR based on merged `main`; PRIME owns review and merge.

## Contract

The shared Play composer submits the selected managed World and exact admitted Run revision with a World Graph request: `mode=world`, matching managed `world_id`, null campaign and revision pin, no narrative focus, and no Graph selection. The server resolves the authoritative managed to native binding and graph revision. Play accepts a Graph receipt for that native World and revision while retaining the selected managed World as the conversation owner. Graph unavailability remains a visible failure with the saved exact request available for recovery; it does not trigger a graphless resend. A pending turn stores and retries the original request bytes, including its Graph request. Older graphless Play requests already in browser recovery storage remain readable and retry exactly as saved. Plan requests and the shared history, dock, and proposal controller retain their accepted behavior.

## Exact write lease

- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx`
- `apps/live-control-ui/src/api/liveApi.worldConversation.test.ts`
- This handoff

APP-STATE owns the separate conversation codec paths. This slice does not change the producer, backend, router, CSS, settings, source data, runtime, provider, or selected World integration gate. The mounted UI and API tests prove only this consumer and transport. DOGFOOD will check the user-facing outcome after PRIME review; operator rollout still requires the full selected World integration gate.

## Verification and handback

The owning mounted and API tests must show the exact selected World/Run request, frozen same-ID retry after navigation and reload, no cross-World pending reuse, acceptance of a native World Graph receipt distinct from the managed owner, visible Graph failure without silent downgrade, and compatibility with saved legacy graphless Play recovery. Keep the Plan path covered by the existing shared conversation fixture. Record actual focused results, cumulative diff, and PR head before handing back to PRIME.

**Focused verification, 2026-10-10:** `npm --prefix apps/live-control-ui run test -- src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx src/api/liveApi.worldConversation.test.ts --configLoader runner` passed 27/27 across the two leased suites. After the final Play response identity guard, its mounted suite passed 18/18 again; the API transport suite had passed 9/9 and was unchanged. The mounted cases prove selected managed World/Run request shape, exact saved Graph request on same-ID retry after remount, replayed native World receipt with managed owner, Graph failure without a graphless repost, foreign World isolation, legacy saved graphless retry, and existing Plan/dock/history behavior. App and Node TypeScript projects passed with their build metadata directed to `/tmp`; `git diff --check` was clean. The existing dependency tree was reused with an identical lockfile, and Vite's runner config loader avoided writing into that read-only dependency tree. These are mocked UI and transport witnesses; no live service, provider, private corpus, or operator acceptance was exercised.
