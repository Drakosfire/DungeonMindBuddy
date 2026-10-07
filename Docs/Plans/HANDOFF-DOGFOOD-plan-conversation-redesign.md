# DOGFOOD — Rebuild the Plan conversation presentation

Status: ACTIVE implementation slice, authorized by the user and PRIME on 2026-10-07. No merge authority.

Branch: `codex/dogfood-plan-proposal-scope`

Base: `main@dae1a57f4be64ce3809aa1bf8c9a87fd642d51fb`, verified as GitHub’s latest default-branch commit on 2026-10-07
Topology: serial, one adopter PR; no unmerged parent. The earlier bottom-dock predecessor (#1000) is merged. PRIME transferred the WorldPlanAgentConversation/history presentation paths from the parked #979 proposal into the bounded adopter lane. #979 remains open as historical review context; it is not the current write lease.

## Outcome

Replace the Plan conversation’s record-heavy, multi-box reading path with a compact conversation presentation in the existing resizable bottom dock. Keep the saved Plan as the primary workspace. Show the latest user/assistant exchange first; collapse earlier exchanges, local-only proposals, provenance, Graph receipts, traces, and recovery records until opened. Keep the composer visible and usable at the bottom, with one input and automatic Discuss/Propose intent routing.

## Invariants

- Keep `WorldPlanAgentConversation` as the sole controller for durable World history, request identity, context capture, recovery, proposal review/apply, and exact target fences.
- Preserve `isWorldPlanGraphCompletion`, `isWorldPlanGraphExecution`, `isWorldPlanContextProjection`, the strict receipt checks, and their imported types. No source IO, provider reroute, Graph write, schema, or backend change.
- Failed or interrupted turns get short human-readable status in the conversation; precise lifecycle, provenance, target receipt and Graph evidence remain inspectable in turn details.
- Do not automatically repost uncertain requests. Preserve exact saved request bytes, ID, refresh-only confirmation, and existing retry rules.
- Editing language routes to the existing proposal/review/apply flow. Questions route to the existing durable discussion flow. No classifier policy changes to Agent/server APIs.
- Default context control starts at “Plan + World” and resets when the verified World changes. The user asked to remove the per-question Graph checkbox gate. Keep Plan-only available as an explicit scope switch; do not claim the known Graph completion failure is repaired.
- Keep the resizable dock and its single composer. Do not add another chat state/store or move the composer out of the existing dock.
- Citation presentation must not claim source text was opened unless the validated server contract can represent that state. On this base `WorldPlanGraphCitationV1.source_opened` is literally `false`; the UI cannot implement a true branch until SERVER updates the owning type/validator contract.

## Exclusive expected write set

Modify:

- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.css`
- `apps/live-control-ui/src/planSurface/components/PlanConversationDockAdapter.css`
- `apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx`

Create:

- `Docs/Plans/HANDOFF-DOGFOOD-plan-conversation-redesign.md`

No other paths are leased. Do not edit API types, validators, adapters, schema, backend/provider, shared Graph policy, lockfiles, runtime services, or database state in this slice. If a source-read status branch is required, SERVER owns that contract and can consume or narrowly lease its phrase after the type/validator lands.

## Verification and handback

Run the focused World Plan history tests, typecheck/build, and `git diff --check` when dependencies are available. Exercise newest-turn visibility, earlier-history disclosure/paging, failed/uncertain recovery disclosure, unified intent routing, graph context default/switch, and exact no-repost behavior. Review the exact cumulative base-to-head diff, commit, push, open one PR, attach it to the task, and send PRIME the exact head for independent review. No merge or operator runtime action is authorized here.

The local `npm ci --offline` attempt failed because the cache lacks `react@19.1.0` (`ENOTCACHED`). This is an environment limitation, not a passing check; report any verification still unavailable.
