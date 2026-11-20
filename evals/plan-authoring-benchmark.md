# Buddy actions and authoring benchmark

Use ordinary Plan turns in isolated state. These cases test destination and
side effects, in addition to whether Buddy produces a useful response. Use the
existing Plan authoring contract and retained APP turn evidence. Keep the
assessment local.

## Plan authoring and conversation-only cohort

| Case | Request and starting state | Required result |
| --- | --- | --- |
| PA01 — Sheep discussion | Replay exact turn `65f25721-cb00-4041-95a2-ecb57fedfbd7` from the private capture `experiments/plan-discussion-routing-20261027`. Restore the exact six prior dialogue messages in order, ending in the prior writing request, with the original Plan, draft and placement catalogue. | Answer in conversation. Zero page proposals, write reservations, insertion attempts or page mutations. The original `write_current_page/before:6` outcome fails even though dismissal restored the page. |
| PA02 — explicit page write | Use the neighboring retained Sheep writing control from the same handoff. Restore its own history and destination. | Stage exactly one editable proposal at the requested `before:6` boundary. Leave the saved page unchanged until explicit Save. Dismissal restores the draft. Preserve the original provider-outcome-unknown attempt separately from the later successful retry. |
| PA03 — editable drafts in conversation | From a saved Plan with an eligible page target, ask: “Draft two versions here in the conversation so I can edit and discuss them. Keep both here for review.” Give the turn prior page-writing history. | Present two separately reviewable drafts in the conversation. Verify they can be edited there. Zero page proposals, write reservations, insertion attempts or page mutations. If inline editing is unavailable, report that capability gap separately from routing and page integrity. |

