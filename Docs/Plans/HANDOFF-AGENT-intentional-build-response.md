# Intentional Build response contract

## Authority and current lane

**Design amendment ACTIVE; runtime integration BLOCKED.** Operator scope is intentional
Discuss/Create routing, removal of `cannot_select`, useful clarification, and page-centered
connected authoring. This serial amendment uses the existing buddy-context-loop checkout,
branch `codex/intentional-response-contract-v2`, base
`f254e9bc8cc016175be4a0ef4db1606a349587b8`. Its exclusive write lease is this file.
No runtime, APP, migration, provider, database, corpus, service or UI write lease is active.
Independent exact-head Bugbot review precedes PRIME merge. No overlapping response-design
PR was open at activation; parked #1764 remains outside this slice.

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
