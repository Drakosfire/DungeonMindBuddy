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

### Final proposal/image reconstruction owner extension

Inspection found that APP completion/reload validates proposal and image owner records
in `src/application_state/agent_conversation/build_authoring.py`. Its current checks
join action, source, selection and producer identities but cannot independently prove
the new acquired-reference packet. PRIME extends the lease to that exact file, plus
`tests/test_build_proposal_shared_writer.py` (already listed), to validate the same
captured producing request and actual source receipts at completion/recovery. No new
publisher/executor is authorized. Independent critique precedes editing the added owner.

The final reconstruction mechanism is a new immutable APP authored-reference provider
inclusion event, defined and validated in the already leased `types.py` and
`authored_graph_references.py`, admitted through `service.py` from the exact validated
prepared request before its provider authorization. It binds capture event, reference-set
digest, exact authored source-read IDs/receipts, provider attempt and envelope digest.
Admission compares actual passage bytes/locators/names with the existing protected
source-read trace, retaining only digests/identities in the inclusion record. No second
source-body store is introduced. Proposal completion and prepared-proposal recovery
require that durable inclusion proof to match the acknowledged producing attempt and
envelope. Image completion additionally validates its existing retained request_json
against the same captured reference/source authority. New proof, omission/tampering,
recovery and old-profile counterexamples belong in the already leased
`tests/test_build_authored_references.py` and `tests/test_build_proposal_shared_writer.py`.

The next object-control slice also needs an explicit Move to Trash action with a
recoverable removed-object state and Restore. The current detached six-dot move
handle should join the object toolbar; retain drag scrolling and keyboard reordering.
The current World Trash supports document/session trash and restore, not emptying
or plan objects. An Empty Trash action needs an owned explicit lifecycle operation;
removing a page projection must preserve the plan identity, dispatches and historical
conversation evidence. No existing user object or Trash item was removed by this work.

### Mandatory context versus optional writer evidence

The real discussion probe found that `writer_evidence_selection.acquired_catalog`
currently catalogs every complete source event, while the acquisition driver knows
only its model-selected material. Authored host reads therefore break exact catalog
closure. PRIME extends the lease to
`src/application_state/agent_conversation/writer_evidence_selection.py`; its existing
runtime selector and `tests/test_build_writer_selection.py` are already leased.
Under the new authored policy only, whole source events required by authored reads
are mandatory writer context and excluded from optional source-unit voting. Runtime
and APP must derive that exclusion from the same admitted authored read events, not
caller lists. Preserve whole-event batch closure, overlap provenance and the final
union with actual Jev-selected reads. Do not emit a relevance vote or fake model
selection for mandatory inputs. Historical policies keep their exact catalog/state.
Independent critique precedes editing the newly named APP catalog owner.

Operator-priority serial interruption: after checkpointing the catalog correction,
keep #1785 in draft and suspend its overlapping UI write lease while the requested
Surface object-toolbar/step-minus slice uses this same checkout from origin/main.
Re-anchor and explicitly resume the Graph UI lease after that slice settles. No
Graph runtime adoption is authorized by this checkpoint; the overall goal stays active.


### Serial UI lease resumed after toolbar settlement

Toolbar #1786 is merged at f7afac0916d91aa864d8445d6eed977a84aab8ba and delivered
on5202 with API340cad98 unchanged. Independent review approved4802bee2290cd7dd373d0911c1734296ca70c5f2.
The attached move/title/plus/green Save/menu, pending-row minus, contrast and sticky
scroll proof complete that bounded lease. Its handoff is a delivered predecessor,
not a concurrent write lane. PRIME resumes this contract's exact overlapping UI lease
in the same serial checkout, merging current origin/main before edits. Preserve these
controls while adding root/step reference inputs. Whole-object Trash/restore, Empty
Trash and conversation projection toggle remain separate unimplemented scope.


### Picker binding provenance owner extension

The shared lens verifies the managed/native response, then currently discards its
binding version before exposing the projection. A picker cannot infer that version
from a label, selected World, or node. Extend the exact lease to:
- `apps/live-control-ui/src/graphLens/useWorldGraphLensProjection.ts`
- `apps/live-control-ui/src/graphLens/useWorldGraphLensProjection.test.tsx`

Expose the already verified managed/native/binding identity alongside the same loaded
projection, with the same request-key and refresh-generation admission. Return null
whenever projection bytes are unavailable or stale; native-only projections have no
managed authored-reference identity. Do not add a second fetch, change graph-lens
selection, reuse old bindings under new request keys, or manufacture a binding from
history. Shared Surface picker consumes this verified tuple and the exact selected
projection revision. Independent critique precedes edits to these added paths.

