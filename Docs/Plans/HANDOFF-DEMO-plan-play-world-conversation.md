# HANDOFF — DEMO: shared Plan↔Play World conversation

**Status:** ACTIVE UI implementation in existing Buddy PR [#927](https://github.com/Drakosfire/DungeonMindBuddy/pull/927); repaired after PRIME review hold [comment 6095146329](https://github.com/Drakosfire/DungeonMindBuddy/pull/927#issuecomment-6095146329). DOGFOOD design re-review and PRIME independent review/merge remain pending. This is a bounded consumer slice, not connected J1–J6 or operator acceptance.

**Owner:** DEMO. SERVER owns Play Run admission and request-time canonical context; APP-STATE owns durable World history and replay; PRIME owns lease, independent review and merge; DOGFOOD owns design quality control before release.

**Base and authority:** Buddy main `dfdb671e1bcd3f8acfb9a44f64e379e928cd6ec9`, including #1059/#1060/#1061/#1062. PRIME activated this successor in [#927 comment 6094751772](https://github.com/Drakosfire/DungeonMindBuddy/pull/927#issuecomment-6094751772), and transferred the overlapping Plan UI reservation from frozen #1014 in [#1014 comment 6094751067](https://github.com/Drakosfire/DungeonMindBuddy/pull/1014#issuecomment-6094751067). Branch: `codex/demo-plan-play-world-conversation`. Original design head `76889a0a85208cf6166c930fffc5a6ca1c5ffae0` is preserved locally as `codex/demo-plan-play-world-conversation-design`.

## Outcome and contract

One World-scoped app shell carries the visible conversation, surface/work-scoped unsent drafts and pending-turn state across Plan→Play→Plan. Both surfaces project the same server-owned World conversation and history through the compact dock, one transcript renderer and one composer primitive. Navigation, reopening and history refresh only read; they never repost a turn. A late result is rendered with the surface and exact work provenance frozen when that turn was sent. Changing the verified World remounts and clears the prior World UI state.

Plan retains its existing committed Plan/card pins, Graph Ask policy, answer receipts, citations, local proposal review/apply and editor controls. Its page adapts the shared World state to the established Plan conversation dock. Play presents the same compact dock and displays local Plan proposals read-only; the original frozen review remains actionable after returning to the same live Plan. Play publishes only an admitted World-owned Run from its native Runbook admission. A new Play request sends the verified World ID, exact Run ID and current Run revision with `surface=play`, `primary_work.kind=run`, `graph_request.mode=none`, and `graph_selection=null`. SERVER #1061 derives the pinned Runbook WorkRevision/content SHA and current Beat/optional Scene from the exact Run snapshot and rejects missing, foreign or stale context before provider dispatch. Browser query parameters or pointers are never admission authority.

The app-level World shell is a volatile UI projection and does not add a conversation store or Graph-truth store. Index's browser-local conversation remains separate. No provider, runtime, backend, Run/backup, or production corpus file belongs to this DEMO lease.

## Exact write lease

Only these paths may change in this PR:

- `apps/live-control-ui/src/App.tsx`
- `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx`
- `apps/live-control-ui/src/agentInteraction/agentInteractionTypes.ts`
- `apps/live-control-ui/src/agentInteraction/WorldAgentConversation.tsx`
- `apps/live-control-ui/src/agentInteraction/WorldAgentConversation.css`
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.css`
- `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx`
- `apps/live-control-ui/src/playSurface/playSurfaceAgentContext.ts`
- `apps/live-control-ui/src/api/liveApi.ts`
- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx`
- `apps/live-control-ui/src/playSurface/PlaySurfacePage.test.tsx`
- `apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx`
- this handoff and `Docs/Roadmaps/ROADMAP-demo.md`

A required edit elsewhere returns to PRIME for an exact amendment before that edit. No runtime, SERVER, APP-STATE, Run or backup path is included.

## Frozen #1014 disposition

The frozen #1014 Plan UI source was compared against this main before the shared adoption. Current main already includes its relevant semantic improvements: card/scene labels and stale selection handling in `PlanSurfacePage.tsx`, Plan composer intent classification, editor-selection precedence, Plan proposal target preview, Graph Ask recovery and conversation scroll behavior in `WorldPlanAgentConversation.tsx`. This PR preserves those accepted behaviors through the Plan adapter; it does not wholesale port older #1014 bytes or touch that PR's Run/backup/runtime scope. The existing Plan history suite remains the owning regression for those controls.

## Review evidence and remaining gate

The owning UI check is a mounted Agent Interaction Chrome/portal transition across Plan→Play→Plan with one World state, exact admitted Run request, deferred response with original provenance, no dispatch on navigation/reopen/replay, and World replacement isolation. Existing Plan history and Play page suites verify their established adapters. Backend #1061 producer tests own fail-closed admission and durable replay; UI fixtures cannot prove those server guarantees. DOGFOOD must inspect the final exact head for the accepted card workspace and one-composer design before release. PRIME must independently review the exact head and merge it; DEMO stops after reporting the PR result.

**UI verification (2026-10-10):** the mounted shared-host integration, Plan World history, Plan page and Play page suites pass 266/266; the scoped TypeScript build passes. The mounted witness includes a delayed Plan answer visible in Play, a delayed Play answer visible in Plan, current Run revision on a new Play turn, no redispatch on route switch/chat reopen/remount, an unadmitted Run, World replacement isolation, and same-World Plan document draft clearing. After the display-label refinement, the focused integration and Play suites passed 21/21, and the final integration assertion passed 5/5; TypeScript remained clean.

**Review-hold repair (2026-10-10):** Play now uses the Plan dock's compact transcript/composer/management styles and latest/earlier navigation. Its visible header carries World, Beat and Scene labels; raw Run identity stays in Advanced. Unsent drafts are keyed to Plan document or Play Run, so a Plan rewrite draft cannot silently become a Play question. A mounted active proposal remains read-only in Play and restores its review/apply control on return to the same Plan; the live Plan binding still gates Apply. New Conversation uses the saved World command path from Play as well as Plan. A pending World turn polls across either view after an uncertain Play POST; terminal history clears only that request's obsolete warning and unlocks the composer without reposting. The expanded focused suite passed 271/271 before the final visible-header label adjustment; the final integration rerun and scoped TypeScript check are recorded with the exact pushed head in PR #927.

**App mounting baseline comparison (2026-10-10):** the exact `src/App.test.tsx` module was run once at this PR head and once at untouched pinned base `dfdb671e` with the same Vitest JSON reporter command and the same dependency installation. Both runs reported 32 tests: 10 passed, 22 failed. All 22 failed test names and leading failure messages match. They group into one Plan title assertion, one ingest heading assertion, two Build shell assertions, and 18 Play Run/status assertions; no introduced failure was observed in this module. This establishes an inherited failure set for this comparison, not a passing broad App suite or a live provider/connected operator witness. The JSON reports are retained locally at `/tmp/demo-app-head-20261010.json` and `/tmp/demo-app-base-20261010.json` for the handback.
