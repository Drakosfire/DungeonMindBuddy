# Explicit Plan operations use native reference-aware execution

Status: API_MERGED; UI adoption/delivery and operator acceptance remain open.
Owner/designer: PRIME. Authority: active reference integration goal.
Topology: serial after merged #2101 b64e9f3e7938ba5c90747cc1973387286e7b8334.
Branch codex/plan-explicit-native-operation, existing buddy-context-loop checkout
and dependencies. No runtime/database mutation lease; delivery separately gated.

## Serial delivery boundary

The native API contract is delivered first; UI adoption is a dependent serial
slice based on its merge. The first PR includes request admission, immutable
intent, SDK outcome constraints, proof validation, history projection, reader
fence and owning host tests. Existing UI controls remain unchanged in that PR.
The successor adopts fresh explicit UI callers and replaces superseded producer
tests while preserving target, draft, review, Save and recovery coverage.
The full reference goal remains active across both deliveries.

## Full outcome

Fresh explicit Plan change/question choices use the existing native Plan producer
with the exact reference bundle and captured Plan target. Freeze the author choice
in the submitted intent, constrain the existing requested-work SDK choices, and
bind the parent proof to that intent. Preserve the choice in pending recovery and
failed-turn Retry. Automatic requests retain their existing exact contracts.
No new endpoint, executor, evidence owner or model allocation.

The explicit choice is not a text prefix or a best-effort prompt. A discussion
choice cannot reserve an edit; a Plan-change choice cannot silently become ordinary
discussion. Missing/ambiguous destinations can clarify, different destinations
remain distinct, and unavailable writing cannot gain a replacement capability.
The same actual SDK request/output/hash and Plan review/Save owners apply.

## Inventory and boundary

Current fresh manual Plan writes call composeEdit and reject references. Current
explicit question choice is not in the submitted native intent. Adopt the fresh
manual callers into submit; retain composeEdit only for the exercised historical
clarification continuation until its separate adoption/demolition slice. Existing
World-facts-off requests have no native Plan context and are advertised discussion
only; do not silently route their Plan changes through the old generator. Preserve
that discussion path and clearly reject unavailable writing. A new explicit choice
cancels an older continuation selection. Historical action readers/application
and all retained outputs remain intact. These are open dispositions, not a claim
that Plan demolition or the full goal is complete.

## Expected write lease

- apps/live_control_server/models/agent_turn.py: native Plan-only request choice
  and truthful history metadata for Retry.
- apps/live_control_server/services/agent_turn_service.py: freeze exact choice.
- apps/live_control_server/services/plan_jev_dispatch.py: current requested-work parent.
- apps/live_control_server/routes/agent.py: history derives the choice from retained intent.
- src/application_state/agent_conversation/types.py: closed submitted intent version.
- src/application_state/agent_conversation/native_execution.py: adopt that intent.
- src/application_state/agent_conversation/authored_graph_references.py: use its actual references.
- src/application_state/agent_conversation/plan_placement.py: closed explicit-choice parent.
- src/application_state/agent_conversation/plan_authoring.py: restrict offered outcomes.
- src/application_state/agent_conversation/plan_jev_decision.py: verify exact choice/proof join.
- apps/live-control-ui/src/api/types.ts: only Plan request/history fields; existing
  ingestion-related contracts are outside this lease and must remain untouched.
- apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx:
  fresh explicit caller, pending/history validation and Retry preservation only.
- src/application_state/migrations/versions/20261105_0113_plan_explicit_operation.py:
  no-op forward-only reader fence, no retained row rewrite.
- tests/test_plan_authored_references.py; tests/test_native_plan_assertions.py;
  tests/application_state/test_plan_placement.py: owning contract and native dispatch checks.
- apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx:
  actual composer selection, captured references, pending outcome and Retry.
- .github/workflows/world-ownership-core.yml: required owning regression selectors.
- This handoff and predecessor HANDOFF-REFERENCE-plan-under-heading.md settlement.

## Verification and gates

Prove wrong-surface/retired-policy choices rejected before provider dispatch,
intent fingerprints differ across choices, parent/SDK substitutions fail closed,
reference input and current target conserved, unavailable/different destinations
remain honest, and pending/failed Retry preserves the original operation rather
than rereading the current composer control. Run owning UI/host/native tests and
inspect cumulative diff. Independent Bugbot and required CI precede merge;
protected delivery precedes ordinary explicit-choice dogfood. All original failures,
accepted authoring, Plans, Run state, history and drafts remain retained. Play,
filters, remaining legacy execution demolition and operator acceptance stay open.

Checkpoint: full UI migration run found 27 old-producer expectations (252 pass).
This is not a passing UI integration. Keep original run evidence and settle
each affected test against a live caller or replacement boundary in the successor.

## API settlement

Merged #2102 at 0e35332a7ddde40a0e4b16755ac36dd0448a55e1 after
independent review of 442f2e827ce09b63906d8bec3504b0ab6ce9e319 and all
seven CI checks. Owning tests: 46; broader native/authoring tests: 88.
Dependent UI adoption is #2103. Runtime remains the prior APP0112 release until
protected combined delivery; this merge establishes neither UI dogfood nor
operator acceptance. Original failures and retained records are unchanged.
