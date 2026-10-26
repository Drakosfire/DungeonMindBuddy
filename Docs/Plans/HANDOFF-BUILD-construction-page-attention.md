# BUILD: make first visible construction the page handoff

PRIME activates this UI-only bounded slice from aa2c10157 in the existing serial
checkout. Topology is parallel-independent with held #1792: that PR owns routing
metadata/backend tests; this slice owns the UI paths below. No unmerged dependency
or shared implementation file. #1792 remains held for external diagnostic approval;
this slice does not bypass that refusal or send captured context to a provider.
No extra worktree, service or port. Reuse current owned5202 after protected delivery.

Current Surface previews emit onVisible once after actual nonempty received content
and restored placement. BuildComposeProposal gates the callback on ready, so the
first streamed content consumes the notification without handing attention to the
page. Use the same existing preview signal at building/ready, never incomplete.
Keep an automatic construction callback separate from explicit Review. Automatic
handoff reads the current controlled composer and leaves the dock open if any
unsent text exists, focused or not. Explicit Review remains a deliberate collapse.
Do not retrigger collapse for later chunks or after manual reopening. Preserve
source/conversation/view epoch and basis retirement, focusOnReveal=false, page
scroll ownership, inert preview/editor JSON, draft retention and final Save owner.
Clarifying questions have no page construction and stay in conversation.

Exclusive writes: this handoff; apps/live-control-ui/src/planSurface/components/
BuildComposeProposal.tsx and .test.tsx; WorldPlanAgentConversation.tsx; existing
agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx for actual
conversation/dock/editor stream-callback proof (no external request); existing
buildSurface/BuildConstructionPreview.test.tsx only if needed.
No backend, API/schema, stream protocol, placement algorithm, new polling owner,
editor save, routing, stored conversation or model instructions change.

Prove mounted actual TipTap editor plus shared ConversationDock: empty preview
never collapses, first paragraph/table/plan objective collapses once, later chunks
after manual reopen do not collapse, incomplete/stale basis do not collapse,
newer unsent composer retains text/focus/open dock, explicit Review still closes.
Real typecheck/build, exact cumulative independent Bugbot review and PRIME merge
precede protected UI delivery. Ordinary external generation is not substituted for
the held captured-envelope diagnostic; retain an honest live-proof limitation
until authorized ordinary work can demonstrate construction on5202.
