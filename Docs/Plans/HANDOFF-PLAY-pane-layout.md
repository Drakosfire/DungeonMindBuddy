# PLAY — chat layout and movable scene notes

Status: ACTIVE. Base origin/main56583e82a8a16bd0fc94a445d95487f3a2707004; branch codex/play-pane-narrow-fit in existing buddy-context-loop checkout. PRIME designs, writes, merges and adopts UI5202; independent Architecture review required. Topology serial, one implementation PR. Operator explicitly authorized this successor. API8000/data remain unchanged.

## Outcome and invariant

The full shared navbar spans the Play content and chat. Opening side chat shrinks only the workspace below it. An explicit chat control switches side/bottom; narrow screens use bottom safely. Text occupies the full chat pane in both orientations. Layout is transient presentation state; changing it cannot change thread, publication/context, draft, Run, Plan, edition or request authority. Preserve existing Build and Plan geometry/plugin ownership.

Collapsed Notes stays in the navbar. Expanded Notes has a titled move handle and collapse control; mouse/touch pointer capture and keyboard arrows reposition it within visible workspace bounds below the navbar. Clamp on resize and chat-layout changes; preserve the textarea node, drafts, autosave and current-scene targeting during movement/collapse/navigation. No durable geometry preference/schema is introduced. Existing note writer stays untouched.

## Failure cases

Do not shrink the whole app-wrap/header. Do not reuse pane visibility as orientation. Exact Play only: the legacy shared Build class is not permission to alter Build. Keep ask-host DOM stable across orientation changes. A drag must stop on pointer cancel/lost capture and must not cause writes or select text. Never trap the move/collapse controls offscreen. Inspecting another scene does not retarget the current-scene Notes writer.

## Exclusive write lease

- This contract; HANDOFF-PLAY-compact-scene-reader.md and ROADMAP-demo.md for predecessor settlement.
- apps/live-control-ui/src/chrome/AppChrome.tsx and affected AppChrome tests.
- apps/live-control-ui/src/agentInteraction/AgentInteractionChrome.tsx and .test.tsx; WorldAgentConversation.planPlay.integration.test.tsx if integration verification requires it.
- apps/live-control-ui/src/planSurface/planSurface.css and components/WorldPlanAgentConversation.css only scoped Play geometry/text rules.
- apps/live-control-ui/src/playSurface/currentMoment/FloatingSceneNotes.tsx, .css, .test.tsx; PlayCurrentMomentCockpit.tsx/.test.tsx for presentation bounds/retention verification only; playSurface.css for scoped layout.

Provider/DTO/API/save controllers, shared context registry, dependencies, authored campaign data and other source paths remain read-only. Existing runtime/UI adoption uses guarded atomic index replacement, retains old assets, checks health and state; no new environment or service.

## Verification

Mounted AppChrome proves header outside workspace geometry. Chrome tests prove orientation preserves host/thread/context and other surfaces; notes tests exercise pointer/touch cancellation, keyboard movement, clamping, collapse retention and no writer changes. Run affected suites and build, inspect cumulative diff, commit/push/PR and independent exact-head review. Normal5202 visible desktop/narrow screenshots and actual side/bottom switching, movable Notes, current target while inspecting, edit/draft retention and API before/after parity complete acceptance. Real Edge remains read-only; disposable existing fixture used for any needed drafts. Do not mark successor Agent/session-context work complete.

## Rendered alignment correction

#1435 merged94cf0cf38 after independent PASS atd3b4184a1. Normal5202 proves side/bottom switching, full-pane messages and pointer/keyboard notes movement with collapse and current targeting; the wide1778px viewport exposed a182px gap because the workspace uses the centered shared wrap while chat remained viewport-aligned. This serial successor changes only scoped Play chat CSS and this contract. Match the established1440px border-box/20px padding geometry, including the existing40rem full-width fallback, so side chat meets the workspace and bottom chat matches the full navbar. Typecheck/build, exact-head independent review and desktop/wide/narrow rendered verification remain required.

#1436 merged56583e82a after independent PASS at61f6a0572. Visible wide1778px geometry now meets within0.02px and matches navbar bounds. Narrow361px inspection exposes a specificity conflict retaining the bottom pane’s36px left inset, and a wrapped Notes title making the panel10px too tall for the space above chat. This final scoped CSS correction matches the bottom selector’s specificity and constrains the whole Notes panel with a flexible scrolling body. Verify the reviewed candidate on5202 before merging; finalize the runtime receipt with its exact merge revision afterward.
