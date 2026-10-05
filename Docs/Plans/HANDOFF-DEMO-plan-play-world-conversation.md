# HANDOFF — DEMO: Plan↔Play World conversation

**Status:** BLOCKED — QUEUED successor design. PRIME directed DEMO to pin this bounded design on 2026-10-05. This handoff grants no implementation write lease, runtime access, provider run, or merge authority.

**Owner:** DEMO. SERVER owns route admission and canonical Play context; APP-STATE owns durable execution/history persistence; PRIME owns cross-owner sequencing, path arbitration, review and merge; the operator retains final journey acceptance.

**Design base:** Buddy main at `6319ff30466dd9ab2e3e0752fce31ac8a71b7d4b`, rechecked from the remote default-branch ref on 2026-10-05.

**Topology:** Serial successor to DEMO #925. Do not dispatch implementation until the gates below are satisfied and PRIME pins a fresh path/runtime lease. No implementation branch is active.

## Purpose

Prove the smallest production Plan↔Play witness for the operator’s preparation-to-run journey: the same World conversation and durable history remain available while moving between Plan and Play; each new turn records the surface and exact work context that existed when it was sent; a late answer retains that original attribution; and switching surfaces or reopening history never sends a turn again.

Reuse the accepted World conversation/history and the existing Agent Interaction Chrome/portal. Do not add another conversation store, state engine, or Graph-truth store. Index’s browser-local conversation remains separate and is not imported into World history.

## Surface contract

- **Plan:** preserve the existing saved-Plan Graph Ask behavior from #925, including its exact committed Plan and card pins, receipt, citations, and response/history provenance. This successor does not change #925 or broaden Graph policy.
- **Play:** a new turn is eligible only when Play has admitted a verified World-owned Run. SERVER must resolve and authorize the selected World, exact Run, exact pinned Runbook work revision and content SHA, current Beat, and optional Scene. Campaign equality and browser-local pointers are not authority. Play requests carry no Graph request.
- **Conversation identity:** Plan and Play read and append to the same accepted World conversation/history. Each turn persists its request-time surface and work attribution. A surface switch does not retag an in-flight answer, start a new thread, or redispatch a prior turn.
- **Failure behavior:** fail closed before provider dispatch for an unverified or changed World, missing/foreign Run, stale or unresolved Runbook pin, unavailable current Beat/Scene context, or any request whose provenance cannot be established. Never expose another World, Run, Plan, or conversation’s history. Exact replay returns accepted history without a second provider dispatch.

## Gates before implementation

1. DEMO #925 must settle, releasing its exclusive ownership of the Plan conversation/API files and `Docs/Roadmaps/ROADMAP-demo.md`. Its current open head is `29a1e326d0259f3dfd3cc29aac0fc6fd8f677c35`; the code was accepted at `504357580a9c785921cc31ec380262169bbe3280`, while producer publication/merge and integrated acceptance remain pending.
2. SERVER #926 and APP-STATE producer work must be independently accepted and published/merged. As of this design pin, SERVER #926 is still a draft and uses fake execution persistence; APP-STATE publication approval remains pending.
3. SERVER must publish an accepted typed admission/provenance contract for `surface=play` with `primary_work=run`. It must define the canonical World-owned Run and pinned Runbook context above, and the fail-closed and replay behavior. #926’s `auto_plan_world` Graph policy is Plan-only and does not satisfy this gate. If the contract needs a SERVER successor, SERVER/PRIME own that sequencing; this handoff does not authorize another owner’s implementation.
4. After those gates, PRIME must re-anchor, inspect open PRs and leases, and issue a fresh exclusive DEMO allowlist plus runtime/test-lane definition. Recheck collisions with #914 and DOGFOOD #917 then. #914’s native Runbook projection paths are outside this proposed write set; #917 remains prototype evidence, not production authority.
5. Keep the Graph-grounded Plan Ask work first in sequence. This queued successor must not delay, expand, or edit #925.

## Candidate DEMO implementation write set

This is a proposed future allowlist, not an active lease. Implementation would use one isolated branch based on the refreshed remote main and one serial PR. No directory-wide lease.

- `apps/live-control-ui/src/App.tsx`
- `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx`
- `apps/live-control-ui/src/agentInteraction/agentInteractionTypes.ts`
- `apps/live-control-ui/src/agentInteraction/WorldAgentConversation.tsx` (new shared surface host)
- `apps/live-control-ui/src/agentInteraction/WorldAgentConversation.css` (new shared surface host styling)
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.css`
- `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx`
- `apps/live-control-ui/src/playSurface/playSurfaceAgentContext.ts`
- `apps/live-control-ui/src/api/liveApi.ts`
- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx`
- `apps/live-control-ui/src/playSurface/PlaySurfacePage.test.tsx`
- `apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx` (new mounted App/portal witness)
- `Docs/Roadmaps/ROADMAP-demo.md` for a truthful predecessor/status settlement after #925 releases the path; never pre-mark this successor complete.

Any need for another path or owner boundary returns to PRIME before edits. Do not edit SERVER or APP-STATE files in this DEMO lane.

## Acceptance boundary

The owning UI witness mounts the actual App-level Agent Interaction Chrome and proves Plan→Play→Plan continuity for one managed World, with the exact Run/Runbook/Beat context on the Play turn, preserved Plan pins on the Plan Graph turn, request-time attribution for a deferred response, and no dispatch on switching, reload, or exact replay. It must reject foreign, stale, or unresolved Run context before dispatch.

The owning SERVER/APP-STATE evidence must prove the accepted durable history projection preserves both turns’ original surface/work provenance and that replay does not execute again. UI fixtures alone are not proof of persistence or route admission. No live Graph/provider run is part of this handoff. This slice does not claim operator acceptance or completion of the full DEMO mission; the full connected rehearsal remains gated on the remaining roadmap and the operator.

## Collision and history notes

- DEMO #925 currently owns the Plan conversation component, its history test, API types/liveApi, its handoff, and the roadmap path. This design PR adds only this new handoff file and does not amend those paths.
- DEMO #914 is open with a visual hold and owns semantic Plan-card projection plus native Runbook projection paths. The candidate write set deliberately excludes those projection files.
- DOGFOOD #917 is prototype evidence with overlapping Plan/API/Agent concepts, not a production reservation. Recheck its state before any future activation.
- The current checkout contains unrelated user changes. They are preserved and are not part of this design PR.

**Current disposition:** queued, no implementation lease.