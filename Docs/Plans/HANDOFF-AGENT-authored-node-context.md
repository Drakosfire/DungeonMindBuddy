# Authored Graph references in Buddy context

## Authority and scope

PRIME designs the operator-authorized next authoring capability: explicitly reference
an existing Graph object from conversation or an editable page-plan step, have Buddy
read that exact object and its sources, and preserve the choice through continuation.
Design lane: codex/authored-node-context-design from remote main
62eb05d04dc4770e0e686c38f29f4bd277f2763d in the existing buddy-context-loop checkout.
Serial topology: this design PR, then one independently useful end-to-end implementation
PR. Implementation is BLOCKED until independent critique clears this contract and an
exact expected-path implementation lease is pinned. No runtime changes in this PR.
No overlapping active implementation PR owns these contracts; #1764 remains parked.
No new checkout, environment, port, publisher, planner, or external service.

## Problem and inspected owners

- Build composer currently sends graph_selection:null. Page Graph chips and the shared
  GraphReferenceSearch already provide selection/display, not model evidence.
- AgentTurnRequest has a generic Graph selection, but BuildGraphIntentV1 deliberately
  fixes it to None. APP _validate_build_submission, Build source validation and historic
  presentation require absent selected_object. Removing these guards would widen V1.
- BuildWorldContext.acquire and APP build_world_context.verify_world_selection require
  a real BuildWorldReadSelectionV1 joined to actual Jev request/result bytes. A human
  selection must never be disguised as that model choice.
- Existing native object broker, read_operation_sources, exact pin deduplication,
  ValidatedGraphOperationEventV3, ValidatedSourceReadEventV2 and named citations own
  acquisition/evidence. Reuse those boundaries rather than injecting node summary text.
- Work plans are APP-owned PlanV2/ReviewV2 with immutable dispatches. The author can add
  a node reference to a pending step after generation: source-turn inheritance alone
  cannot represent that edit. The review/dispatch owner must preserve it durably.

## Product interaction

Use the existing scoped Graph picker and its verified Surface information channel.
A Reference action in Surface navigation and typing @ in the focused composer or
editable plan step open the same picker in navigation, not a body/cursor floating
button. Search by name, inspect matching kind/scope, choose the actual node. Ambiguous
names require an explicit choice. No hard-coded cedar-box/Brin/Edge identities.

A compact named reference accompanies the text. It can be inspected and removed before
submission, and pending-step references are directly editable with that plan. A visual
chip means selected, not read. Read status appears in actual activity/trace; exact
scope/revision/digests live behind Developer. Keep clarifying questions inline in chat;
plans and generated writing remain on the page. Do not auto-create a missing node or
interpret a free-text name as an established identity.

## Input contract and frozen authority

Introduce a closed versioned authored-reference input, separate from generic
Graph selection. Keep graph_selection absent for Build and retain V1 interpretation.
The reference basis includes managed World, native World/binding version, graph revision
and durable node ID. Preserve colons and exact case; labels/kind/summary from the client
are display data and must be resolved by the host. No new bearer token or second store
is needed: validate the submitted basis against the existing managed binding and exact
native snapshot, including admissibility and node membership.

Use a new submitted-intent variant and explicit capability/policy marker, included in
its fingerprint and exact prepared request. New APP event capture binds the submitted
reference set to turn, conversation, attempt, source basis and frozen Graph scope
before the first provider authorization. New policy/event support requires additive
APP migration0073; old stored intent/event/policy meaning and bytes remain unchanged.
No backwards execution fallback. Inspect the actual current migration head before
implementation; if0073 is taken, the steward updates this contract before mutation.

The first semantic routing request sees attached identities explicitly marked unread.
It does not receive fabricated node/source content or re-decide which node the author
meant. After ordinary admission, the host performs the exact authored object read before
writer synthesis, independent of whether Jev separately requests other evidence.
An explicit authored-read event authorizes only those frozen object IDs in the resolved
scope. It binds the reference capture, executable argument digest and actual validated
object/source events. Never emit fake model selection, provider authorization or usage.

Reuse broker paging, exact source-pin reading and existing budget accounting. A node
outside the limited initial navigation projection may be resolved through the existing
exact-object boundary under the frozen scope; do not require its presence in a truncated
navigation list. Reject an inadmissible/missing identity, changed managed binding or
unavailable snapshot precisely. Never search for a similarly named substitute.

## Reads, synthesis and failure

APP admission and final reconstruction validate the join from authored reference to
object-operation result and source-read receipts; writer projection is reconstructed
from those validated records. Client labels, picker previews and object summary text
alone grant no factual/citation authority. Sources retain their original authorship,
proposed/played distinction and exact names. Each actual read is inspectable and may
be cited through existing source citation authority. Reuse overlapping exact pins while
preserving both author-selected and model-selected provenance.

