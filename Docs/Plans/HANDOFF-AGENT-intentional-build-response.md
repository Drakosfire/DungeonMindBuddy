# Intentional Build response contract

## Authority and current lane

**Runtime integration delivered through #1772**, merge
c72a498349a520b7091892badfdf09d775bbfea8, independently reviewed at
6946e283a44ca0a66903be1c97e1a1fb18355493. The later typed-library delivery below
is the current paired API/UI8000/5202 checkpoint, APP0070/native0017. Protected delivery and ordinary synthetic writing, inline object-only
questions and page-plan Save/reload are retained privately. Current-build reload during
actual table generation resolved by Check saved request with one turn/attempt/writer and a
newer composer preserved. Genuine failed-generation retry and operator creative-chain
acceptance remain open. The prior runtime integration source lease is settled.

## Typed library readback — settled

Delivered through #1773, merge bdee447f6c1f6ae537e2b3cab9f9b8fde073d960,
independently reviewed at f5db9f2d0f72c42fad2982724943224a776a718e. The paired
API/UI use this revision, APP0070/native0017. Ordinary current and archived library
inspection preserves typed questions, page-object references and the newer composer.
The readback write lease is settled. Detailed protected-delivery and dogfood evidence
remains private; the library does not activate archived conversations or grant execution.

## Durable Build retry relationship — design approved; implementation BLOCKED

Independent Bugbot critique approved this design-only contract. The implementation
audit and activation gates below remain open.

The next bounded capability is one logical conversation item with durable, inspectable
retry history. An interrupted request currently retries as a new physical turn; the
client's transient retry origin is lost on reload. Proposal events can also break the
adjacent equal-question grouping. A terminal failed original can consequently retain a
live Retry control after its explicit successor succeeded. Do not fix this by comparing
question strings, hiding all failures or replaying the old provider authorization.

Design steward: PRIME. Existing buddy-context-loop checkout; serial topology, branch
`codex/durable-build-retry-contract`, base bdee447f6c1f6ae537e2b3cab9f9b8fde073d960.
No runtime write lease is activated by this document. #1764 remains parked. This design
PR is followed by one separately activated implementation PR after independent critique
and an exact owning-path audit. No new service, store, provider, port or orchestration.

### Contract

1. A deliberate ordinary Build retry names its exact predecessor durable turn ID and
   observed revision. The host captures the current page/draft/placement using existing
   owners. The exact normalized submitted intent binds the retry reference before
   provider authorization; replay with another reference is an idempotency conflict.
   Requests without a retry reference retain their historical fingerprints. Equal text
   alone never establishes a relationship. Do not backfill links into historical turns.
2. APP owns an immutable predecessor→successor edge, recorded atomically with successor
   acceptance under existing World pointer/conversation locks. Both endpoints must join
   the same verified World, active conversation, Build Surface and primary page ID; the
   question is unchanged. Page/draft revisions and insertion authority may be freshly
   captured. Never reuse the predecessor's placement capability. Reject self-links,
   cycles, foreign/stale/archived predecessors and a second child of the same predecessor.
   A retry of a failed successor links to that leaf, retaining the chain.
3. Eligibility is server-owned, not inferred from a visible error or complete trace
   capture. Only a terminal failed/interrupted leaf with no admitted completion and a
   known settled failure disposition may acquire a successor. Resolve uncertain provider
   or operation outcomes first. Existing successful/prepared/inserted objects, unresolved
   reservations and reviewed-plan continuation authority must not become replayable via
   this generic path. Audit actual Build operation effects before defining the predicate;
   a terminal turn alone is insufficient evidence. Reviewed steps retain their saved-plan
   Try step again owner. No automatic retry, reset of claims or new right to publish/save.
4. Preserve each physical turn, attempt, provider authorization/outcome, trace, proposal
   and receipt. The new successor has fresh execution identity and current context; it
   is another physical attempt of the same explicitly linked logical request. Matching
   network delivery of that accepted successor returns its exact receipt even if the
   active pointer/page later changed. Concurrent clicks/tabs must create at most one
   successor; the loser receives a recoverable conflict or the already accepted identity,
   never a second model dispatch. No provider call before durable acceptance.
