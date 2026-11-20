# Exact Plan insertion below a heading

Status: MERGED_AND_DELIVERED; operator acceptance remains open. Owner/designer: PRIME. Authority: active reference integration goal
and ordinary turn e499e5e7-6c25-413f-8ac1-03f7c5eb6bcb. Topology: serial,
base e6e5131135a2437621f85e131672680941a189c3, branch
codex/plan-under-heading-placement, existing buddy-context-loop checkout/dependencies.
No implementation overlap with currently open ingestion PRs. Implementation lease
only; no port, database mutation or delivery lease is acquired by this handoff.

## Outcome and invariant

Offer an exact insertion directly below a named root heading, distinct from
before the heading and after its whole section. Adopt the existing frozen placement
catalog, captured root-boundary target, native requested-work selection, proposal
review and Save/recovery bridge. No replacement authority, Graph publication or
new endpoint/store/executor. Preserve the original failed request and proposal.
The complete reference integration goal and operator acceptance stay open.

Only root headings already eligible for placement are offered. A table caption
cannot become a destination or be split from its table. Nested heading hierarchy,
duplicate labels and UTF-16 positions retain their existing owner. Host admission
binds the under-heading selector to exactly the following root boundary; the UI
recomputes the captured editor position before application. Missing/ambiguous
locations must clarify, not silently substitute a default caret.

The new closed placement kind is within the current catalog envelope. A no-op
APP reader fence prevents older executables from reading its retained history;
no documents or rows are rewritten. Older catalog values and captured wire proofs
keep their exact meaning and verification. No compatibility executor is added.

## Expected write lease and adoption

- src/application_state/agent_conversation/plan_placement.py: exact kind/selector
  and root-boundary validation in the existing catalog owner.
- src/application_state/agent_conversation/plan_authoring.py: decision guidance
  for catalogs offering the new location; preserve retained old wire projection.
- apps/live-control-ui/src/planSurface/agentEdit/planPlacementCatalog.ts:
  compile the exact existing root boundary below each eligible heading.
- apps/live-control-ui/src/api/planAuthoringReviewApi.ts: closed placement kind.
- tests/application_state/test_plan_placement.py: snapshot/digest/placement checks.
- tests/test_plan_jev_authoring.py: actual dispatch, action reservation and retained
  replay of the new location through existing owners.
- apps/live-control-ui/src/planSurface/agentEdit/planPlacementCatalog.test.ts:
  placement, hierarchy, duplicate labels, Unicode, protected captions.
- apps/live-control-ui/src/planSurface/agentEdit/planAgentEditProposal.test.ts:
  reviewed application and reload preserve every surrounding node.
- src/application_state/migrations/versions/20261105_0112_plan_heading_placement.py:
  no-op reader fence, recovery forward only.
- .github/workflows/world-ownership-core.yml: include owning provider-free placement
  checks in the existing query-and-answer suite.
- This handoff and predecessor native-writer-evidence-order settlement.

## Gates and disposition

Inspect exact cumulative diff; run owning host placement and native Plan authoring
checks, browser catalog and proposal application/recovery tests, typecheck and
migration head checks. Independent Bugbot review plus required CI precede merge.
Delivery requires a re-anchored runtime lease and protected API stop/upgrade/restart,
then ordinary under-heading reference proposal dogfood. Do not call this complete
from fixture success. Duplicate generated prose, manual Plan route adoption and
Play Run-context reference integration remain separate serial slices.

## Settlement before explicit-operation adoption

Merged #2101 b64e9f3e7938ba5c90747cc1973387286e7b8334 after independent
review of f8d9f3c18f367b0a41d019e5ea890eeef0d663b4 and all seven CI gates.
Delivered union 86f9b112f49b89282ea05b25b098d6d927ed9b78 / APP0112 with
full retained-state conservation except the no-op reader-fence row. A graceful
API-stop timeout was preserved; an independently reviewed unchanged UI-proxy
restart let the old API drain naturally before forward continuation. No forced
kill or data rollback. Ordinary turn 175cb828-35db-4de5-a17b-b999cd686aa5
selected under:2, produced the correctly placed paragraph, and supported editing,
Save and reload at rehearsal revision 2. The original Plan and unsent draft were
unchanged, and all original failures remained. This is a bounded case, not general
writer reliability or operator acceptance.
