# Buddy actions and authoring benchmark

Use ordinary Plan turns in isolated state. These cases test destination and
side effects, in addition to whether Buddy produces a useful response. Use the
existing Plan authoring contract and retained APP turn evidence. Keep the
assessment local.

## Action catalog

| Action | Strongest verified boundary | Remaining proof |
| --- | --- | --- |
| Discuss, clarify, or brainstorm in chat | The opening Meat Mind dogfood produced a grounded reply with excessive retrieval. PA01 retains a Sheep discussion where Buddy offered an unsolicited insertion after prior page writing. A default-off guest Plan discussion slice exercises a real guest session, copied synthetic World, selected Graph object and source, sourced answer and citation with synthetic provider transports, including reset and cross-session denial. Guest Build and Play discussions also complete through their normal guest HTTP paths with synthetic providers and reject reset-during-writer responses. [Plan evidence](../Docs/Plans/HANDOFF-ONBOARD-guest-buddy.md) · [Build evidence](../Docs/Plans/HANDOFF-ONBOARD-guest-build-buddy.md) · [Play evidence](../Docs/Plans/HANDOFF-ONBOARD-guest-play-buddy.md) | Stay in conversation, ask a focused question when needed, reuse adequate admitted context, and offer zero page proposals. Verify guest discussion and Graph selection through the normal deployed UI with real Sizzek sources and provider; effects and streaming are not established by these synthetic tests. |
| Resolve an ambiguous Build paragraph placement | The [pending App HTTP regression](../tests/application_state/test_pending_build_storage.py) exercises the saved clarification, original request with its answer, and exact paragraph review without acquisition. The [client protocol](../apps/live-control-ui/src/shared/surfaceNativeProtocol.test.ts) checks the pending proposal acknowledgement. The [editor regression](../apps/live-control-ui/src/buildSurface/buildComposeBridge.test.ts) covers proposal reopening after plain Markdown reload. | Exercise the pending question, answer, and proposal reopen in the deployed app. The editor and saved page must remain unchanged until acceptance. |
| Ask and resume clarifying questions in conversation | Clarification is an existing intent and inline conversation response. Retained [conversation-first cases](conversation_first/cases.py) cover asking first, staying off the page, and proceeding after the user answers. The [duplicate-question delivery slice](../Docs/Plans/HANDOFF-CLARIFICATION-duplicate-question-delivery.md) verifies native completion replay; a synthetic local app retry rendered the question and accepted its answer, but the subsequent suggestion failed to complete. | Qualify reopen and continuation with ordinary-turn evidence. An unanswered preference calls for a question, with no retrieval or page proposal. Keep the request and the user's answer bound to the same workflow. |

| Generate, preview, and save artwork | Guest Build uses the existing Image Studio with a session-owned private library when enabled. [Guest scope and tests](../Docs/Plans/HANDOFF-ONBOARD-guest-inline-media.md) | Fake-provider HTTP and mocked-transport Build tests cover placement, save and reopen. Verify the complete workflow with the real provider in production. |

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

## AW10 — Maelthor from the conversation

Extend the original [Maelthor conversation-to-page benchmark](https://github.com/Drakosfire/DungeonMindBuddy/pull/4017)
with the explicit operator turn **“Create a page for Maelthor”** after the
discussion has already collected sufficient evidence. Keep the original
blank-to-populated and stale-review controls.

Freeze the preceding conversation and the exact supports already admitted in
its completed turns. Before execution, verify that the required prior claims
and exact citations are present in that prefix. A fixture missing either
support is unqualified for the grounded zero-retrieval case. Do not backfill
its prior turns with facts recovered by the failing creation turn. A read-only
check of the hosted prefix found that completed turns 7, 8 and 12 mention
Maelthor, Ethel and the password and each retain two native body citations.
The frozen 12-turn prefix has SHA-256
`ff14046ef3e593a61957eb5e2df5f6d5295e9389057d722b698d186834cdcb4b`.
Turn 8 supplies the two cleanly separated passage claims. The admitted dream
excerpt hashes to `7080c5f78d97bc39d2ac21a08e7f8b889da77844c376e64d67ea9269f5468bec`
and the password excerpt hashes to
`c4fe6d1592e97a550d250fb88bd914d239134868a48c3905ace8bb3162800b94`.
Both citation records bind the original answer segment digest and the
original read event and section. The frozen prefix and supporting records
stay in the isolated evaluator evidence workspace.

| Boundary | Acceptance |
| --- | --- |
| Intent and acquisition | An ordinary Build turn recognizes the named standalone page. The draft uses the prior discussion and its admitted evidence. The trace shows zero new Graph, corpus, or related-page discovery and reads. Loading the exact retained conversation and citation records is allowed. |
| Draft and provenance | Offer one reviewable Maelthor draft. Retain Ethel’s Session 3 dream and the Session 6 use of “Maelthor” as a password where supported by the pinned prior turns. Carry their exact citations into the draft. Keep Maelthor’s identity and motives, Dust Walker’s connection, and the Meat Mind’s relationship open where the discussion left them open. Keep the author’s ideas visibly proposed. |
| Confirm and reopen | Before confirmation, there are zero page, revision, or Graph mutations. Confirm the displayed review digest in the isolated evaluator, then reopen the page and inspect the exact citation targets. Repeating the confirmation returns the same receipt and leaves one page. |
| Controls | A foreign conversation, wrong citation owner, or stale review cannot create a page. A separate explicit research request can use normal retrieval. An uncited prior assertion never gains a citation merely by appearing in dialogue. |

The hosted capture of turn `9e60e894-dcb2-4e52-b84e-06481be35cf0`
(SHA-256 `dff451e679e7cef5726e3bb22b0b247072902e48bdc1d96c8bb0981de569667e`)
selected `review_lore_page` and produced a Maelthor proposal after about 75
seconds, including related-page and corpus retrieval. A read-only check found
zero save-review or confirmation receipts for that turn. Record the observed
routing and proposal separately from the acquisition failure and unexercised
save boundary. This capture does not qualify the candidate.

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