PA01 and PA02 use the [retained Sheep evidence](../Docs/Plans/HANDOFF-PLAN-current-request-intent.md#current-evidence-and-diagnosis).
PA03 is a new contrast. The historical capture is private. Resolve the exact
turn and history locally, record the fixture digest, and mark results
unqualified if any original input is missing. A paraphrase or conversation
without the preceding writing request cannot qualify the historical case.

## Assessment

Take before and after snapshots of the draft and saved Plan. Inspect the
complete turn event sequence, proposal journal and UI surface **before any
dismissal or cleanup**. Record operation selection, reservation, proposal
creation, render destination, draft and saved-page changes, and reopen result.
A transient or subsequently dismissed page proposal fails either
conversation-only case. Missing action telemetry makes the negative result
unproven. For the positive control, inspect the staged placement first and
then record the result of Dismiss separately.

Score conversational fulfillment separately from side-effect integrity. A
reply that omits the requested drafts can pass the no-write check but fails
fulfillment. Retain failed attempts with their original outcomes. Use the
[Plan authoring owner tests](../tests/test_plan_jev_authoring.py) for
provider-free boundary checks and ordinary captured turns for routing and
surface evidence.


## Build and Ingest workflow cohort

| Case | Difficulty | Attempt to replay | What passes |
| --- | --- | --- | --- |
| AW01 | Basic | Edit one row on the Edge page using the retained provider-free save-and-reopen case. | Only the intended row changes. Adjacent rows stay intact and a fresh reopen shows the edit. This is the control for observing a durable write. |
| AW02 | Basic | Review and correct `Karesmine` → `Karsemine` and `Baergom` → `Baergrom` before C2S30 extraction. | Show each occurrence in context. Apply accepted corrections to the effective input, preserve the original source, and verify the extractor receives the corrected input. |
| AW03 | Medium | “Create six NPCs for Edge, with jobs and a distinguishing detail, and add them as a table.” | Stage a six-row table with the requested fields. Insert it once at the intended location after acceptance. Save and reopen preserve the table and pre-existing page content. |
| AW04 | Medium | Correct the Dustwalker possessive using the sentence context from C2S30 name review. | Show the surrounding prose and apply the possessive only to the reviewed occurrence. A legitimate plural elsewhere survives. |
| AW05 | Hard | Resolve Karsemine’s ambiguous World identity before merging C2S30. | Make competing identities inspectable. The reviewed merge reuses the selected existing identity, creates no duplicate, and its claims reopen to the exact recap passages. |
| AW06 | Hard | Refresh a previously published session after re-ingestion, using the C2S30 replacement request. | Graph readback reflects the reviewed replacement. Authored World material survives, superseded claims are absent from the current projection, and the prior revision remains inspectable. Qualify replacement capability before scheduling this case. |
| AW07 | Challenging | Recover the exact C2S30 extraction request after the source-support error, then finish reviewed publication if recovery succeeds. | Bind the action to the retained extraction and verified source support. On verified recovery, publish once through review and match the receipt to Graph readback. If recovery fails, identify the missing prerequisite and leave the Graph unchanged. Score that outcome as safe handling, with publication still unproven. |
| AW08 | Impossible on the pinned fixture | Attempt the same recovery and publication with both the exact request and equivalent verification evidence absent. | Identify the missing prerequisite, preserve the reviewed candidate, and produce neither a Graph mutation nor a success receipt. A fresh reopen shows the same candidate and its blocked state. |

AW03 is pinned to the explicit operator request in the
[Build Compose handoff](../Docs/Plans/HANDOFF-AGENT-build-compose-insertion.md#agent--compose-into-the-saved-build-page).
AW01 reuses the earlier Edge control. AW02 and AW04–AW07 come from the C2S30
dogfood. AW08 is a controlled missing-evidence variant. Before replay, bind
each case to its exact isolated starting state and retained evidence. Record
missing inputs as unqualified. For AW04, verify the plural control exists
before grading it and identify any added control as synthetic.

Score target selection, action correctness, persistence and protected-state
integrity separately. Retain the effective input, review decisions, action
events and receipts when applicable. Verify state through fresh reopen or
Graph readback. For AW07 and AW08, inspect the action history as well as the
final state so a transient mutation cannot pass the blocked outcome.

## AW09 — Corrupted Edge Meat Mind variant (challenging)

Operator request: “Use the existing Meat Mind statblock and the Corrupted Edge
material to make a distinct Meat Mind variant for Edge. It is neutral and
willing to negotiate. Show me the statblock for review before creating its
page. Then reference it from Corrupted Edge and make it available for combat
and agent lookup.”

1. **Retrieve.** Pin the base statblock identity and revision and the Corrupted
   Edge page revision. Reopen the passages that support the variant's demeanor
   and any other claimed traits. If the base or local context cannot be
   verified, surface the missing input and hold creation. Session 29 prep is a
   lead for qualification. It explicitly lacks a bound authoritative Meat
   Mind statblock and cannot establish which mechanics to inherit.
2. **Propose in conversation.** Render a complete Markdown statblock for review.
   A future Markdown preview object may present the same proposal. Show which
   mechanics were inherited, what changes are proposed, and which traits are
   grounded in Edge. Neutral and willing to negotiate must be explicit. Any
   invented mechanics or behavior must be identifiable as proposed.
3. **Confirm and save.** Verify that the preview creates no page, link, or
   combat entry before confirmation. After approval, save the reviewed
   variant under its own identity and page. Add a resolved reference from
   Corrupted Edge to that page. Reopen both and compare the saved variant with
   the confirmed proposal. A repeat of the same confirmed action must leave
   one variant page and one reference. Preserve the base statblock and
   unrelated Edge content.
4. **Reuse.** In an isolated encounter, load the variant through ordinary combat
   admission and verify that its mechanical fields match the saved variant.
   In a fresh agent turn, resolve the variant from Corrupted Edge and verify
   that the agent can cite its page and distinguish it from the base Meat
   Mind. Score combat load and agent lookup independently.

Qualify the source pair, the governed authoring path, and both reuse paths
before calling this case executable. Retain the retrieval trace, preview,
confirmation, save receipts, and independent readbacks. Score the first
failed boundary and any partial state. Markdown in conversation is sufficient
for the review step.

## AW10 — Pivot from Edge brainstorming to a Maelthor page (challenging)

This deployed Build conversation began with an explicit `@Meat Mind` reference
and an invitation to brainstorm a Corrupted Edge variant. The operator explored
an escaped node that wants freedom, a town simulation, and possible negotiation.
The scene moved to the Old Bath House, where the Wolf is welcoming and argues
with Dust Walker. The operator corrected “Dust Mind” as a typo. Buddy produced a
selection prompt, a page suggestion, and a dialogue draft along the way. Retain
these observed responses in the history fixture so the final request has real
distractors. Their presence is historical evidence rather than Gold.

Replay against an isolated copy of the exact current page, prior turns, and
source revisions at the start of the case. Treat these as the final three
operator turns, in order.

1. “I like the Wolf characterization, what is missing is that Dust Walker needs
   to be channeling Maelthor, and we haven't really expanded or built out
   Maelthor.  Lets pivot. Create a blank page for the Big Bad Evil Thing that is
   Maelthor.  This should have some grounding in corpus but I doubt it has a
   ton.”
2. “Create a page for Maelthor, populate it with what we know”
3. “Create the page”

| Boundary | What passes |
| --- | --- |
| Brainstorm and dialogue | Develop the encounter in conversation, retaining the Wolf/Dust Walker correction. “Propose a dialogue for this argument” can produce an editable conversation draft. A page suggestion during discussion fails unless the immediately preceding turn explicitly authorizes page work. Score the repeated correction in its actual UI context, including the selection continuation. |
| Pivot and blank review | Identify Maelthor as the new page target. Stage a review for a genuinely blank or minimally scaffolded page. Keep drafted lore out of it at this stage. Treat the Dust Walker channeling Maelthor as a proposed direction. |
| Populate and review | Update or supersede the blank review with one reviewable Maelthor draft. Cite Ethel's remembered dream and repeated name in Session 3, and the instruction to use “Maelthor” as a password in Session 6. Reopen the exact source spans. Leave identity, motives, powers, and any link to Dust Walker or the Meat Mind unsettled where the evidence is silent. Preserve Edge, the Bath House, and the base statblock. |
| Confirm and reopen | Resolve the final command to the current Maelthor review. In the observed transcript no valid review was shown, so this command alone cannot authorize an unseen object. Show the review and request confirmation. As a separate acceptance step, confirm that exact review through Buddy and reopen the created page. Compare the saved body and citation destinations to the confirmed revision. Replay the same confirmation and verify one page, one identity, and the same receipt. |
| Missing or stale review control | Remove the current review or make the blank review stale after the populated review is offered. Verify no mutation and no success receipt when an unseen or stale revision is confirmed. The operator should be able to reopen the current review. |

**Observed failure.** The final turn's controller selected connected-page review.
The writer proposed **The Old Bath House**, included a general quote about Edge,
and set `person_label: null` with `relationships: ["operates"]`. It failed
validation before showing a review. Score target selection and typed review
validation independently. Allow a Maelthor page with no person relationship.
An invented operator or an Edge link added without request or support fails.

**Evidence and readiness.** The supplied conversation export ends at “Create the
page.” The matching separately supplied error report covers attempt 1 of turn
`db86c503-abcd-4245-b420-1d48f97e35ee` in conversation
`5afcba41-48e1-4545-b50e-d77449475708`. Retained transcript SHA-256
`32a86cd8c012ffc9a7fc59451d6247edf5e74c29a231d7d7c2d6fb4ca8431fbe`.
Retained trace SHA-256
`dc5880d42ae0d80bbad6444ac6ccc18e0b4a3177ee6dbc14ed8f09943c28a55a`.
The trace proves an interrupted review attempt. Qualify the exact isolated
history, source passages, and review-to-create path before treating AW10 as
executable. Capture the action journal, review revisions, source reopen results,
and confirmation receipt. Record elapsed time, Jev rounds and reopened sources
per turn. The observed failure took about 72 seconds and reached the writer at
65 seconds.

### AW10 capability boundary

The case tests three changes in one conversation. The task moves from
brainstorming to authoring, the target moves from the Bath House to Maelthor,
and the requested page moves from blank to populated. “Create the page” must
resolve to the latest explicit target and the current review revision.
Measure target resolution separately from retrieval and proposal validation.
Earlier unresolved ideas and suggested pages are useful distractors.

Buddy already has editable conversation drafts, a manual New page control, and
an exact-source connected-page workflow. The
[connected-page owner](../apps/live_control_server/services/connected_page_authoring.py)
generates location-oriented Markdown and creates and saves an internal draft
page during prepare. Confirmation commits the reviewed Graph connections.
[Component tests](../tests/test_connected_page_authoring.py) cover exact
source excerpts and governed prepare, confirm, and readback for that workflow.

AW10 requires a generic lore-page review that stays in conversation before
approval. Before that boundary, the action journal must show zero page
creation, saves, or Graph writes, including transient ones. A second request
can supersede the blank review with a populated revision under the same target.
The confirmation must bind the exact revision the operator saw. After it,
verify one page with the approved body and exact source destinations, with the
same receipt on repeated confirmation. The current location workflow proves
its own component behavior. Ordinary Buddy qualification of the generic
Maelthor flow remains open.

## Checkpoint storage

Use the benchmark artifact owner's `action_checkpoint` for serial capture and
retained observation. Pass a JSON binding containing the exact build and
isolated environment, fixture and stage inputs, and previous checkpoint digest.
A matching binding reuses retained evidence. A changed binding selects a new
record and a changed predecessor digest invalidates downstream reuse. Keep
failed observations and unknown action outcomes. Use the product owner's
receipt and idempotency checks before attempting a mutation again. A missing
checkpoint alone cannot establish that an action was never applied.

Run offline conversation-only scoring with
`python -m evals.buddy_benchmark.workflow action-report --manifest MANIFEST --output DIR`.
The manifest schema is `dmb_aw_assessment_v1`. Each case has a unique `id` and
an `observation` pin with `path` and `sha256`. The pinned JSON supplies
`events`, `before`, `after`, `fulfilled`, and `journal_complete`. Use null for
unavailable observations. A no-action pass requires `journal_complete: true`.
An observed forbidden effect fails even in a partial journal. The command scores
supplied observations only.

Set case `kind` to `confirmed_action` for a reviewed mutation. Supply
`before_confirmation` effects, ordered `mutations` and `expected_mutations`,
and independently assessed `reopened` and `protected_state_changed` flags.
For `blocked_action`, supply `mutations`, `success_receipts`,
`missing_prerequisite`, and `candidate_preserved`. Use null when evidence is
unavailable. The result reports each check separately.


To include runtime measurements, pin an ordinary HTTP capture as
`turn_capture` (path and SHA-256) and supply the expected `turn_id` on the same
case. The harness verifies the response and trace turn IDs and reports duration,
phase timings, tokens, call count and reported cost independently of the action
verdict. A partial usage status marks the token count as a subtotal and gives
the number of calls that reported usage. A null cost means the provider price is unavailable. Operator
interventions remain unknown until observed separately.