5. Authenticated history and current/archived library reads expose server-validated retry
   lineage. Shared UI grouping follows those explicit edges through intervening proposal
   events and reload. Show the newest attempt once with inspectable previous attempts;
   only the eligible leaf exposes Retry. Keep each trace/citation attached to its actual
   physical turn. A repeated independent question remains a separate item. Preserve
   typed library results and existing source-page links. Historical unlinked failures
   remain readable without inventing ancestry.
6. Pagination must preserve logical identity: a boundary may not revive an ancestor's
   Retry button or render it as a new question. Retain bounded, explicit access to older
   attempt records when a chain crosses a history/library page boundary; no silent
   unbounded full-history fetch. Implementation must name the versioned projection and
   read owner for that continuation before activation.
7. Preserve pending-request reconciliation, newer composer text, selections, source
   revisions and Save ownership. A failed partial construction remains observation only.
   Keep actionable failure recovery accessible rather than collapsing the conversation
   solely because an incomplete preview was observed. This presentation change is limited
   to the failed/pending retry experience; no new layout or annotation capability.

### Owning-boundary audit required before activation

- AgentTurnRequest → normalized BuildGraphIntent → reconcile/accept path in
  `apps/live_control_server/models/agent_turn.py` and
  `apps/live_control_server/services/agent_turn_service.py`.
- `src/application_state/agent_conversation/{types,service,repository}.py`: immutable
  submitted-intent fingerprint, APP acceptance/CAS, terminal/outcome validation and
  exact-receipt replay. Prefer an APP relationship table with a unique predecessor over
  rewriting lifecycle history. Name migration0071 and its database-level ownership,
  uniqueness and immutability constraints after auditing the current migration tip.
- History projection in `apps/live_control_server/routes/agent.py` and its models;
  `src/application_state/agent_conversation/library.py`; their UI decoders in
  `apps/live-control-ui/src/api/`. Name exact projection versions and bounded lineage
  pagination; do not introduce alternate execution paths for old records.
- Shared `agentInteraction/conversationAttemptGroups.ts`, ConversationLibrary and
  `planSurface/components/WorldPlanAgentConversation.tsx`: retry submission, durable
  grouping, ancestor controls, newer composer and failure/preview presentation.
- Existing boundary tests for APP acceptance, agent request/history routes, library,
  retry grouping and Build conversation integration. Audit inherited failures separately.

### Required proof

Real PostgreSQL acceptance and concurrent-tab races; changed predecessor under the same
idempotency key; accepted receipt replay after pointer/page change; foreign/archived,
completed, unknown-outcome, already-retried and reviewed-step rejection; chain retry;
identical independent questions; intervening proposal events; current/archived pagination
across an attempt chain; no read mutation; strict projection decoding; newer composer and
current placement after reload. Confirm provider dispatch occurs once per accepted
physical attempt and one successful Save writes one result.

After exact cumulative independent Bugbot review, PRIME merge and protected paired
8000/5202 adoption, repeat ordinary controlled failure→Retry→edit→one Save→reload and
library inspection. Label injected failure honestly; it is not a spontaneous provider
failure. Preserve all retained state and remove any private hook afterward. No synthetic
proof substitutes for creative-chain/operator acceptance. Keep detailed runtime/story
traces private; PRs contain contract/code scope only.

This amendment supersedes the prospective output-only routing and host-singleton design
below its predecessor ref. The earlier implementation is retained history, not an alternate
runtime to activate. Predecessors: #1762 design, #1763 proof/registry merged at
81db52ec92b574207016eda913bcab4b2e12a366, reviewed at
79da3cebdf54361280e419d96d7fa8b4d41c6468. The registry has no runtime caller.
Existing frozen controls/results and separate operator adjudication remain immutable.
Neither narrow routing scores nor this design authorizes adoption.

## Owning invariant

A valid utterance must receive an intentional supported response while preserving what
was requested. Understanding a request to create an encounter does not mean the current
Surface can execute it. Selecting conversation to explain that boundary does not turn the
request into discussion or authorize substitute encounter prose.

