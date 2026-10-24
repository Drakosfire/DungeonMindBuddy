# SURFACE — minimal conversation chrome

ACTIVE PRIME bounded user-requested UI slice fromfa69816c4, branch
codex/conversation-minimal-chrome, existing Buddy context-loop checkout.
The broad goal and API fixPR1709 stay paused; this independent UI request does
not resume them. No API/schema/model/source changes. One UI PR, independent of1709.

Exclusive writes: shared ui/ConversationDock.tsx/.css/tests; Document conversation
adapter/tests; WorldPlanAgentConversation.tsx and presentation CSS/tests; focused
UI tests; this handoff. Preserve paused1709branch and retained data. UI5202 delivery
owned, API8000 unchanged; preserve API/APP/native state and draft recovery.

Assessment: New(+), fullscreen and close serve direct user control. Context scope,
graph exploration, history management and diagnostics are useful on demand, not
primary conversation content. Debug and expanded evidence trails expose technical
inspection duplicating statement citations; hide them by default behind a menu
setting. Redundant Conversation headings add no task value. Keep citations,
actual user/assistant content, readable error recovery and Retry discoverable.

One shared hamburger menu owns context visibility and technical-detail visibility
plus existing surface management actions. Preserve lazy context mounting, focus,
outside/Escape dismissal, fullscreen containment, drafts and scroll position.
Plan/Build adapter and Play/read-only host use the same component. Accessible
labels/tooltips remain even though the primary header displays only icons.
Do not delete exact Debug prompts, evidence authority, recovery or underlying
Graph actions. No provider calls required for UI verification.

Verify focused shared/adapter/host tests, typecheck/build, independent Bugbot exact
cumulative review, PRIME merge, protected UI-only adoption and ordinary rendered
Build/Play inspection including hidden technical content, menu access, close/
reopen/fullscreen and retained composer draft. The broad goal remains paused.
