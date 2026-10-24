# SURFACE — constructive document and conversation spacing

ACTIVE PRIME UI-only serial slice at fe403ee23, branch
codex/constructive-pane-spacing, existing context-loop checkout. Operator approved
removing redundant document frame/gutters and tightening shared conversation
spacing. Broad goal/API1709 remain paused.

Exclusive writes: buildSurface/buildSurface.css; ui/ConversationDock.css;
planSurface/components/WorldPlanAgentConversation.css; this handoff. No content,
API, save schema or model change. Build outer projection loses decorative frame,
margin and padding; paper keeps one inset proportional to available pane width.
Shared conversation uses available message width and bounded quote/figure insets,
including nested quotes. Preserve controls, citations, semantic quotations,
fullscreen, draft retention, history and Edit drawer collision behavior.

Verify production build and exact cumulative independent Bugbot review. Render
real Build split/closed and fullscreen conversation views without source writes
or model calls; inspect geometry for useful text width and horizontal overflow.
PRIME merge and protected UI5202 adoption, API and retained data unchanged.