Keep four things separate:

1. **Requested work:** what the user wants now, including Discuss versus Create.
2. **Offered capabilities:** what this captured request can actually prepare or execute.
3. **Resolved response:** the supported operation and exact barrier, if any.
4. **Evidence:** what supplied authored/source material supports; unavailable execution is
   not missing factual evidence, and an unanswered creative choice is neither.

The existing driver offers `cannot_select` and then rejects it. That is not a clarification
workflow. The current draft-answer validator also derives `insufficient_evidence` for
unattributed discussion and requires an evidence qualification. A plain acknowledgment or
capability explanation must not need an invented source gap, a suggestion label, or an
irrelevant page citation to pass validation. Fix these contracts rather than padding prose.

## One semantic decision, then host capability resolution

For an ordinary free-form Build turn, use one real Jev semantic choice, provisionally
`requested_work`, in the existing initial controller call. Do not ask Jev to pick an
executable operation from the offered capability subset. The requested-work menu describes
user intentions, including intentions that this Surface cannot execute. It does not grant
capability. Use one closed registry for definitions, intent family and host resolution.

The proposed proof vocabulary is:

| Requested work | Intent family | Meaning |
| --- | --- | --- |
| discuss | Discuss | Answer, retrieve, compare or explicitly discuss first. |
| clarify_request | Discuss | The immediate request/reference needs an author choice before useful work. |
| plan | Create | Prepare an editable plan/checklist for author selection, not execution. |
| write_current_page | Create | Concrete current-page prose, list, table or revision. |
| prepare_image | Create | Prepare the supported image-prompt review. |
| review_connected_page | Create | Prepare a separately enabled connected-page review. |
| review_relationship | Create | Prepare a separately enabled saved-page relationship review. |
| change_mechanics | Create | Create/change/save a mechanics version, not prose about one. |
| build_encounter | Create | Compose a runnable encounter/combatant roster, not encounter prose. |
| place_map_coordinates | Create | Attach coordinates/pin to a map object. |
| save_page | Create | Commit page changes, not generate writing. |
| publish_relationships | Create | Publish Graph relationships, not prepare their review. |
| other_creation | Create | A concrete creation/action outside the closed supported work kinds. |
| clarify_creation | Create | Creation is requested but the artifact or target is unresolved. |

This vocabulary is a **proof candidate**, not adopted runtime authority. Freeze descriptions,
resolution rules and new holdouts before inference. The immediate meaning wins: an explicit
request for encounter *prose* is `write_current_page`; an actual runnable encounter is
`build_encounter`. Concrete name/insect/economy proposals follow the operator's answered
preference for editable page suggestions; explicit discuss-first remains discussion.
History resolves references, never supplies current instructions or played facts.
Intent and presentation destination are separate dimensions: discussion could be page-anchored
feedback if such a capability were offered. This proof does not add annotation objects or
threads, and it must not claim they exist. Operator feedback about that possibility does not
choose either writing or chat as new benchmark gold for an ambiguous utterance.

The host resolves the admitted semantic result against the exact captured capabilities:

- `discuss`, `clarify_request`, `clarify_creation`: `answer_from_sources`; clarification uses
  the existing typed questions object where a substantive author choice is needed.
- `plan`: `answer_from_sources` produces the existing typed plan, which the shared host
  stages on the Surface after validation. If that object/placement capability is unavailable,
  explain that exact barrier; do not emit a copied Markdown checklist in chat.
- `write_current_page`: `propose_build_insertion` only with its exact editor capability.
- `prepare_image`: `prepare_build_image` only with its actual image capability and existing
  probability threshold. Apply that threshold to the actual semantic image selection;
  never fabricate probabilities for the host-resolved operation.
- `review_connected_page` and `review_relationship`: `answer_from_sources` only with the
  matching typed review policy; obtain required saved-page evidence before constructing
  the review. Unread, failed acquisition and unsupported review are distinct barriers.
- A missing capability, `other_creation`, and currently unavailable mechanics/encounter/
  coordinates/Save/publication actions resolve to `answer_from_sources` with a host-derived
  capability barrier. Preserve requested work. Do not substitute prose or claim execution.

