# One visible request across Retry attempts

MERGED and UI-delivered as4bcc6ad39 after exact Bugbot71859292a. Ordinary
retained duplicate history shows one request; both previous failures remain in
Debug, with no model dispatch during verification. Successor:
HANDOFF-BUILD-open-page-context.md.

Former serial PRIME slice on codex/surface-retry-attempts, base
d356f96547fd7b7b67390a9f165a819676141c1d, existing buddy-context-loop checkout.
Operator correction: Retry should replace the visible failed request, not append
copies of the same question/failure. Keep prior executions inspectable in Debug.

## Invariant and bounded design
Shared Build/Plan/Play display groups consecutive matching requests when all earlier
members failed/interrupted without accepted assistant output. Exact question text,
World, surface and primary object must match; sequence gaps, successful answers,
local proposals and page/media result placements break groups. Different saved
revisions can be deliberate current-context retries. Grouping is display-only,
never evidence of idempotency, authorization, provider safety or semantic identity.
Every retained row, exact request and trace remains intact. No history deletion,
provider replay or unknown operation reclaim. Only latest attempt offers Retry.
Pending resend of the matching latest failed question occupies that visible request
and shows progress; preserve pending recovery/error controls and unsent drafts.
Reload rebuilds grouping from verified ordinary history, including older duplicates.

## Exclusive writes / ownership
- This handoff; HANDOFF-BUILD-creative-context.md; Docs/Roadmaps/ROADMAP-demo.md.
- apps/live-control-ui/src/agentInteraction/conversationAttemptGroups.ts and .test.ts.
- apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx.
- apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx.
One serial PR, no active overlap in fetched census. PRIME owns UI5202 delivery;
API d356f965/APP0060/native0017 remain unchanged. No API/schema contract changes.

## Verification
Mounted shared surface tests: one visible question across repeated failures,
pending retry progress at the existing request, latest success replaces failure,
older attempts available in Debug, reload grouping, unrelated requests separated,
no double dispatch, drafts survive and unknown pending work remains fenced.
Typecheck/build; exact Bugbot; PRIME merge; protected UI-only delivery. Ordinary
retained duplicate history must render once and keep prior Debug inspectable.
Actual reply quality is a separate live gate; never call grouping a fix for provider
or acquisition failure. No private questions, prompts, IDs or traces in GitHub.

## Predecessor settlement
#1679 mergedd356f965 after Bugbotafa5d5722 and132 tests; protected API-only
delivery retained2382 rows,27 frozen components,89 mechanics products/native rows.
Synthetic ordinary brainstorming finished in7.98s (4 decision calls+1 writer) but
abstained without reading the requested current page. No useful creative answer
acceptance: the next authoring correction must require actual acquired page context
rather than treating history/discovery as adequate current-page content. Existing
failed user request has not been retried again during this investigation.
