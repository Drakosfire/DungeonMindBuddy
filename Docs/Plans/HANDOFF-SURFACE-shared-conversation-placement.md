# SURFACE — shared conversation placement

ACTIVE PRIME serial UI slice at27502a570, codex/shared-conversation-placement,
existing context-loop checkout. Explicit operator direction: placement is owned
by shared agent interaction with a Surface, not one surface. Implement Side /
Bottom / Float in shared ConversationDock menu with one remembered browser
preference; replace Play-local state/buttons. Side reserves horizontal space,
Bottom reserves vertical space, Float overlays without shrinking the reader.
Narrow Side falls back to Bottom while retaining preference. Fullscreen remains
independent; placement does not remount messages/composer or alter drafts/state.

Exclusive writes: ui/ConversationDock.tsx/.css/.test.tsx;
ui/conversationPlacement.ts; agentInteraction/AgentInteractionChrome.tsx/.css/
.test.tsx; WorldAgentConversation.planPlay.integration.test.tsx if needed; this
handoff. No API/schema/model/source changes. No automatic conversation operation.
Verify shared menu ownership, persistence/synchronization, narrow fallback,
mode switches retaining composer and fullscreen return. Production build,
exact independent Bugbot review, PRIME merge, protected UI5202 adoption and
ordinary rendered Build+Play controls/geometry. Full goal remains unproven;
API1709 remains paused until explicitly selected.