This is a pure finite resolution table, not a keyword classifier, extra planning loop,
second publisher, or new executor. Resolve only among the existing three executable
operations. A genuinely ambiguous request receives useful clarification, never a terminal
pseudo-operation. Malformed, tied, foreign, nonfinite or otherwise invalid provider output
still fails closed with an actionable trace; it is not silently treated as clarification.

Independent Rules/read choices remain real questions in that same call where currently
required. Preserve their actual responses, provenance and later acquisition. Do not invent
read votes or skip a required decision because the resolved output is conversation.
Reviewed-step continuations preserve the author's admitted action without another semantic
classification; they retain their existing selection, dispatch and recovery owners.

## No singleton executor fiction

The semantic menu has multiple genuine possible user intentions even when the only offered
executable operation is conversation. Thus it is valid for the installed SDK, and a real
initial semantic controller request/response remains available for admission/accounting.
This supersedes the unimplemented `BuildOnlyAvailableActionSelectionV1` and host-only initial
admission-manifest proposal. Do not implement either, add fake executable alternatives,
or reuse reviewed-author admission for an ordinary utterance.

There is no additional routing call relative to the ordinary multi-operation path. The
no-editor case now also makes one truthful semantic call; do not claim zero calls/usage for
it. Missing editor capability changes resolution, not the semantic question's meaning.
The original reviewed-author admission path remains only for actual reviewed actions.

## Durable resolution and writer authority

A new versioned policy, provisionally `build_intentional_response_v2`, must bind the exact
semantic menu, intent-family map, resolution table and host-derived capability projection.
Use a new immutable selection event, provisionally `BuildRequestedWorkResolutionV1`, for
this policy. It records the actual requested-work label/family, controller attempt/envelope/
response commitments, machine request identity, capability/menu/resolver digests, resolved
existing operation, response mode/barrier, broker identity and argument commitment.

APP recomputes equality from the frozen admitted request, actual validated semantic answer
and captured capabilities. It rejects foreign/missing/duplicate selections, changed menus,
resolvers, capabilities, semantic answers, operation arguments and role/order joins. Record
one applicable proof per turn: real requested-work resolution, historical operation
selection, or an actually reviewed author selection. Historical events remain readable but
do not grant new-policy authority. Do not rewrite an actual provider response into a fake
`operation` selection or fabricate operation scores, author choice or provider usage.

Existing first-provider envelope freeze, accounting, continuation ancestry and usage remain
bound to the real initial semantic call. Extend their validation for the exact new policy
without bypassing them. No new host-first-provider exception is needed. A required persisted
schema migration must be named and reviewed before runtime lease activation; no broad APP
or migration permission follows from this design.

The actual writer input receives host-derived fields distinguishing:

- requested work and intent family;
- current resolved operation and response purpose (fulfill, clarify, or explain capability);
- exact available output/review capabilities and the current barrier;
- supported deliberate follow-up actions, separately from this reply's operation.

The writer can discuss a future insertion when insertion is offered even though the current
reply is conversational. It cannot infer a map editor, coordinate picker, external executor
or publication workflow from a requested action or a generic return-to-editor instruction.
A missing *current-page writing target* may offer recapture/retry through the existing page
editor; it never implies map-coordinate or mechanics execution. Available follow-ups must
come from an owned host capability, not model invention. These fields are descriptions,
not tools, saved state or authority to execute the proposed next action.

## Neutral conversational output

Add a versioned writer output/completion contract under the new policy, provisionally
`build_intentional_response_answer_v1` and
`dmb_build_intentional_response_completion_v1`. It supports `discussion` status for pure
acknowledgments, author-choice clarification and capability explanations with no authored
or source claims and no evidence limitations. It does not relabel these as creative ideas.
Questions stay inline in chat; a generated typed plan remains the shared Surface object.
A valid typed collaboration object may be the entire response, without a filler acknowledgment.
The new format/completion may therefore carry no prose segments only when the admitted typed
object is present and valid; an entirely empty response still fails. Do not duplicate a question
in both prose and its interactive object. Historical formats retain their original constraints.