Distinguish selected/unread, reading, read, source gap and acquisition failure. If the
requested object or its evidence cannot be obtained, preserve the request/reference
and report the specific obstacle. A partial object/read must not be presented as complete
or silently dropped. Do not synthesize a supported answer from the chip text. Allow
honest creative proposals/inferences, for example a possible hinge on a described box,
without upgrading them to established facts. No Graph write is implied by a reference.
No arbitrary character/token/reference caps or optimistic partial-success label.

## Durable review, continuation and retry

Use a new PlanV3/ReviewV3 with authored root references and step-specific references.
Root references originate in the captured request and are explicitly visible/editable;
step references may be added to an existing pending step. They are author inputs, never
model-generated node IDs. New typed plans bind initial references from their immutable
source turn at host admission, not by asking the writer to echo arbitrary identifiers.
Old PlanV1/V2 remain readable; explicit reference editing/Save upgrades without changing
existing rows, outcome, source identity or prior dispatches. Preserve newer local copies,
CAS, cross-tab comparison, unreadable-copy retention and page Save ownership.

An explicit dispatch freezes applicable root plus selected-step references, includes
these in a versioned dispatch and reviewed-action binding/fingerprint, carries the same
typed snapshot in the submitted intent, and excludes sibling-step references. Deduplicate
identical scoped identities; refuse conflicting bases instead of choosing one silently.
Root references are mutable review state: edits affect only future dispatches. Existing
provider-envelope and real read budgets apply; add no arbitrary reference count/byte cap.
Dispatched reference snapshots are immutable even when a later root/outcome review is
edited. Continue only the selected action; this does not authorize deferred writing.
Source-turn inheritance is provenance, not a substitute for author edits to the review.

New continuation reads the same durable identities at its newly frozen current Graph
revision, retaining the original selection basis separately. Node removal, new tenancy
or binding change is a concrete obstacle, not a rename lookup. Uncertain-outcome recovery
reopens the exact stored request and original read snapshot without resending. A deliberate
retry preserves the failed request's reference identities/origins, never imports unrelated
newer composer references, and records any fresh read revision separately under its new
physical attempt. Preserve newer unsent composer text/references throughout.

## Implementation owner inventory and activation gate

Runtime/product implementation belongs to DungeonMindBuddy. The following inspected
owners define the contract; activation must pin exact expected files, including tests,
from current source rather than claiming a wildcard write lease:

- API/APP: models/agent_turn.py; agent_conversation types/service/related action,
  work_plan, submitted intent/retry owner; new authored_graph_references module;
  migrations/versions additive0073 and relevant Postgres checks/readback.
- Runtime: agent_turn_service, build_jev dispatch/driver/harness/writer selection,
  build_world_context, world_source_acquisition and context capture/presentation.
- UI: API request/work-plan/progress/trace decoders; WorldPlanAgentConversation and
  pending-request/composer owner; shared Graph picker adapters and Surface navigation;
  staged/saved work-plan renderers, capture and placement/review persistence.
- Existing capture, retry, reviewed-action, source/citation and construction tests need
  actual owner fixtures; preserve current policies and exact request accounting.

Inspect and name every required policy union, stored lifecycle/readback constraint,
request decoder, continuation/retry fingerprint and source-input validator before
activation. No read lease for a design reviewer grants a write lane. One implementation
PR after this contract, with a separate steward amendment if ownership expands.

## Required proof

1. Actual native/APP/Postgres boundary: selected object and exact source reads appear in
   the real writer input with authored provenance; no Jev-selected event fabricated.
2. Counterexamples: duplicate labels, forged label/World/revision, missing/deleted node,
   changed managed binding, source read refusal/truncation, unrelated newer references,
   empty reference set, object outside navigation projection and overlapping source pins.
3. Actual saved plan: add reference after generation, Save/reload, defer another step,
   continue only selected step, verify its frozen references/read sources; later root
   edits do not alter prior dispatch or output. Old plans preserve bytes until explicit
   upgrade. Retry/reload/cross-tab and newer composer references retain identity.
4. UI actual request serialization and real-loader/readback tests; actual tsc-b/Vite
   build; exact cumulative independent Bugbot review; protected8000/5202 adoption.
5. Ordinary synthetic authoring through picker/@, node inspection, real response/proposal,
   edit/Save/reload and fresh conversation retrieval. No console/SQL/manual-ID repair;
   no hardcoded adventure runtime paths. Then use the approved creative chain, preserving
   pending Noll choice and operator acceptance. Synthetic proof is not creative acceptance.

## Delivered predecessor settlement

