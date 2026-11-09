# REFERENCE: direct retry from lightweight Plan history

Status: SETTLED predecessor. PR2292 merged at
`d39db0c6a2a0493800f82eb77d69e3ef3deb3d4e`; delivered UI
`e994d7b1a31f65e2cbc4cb9132ce66a2cd4fd5b0`. Independent source, composition
and procedure reviews plus all seven CI gates passed. Controlled read-only
verification confirmed direct retry visibility without Details, native citation
opening and unchanged Plan/reload; no user request was retried. APP/Core/session
conservation passed; API/schema stayed unchanged. This does not close held Play
or the broader References goal. Original slice base:
`7abfaccaccf63737a31a52e33c79a0df75e1b873`; branch
`codex/reference-plan-light-retry`, existing buddy-context-loop checkout.
Topology: serial, no unmerged parent. Coordination remains off.

## Outcome and ownership

A failed/interrupted Plan message on the current Plan can be retried directly
without opening Details or eagerly loading execution history. The existing exact
single-turn reader verifies the original before submission. Preserve its source
references and explicit operation, newer composer input, and all host checks.
Late reads after World/document/conversation or editor-basis changes must not send.
An unavailable, mismatched or reviewed-step-only original stays visible and fails
with actionable feedback. Never infer publication/write authority from light data.

## Write lease

- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx`
- `apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx`
- this handoff

No API/schema/provider/model/CI changes. Play2172 and server2104 remain held;
active CI2288 paths are disjoint. Preserve running API16cb2c50/schema142,
UI724ed4d58d7d and all retained state until separate reviewed delivery.

## Verification and delivery

Reproduce missing direct retry on the served lightweight path; test exact read
only on click, original references/operation, delayed scope changes, failed reads
and newer drafts. Run focused mounted owners, TypeScript and build. Inspect the
cumulative diff, obtain independent Bugbot review and source checks, then merge
and perform protected UI-only delivery under standing PRIME authority. Retain
original failed verification. Broader goal and held Play integration stay open.