Independent critique requires explicit nullable fixture coverage, rather than an
optional field. Extend the picker binding lease also to these exact typed consumers:
- `apps/live-control-ui/src/buildSurface/reference/useBuildWorldGraphProjection.test.tsx`
- `apps/live-control-ui/src/planSurface/components/WorldPlanGraphReferenceActivation.test.tsx`
Set `managedBinding:null` on native-only/mocked projections; never manufacture a
managed tuple to satisfy typing. Real managed fixtures retain their verified tuple.


### Composer continuation/retry transport owners

The actual page host queues continuation outside WorkPlanHost.tsx, in BuildWorkPlanHost.
Retry readback currently omits the captured authored identities required by the existing
retry validator. Extend the exact lease to:
- `apps/live-control-ui/src/buildSurface/BuildWorkPlanHost.tsx`
- `apps/live-control-ui/src/buildSurface/BuildWorkPlanHost.test.tsx`
- `apps/live-control-ui/src/api/conversationRetryApi.ts`
- `apps/live-control-ui/src/api/conversationRetryApi.test.ts`
- `apps/live-control-ui/src/agentInteraction/surfaceConversationRequests.test.ts`

Carry only immutable DispatchV2.authored_references through the existing queued request;
request deduplication must compare that snapshot and must not import composer selections.
For retry readback, extend the already leased APP retry.py with a discriminated
RetryContextV2 row carrying the exact captured authored reference set. Its existing
batch/history owner remains unchanged; old rows remain historical readers. The same
closed UI decoder admits V2 only in its exact World/conversation/turn. Parent revision
and existing server fingerprint/capture validation still gate a retry; no new executor,
retry endpoint, table, optimistic recovery or inferred IDs. Keep all newer composer
references out of a retry. Capture the authored input before origin-snapshot membership
IO so a known pre-provider read failure cannot lose its input; capture is input retention,
not proof of membership, read completion or permission to write. Do not authorize any
provider after a failed membership read. Add boundary tests for that failure and retry
readback, including malformed/foreign reference packets. Independent critique precedes
edits to these added owners and the versioned retry-readback contract.

Independent critique adds the actual submitted-request/recovery test owner:
- `apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx`
Prove composer selection serialization and exact pending reload, queued DispatchV2
selection over unrelated composer inputs, retry from saved V2 context over newer
composer refs, and preservation of newer drafts. Queue/helper tests do not replace
this mounted conversation boundary. No additional production owner is needed.

### Rejected-request composer recovery fence

Interim review found that empty references can be a deliberate newer edit. Content
comparison cannot prove absence of an intervening edit. Version the local composer
reference copy to V2 with `submitted_turn_id: UUID|null`. Only the ordinary send owner
may mark the post-submit empty copy with its exact request ID, after the pending request
has been durably retained. Any author reference edit clears the marker, even when it
returns to an empty list; the first newer text edit also clears it. V1 local copies are
historical readers with no marker. A rejected request may restore its references only
while its exact marker still owns the current copy. Otherwise preserve the original
pending request and newer composer; never infer ownership from an empty list. No new
pending-request store, executor, API, reference count limit or provider authority.
Keep exact storage compare/write/readback and protect reload/ABA cases in the existing
leased helper and mounted conversation tests. Independent critique precedes this local
recovery contract correction.


The marker failure review adds a second necessary fence: automatic reference restoration
belongs only to the original ordinary submission call, while its component can observe
all edits. Recovered/exact-replayed requests never automatically write their references
into the current composer; retain both copies for explicit recovery instead. A failed
retirement is also remembered for that live request. Prove denied reference-copy writes,
text ABA, remount, exact replay and known rejection without replacing the empty newer
composer. This read-only recovery fence grants no resend or second executor authority.
The separate explicit no-lockout recovery UX remains required before adoption.


### Source-aware staged-plan recovery contract

Independent critique approved placement/notes V3 in existing owners. Use validated
getWorkPlanRecord: saved V3 roots (including empty) are exact author authority;
otherwise initialize from captured sourceReferences. Every V3 row has explicit
references; never infer IDs from writer labels. CAS/prepared immutability cover roots
and rows; retired snapshots preserve both. Historical notes restore wording/selection
by step_id without erasing V3 context. ReviewV3 and exact objective/root/row/revision
readback gate application and recovery. Do not reinterpret prepared V1/V2 receipts.
Extend the exact test lease to:
- `apps/live-control-ui/src/surface/workPlans/workPlanCapture.test.ts`
No new storage key, executor, provider authority or publisher is added.


