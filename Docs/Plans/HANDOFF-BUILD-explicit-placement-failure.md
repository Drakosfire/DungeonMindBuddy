# Explicit Build placement failure

ACTIVE serial PRIME slice on codex/build-explicit-placement-failure, based on
origin/main1dfbc8dfb09e769019b24458b14f64aa44039ced. Reuse buddy-context-loop.
No overlapping open product implementation lane. Existing API8000/UI5202 owned
by PRIME; preserve user tabs, sources, draft copies and retained state.

## One capability
An editable Build send whose advertised insertion preparation fails or returns no
capability must not silently become
an answer-only turn. Preserve the full composer and show the actual preparation
failure before durable submission or provider I/O. The author can resolve the
page/selection and send normally, or explicitly choose discussion using the saved
page. Bind that deliberate choice to the exact current composer generation and
surface/source fence; never carry it to another message or page. Discussion does
not claim to include the unavailable working draft or execute a page operation.
Ordinary successful capability capture and exact saved-request recovery retain
existing behavior. No text intent heuristics, new backend contract, automatic
retry, new cap or authoring-permission bypass.

This is a prerequisite for page-centered staged proposals, not their completion.
Initial conversation capability, shared page placement, draft-aware grounding and
mapped-anchor editing/reload require subsequent bounded ownership/design work.

## Failure critique
Capture rejection, undefined capability, late result after page/editor switch, changed
message while capture runs and repeated clicks must
not lose text, submit implicitly, or grant another request's deliberate choice.
After successful capture, existing request identity, pending storage and dispatch
fences remain mandatory. An interrupted admitted request uses its saved envelope.

## Exclusive writes
- This handoff; HANDOFF-BUILD-named-source-citations.md; ROADMAP-demo.md.
- apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx
- apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx
  for mounted Build send/failure/stale scope/draft verification.
- useBuildCompose/BuildComposeProposal.tsx only if a named unavailable reason is
  needed; no producer/editor mutation contracts changed by this slice.

## Gates
Mounted actual conversation tests prove zero dispatch/storage on capture failure,
complete/newer composer preservation, deliberate saved-page-only discussion,
no inherited bypass after message/source change and normal successful capture.
Exact cumulative diff and independent Bugbot. PRIME merge; protected UI-only
adoption with API/state unchanged; ordinary synthetic selection-related refusal,
explicit discussion and corrected-caret send without modifying the operator page.
Settle the roadmap for the new authoring priority and shipped citation predecessor.
