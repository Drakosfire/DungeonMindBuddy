# One-click terminal question retry

ACTIVE serial PRIME slice on codex/surface-one-click-retry, base
358895739c41e67756a4ed964ce579caf827bb6f, existing buddy-context-loop checkout.
Operator explicitly requests a simple circular-arrow Retry button that sends the
question again, without restore/review/Send ceremony. Applies to the shared
Build/Plan/Play terminal question control on its owning current document/Run.

## One capability and critique
Retry a known terminal question through the normal current-context sender with new
request identity. Preserve a different unsent composer draft and newer typing.
Use existing pending-request, exact recovery, capability, current-page, pointer,
credential and source/Run checks. Never blindly replay an unknown saved operation
or cross-surface historical request. Prevent double-click dispatch. Compact icon
has accessible Retry question name, tooltip and busy/disabled state; remove the
extra review instructions. Unknown pending work remains reconciled by its owner.

## Exclusive writes
- This handoff; HANDOFF-SURFACE-proposal-keyboard.md; Docs/Roadmaps/ROADMAP-demo.md.
- apps/live-control-ui/src/agentInteraction/ConversationRecovery.tsx and .test.tsx;
  WorldAgentConversation.planPlay.integration.test.tsx.
- apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx,
  WorldPlanAgentConversation.css: retry sender override and compact control only.
No API/schema/provider contract change. No active overlap. PRIME owns UI5202;
API7ed38faf and all retained state remain unchanged. User tabs/drafts protected.
One serial PR, existing checkout.

## Gates
Shared mounted Build/Plan/Play tests prove one click sends original terminal
question using current work and a new identity, double-click sends once, different
unsent and later-typed drafts survive, failures retain recovery, blocked pending
work and foreign historical work cannot retry. Existing relevant sender/recovery
checks; TypeScript/build; exact Bugbot; PRIME merge; protected UI-only deployment.
Ordinary rendered proof uses existing terminal history if available, without
fabricated runtime rows or source writes. Keep any unavailable live proof explicit.

## Predecessor settlement
#1677 merged358895739 and UI-delivered; native document-end focus and direct typing
stay inside suggestion. Native drag and chosen placement persisted through reload;
explicit caret placement and Keep/Save/reload retained edited text once. Synthetic
source bytes stayed unchanged before Keep. Earlier focus regression restored via
ordinary Undo/Save. Floating layout and full goal acceptance remain open.