### Rejected-request and malformed-composer recovery

Independent critique clears immutable local recovery receipts within the existing
conversation/helper/test owners. For authored ordinary Build requests, only existing
allowlisted known pre-dispatch rejection codes may retain exact original bytes in a
World/document/request-scoped receipt. Verify readback before CAS-clearing the matching
pending envelope. Crash recovery recognizes an exact retained receipt and finishes
cleanup without dispatch or duplicate items; changed bytes retain both and report a
conflict. Local receipts are informational, never cryptographic server refusal proof
or execution authority. Unknown outcomes stay pending. Preserve newer empty/ABA drafts.
Malformed composer-reference recovery is an explicit author action: retain exact raw
bytes in a scoped immutable receipt, verify, then replace only the unchanged malformed
copy with empty references. Do not change message text. Storage failure retains work.


### Typed authored-reference observations — owner extension

Independent critique clears one non-authoritative trace variant wrapping only the
four existing BuildAuthored capture/authorization/read/provider-inclusion event types.
Validate complete event equality (UUID/kind/sequence/all fields) against the exact
turn ledger on append and readback. Reject missing/foreign/altered/unknown events and
duplicate event IDs at different trace sequences; exact same-sequence replay stays
idempotent. Bind outer World/conversation/turn/attempt to the stored trace row. Capture
may predate trace start; membership, not execution_start_sequence, owns its validity.
Emit after APP append returns. Preserve committed APP authority on capture failure;
known trace admission/capacity failure marks incomplete, existing claim/transport
fencing still propagates. Observation is never rollback, evidence or action authority.
Label inclusion Prepared writer input; only provider lifecycle records transmission.
Read, partial and source gap stay distinct. Export exact metadata, no source bodies.
Extend the exact write lease to:
- `src/application_state/agent_conversation/context_trace.py`
- `src/application_state/agent_conversation/context_trace_store.py`
- `tests/test_agent_context_trace_types.py`
- `tests/application_state/test_agent_conversation_context_trace_postgres.py`
- `tests/test_agent_context_trace_collector.py`
- `apps/live-control-ui/src/planSurface/components/buddyTraceText.ts`
- `apps/live-control-ui/src/planSurface/components/BuddyContextTrace.test.tsx`
No new table, endpoint, source store, executor, arbitrary limit or historical policy.

The exhaustive live activity consumer also requires this independently cleared extension:
- `apps/live-control-ui/src/planSurface/components/BuddyActivity.tsx`
- `apps/live-control-ui/src/planSurface/components/BuddyActivity.test.tsx`
Use the existing exact turn inspection owner, unchanged ordering/dedup/polling. Selection
is unread, authorization does not mean read completion, partial/source gap are not
complete, and prepared input is not a provider arrival. Cover all four types and gaps.

Independent critique also requires authorization/read/inclusion observations to have
ledger sequences at or after execution_start_sequence on append and readback. Exact
same-turn membership cannot make earlier physical work current. Capture stays exempt.
A current inclusion may retain earlier immutable source provenance without replaying
the old activity. Same-turn reclaimed acquisition currently risks duplicate APP
authorization/read events; resolve and prove that execution-resume gate before adoption.

### Reviewed-step host-read admission correction

The real SDK/APP reproduction found an earlier guard defect: a reviewed insertion
with no auxiliary controller call cannot acquire its explicit authored object because
the shared broker requires a provider attempt. Independent critique clears an exact
host-authority exception within the existing service/authored owner lease. Parse and
normalize first; only the latest one-shot authored object authorization may replace
the provider prerequisite. Pagination remains provider gated. Source reads and large
native waves must independently prove fresh selected pins of that pending object;
settled overlapping source authorizations require exact receipt recovery, and orphan
source authorizations refuse as indeterminate. Preserve frozen scope, budgets, capture,
APP append validation and writer phase fences. No fake provider call or usage.

The independently cleared exact owner extension adds
`apps/live_control_server/services/build_related_pages.py` only for recognizing the
V2 reviewed-action subtype in the existing empty-catalog early return.

