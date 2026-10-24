# Current working draft as authored discussion context

ACTIVE serial PRIME implementation, branch codex/build-working-draft-runtime,
base f7c3670e6335fa6e299bebf19cd83bc8120f47b9, existing buddy-context-loop checkout.
Adopts the independently Bugbot-reviewed design merged in #1689. One cumulative
implementation PR; incomplete commits remain draft and do not authorize deployment.
Fetched open lanes are disjoint. PRIME owns API8000/UI5202; preserve the deployed
df2f6fed8 API/UI and all retained APP/native/source/editor state until review/delivery.

## Observed problem and owning boundary
At this base the browser already captures draft_markdown and exact editor/draft
hashes in BuildWriteCapability. Proposal and image writers receive that draft.
Build discussion instead acquires ValidatedBuildSectionReadV1 from the saved source,
and build_primary_context.project exposes only those saved reads. A route selection
therefore sees selection text, but an ordinary discussion cannot reliably see newer
unsaved prose. Treating the draft as a saved section, dialogue pair or Graph receipt
would misrepresent its origin. Requiring a writable caret would also conflate reading
with editing permission.

Owning contract: the Surface editor supplies immutable authored context to Buddy;
APP freezes its identity and governs each provider exposure and resulting reference.
The Graph broker continues to own admitted World evidence. The document save owner
continues to own saved revisions. These authorities are separate.

## One capability / required behavior
Discuss the exact working page captured on Send, including unsaved edits, without
saving or publishing it and without acquiring the same page as older saved prose.
Keep requested writing on the existing reversible proposal path. A response refers
to its captured draft even if the author continues typing during generation.
A later turn captures the newer draft. The page remains editable throughout.

## Input contract
- Split read-only page context from optional insertion/replacement authority. Shared
  editor capture returns a context snapshot even when there is no writable target.
  Capture page/world identity, exact saved basis, complete Markdown, editor digest,
  Markdown digest and generation. Preserve selection independently for a proposal.
- Capture against one mounted editor and recheck its identity/generation after async
  hashing. Reject cross-page/cross-tab/capture races before dispatch. Conversation
  pointer fencing and existing request identity remain in force.
- The server validates Markdown digest and exact saved basis/World ownership. It must
  not equate the editor digest with a server-reconstructed document: the browser owns
  that editor snapshot. Never claim server verification of unsaved authorship.
- Freeze the complete context in a typed APP execution record before exposing text.
  Bind it to turn, conversation, saved basis and request fingerprint. Repeated same-ID
  admission uses exactly the same snapshot; explicit Retry captures current work as a
  new attempt under the existing retry identity rules. No implicit replay or save.
- No new arbitrary character/token cap. Count actual provider input against its real
  configured capacity. If it cannot fit, preserve the request and report the specific
  context obstacle; do not silently substitute saved prose or truncate the draft.

## Retrieval, model input and duplication
- Operation selection receives target kind plus context identity and a page label;
  routing is not a new full-page summarization call.
- Before current-page content judgment, materialize the already admitted draft once
  through its typed context lane. It requires no disk/Graph fetch or model call.
  Subsequent phase projections expose the body only when that phase needs it; IDs
  and exposure manifests retain continuity without repeating bodies unnecessarily.
- Current-page discussion uses the captured draft as primary authored context. Saved
  source discovery remains available for an explicit comparison with saved history;
  related World sources remain available when needed. Do not automatically acquire
  older saved sections merely because a current page exists.
- The writer gets the captured draft once, distinctly labelled as authored work in
  progress, plus selected source evidence. Deduplicate equivalent body exposure while
  retaining each distinct provenance binding; equality does not merge authority.
- Exact Debug captures retain the real complete prepared input and output, including
  rejection/failure. Provider usage remains actual reported usage or explicitly
  unavailable; estimated admission counts must not be presented as billed usage.

## Output and durable proof
- Add an explicit authored-draft reference variant rather than fabricating
  saved_source_claim, source_read IDs or Graph claims. Finite provider selectors refer
  only to the included draft record. APP independently validates the included record,
  producing envelope and selected reference before durable completion.
