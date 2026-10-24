# Compact terminal retry presentation

ACTIVE serial PRIME slice on codex/surface-compact-retry-status, base
73ec0bd788144403dfc6fb678fd81870ec0e9210, existing buddy-context-loop checkout.

## Invariant and critique
Terminal conversation failure shows the shared red circular Retry action. Keep
failure explanation in per-turn Debug rather than repeating it beside the action.
Accessible labels, busy/disabled state, keyboard operation, exact recovery controls
for uncertain submissions and surfaced retry errors remain. Presentation must not
change submission, history grouping, correlation or capability behavior.

## Exclusive writes / state
This handoff; HANDOFF-BUILD-proposal-route-selection.md; Docs/Roadmaps/ROADMAP-demo.md;
apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx and .css;
apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx.
Serial one PR, no conflicting fetched open work. PRIME owns UI5202; API73ec0bd78,
APP0060/native0017 unchanged. No schema or provider calls. Preserve all saved rows.

## Verification / delivery
Shared Plan/Play/Build rendering tests assert icon-only terminal presentation,
Debug explanation and one-click dispatch without duplicate submission or draft loss.
Typecheck/build, independent exact Bugbot, PRIME merge, protected UI delivery.
No live model calls while the operator dogfoods.