Derive status from typed output, not the model's preferred enum:

- Draft/related-page claims retain authored grounding and existing provenance checks.
- Saved/opened-source claims retain source grounding, exact quotes/citations and existing
  required retrieval qualifications.
- Actual creative suggestions retain their creative-proposal meaning.
- Pure non-factual discussion with no evidence limitation uses `discussion`.
- A genuine factual evidence gap retains `insufficient_evidence` and its exact qualification.

Keep factual source claims out of discussion/suggestion segments by instruction and existing
claim/citation validation. New discussion status grants no evidence authority, relationship,
page or Graph mutation. It is not permission to hide factual assertions in uncited prose.
Do not weaken exact requested-detail phrase matching: gaps must quote a unique literal
substring of the current question. A requested action or creative choice does not itself
require such a gap. Neutral output must pass without padding it with unrelated facts.

Bind the new writer format, status derivation and completion through its producing policy,
prepared envelope and existing APP writer-admission checks. Old formats, envelopes,
completed history and uncertain outcomes retain their exact identities and validation;
new discussion status must not broaden an old frozen format. Use the same execution owners,
not a compatibility executor or a second response transport.

## Activation and acceptance gates

1. Independently approve this exact design before activating owner paths. A proof-only
   successor may enumerate registry/eval/test writes without runtime authority. Freeze the
   proposed semantic menu and writer contract, historical controls, operator-adjudicated
   destinations and fresh holdouts before provider calls. Keep private captures, exact
   story/trace data, detailed usage and local test evidence private.
2. Prove requested-work selection **and** host resolution **and** actual useful writer output.
   Include acknowledgments, discuss-first, creative names/insects/economics, selected-range
   revision, ambiguous reference, typed questions/plan, connected-page and relationship
   review, unavailable mechanics/encounter/map/Save/publication, absent editor, Rules and
   media. Report routing errors, image admission, output-validation failures and semantic
   failures separately. A schema-valid output is not automatically useful or correct.
3. Before runtime activation, enumerate the exclusive owner paths after inspecting actual
   driver/SDK conversion, APP request/selection/ledger and completion unions, first-envelope
   freeze, writer projection/validation, UI completion decoding and affected tests. Expected
   owners include build_action_registry, build_jev_driver/transitions/harness/dispatch/writer,
   narrow agent_turn_service projections, APP types/selection/writer/status validators and
   completion consumers. Name any necessary migration explicitly. No broad lease is granted.
4. At those boundaries prove exact real semantic-response joins, deterministic capability
   resolution, no fake operation scores/usage, singleton-editor absence without singleton
   SDK questions, preserved actual Rules/read decisions, reviewed-author binding, changed
   capability rejection, old history/uncertain recovery, and neutral discussion accepted
   without invented limitations or unrelated facts. Pure discussion cannot carry source
   claims. Unsupported actions produce no page/Graph writes and promise no invented tools.
5. Exact cumulative Bugbot approval, PRIME merge and protected paired delivery precede
   ordinary controls proof: actual free-form writing stages correctly, edit/one Save/reload;
   clarification inline and plan on Surface; one failed-generation retry without duplicate
   turns/writes or lost newer composer text. Preserve shared Surface construction/placement,
   retained sources, drafts, histories and session state. Do not resend uncertain outcomes.

## Completion and exclusions

This capability is intentional response to valid Build requests, including useful handling
of requests whose execution is unavailable. It does not make those actions executable.
Actual connected-authoring dogfood and operator acceptance still precede the wider goal.
Noll's proposed selection remains pending; do not infer approval or re-ask. Preserve existing
creative decisions and do not invent played events.

Shared construction and Surface plan delivery from #1765/#1767/#1768 remain delivered
foundations; real typed-plan row streaming and continuation acceptance remain open. Settle
current delivery/roadmap anchors with the consuming implementation, not a status-only PR.
Hosted, richer combat automation, canvas/map authoring and full-stop orchestration remain
separately selected scope. No service rollout is required for this design or proof alone.


