# Build review page reload

ACTIVE serial PRIME correction on codex/build-review-page-reload, base
4b851a07a7cf5112a60a8439a93fa336f15a855d, existing buddy-context-loop checkout.
The parent page-review capability is merged and delivered after exact Bugbot;
ordinary staging/edit/save passed and left document bytes unchanged. The pending
synthetic review remains retained. Rehearsal exposed history loading gated on the
conversation drawer, so page review did not reappear on a closed-drawer reload.

## One capability
Resume saved suggestions as page-owned work when a committed Build page opens,
independently of opening chat. Reuse the existing bounded World history controller
and proposal owner; do not add a second history reader. Keep the selected staged
proposal scoped to the actual current Build document; proposals from another page
remain readable history and never stage on the current page. Conversation opening
must not repeat a satisfied bootstrap read. Preserve Plan/Play demand loading and
all proposal/anchor/review/apply gates. No provider request, schema or API change.

## Exclusive writes
- This handoff; HANDOFF-BUILD-page-proposal-review.md; Docs/Roadmaps/ROADMAP-demo.md.
- planSurface/components/WorldPlanAgentConversation.tsx.
- planSurface/components/BuildComposeProposal.tsx and .test.tsx.
- buildSurface/BuildCompose.integration.test.tsx.
Paths above are under apps/live-control-ui/src unless Docs-prefixed. No other
open implementation lane leases them. User tabs/drafts unchanged; PRIME owns5202.

## Gates
Mounted actual Build+global conversation host proves closed-drawer bootstrap and
staging, persistence after remount, no duplicate bootstrap on open, and foreign
page proposals not staged. Existing shared conversation and review checks,
typecheck/build, cumulative independent Bugbot; PRIME merge and protected UI-only
delivery. Resume the existing retained ordinary synthetic review without another
provider request, then finish Keep/Discard/reload. Parent on-page review is not
full floating conversation, media/replacement review or full goal completion.
