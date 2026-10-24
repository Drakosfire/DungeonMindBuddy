# Floating conversation beside authored work

SETTLED implementation: #1686 merged 8b8ea74f1 after exact Bugbot approval and
protected UI delivery. 168 shared checks and 27 final focused checks passed; Bugbot
ran 42 independent checks. Authenticated Build wide/narrow history, readable input
and fullscreen/Escape passed without requests or source edits. Hosted Play exposed
old wrapper padding/height and missing shared presentation styles; the dependent
hosted-frame correction owns that remaining rendered gate. Operator acceptance open.

Completed serial PRIME slice, codex/surface-floating-conversation, base
7f5d3ca754b5436334f8394f7877bd12fce770f2, existing buddy-context-loop checkout.

## Capability / critique
ConversationDock owns the shared floating panel appearance and responsive workspace
composition. Build/Plan retain a full-height mounted reader and place a bounded
column beside it on wide workspaces; narrow workspaces use an inset sheet whose
overlap remains scrollable. Existing hosted Play conversation uses the same panel
appearance within its owning chrome. Keep opaque fallback/readability, reduced
transparency, fullscreen keyboard/focus, height resizing, drafts, scroll, context
and current routing/save/recovery ownership. Never remount editors for layout.

## Exclusive writes / state / topology
This handoff; HANDOFF-BUILD-decision-response-debug.md; Docs/Roadmaps/ROADMAP-demo.md;
apps/live-control-ui/src/ui/ConversationDock.tsx, .css and .test.tsx;
apps/live-control-ui/src/planSurface/components/PlanConversationDockAdapter.tsx, .css and .test.tsx;
apps/live-control-ui/src/agentInteraction/AgentInteractionChrome.css;
apps/live-control-ui/src/agentInteraction/WorldAgentConversation.css;
apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx and .css;
apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx.
The rendered narrower column exposed stale JS textarea heights. Transfer composer
height ownership to the existing CSS content sizing so width changes reflow input.
One serial PR, fetched open work disjoint. PRIME owns UI5202 and temporary read-only
preview5301 if free; API7f5d3ca75/APP0060/native0017 unchanged. No inference probes
while the operator writes. Preserve retained sources, drafts and history; no data or
schema changes. No new runtime compatibility path or provider limits.

## Verification / delivery
Shared mounted draft/focus/scroll/context/fullscreen/resize tests; Plan/Play/Build
integration; typecheck/build; rendered wide/narrow geometry, no horizontal clipping,
page access and readable controls. Use a background browser tab without changing
operator drafts or sending questions. Independent exact Bugbot, PRIME merge,
protected UI delivery and retained-state proof. Operator aesthetic acceptance remains
open; no full authoring or journey completion claim from presentation alone.