## Inspected integration contract and prospective exclusive lease

This section pins the owner boundary at base
`5374f664c2aa2bc7fdc5b7f9977aeac67202814d`. It is a consuming design artifact, not a
completion report. After independent approval and PRIME merge, the designing steward may
activate the following **single serial integration slice** from the resulting remote tip.
Record that pinned activation in the consuming implementation; do not dispatch against an
unreviewed design. Any extra owner path or contract requires explicit steward amendment.

### Runtime and APP ownership

| Exclusive path(s) | Permitted change / invariant |
| --- | --- |
| `src/application_state/agent_conversation/build_intentional_response.py` (new) | Single closed runtime semantic vocabulary, capability projection, resolver, commitments, selection proof validation and neutral response normalization/schema helpers. No imports from evals or server/UI. |
| `src/application_state/agent_conversation/types.py` | New policy variants, immutable event, completion and closed unions; ledger ordering, first-provider binding, result/readback/completion checks. Historical types keep their exact fields and behavior. |
| `src/application_state/agent_conversation/service.py` | Fenced APP selection append with transient exact request/response proof and captured-trace verification, plus narrow new completion admission. Reviewed bindings reject semantic reselection. |
| `src/application_state/agent_conversation/source_writer_output.py`, `build_draft_answer.py` | New-policy format dispatch and independent completion reconstruction. Preserve finite claims, exact quotes, literal requested-detail gaps and old normalization unchanged. |
| `src/application_state/agent_conversation/build_authoring.py` | Existing proposal/image owner verification accepts exactly the applicable new selection event and preserves arguments, capability and broker joins. No second proposal/image owner. |
| `src/application_state/agent_conversation/work_plan.py` | Permit a valid new completion containing only a typed plan to seed the existing plan owner; preserve its exact empty text digest and structured completion. No fabricated acknowledgment or additional dispatcher. |
| `src/application_state/migrations/versions/20261025_0070_intentional_build_response.py` (new; re-anchor number if occupied) | Append new completion admission and narrowly allow an object-only completed reply in the lifecycle constraint. Preserve old predicates and retained rows; guard downgrade. |
| `apps/live_control_server/services/build_jev_driver.py` | Initial real semantic question, actual SDK answer validation, exact APP proof append, derived operation, relevant writer projection and object-aware new-format history. Preserve reviewed-author action and actual read/Rules votes. |
| `apps/live_control_server/services/build_jev_harness.py`, `build_jev_writer.py` | Trusted capability/policy construction, new writer format and neutral/object-only result delivery through existing owners. No fake usage or extra classification call. |
| `apps/live_control_server/services/agent_turn_service.py` | Narrow policy construction/budget equality, completion projection and binding to new output; preserve receipt/envelope/recovery fences. No unrelated service rewrite. |
| `apps/live_control_server/services/build_related_pages.py` | Steward amendment discovered by the actual migrated citation-open test: `open_page` admits only the old draft-completion class. Extend that exact completed-answer guard to the new completion while preserving World/turn/read-ID, original acquired-body, and claim membership checks. No discovery/materialization or additional read authority change. Independent Bugbot amendment review approved this guard-only extension before the path was edited; full cumulative implementation review remains required. |
| `apps/live_control_server/models/agent_turn.py` | Add the new closed completion to Build response decoding. |
| `apps/live-control-ui/src/api/types.ts`, `shared/sourcePassageProtocol.ts` | Closed new completion/status decoding, optional prose only with a valid supported typed object. No widening old formats. |
| `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`, `BuildSourcePassageEvidence.tsx` | Render new completion/citations and typed questions/plans through existing presentation and Surface placement owners; preserve empty-prose objects, pagination, turn joins and composer focus. |
| `Docs/Plans/HANDOFF-AGENT-intentional-build-response.md` | Settle the predecessor and record the exact consuming activation, constraints and next acceptance gate. |

