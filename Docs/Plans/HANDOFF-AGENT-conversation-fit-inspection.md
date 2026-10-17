# Conversation table fit and request inspection

Status: SHIPPED — PRIME implements the operator's three dogfood corrections;
ARCHITECTURE reviews. Base d5872d85, serial branch codex/conversation-fit-and-inspection
at /tmp/prime-recap-mention-boundaries. No overlapping open UI lease found.

Outcome: content-sized table columns (compact numeric roll columns), readable
pretty-printed nested JSON input in The Prompt with exact captured bytes preserved,
and remove redundant JSON shape instructions from the strict-schema Build generator.
Keep historic captures truthful. No provider calls required or database changes.

Exclusive paths: this handoff; apps/live-control-ui/src/planSurface/components/
WorldPlanAgentAnswer.tsx, WorldPlanAgentAnswer.css, WorldPlanAgentAnswer.test.tsx,
BuildComposeProposal.css, PreparedRequestInspector.tsx, BuddyPromptInspector.test.tsx,
BuddyContextTrace.css; apps/live_control_server/services/build_document_proposal.py;
tests/test_build_document_proposal.py; apps/live-control-ui/src/ui/ConversationDock.css
(operator's added fullscreen side-spacing correction). Render desktop/narrow table and prompt views,
verify component and strict schema boundaries, typecheck/build; exact independent
review, PR/merge, matched UI5202/API8000+8002 deployment without document mutation.
Old prompt captures retain old instructions; only new requests change.

## Settlement
PR1293 merged afa8ab32a0bd292ed8faba1a41476c0da410e1f8; ARCHITECTURE PASS cf461e53;35 UI and13 generator tests, typecheck/build pass.
Matched UI5202 and API8000/8002 now serve immutable7147d1e4;5876 UI unchanged.
No schema migration, provider call or operator document edit. Compiled assets and
authenticated routes verified. Desktop actual d20 column46px, name106px; narrow
viewport has no horizontal conversation overflow. Existing input pretty-printed
without request-byte changes. Existing proposal retains Insert at current caret.
Operator approval/Save still required. Lease closed.