- Preserve useful discussion prose and clearly identified creative suggestions.
  Draft-only discussion is a valid authored-context answer, not an automatic missing
  evidence failure. World gaps qualify only the requested World claims. Mixed answers
  keep source citations tied to their actual passages and source names.
- User-facing prose need not repeat hashes, revisions or a generic 'not canonical'
  warning. Draft reference provenance is inspectable with context/Debug; it must never
  acquire the source citation icon or imply external evidence. Source citations keep
  their shared numbered presentation.
- Introduce the necessary current output/receipt variants explicitly across APP,
  server and shared conversation rendering. Historical stored completions remain
  readable with their original proof. Do not add a second live legacy execution path
  or rewrite historical records into the new authority.

## Consuming implementation boundaries / verification
Expected owners: shared editor capture/Build bridge; Build conversation registration,
request composer/API types; server AgentTurnRequest and Build Jev driver/harness;
APP execution/input-inclusion/output-validation types and source-writer owner; exact
Debug capture and shared answer rendering. Keep this one capability in one serial
implementation PR unless the steward explicitly splits an owning contract.

Tests must prove fresh unsaved text absent from the saved source reaches the actual
prepared writer once; second turn sees a newer draft; selection/caret/edit permission
does not hide readable context; no save/publication/Graph mutation; exact raw Debug
input; no saved-source citation for draft text; mixed source citations remain exact;
request/response tampering and stale pointers fail; in-flight typing survives; Retry
and uncertain outcomes do not replace newer work or duplicate exposure. Exercise the
real mocked transport and durable APP completion, not only projection helpers.

After independent Bugbot and exact cumulative review, PRIME merges and delivers
API/UI together to 5202. Recheck owned processes, active claims and all retained APP,
native, source and draft state. Old UI/API artifacts cannot interpret newly persisted
authority variants: once new records exist, recover forward rather than rolling back
blindly. Rehearse ordinary discussion → proposal → direct edit/Keep → save → reload
when live calls no longer compete with operator dogfood. That real acceptance remains
open; design review and offline tests do not prove the authoring journey.

## Implementation exclusive writes
This contract; Docs/Roadmaps/ROADMAP-demo.md;
src/application_state/agent_conversation/build_draft_context.py, build_draft_answer.py, types.py, service.py,
source_writer_output.py, build_primary_context.py, build_world_context.py and
rules_authority_build_input.py/rules_authority_output.py as required by exact carriers;
apps/live_control_server/models/agent_turn.py and build_document_proposal.py;
apps/live_control_server/services/agent_turn_service.py, build_jev_harness.py,
build_jev_driver.py, build_jev_writer.py, build_jev_writer_selection.py,
build_jev_transitions.py and build_jev_dispatch.py;
apps/live-control-ui/src/api/types.ts;
apps/live-control-ui/src/shared/sourcePassageProtocol.ts and its tests;
apps/live-control-ui/src/planSurface/components/BuildSourcePassageEvidence.test.tsx;
apps/live-control-ui/src/buildSurface/buildComposeBridge.ts and .test.ts;
apps/live-control-ui/src/planSurface/components/BuildComposeProposal.tsx,
WorldPlanAgentConversation.tsx, WorldPlanAgentAnswer.tsx and affected tests;
apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx;
apps/live-control-ui/src/buildSurface/BuildCompose.integration.test.tsx;
tests/test_build_draft_context.py, test_agent_build_jev_ordinary_harness.py,
test_build_jev_writer.py, test_build_jev_driver.py and test_agent_turn_service.py.
Inspection confirms agent_turn_graph_completion_check enumerates completion shapes:
this lease also owns src/application_state/migrations/versions/20261024_0061_build_draft_context_completion.py
and tests/test_build_draft_context.py migration/reopen coverage. APP0060→0061 admits
the new authored-context completion without rewriting rows. Downgrade refuses when
new records exist. Historical proof/read semantics remain intact. No live model probes while the operator writes. Exact independent
Bugbot, cumulative verification and protected delivery remain required.