For reclaimed completed authored reads, recover exact reviewed-selection bindings
(including original broker identity), reconstitute the object through the existing
frozen native packet builder, and compare the original digest and all returned pins
before any ordinary mutation. Restore source bodies only by an exact protected
same-turn passage/authorization/receipt join. Populate existing maps, then re-run the
existing writer material validator. Do not append/replay selection/read/activity,
change session metadata or extend scope. Unsettled authorizations and unavailable or
changed bytes refuse precisely; provider-authorized turns remain non-reclaimable.
This independently critiqued correction uses the existing service/driver/authored
owners and tests, with no new store, event, executor or provider authority.

The same independently cleared empty-catalog V2 subtype correction also owns
`src/application_state/agent_conversation/build_related_pages.py` at project(): retain
empty catalog/no choices and recognize the reviewed-selection base class.

Independent critique clears a shared same-turn protected source inventory for runtime
preparation, APP inclusion admission and final reconstruction. Load typed traces with
exact row-attempt and World/conversation/turn binding; only original source-passages,
uniquely joined to immutable authorization/read receipts with exact scope, IDs, pin,
outcome, hash and length, may supply bodies. Reject duplicate IDs, wrong physical
ownership or altered/missing bytes. Prior activity remains in its original trace; no
new activity or source authority is created. The inventory uses existing trace rows.

The final generic provider-admission capture check has an independently critiqued
partition for the exact authored writer identity: require its existing attempt/envelope
inclusion witness, then validate only that witness's mandatory authored source IDs
against the shared protected inventory. All other included reads and all other policy
identities still require current-trace captures. No copied passage/activity or bypass
of generic provider scope/admission is permitted; failures abort atomically.

Provider-input trace materials use existing historical source references for exact
same-turn captures from earlier physical attempts, without copying source observations
or text. Independently critiqued collector/store correction requires same World,
conversation, turn and earlier attempt, exact source trace/event/read/digest, and an
existing current authored writer inclusion/authorization. Existing cross-turn behavior
and all non-authored read authority stay unchanged. The existing historical passage
inspector opens the original capture. Verify this through the restart proof.

The validated-answer snapshot may echo a same-turn historical reference only when
that exact reference already appeared in this attempt's preceding before/provider-input
snapshot; revalidate the original persisted source capture. Independent critique
clears this echo, preserving answer_context without permitting new historical inputs.

Repeated-loss recovery identifies the existing reviewed selection's actual prior
physical attempt from persisted trace start intervals, rather than assuming selection
and input capture occurred together. That provenance only verifies the original broker
identity salt; the exact immutable APP selection/intent/capability/arguments remain the
action authority. Missing/ambiguous provenance refuses; no new selection is appended.
Prove capture-loss, later read-loss and third-attempt completion.

### Bounded cumulative-review corrections

The operator stopped scope growth and requested merge readiness for #1785. Full
cumulative review at7347adcd4 held two defects. Independent critique clears only
these corrections: expected writer passages use the same sorted operation union and
shared-pin donor rule as reconstruction, validating every object's source membership
before deduplicating physical event/read identities; selected objects and their
immutable read provenance remain distinct. V3 step references are required, including
an explicit empty set; V1/V2 plan/review readers retain their historical shapes.
Verify shared-source proposal and image admission, altered/missing passage refusal,
and explicit V3 input versus legacy readback at their actual boundaries. This does
not authorize adding capabilities or bypassing the outstanding activation gates.

### Existing-scope merge-readiness proof

Pre-merge gates are actual native/APP boundary behavior, the twelve effective writer
profiles with empty and populated citation-binding maps, failure/recovery boundaries,
UI request/build evidence, and exact cumulative independent review. Protected adoption
uses the clean merged revision; ordinary live UI and creative acceptance follow that
adoption. These phase labels clarify ordering without waiving any required proof.

The profile proof exposed a draft-bundle integration defect: a required authored
inclusion sat between draft inclusion and provider authorization. Independent critique
permits that event only under the explicit authored policy and only for the exact
attempt/envelope bundle. Historical event reading is preserved; no old execution path,
automatic V3 default or compatibility fallback is added.

Actual native source refusal also exposed successful-read classification of failed
receipts. Independent critique requires exact pin/evidence/artifact/revision support
before marking read. Otherwise retain source_gap; only an unavailable receipt may lack
a revision, and it never supplies writer support. Ordinary initial semantic routing
still occurs once; the gap authorizes/sends no writer. Keep object partial coverage
separate from missing source support. The existing dedicated native fixture and pinned
migration code isolate native/APP databases and verify retained native rows unchanged.
