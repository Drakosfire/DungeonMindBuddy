# Buddy actions and authoring benchmark

Use ordinary Plan turns in isolated state. These cases test destination and
side effects, in addition to whether Buddy produces a useful response. Use the
existing Plan authoring contract and retained APP turn evidence. Keep the
assessment local.

## Action catalog

This is Buddy’s canonical action inventory. Follow the
[maintenance rule](../AGENTS.md#agent-action-catalog) when action availability,
workflow behavior, or verification evidence changes.

An **ordinary turn** uses Buddy’s product intent and provider routes in an
isolated or hosted setting. Record which setting and turn were observed.
**Component evidence** covers isolated owners, scripted rehearsals, or
prototypes. **Requested** describes the behavior to qualify. Record draft,
confirmation, mutation, and independent reopen individually. A successful
stage supplies evidence only for that stage.

| Action | Strongest verified boundary | Requested behavior or remaining proof |
| --- | --- | --- |
| Discuss, clarify, or brainstorm in chat | The opening Meat Mind dogfood produced a grounded reply with excessive retrieval. PA01 retains a Sheep discussion where Buddy offered an unsolicited insertion after prior page writing. A default-off guest Plan discussion slice exercises a real guest session, copied synthetic World, selected Graph object and source, sourced answer and citation with synthetic provider transports, including reset and cross-session denial. Guest Build discussion also completes through the normal guest HTTP path with synthetic providers and rejects a reset-during-writer response. [Plan evidence](../Docs/Plans/HANDOFF-ONBOARD-guest-buddy.md) · [Build evidence](../Docs/Plans/HANDOFF-ONBOARD-guest-build-buddy.md) | Stay in conversation, ask a focused question when needed, reuse adequate admitted context, and offer zero page proposals. Verify guest discussion and Graph selection through the normal deployed UI with real Sizzek sources and provider; effects, Play and streaming are not established by these synthetic tests. |
| Resolve an ambiguous Build paragraph placement | The [ordinary Build HTTP regression](../tests/test_surface_native_build_ordinary.py) checks that Build conversation saves the inline question and resumes the original request to stage an inert proposal. The [editor regression](../apps/live-control-ui/src/buildSurface/buildComposeBridge.test.ts) exercises Build proposal review after plain Markdown reload discards temporary block IDs. | In the deployed app, verify that the answered request resumes, the proposal reopens at the intended paragraph, and the editor and saved page remain unchanged until acceptance. |
| Draft and edit in conversation | Revisioned conversation draft ownership shipped [in #3827](https://github.com/Drakosfire/DungeonMindBuddy/pull/3827). | PA03 must demonstrate two independently editable drafts and restore both edits after reopen, with zero page effects. |
| Propose a targeted edit, insert a table, then apply and save | PA02 retains a Sheep placement control. AW01 proves provider-free targeted Edge row save and reopen. | AW03 needs an ordinary six-NPC request, one reviewed table insertion in the exact location, and preservation of neighboring content. |
| Research and cite PDF evidence, then assemble Plan cards | The ordinary Conks Plan turn used 13 reviewed Events and returned 26 links to 13 PDF regions, all reopened. The full proposal covered 9 of 24 qualified items fully, 11 partially, and missed 4. The separate three-card aftermath slice saved and reopened after review and reorder. | Build and save the full playable Plan with choices, triggers, optional scenes, numbered cards, and exact source links. |
| Draft a standalone page from prior discussion and confirm it | AW10’s isolated ordinary Maelthor replay used zero new acquisition, kept exact retained citations, and saved/reopened one page with an idempotent confirmation receipt. [Release evidence](../Docs/Plans/HANDOFF-DOGFOOD-aw10-release-selection.md) | Keep the research contrast, stale and foreign review controls, and exact citation ownership checks. |
| Retrieve, adapt, preview, save, link, or load a statblock | AW09 has component evidence for draft review, variant save/reopen, confirmed link, and exact Combat admission. The joined rehearsal used scripted outputs. [Evidence](../Docs/Backlog/IDEA-aw-workflow-capabilities.md) | Ordinary Meat Mind brainstorming through confirmed save, Edge link, independent discovery, and Combat load. Also qualify a new incidental NPC from a name and description in both Plan and Play. |
| Correct names and resolve existing identity | C2S30 supplies the observed corrections, possessive, and identity ambiguity used by AW02, AW04, and AW05. | Preserve original input, apply only the accepted occurrence, and reuse a reviewed identity without creating a duplicate. Qualify each boundary. |
| Verify support, publish, block, or replace | Reviewed PDF Event prep publication and exact citation reopening are proven component boundaries. C2S30 supplies the support-error fixture. | AW06–AW08 must distinguish safe refusal from verified publication. Replacement must preserve authored and shared material and keep the prior revision inspectable. |
| Prepare an image direction and open Image Studio | Build has live prompt preparation and history reopen. Plan can hand an editable image prompt to the studio. [Build evidence](../Docs/Plans/HANDOFF-MEDIA-agent-build-image.md) · [Plan evidence](../Docs/Plans/HANDOFF-PLAN-image-prompt-handoff.md) | Qualify the current route for illustration versus map purpose and prove that prompt preparation alone produces zero image jobs or page changes. |
| Generate, preview, and save artwork | Hosted Buddy supports World-owned generation and save. Guest Build uses the same operator-controlled Image Studio with a session-owned private library when enabled; the guest release does not enable public CDN save. [Guest scope and tests](../Docs/Plans/HANDOFF-ONBOARD-guest-inline-media.md) · [Generation](https://github.com/Drakosfire/DungeonMindBuddy/pull/3946) · [Save](https://github.com/Drakosfire/DungeonMindBuddy/pull/3944) · [Live benchmark](../Docs/Benchmarks/BASELINE-old-bath-house.md) | Guest evidence combines fake-provider mounted HTTP with a mocked-transport Build Studio placement, save and reopen test. Verify the complete workflow with the real provider in production. |
| Edit, place, or move artwork | Exact existing-image moves have mounted Review, Apply, Save, and cold-reopen evidence. Contextual regeneration has implementation and instruction-recovery evidence. [Move evidence](../Docs/Plans/HANDOFF-BUILD-image-move-mounted.md) · [Regeneration evidence](../Docs/Plans/HANDOFF-MEDIA-contextual-image-edit.md) | Qualify live image-to-image and new-image variants with exact source ownership, explicit Apply, and reopen. |
| Prepare map, reference objects, and scene-aware NPC art | The Conks prototype provides design evidence for linked map markers and scene references. Saved variant portrait binding has separate product evidence. | Excerpt or generate a map with navigable location nodes, support editable Items and rollable Tables, and surface art automatically for an NPC identity in the current scene. |
| Run a prepared scene, load Combat, record notes, and carry forward played history | Isolated controls exercised loaded Guardian mechanics, a combat round, a resource change, scene notes, and cited Event readback. | Prove the joined flow with PCs and saved mechanics, a departure from the Plan, reviewed recap publication, and a cited fresh follow-up. |

### Additional shipped action and operator boundaries

This audit compared the mounted server route inventory, Build and Plan work
choices, merged handoffs, and retained reports against the existing PA/AW
cases. Product owner actions include explicit buttons and confirmations.
Their availability does not establish that the model can select or execute
them on an ordinary conversational turn.

| Capability | Verified boundary | Decision checkpoint to qualify |
| --- | --- | --- |
| Look up public Rules and cite them with World evidence | Native Plan Rules tool accepted on local Buddy. Rules authority and World evidence have separate owners. [Plan Rules evidence](../Docs/Plans/HANDOFF-RULES-native-plan-host.md) | Use Rules for a mechanics question, World sources for campaign history, and both when requested. Verify citation ownership and no Rules call for a lore-only control. |
| Ask and resume clarifying questions in conversation | Clarification is an existing intent and inline conversation response. Retained [conversation-first cases](conversation_first/cases.py) cover asking first, staying off the page, and proceeding after the user answers. Restore Clarifying Questions owns restoration work. | Qualify reopen and continuation against that lane's accepted evidence. An unanswered preference calls for a question, with no retrieval or page proposal. Keep the request and the user's answer bound to the same workflow. |
| Create a connected page from a saved origin | Saved-origin review owner, UI and readback were delivered. [Connected-page evidence](../Docs/Plans/HANDOFF-PLAN-connected-page-review.md) | Contrast standalone page, connected Location page, and current-page edit. Verify destination, exact origin link, confirmation and independent reopen. |
| Review and publish relationships or manual World knowledge | Build's relationship review and native confirmation, hosted owner publication, and exact Worldbuilding support review have shipped. [Relationship confirmation](https://github.com/Drakosfire/DungeonMindBuddy/pull/3322) · [Exact support review](https://github.com/Drakosfire/DungeonMindBuddy/pull/4614) | Contrast suggesting a relationship, reviewing an exact edge, and explicitly confirming the publication. Missing support or ambiguous endpoints must hold the mutation. |
| Review and continue a multi-step work plan | The ordinary continuation rehearsal saved edited selected and deferred steps, reloaded them, and ran only the explicitly continued discussion step. [Continuation evidence](../Docs/Plans/HANDOFF-MIND-work-plan-continuation-copy.md) | Select one step while leaving another deferred, interrupt after acceptance, and recover without starting the deferred step or repeating a durable action. |
| Add Choices and Options to a Plan | Ordinary Conks authoring, Save and reload preserved the surrounding saved content. The later Start Session control was blocked in that rehearsal. [Choice evidence](../Docs/Plans/HANDOFF-PLAN-choice-body-boundary.md) | Use an option for a branching outcome and prose for ordinary scene detail. Confirm that pre-existing prose stays in its original scene. |
| Review an edit to the current Play session copy | Rendered acceptance delivered reviewed session-scene proposals on ordinary local Buddy. [Play edit evidence](../Docs/Plans/HANDOFF-PLAY-session-edit-proposals.md) | Contrast discussion, a requested session-local edit, and a request to revise long-term Plan prep. Bind the edit to the active Run and scene and preserve the original Plan. |
| Open a prepared table and record a roll | A source-to-Plan-to-Run rehearsal recorded an explicitly entered value and preserved the same outcome, Scene and note after reload and restart. [Recorded roll evidence](../Docs/Plans/HANDOFF-PLAY-prepared-table-implementation.md) | Opening or discussing the table has no roll effect. An explicit recorded value resolves once against the active table, even on retry. Editable source-backed Graph tables remain a separate requested capability. |
| Prepare and preview a saved encounter, start Combat, and persist state | Saved encounter preparation and Plan preview are shipped. Old Bath House qualified exact mechanics and portrait handoff, a parley path that left Combat unstarted, explicit Combat start, and durable HP edits. [Preparation](https://github.com/Drakosfire/DungeonMindBuddy/pull/4316) · [Old Bath House evidence](../Docs/Benchmarks/BASELINE-old-bath-house.md) | Distinguish encounter prose, preparing an exact roster, previewing it, and starting Combat. Carry exact saved revisions and protect the prepared encounter from changes to the running copy. |
| Recover a saved request or lost acknowledgement | Build has recovery for a lost page commit response. Worldbuilding has timed-out extraction recovery. [Page recovery](https://github.com/Drakosfire/DungeonMindBuddy/pull/4407) · [Worldbuilding recovery](https://github.com/Drakosfire/DungeonMindBuddy/pull/4548) | Distinguish an unsent draft, unknown outcome, and a committed action whose acknowledgement was lost. Use the existing receipt before offering to run a mutation again. |

The Build decision contract recognizes direct mechanics changes, encounter
construction, map-coordinate placement, page Save, and relationship
publication while listing those work choices as unavailable for direct
dispatch. Use this as a negative benchmark surface. A relevant suggestion
or operator handoff can be appropriate. A reported direct execution requires
evidence from the owning operator path. [Build decision contract](../src/application_state/agent_conversation/build_intentional_response.py)

The [adventure-to-follow-up benchmark](adventure-to-follow-up-benchmark.md)
owns the Conks and Sheep journey acceptance and its evidence. The original AW
and PA cases below retain their fixture and execution requirements.

## Workflow decision benchmark

**Design for qualification.** Reuse PA/AW and adventure fixtures and the
existing capture and scoring owners. Each row below is an independent
decision checkpoint with a pinned dialogue prefix, active surface and
selection, available sources, durable state, and confirmation state. Change
one condition per contrast. Keep the expected decision and evidence rubric
local. Ordinary Buddy turns exercise selection with the normal decision
route. Provider-free owner tests exercise persistence, retry, and readback.

### Right Action at the Right Time

The [coverage matrix](right-action-coverage.md) sets three increasing
challenges per action and defines the baseline before tool-presentation tuning.

Start with **fresh conversations and sufficient first-turn input**. Freeze the
user message and any exact selection, supplied source, or available draft that
Buddy normally receives. A visible page or a mention alone does not establish
admission. Check what the decision model actually sees before labeling a case
sufficient. Keep the same permissions and target across each contrast.

| Initial case | Supplied context and request | Expected first action |
| --- | --- | --- |
| Clarify before work | Give a complete shop objective and ask for two questions about tone and conflict before doing anything else. | Ask two relevant questions in chat, then wait. No retrieval, draft, proposal, or write. |
| Current-page revision | Supply the exact selected paragraph and say “Tighten this paragraph and stage it here for review.” | Stage one review against the selection. Zero new evidence acquisition and zero save. |
| Editable conversation drafts | Supply the complete premise and ask for two editable alternatives here in chat. | Prepare two chat drafts. Zero new acquisition and zero page proposals. |
| Image direction | Supply the composition, subject, and purpose and ask for an editable illustration prompt. | Prepare the direction. Zero new acquisition, zero generation jobs and zero page changes. |
| Connected Location | Supply the admitted origin passage with name, role, and exact origin and explicitly request a connected-page review. | Stage one review at the connected destination. Resolve the exact binding only. No discovery or publish. |
| Mechanics or encounter handoff | Supply the mechanics or roster and request an operation unavailable to the current conversation route. | Give the appropriate review or operator handoff, as specified by the surface fixture. No discovery to compensate for an unavailable action and no false success receipt. |

Each case gets at least one close contrast. Remove a required fact from the
selected paragraph and ask for a factual addition so a targeted read becomes
necessary. Leave a preference unresolved so a question is the right action.
Change chat-only to explicit page review while keeping the prose fixed.
Change prompt preparation to explicit Generate at the operator boundary.
Include an explicit research request on a fully specified fixture to ensure
the benchmark also rewards retrieval when requested. Predeclare the allowed
read count or scope for each contrast.

**Measurement.** Label reads as supplied context loading, exact reference or
retained receipt resolution, fresh discovery, or fresh source acquisition.
Count each separately using the request, tool trace, and action journal.
For a zero-new-retrieval case, any new search, traversal, or source
acquisition fails the choice check even if the final artifact is correct.
Permit only the pinned fixture's required identity or provenance resolution.
Missing acquisition telemetry means the result is unverified. Measure
Send-to-first consequential action, Send-to-review or reply, and time in
fresh retrieval, alongside calls and tokens. Compare sufficiency and
necessary-retrieval controls separately. Keep writer fulfillment and effect
integrity visible so an empty reply or a blanket retrieval bypass cannot pass.

**Then add multi-turn cases from traces.** Pin the turn that acquired evidence
and the later step that applies it. Start with Sheep's change from writing to
discussion, Maelthor's existing citations, Meat Mind's follow-up premise and
draft request, and an answered clarification. Reopen the conversation where
appropriate. Pair reuse with a materially changed source, a new question, or
newly requested research. Record which citation or admitted fact carried
forward and verify exact reopening. Track pending, answered, and restored
clarification separately from evidence acquisition.

Use the retained [conversation-first cases](conversation_first/cases.py)
as development evidence. Freeze fresh first-turn contrasts before prompt
tuning and keep additional surface/action combinations for validation.
Record new actions as data in the same manifest with a stable case ID,
pinned context, allowable reads, expected action and destination, forbidden
effects, and stage checkpoints. Reuse the ordinary capture workflow and
extend the shared scorer once. No action-specific scripts are required.

### Retained workflow checkpoints

| Workflow checkpoint | Expected choice | Contrast and prohibited effects |
| --- | --- | --- |
| Sheep discussion after a page-writing turn | Discuss or ask a relevant question in chat. | Explicit insertion request on the same Plan stages one proposal at the requested placement. Any page proposal during discussion fails, including a dismissed proposal. |
| Two editable drafts requested in chat | Stage two editable conversation drafts. | An explicit later request can stage a chosen draft at the page target. Draft edits alone never reserve or mutate the page. |
| Maelthor evidence already in prior turns | Stage a sourced standalone page review from retained turns. | Explicit research or materially missing support calls for a bounded read or clarification, as specified by the fixture. Sufficient retained evidence permits zero new discovery. |
| Maelthor or Meat Mind confirmation | Commit the displayed revision once and reopen it independently. | Unconfirmed or stale review produces zero durable mutations. Retry after a lost acknowledgement resolves the existing receipt. A link or Combat action needs its own requested destination and boundary. |
| Meat Mind discussion with an explicit statblock reference | Open the exact reference and relevant Edge context once, then discuss. Reuse it when the follow-up only changes the premise. | A request for a draft stages a reviewable statblock. A new evidence gap permits a targeted read. Neither discussion nor preview creates a saved variant. |
| Image discussion, prompt, generation, and placement | Discuss in chat, prepare an editable direction when asked for a prompt, and call the provider only at explicit Generate. Preview keeps the original and page intact. | Contrast illustration with map purpose and a new image with editing an exact existing asset. Explicit Use/Apply binds or replaces the intended asset or occurrence; page persistence requires Save. A stale selection preserves the candidate and leaves the page unchanged. Verify job count, provenance, exact asset and reopen. |
| Conks prep versus an unexpected encounter in Play | In Plan, propose playable branches and source-backed cards. In Play, offer usable reviewed mechanics for the incidental NPC when requested. | Combat begins only after explicit authorization with the exact saved mechanics. Play notes and recap reflect the branch actually played. |
| C2S30 ambiguity or missing support | Ask for identity selection or report the missing publication prerequisite. | Verified support and a reviewed identity permit one publication. A blocked case preserves the candidate and produces zero mutation or success receipt. |
| Review a recap after Play | Stage a draft from played notes and retain open threads. | Publish only on confirmation and reopen cited played Events. Unused Plan branches remain prep. A fresh follow-up reads the played outcome. |

At each checkpoint record the first consequential action and the ordered
sequence through the next review or delivery boundary. Include read
discovery and exact opens, destination, proposals, confirmations,
mutations, receipts, and reopen results. Score independently:

1. **Choice** — the observed operation, acquisition scope, destination, and
   timing fit an explicitly allowed sequence for the pinned state.
2. **Safety** — forbidden effects fail immediately. Missing telemetry makes
   a no-action result unverified. Measure duplicate and preconfirmation
   mutations with the ordered journal and independent readback.
3. **Fulfillment** — the requested reply, draft, or durable state is usable
   and required citations reopen exactly. A safe refusal can pass a blocked
   fixture without proving the blocked mutation.
4. **Efficiency** — report new reads, repeated opens, provider calls, tokens,
   time, and operator interventions when observed. Record unknown values.

Use the decision checkpoints in the additional capability table as a second cohort after the retained PA/AW controls. Pin and qualify each fixture before use.

A workflow passes when every required checkpoint passes choice, safety, and
fulfillment. Report checkpoint totals and the first failing step. Use the
existing action report for its supported side-effect and fulfillment checks.
Action-sequence grading is new work. Qualify the first-turn cohort through
ordinary Buddy first. Use retained Sheep and Maelthor evidence to map the
subsequent multi-turn fixtures and identify telemetry gaps before rerunning.

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
