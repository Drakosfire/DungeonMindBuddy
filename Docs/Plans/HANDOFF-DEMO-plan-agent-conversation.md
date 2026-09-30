# DEMO — saved managed-World Plan Agent conversation

**Status:** ACTIVE — bounded Plan adoption authorized by PRIME after Buddy #803 merged

**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`

**Authority:** [STEWARDS-HANDOFF-demo.md](STEWARDS-HANDOFF-demo.md), accepted [universal Agent turn contract](HANDOFF-DEMO-universal-agent-turn-context-v1.md) §3–§4, and PRIME's bounded Plan activation.

**Pinned base:** Buddy #803 merged as `3c9d5f2300d8658b678d25c357760905538dabbd`; fetched `origin/main` at that exact commit before this lane.

**Branch/checkout:** `codex/demo-plan-agent` in `/home/drakosfire/.codex/worktrees/8b2b/DungeonMindBuddy`.

**Topology:** serial. The Index slice is merged. No other DEMO Agent adoption lane is active. Open PRs #781, #798, #760–#761, and #763–#765 were inspected. #764's exact write set is limited to Rules Lawyer / Plan projection catalog files and does not overlap this lease; `planSurface/config/planSurfaceConfig.ts` remains read-only. Recheck paths before opening the implementation PR.

## One capability and failure cases

On a saved Plan owned by the independently verified managed World, a user can
open the existing app Agent chrome and have a multi-turn conversation through
`POST /api/live/agent/turn`. Each turn sends the exact leased Plan surface
instance, World owner, saved Plan document ID, expected document revision, and
`graph_request: {mode:"none"}` with no graph selection. The request contains
no local Markdown, title, path, fake document ID, or browser thread scope. A
saved dirty editor is reported as `saved_dirty`; a clean one is `saved_clean`.

The current `PlanAgentInteractionBar` remains the owner of existing campaign
Plan retrieval/citation and reviewed document-edit proposal behavior. This
slice does not route those flows through the new endpoint and does not alter
that component. The generic turn is available only for a saved managed-World
Plan. The accepted generic response has no typed citations or grounding
envelope and reports `graph_grounded: false`, so this conversation makes no
graph request and displays no retrieval or citation claim. Campaign-target
Plans remain unsupported by this new turn path pending campaign-to-World
authority. A World Plan local draft has no durable work ID or revision and
cannot submit a generic Plan turn; show that the user must save first. Never
put a `local-plan:*` token on the wire. A later unified cited conversation
would require a separate Buddy response-contract proposal.

Pre-dispatch critique: the easiest false success is answering from a selected
World while omitting the exact Plan or using a stale document revision. The
highest identity risk is treating a local draft as a saved Plan or carrying a
late answer across a Plan/World/revision/thread/route change. Fail closed for
foreign, removed, unavailable, malformed, or mismatched saved work and for an
unavailable/rejected graph result. The accepted contract treats
`expected_revision` as a freshness expectation, not a historical content pin:
if the same Plan is still authorized at a newer committed revision, the
backend may answer from that actual revision and reports
`changed_since_expected`, expected revision, and used revision. The UI must
show that distinction with the actual revision and must never imply that the
answer used the older revision. Graph is not requested in this slice, so
graph-unavailable and graph-pin behavior are outside this implementation.

## Exclusive expected write lease

- `Docs/Plans/HANDOFF-DEMO-plan-agent-conversation.md` — this bounded ACTIVE
  authority and exact evidence.
- `Docs/Plans/HANDOFF-DEMO-index-agent-conversation.md` — backward-looking
  #803 merge settlement only.
- `Docs/Roadmaps/ROADMAP-demo.md` — #803 settlement and this slice's bounded
  execution facts.
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx` — expose the
  current saved revision/dirty hint to the World Plan Agent plugin; mount it
  only on the managed-World Plan path.
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
  — new Plan Ask plugin, exact request capture, response validation, transcript,
  thread persistence, and stale-response fencing.
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.css`
  — content placement inside the existing shared Ask portal.
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx` — mounted
  World Plan / Agent chrome / endpoint witness.
- `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts`
  and `agentInteractionHistory.test.ts` — bounded safe Plan turn-result
  summary persistence and reload.
- `apps/live-control-ui/src/api/types.ts` — typed Plan request/response and
  source-free resolved summary.
- `apps/live-control-ui/src/api/liveApi.ts` and `liveApi.test.ts` — typed
  `/api/live/agent/turn` client and transport behavior.

The existing `PlanAgentInteractionBar.tsx` and its tests are read-only. So are
`AgentInteractionProvider.tsx`, `AgentInteractionChrome.tsx`, `AskPluginSlot.tsx`,
`surfaceInteraction/**`, App/root provider composition, all other surface
owners, `planSurface/config/planSurfaceConfig.ts`, backend routes/resolvers,
schemas, providers, dependencies, lockfiles, and root configuration. If the
capability needs any path outside this list, stop and return the exact blocker
to PRIME before editing it. No server, provider, port, database, corpus,
production data, or `.env` is leased.

## Owning-boundary acceptance witness

Mount the real `PlanSurfacePage` World-owned Plan path with the real selected-
World authority, Agent provider, Ask portal, and shared Agent chrome; mock the
typed endpoint and existing Plan snapshot/write APIs. Prove:

1. A loaded saved World Plan opens Ask and submits two turns through the
   accepted endpoint with one stable client thread ID, distinct turn IDs, exact
   `surface_id="plan"`, current leased instance, World ID, saved document ID,
   and expected revision. The graph request is explicitly `none` with no
   selection; the UI makes no retrieval or citation claim.
2. The actual answer and bounded per-turn resolved owner/work/graph/provider
   facts are visible and survive thread reload. No trace, source prose, local
   Markdown or path persists in the new summary.
3. Clean/dirty saved state is reported accurately. A local unsaved draft has
   no enabled generic Ask and causes no endpoint call or fabricated document
   ID. Campaign-target Plan requests are not sent through this new path.
4. Unavailable, foreign, removed, or mismatched work produces a visible error
   without rendering an answer. The no-graph result is validated as
   `not_requested`, and the UI never presents it as grounded. A
   `changed_since_expected` result may render its answer only with a visible
   status naming both expected and actually used revisions.
5. Pending responses are suppressed after World, Plan document, expected
   revision, route, or thread replacement/unmount. Existing campaign Plan
   Ask/citation and reviewed document-edit proposal regressions still pass.

Run the focused World Plan and legacy Plan Agent tests, relevant API/history
tests, UI typecheck, and cumulative base-to-head diff review. Name inherited
failures. Mocked UI tests do not certify a live provider, campaign authority,
the other four surfaces, or full DEMO acceptance.

**Activation:** PRIME explicitly activated this bounded saved managed-World
Plan slice and specified the owning-boundary acceptance witness. Deliver one
PR titled `DEMO: add saved World Plan Agent conversation`; return its exact
base/head, evidence, and remaining gates to PRIME for independent review and
merge control.