Surface plan controls #1782/#1783 are delivered at UI62eb05d04 with API340cad98,
APP0072/native0017 on8000/5202. Independent final implementation review approved
f69ef0b7b539e422bc359286e7e5abcd0c73b6d7. Protected UI-only delivery retained3276 APP
rows, native rows,27 frozen components and89 product files.26 focused checks and actual
tsc-b/Vite passed. Ordinary narrow/normal page verification fixed inherited CSS/header
and non-text selection issues, proved object-menu Developer opt-in and exact receipt,
completed disclosure, editable deferred rows and navigation-only passage actions.
The newer composer and older blank unsaved plan step survived. Private proof audit
found no contradiction; UI observations remain direct CUA attestations, distinct from
aggregate adoption retention. No new model request, plan dispatch or page Save was used
for that proof. HANDOFF-SURFACE-plan-controls.md is the delivered predecessor, not a
concurrent active implementation lease. Detailed story/runtime evidence stays private.

The separate Discuss reply that drafted content for a deferred insertion remains a
semantic scope defect. This reference capability must not obscure or claim to fix it.


## Implementation activation — ACTIVE serial owner amendment

PRIME activates codex/authored-node-context from merged design fec4a1a91a0fa1809803d309ed5427cdd37602a6,
independently approved at4c7284d95382ba9470f927ff3da72bc69bbed17f. This is the one
implementation PR declared above. No parallel implementation lease overlaps; #1764
remains parked. Existing checkout,8000/5202, APP0072/native0017 stay untouched until
reviewed protected additive0073 adoption. Independent critique of this exact owner
amendment precedes runtime edits. Frozen historical contracts remain historical readers,
not compatibility execution paths.

The writer integration uses an explicit host-acquired reference context lane, analogous
to existing acquired primary-page context. Do not fabricate a model evidence-selection
vote or add a second writer selector. Join mandatory authored object/source records
alongside actual Jev-selected evidence and deduplicate exact passage bodies; preserve
distinct authority. A new policy marker owns that join; legacy selection validators
keep their current meaning. Never hide an acquisition gap by marking the reference read.

Exact expected write lease (paths relative to Buddy):

- `Docs/Plans/HANDOFF-AGENT-authored-node-context.md`
- `src/application_state/agent_conversation/authored_graph_references.py`
- `src/application_state/agent_conversation/types.py`
- `src/application_state/agent_conversation/service.py`
- `src/application_state/agent_conversation/repository.py`
- `src/application_state/agent_conversation/work_plan.py`
- `src/application_state/agent_conversation/reviewed_action.py`
- `src/application_state/agent_conversation/retry.py`
- `src/application_state/agent_conversation/build_world_context.py`
- `src/application_state/agent_conversation/build_draft_context.py`
- `src/application_state/agent_conversation/build_primary_context.py`
- `src/application_state/agent_conversation/source_writer_output.py`
- `src/application_state/agent_conversation/plan_objective.py`
- `src/application_state/agent_conversation/build_intentional_response.py`
- `src/application_state/migrations/versions/20261025_0073_authored_graph_references.py`
- `apps/live_control_server/models/agent_turn.py`
- `apps/live_control_server/routes/conversation_work_plans.py`
- `apps/live_control_server/services/agent_turn_service.py`
- `apps/live_control_server/services/build_authored_references.py`
- `apps/live_control_server/services/build_jev_harness.py`
- `apps/live_control_server/services/build_jev_driver.py`
- `apps/live_control_server/services/build_jev_dispatch.py`
- `apps/live_control_server/services/build_jev_transitions.py`
- `apps/live_control_server/services/build_jev_writer.py`
- `apps/live_control_server/services/build_jev_writer_selection.py`
- `apps/live_control_server/services/build_world_context.py`
- `apps/live_control_server/services/world_source_acquisition.py`
- `apps/live_control_server/services/agent_context_trace_collector.py`
- `apps/live_control_server/services/agent_context_trace_projection.py`
- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/api/liveApi.ts`
- `apps/live-control-ui/src/api/conversationWorkPlanApi.ts`
- `apps/live-control-ui/src/api/buddyContextTraceTypes.ts`
- `apps/live-control-ui/src/agentInteraction/authoredGraphReferences.ts`
- `apps/live-control-ui/src/agentInteraction/surfaceConversationRequests.ts`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/planSurface/components/DurableWorkPlan.tsx`
- `apps/live-control-ui/src/planSurface/components/BuddyContextTrace.tsx`
- `apps/live-control-ui/src/surface/SurfaceGraphReferenceInput.tsx`
- `apps/live-control-ui/src/surface/SurfaceGraphReferenceInput.css`
- `apps/live-control-ui/src/surface/workPlans/StagedWorkPlan.tsx`
- `apps/live-control-ui/src/surface/workPlans/SurfaceWorkPlan.tsx`
- `apps/live-control-ui/src/surface/workPlans/workPlanCapture.ts`
- `apps/live-control-ui/src/surface/workPlans/workPlanPlacement.ts`
- `apps/live-control-ui/src/surface/workPlans/WorkPlanHost.tsx`
- `apps/live-control-ui/src/buildSurface/reference/BuildReferenceCapability.tsx`
- `apps/live-control-ui/src/buildSurface/reference/BuildReferenceSearchProjection.tsx`
- `apps/live-control-ui/src/graphReference/GraphReferenceSearch.tsx`
- `tests/test_authored_graph_references.py`
- `tests/test_build_authored_references.py`
- `tests/test_build_world_context.py`
- `tests/test_agent_build_submitted_intent.py`
- `tests/test_reviewed_action_binding.py`
- `tests/test_build_turn_retry.py`
- `tests/test_conversation_work_plan_routes.py`
- `tests/application_state/test_authored_graph_references_postgres.py`
- `tests/application_state/test_reviewed_work_plan.py`
- `tests/application_state/test_turn_retry.py`
- `tests/test_build_proposal_shared_writer.py`
- `tests/test_build_writer_selection.py`
- `apps/live-control-ui/src/surface/SurfaceGraphReferenceInput.test.tsx`
- `apps/live-control-ui/src/agentInteraction/authoredGraphReferences.test.ts`
- `apps/live-control-ui/src/api/conversationWorkPlanApi.test.ts`
- `apps/live-control-ui/src/planSurface/components/DurableWorkPlan.test.tsx`
- `apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx`
- `apps/live-control-ui/src/surface/workPlans/StagedWorkPlan.test.tsx`
- `apps/live-control-ui/src/surface/workPlans/workPlanPlacement.test.ts`
- `apps/live-control-ui/src/buildSurface/reference/BuildReferenceCapability.test.tsx`
- `apps/live-control-ui/src/graphReference/GraphReferenceSearch.test.tsx`

