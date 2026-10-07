# DOGFOOD — Adopt the bottom conversation in World Plan

Status: ACTIVE, implementation submitted for independent review; no merge authority.

Branch: `codex/dogfood-plan-bottom-dock`. Base: merged `de22fdefd5b3d8265f85c6b1109f5edd67db660f`. Topology: serial; no unmerged parent inherited. PRIME explicitly activated this bounded frontend design and exclusive write lease on 2026-10-07. #970 merged with controlled focus acceptance and released Page/test ownership; parked #979 conversation paths were explicitly transferred. No further operator or architecture design gate applies.

The unpublished terminal recovery repair `2bdfb4050ab1bc235c6022741d43a5d99cfac1db` is excluded. This implementation neither copies nor inherits it and preserves merged-main request/recovery semantics, including current stale warnings. Source acceptance and runtime adoption remain separate.

## Outcome and invariant

World Plan has one readable document/card workspace above one resizable bottom conversation. The existing WorldPlanAgentConversation remains the sole controller of messages, typed drafts, intent, captured context, pending requests/recovery and proposed edits. No second history or Ask store, provider reroute, new intent classifier, Graph policy change or context-scope policy. The real document must remain mounted and usable when Ask is unavailable.

## Pinned frontend composition contract

1. A Plan-only PlanConversationDockAdapter consumes merged ConversationDock and owns only stable DOM presentation hosts and layout. Its reader is the actual existing Plan main/editor/card tree. It binds expansion to existing useAgentInteraction paneState/setPaneOpen, not another persistent chat-open state.
2. ConversationDock gains optional controlled expanded state, preserving current uncontrolled initialExpanded behavior for existing consumers. This is the minimal adopter dependency, not a new primitive or provider contract.
3. WorldPlanAgentConversation gains optional Plan presentation hosts for header actions, context, messages and composer. It portals existing rendered regions into those stable hosts; all controller state and existing actions remain in the same mounted component. Without hosts, existing legacy portal behavior stays available. Hosts survive collapse/expand and Document/Cards switches. Their absence must not unmount the reader or cause an automatic request.
4. AskPluginSlot gains a bounded layout-owner discriminator: chrome or plan-workspace. It does not hold chat payloads or commands. While plan-workspace owns presentation, AgentInteractionChrome preserves the existing dragon launcher and pane state but does not mount a duplicate Plan Ask overlay, resize rail or root-width reservation. Cleanup restores legacy ownership when leaving the adopted Plan.
5. AppChrome gains an opt-in bounded workspace mode requested only by this World Plan adopter. Inspection correction: current AppChrome center/Peek workspace wrapper is mounted for Ingest, not automatically for Plan. The adopter therefore needs an explicit Plan height-owning center below existing navigation; it must not assume that wrapper already exists. Do not add a competing Graph inspector or reroute #970's inspection controller in this slice.
6. styles.css changes are limited to the opted-in Plan workspace's height/scroll composition and suppressing obsolete agent-width reservation for that owner. Existing edit-toolbox and legacy other-surface behavior stay supported. No guessed fixed navigation offsets.
7. Normal composer presentation is one controlled text box and Send with a compact existing intent control. Initial open conversation height is220px; users may deliberately resize. Settings/New Conversation remain existing controller actions under a closed More disclosure. Graph policy, exact IDs and target metadata are inspectable context. Settings/recovery/proposal review use the existing scrollable message region when opened, not another floating panel. Defaults and request/retry rules are unchanged. Current card focus still includes the saved Plan; do not label it scene-only context.

## Exact expected write set for activation

Modify only:

- apps/live-control-ui/src/ui/ConversationDock.tsx
- apps/live-control-ui/src/ui/ConversationDock.test.tsx
- apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx
- apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.css
- apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx
- apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx
- apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx
- apps/live-control-ui/src/agentInteraction/AskPluginSlot.tsx
- apps/live-control-ui/src/agentInteraction/AgentInteractionChrome.tsx
- apps/live-control-ui/src/agentInteraction/AgentInteractionChrome.test.tsx
- apps/live-control-ui/src/chrome/AppChrome.tsx
- apps/live-control-ui/src/chrome/AppChrome.test.tsx
- apps/live-control-ui/src/chrome/AppChrome.surfaceInteraction.test.tsx
- apps/live-control-ui/src/styles.css

Create only:

- apps/live-control-ui/src/planSurface/components/PlanConversationDockAdapter.tsx
- apps/live-control-ui/src/planSurface/components/PlanConversationDockAdapter.css
- apps/live-control-ui/src/planSurface/components/PlanConversationDockAdapter.test.tsx
- Docs/Plans/HANDOFF-DOGFOOD-plan-bottom-dock.md (activated copy of this contract)
- Docs/Plans/evidence/dogfood-plan-bottom-dock/ (owned screenshots and validation evidence)