Proof-only `evals/utterance_intent/semantic_contract.py` and the earlier
`apps/live_control_server/services/build_action_registry.py` remain frozen controls, not runtime
imports or alternate executors. The new APP-owned module is the sole prospective runtime
registry. Existing transitions/SDK conversion/dispatch/accounting carriers remain unchanged:
inspection found generic named choice conversion; changing `operation` to `requested_work`
does not require a new SDK request or carrier schema. If integration demonstrates otherwise,
return for a bounded lease amendment rather than editing those owners implicitly.

### Policy, capabilities and selection proof

Use marker `intentional_response_policy="build_intentional_response_v2"` plus exact menu,
resolver and capability commitments in new closed policy variants. Two axes are real:
working-draft capture present/absent and image capability offered/absent. Extend the matching
existing bases (`BuildRelationshipReviewPolicyV1` / image variant with a draft;
`BuildNamedWorldContextPolicyV1` / image variant without a draft). The new required marker
and closed fields distinguish these union members; keep the existing `driver_schema` carrier
identity and do not invent an `execution_driver` field. Do not add default fields to old policy
models or change historical serialized hashes. No-draft variants do not manufacture draft,
related-page, quote or relationship-review authority. They can support neutral discussion
and typed questions; other review kinds require their actual existing policy and destination.

The host projects offered operations from frozen policy, reviews from their exact admitted
policies, plan destination from the captured shared Surface capability and manual controls
only when host-backed. Unknown/unacquired is not false/unavailable. Do not infer a manual
map editor or an agent Save from page-writing capability. Preserve the proof's relevant
follow-up filtering and separate saved-content acquisition inventory. An absent editor changes
resolution, never the requested-work question or number of its genuine semantic options.

`BuildRequestedWorkResolutionV1` stores actual controller attempt/envelope/response digests,
machine request ID, semantic label/family, exact menu/resolver/capability commitments,
resolved operation, purpose/barrier, broker ID and argument digest. At the fenced append,
APP receives transient `request_json` and `response_json`. Verify their exact raw hashes,
unique-key strict JSON/SDK response shape, model identity, actual unique-max probability vector
and original semantic question; recompute resolution, broker identity and tool arguments.
Compare the request and response with the matching captured provider observation in
`agent.turn_context_trace`, following the existing related-page proof pattern. A caller-supplied
digest alone is insufficient. Reject missing captures or mismatches before acquisition or writer
authorization; do not synthesize scores for the resolved operation. Persist the event, not a
second free-standing execution receipt or parallel provider history.

Ledger validation independently enforces exactly one applicable selection kind per turn;
old Jev action events cannot authorize a new semantic-policy turn, and a semantic event cannot
authorize an old policy. Actual reviewed-author selections remain valid under their separately
bound intent and cannot coexist with a model action selection. Bind semantic selection after
its acknowledged controller and before acquisitions/writer; related-page/Rules auxiliary
selections from the same real response remain independent and retain their existing joins.
The real initial semantic call retains the existing first-envelope/accounting equality; do not
add a host-first-provider exception. Image admission uses the selected semantic image score
with the existing threshold and only when resolution actually offers image preparation.

### Completion, empty prose and persistence

The new `dmb_build_intentional_response_completion_v1` is a separate closed completion rather
than a subclass that accidentally inherits a required draft. Its host-derived basis describes
actual admitted material: `working_draft_context`, `saved_source`, `saved_source_and_opened_passages`,
`opened_source_passages`, or `conversation` for neutral output without factual claims.
Steward amendment from the actual saved-only Rules flow: retain `saved_source` when no
opened passage is used; do not label that reply as passage-backed. The other basis values
remain distinct. This field amendment receives the same cumulative independent review as the
implementation before merge.
Neutral acknowledgments/capability explanations use `discussion`; genuine limitations and
creative suggestions retain their distinct statuses. Source/draft/related factual segments
retain all existing provenance, selector and citation checks. Do not claim an arbitrary-prose
fact classifier exists: schema validation alone cannot establish semantic truthfulness.