Only amend this lease explicitly if inspection establishes another owning path; do not
edit an unlisted file merely because tests or TypeScript point at it. No user data,
retained source, native Graph schema or dependency changes are leased.


### Effective policy coverage (activation gate)

Cover all twelve currently supported closed-schema Build writer profiles that may
carry this input: BuildCollaborationPolicyV1/BuildCollaborationImagePolicyV1,
BuildConnectedPageReviewPolicyV1/BuildConnectedPageReviewImagePolicyV1,
BuildSourceQuotePolicyV1/BuildSourceQuoteImagePolicyV1,
BuildRelationshipReviewPolicyV1/BuildRelationshipReviewImagePolicyV1,
BuildIntentionalResponsePolicyV2/BuildIntentionalResponseImagePolicyV2,
BuildIntentionalResponseSourcePolicyV2/BuildIntentionalResponseSourceImagePolicyV2.
Use new explicit authored-reference policy variants selected from the actual effective
profile after capability resolution, not a marker added only to a base type. Each
retains its own source/draft/image/collaboration/quote/relationship/output authority.
The current initial four variants and reviewed-action profile must pass actual SDK/APP
producer/admission tests. Exercise all twelve new variants through exact writer input,
finite format and final reconstruction, with and without source bindings. Older
non-source-writer/unversioned execution profiles cannot gain authored input: reject it
before any provider authorization with a specific unsupported-profile error and keep
the request/reference. They remain historical readers, not fallback runtime paths.
No omitted reference may silently disappear during profile selection. Tests must show
old policy/event digests and validation semantics are unchanged when no new input is
present, and every effective new profile accepts only its exact frozen host-read lane.


### Owner extension found at the actual output forks

The discussion writer is not the only consumer: _proposal calls the existing
build_document_proposal.prepare_writer_request/compose_with_writer owner, and image
preparation uses build_image_writer.writer_request. Both must receive the same proved
host context and source bodies; a successful acquisition followed by omission here is
not completion. PRIME extends the expected lease to:
- `apps/live_control_server/services/build_document_proposal.py`
- `apps/live_control_server/services/build_image_writer.py`
- `tests/test_build_document_proposal.py`
- `tests/test_build_jev_image.py`

No new proposal or image executor is authorized. Extend their exact-input validation
and existing parent authorization, preserving one producing call and uncertainty.
This owner amendment requires independent critique before editing these added paths.


### Operator presentation steering retained for the next Surface slice

The operator requests a shared object toolbar with editable title, plus, green Save
and hamburger together, attached to the object and sticky during its scroll. Remove
the duplicate title field and separated bottom actions when that UI owner is changed.
The operator also permits an explicit page/conversation view toggle for the same
saved object. Page remains the default for generated objects; clarifying questions
remain inline. A view switch must preserve one durable object identity, edits and
execution state, without copying or executing a plan. This supersedes the earlier
unconditional page-only presentation rule. These controls are not implemented by the
reference backend work and must not be reported as delivered.