No planSurface.css blanket rewrite, card parser/model, SceneLensReader adoption, selected-World registry, public API/types/schema, backend/provider/database, dependency or lockfile edits. If another path is required, amend the contract with PRIME before editing.

## Ownership and runtime boundaries

- #970's merged source and mounted focus acceptance settled its Page/test lease. No unreviewed inspector parent is inherited.
- PRIME explicitly transferred the parked #979 conversation/history paths and granted the named shared chrome paths for this single adopter. No parallel writer is authorized here.
- The unpublished terminal-recovery work remains excluded as recorded above; its export approval is separate and does not block this layout slice.
- #939 attribution semantics remain unchanged.
- Runtime 5202/8000/7860 belongs to PRIME/SERVER. This adopter uses owning mocks and an isolated 5203 fixture only. No operator restart, provider call or production mutation.

## Required proof before handback

Use mounted PlanPage→adapter→existing controller tests, not only slot fixtures. Prove controlled expansion and one composer/launcher ownership; reader/editor/selection/typed draft/message scroll retained across collapse and view changes; late answers stay on captured target/revision; existing failed/uncertain/running outcomes and no-repost recovery stay truthful; proposal review/Apply/ordinary Save guards stay unchanged. Ask-unavailable states must leave the document usable and explain blocked sending.

Capture desktop and390px: navigation does not shift/overlap; input and Send reachable; message/reader scroll independent; pointer/keyboard resizing bounded; context, settings, long recovery and proposal previews do not strand the composer. Preserve native Enter/ShiftEnter/IME behavior. Verify legacy fallback and other route chrome through existing tests. Run full typecheck/build now that #991's shared gate is merged. Inspect exact cumulative base→head diff; commit/push/open one adopter PR and send exact head to PRIME for independent review. Merge and operator acceptance remain separate.

## Predecessor settlement

Verified #986 merge6aa5d19c3fd03b0cdd489c65740022b3ebfb69da (reviewedb79c162); #989 merged897128641143c25d6390483a8b619bc8d833bd1 (reviewed75c3c09); #990 merge12e96a572d1f43ca1fb6772c61eea5f73e26c4e1 (reviewed4bffbc15); #988 merge7449c7d075da1a4bfbafc14f17b5c1f0fdf149c4 (reviewede70d6ead); #991 shared typing/build gate merge7ebac37117d51265910d221d253e6f7fe08e79b0. These accept bounded source capabilities, not production prototype parity. Record future settlement in this consuming handoff, not a status-only PR.

DOGFOOD independently verified npm run build on detached, clean mainc49bde2 in its isolated checkout: exit0, TypeScript and Vite build complete. Raw evidence is saved task-locally at surface-design-kit/evidence/main-c49bde2-build.txt. Vite retains the oversized-chunk warning (main JS2,167.30kB / gzip586.96kB); this is a build result, not measured runtime responsiveness. No product server, API, model or database operation was part of that check.

Additional predecessor settlement: #995 themed-inline contrast repair verified MERGED1cf33abe2e0acdcfad45529d2c5943e74b6cbe33 from independently reviewedf0c93b2e. Its exclusive prepMarkdownThemes.css slice lease is released by PRIME. The old J2/BUILD stylesheet authority was explicitly transferred for that repair; their stale ACTIVE per-path references are not competing permission for this file, and broader programs were not marked complete. This adopter does not lease or rewrite prepMarkdownThemes.css. Preserve the accepted ink/role-tint behavior and use a fresh post-gate base including it. Runtime diagnostic0f5c96d5 does not yet prove production adoption of the contrast change.

Activation record: PRIME settled/released #970 Page/test lease and explicitly transferred parked #979 WorldPlanAgentConversation/history paths. Terminal repair is frozen at2bdfb4050ab1bc235c6022741d43a5d99cfac1db with no active writer. Its unapproved GitHub export does not block independent layout. This implementation starts from MERGED main only; never copy/inherit/recreate/export that unpublished repair. Preserve existing merged-main recovery/state/request semantics exactly, including the unresolved stale-warning limitation. No semantic recovery fix in this slice. No production/model operation; isolated fixtures only. DOGFOOD owns final post-integration usability scrutiny. These named transfers satisfy dispatch without another design/prototype/operator gate.

## Verification and remaining limits

See `evidence/dogfood-plan-bottom-dock/README.md`. The isolated 5203 preview intercepts every request, never forwards provider or backend work, and uses synthetic identities. No operator database or 5202/8000 runtime changes are owned by this lane. Current Cards remain the existing presentation; this slice does not adopt SceneLensReader, unify intent, change Graph defaults, compose smaller context, or fix terminal recovery.