The new format supports optional admitted collaboration. `answer_segments=[]` is valid only
with a nonempty valid supported typed object and no factual citations. `assistant_text` is
then exactly the empty segment join, not null or invented filler. Enforce this same exception
in `TurnResult`, persisted Turn/readback validation, the database lifecycle constraint, API and
UI. The inspected baseline migration0010 has an unnamed lifecycle CHECK that currently requires
`btrim(assistant_text)<>''` for every completion. The new migration must identify that one
installed constraint by its verified definition/catalog identity, replace it with an explicitly
named equivalent plus the narrow new-completion exception, and abort on an unexpected shape.
Do not guess its PostgreSQL-generated name or weaken accepted/running/failed/interrupted
conditions. Add a new completion branch to `agent_turn_graph_completion_check`; keep historical
branches unchanged and SQL NULL fail-closed. Require exact new policy/basis/status/typed shape,
closed fields and a valid nonempty object for the empty-text exception. No retained row rewrite.

Downgrade locks affected state and refuses if new policies/events/completions exist (including
interrupted attempts), rather than abandoning them or lying about readiness for older code.
Guard source-policy cases without a working-draft capture as well as object-only completions.
Exercise installed constraints and actual completed-turn insert/readback on disposable Postgres;
an evaluated SQL fragment or Pydantic-only test is not the owning-boundary proof.

New completion decoding must preserve inline citation indexes, questions in conversation and
plans on the Surface. The existing work-plan `_source` rejects empty assistant text, so it needs
the same exact new-object exception, with the original text digest kept intact. No completion
may be dropped from history merely because prose is empty: project its actual typed object as
reference data in new-format controller history, preserving turn identity and content commitment.
Do not render the object twice, replace it with a generic acknowledgment, treat a preview as
executable or change existing explicit continuation admission.

### Verification and rollout gates

Permitted test writes (exclusive): new
`tests/test_build_intentional_response.py`,
`tests/application_state/test_build_intentional_response_postgres.py`, and focused extensions to
`tests/test_agent_build_jev_driver_decisions.py`, `tests/test_agent_build_jev_ordinary_harness.py`,
`tests/test_build_jev_initial_accounting.py`, `tests/test_build_jev_image.py`,
`tests/test_build_draft_context.py`, `tests/test_build_writer_selector_schema.py`,
`tests/test_build_related_pages.py`, `tests/test_rules_build_parent.py` (independently approved steward amendment: scripted semantic answers and versioned typed base-output shape only; no weaker assertions), `tests/application_state/test_reviewed_work_plan.py`,
`apps/live-control-ui/src/planSurface/components/BuildSourcePassageEvidence.test.tsx`, and
`apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx`.

Prove the actual driver→APP→writer→completion path, not only pure resolver helpers:

- Exact SDK call and truthful accounting with and without editor/draft/image capability;
  real read/Rules votes preserved; old/reviewed paths retain authority and recovery semantics.
- APP rejects changed request/response, foreign provider/attempt, duplicate/tied/nonfinite
  votes, changed resolver/capabilities/arguments, mixed selection kinds, wrong sequence and
  completion/operation mismatch. Valid neutral and object-only results survive DB readback.
- New neutral output passes without invented limitations or unrelated facts; old format still
  rejects the same newly permitted shape. Empty total output, factual references under neutral
  status, invalid typed objects and unattested exact quotes fail. No-draft neutral must exercise
  a genuinely absent draft packet, not just a synthetic capability flag.
- Real inline questions, Surface plan staging, citations and empty-prose history remain usable
  through ordinary decoding. Reviewed plan continuation stays one explicit action.
- Retain frozen provider proof and inspect actual writing scope/relationship drift/magical
  specificity in live acceptance. No favorable-only inference rerun substitutes for it.

After exact cumulative independent Bugbot approval and PRIME merge, re-anchor the protected
API/UI lease and actual processes, snapshot retained state, migrate and deliver the matched
runtime/UI revision using established ports8000/5202 and rollback protections. Then ordinary
synthetic controls must prove free-form writing→placement→edit→one Save→reload; questions inline;
plan on page; one genuine failed-generation retry preserving newer composer and no duplicate
turns/writes; historical/uncertain recovery. Keep Brin’s actual creative state untouched until
its existing pending choice. Operator creative-chain acceptance remains required afterward.
No code, migration or deployment is accomplished by this design approval itself.
