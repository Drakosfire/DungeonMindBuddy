# MIND — retain unsent conversation text through reload

ACTIVE PRIME implementation after amended owner design APPROVED exact head
d08903881a2747feb8575a4ce4d89c4511c20eb7. Original design APPROVED exact head
8f7150bd1da91886b825281d35960eea3fc3ce72 on2026-10-24. Active authoring goal §3 supplies implementation authority.
Serial successor to PR1721 merge5829c6e8f96f0a536577da8b1dca164e99bc6bb9.
Existing buddy-context-loop checkout, branch codex/shared-composer-reload-drafts.
No overlapping shared-composer lease found among current open PRs. One PR; no
backend, migration, provider, routing or inference work.

## Owner amendment after implementation review

Independent review ofc6ed8953f held three P2s: callbacks retained write authority
after unmount/A→B→A; failed-write memory was lost on World navigation; extra
stored envelope fields were overwritten. PRIME activated this amendment after independent exact-head design approval.

The App's AgentInteractionProvider outlives its World-keyed conversation registry.
It will host a small ConversationComposerDraftProvider containing a per-World
snapshot store for this browser page lifetime. World registries consume that
owner through the existing hook; an isolated registry without the App host gets
one local owner. There is no second active storage writer and no module-global
cache. Valid and failed/blocked World snapshots remain in that owner's memory
through World navigation, including actual registry unmount/remount. The existing
sessionStorage envelope remains the only reload copy, with the same exact scope.
No read/write fallback or external synchronization is introduced.

Use useSyncExternalStore with stable per-World snapshots and subscription lifetime
for React-safe updates. Each consumer setter also requires the mounted consumer,
exact owner and World lifecycle epoch; string equality cannot reactivate an old
setter after A→B→A. A retired/unmounted registry cannot mutate storage or owner
memory. Writes still complete synchronously before publishing the new snapshot.
Closed top-level envelope shape is exactly schema/world_id/drafts; unknown fields
fail recovery and retain original bytes. Failed-write/blocked memory and warning
remain intact when navigating away and back without a reload; a full page reload
still has the explicit warned limitation if browser storage could not retain it.

Add AgentInteractionProvider.tsx to the exclusive write lease for the wrapper only.
Regression gates: unmounted setter vs newer same-World remount; first-A setter
after A→B→A; failed/blocked World snapshots survive keyed registry remount under
the actual App-level owner; unknown fields are never overwritten. No other
provider/runtime behavior or new capability is authorized by this amendment.

## User outcome and contract

An author can type a next thought while Buddy works, reload, recover the submitted
request, and find that next thought intact. The shared conversation host owns this
for Build, Plan and Play. Saved page content, page proposals and submitted exact
request envelopes remain distinct owners and are never reconstructed from drafts.

Persist the existing work-keyed composer map in sessionStorage, scoped by exact
managed World. Existing keys remain build:<document>, plan:<document>, play:<run>.
This is browsing-tab-session recovery: reload and API/UI service restart preserve
text; separate tabs have separate session stores. It is not cross-device storage,
a guarantee after closing the browser session, or a claim of full-goal completion.
No localStorage last-writer-wins map, storage-event synchronization, TTL, arbitrary
character limits, or automatic sending. No AI call is needed to type/recover text.

Use one versioned envelope with exact World ID and string draft map. Validate
stored shape/scope before exposing text. Preserve Unicode and whitespace exactly.
Read on shared-provider initialization and exact World changes even if its parent
fails to key it. A stale callback from another World cannot write the active one.
The production shared owner persists; the isolated legacy controller fallback
retains its current in-memory behavior and is not a second storage writer.

Persist each meaningful update synchronously before scheduling React state. Keep
newer in-memory text when storage fails; display one concise composer warning
that text needs copying before reload. Never claim recovery is available when
read/write access failed. Do not block ordinary typing or generation merely
because this optional recovery copy failed. A malformed/foreign envelope remains
byte-for-byte intact and is not overwritten automatically; warn that new typing
is memory-only until the retained copy is repaired. No silent cleanup of unknown
storage, no destructive recovery repair, no fallback store or inferred draft.

Successful submission clears only the captured text under existing edit-generation
checks; failure/status/retry must preserve newer text. Remove the existing deletion
of the prior Plan document's slot during navigation; keep presentation/continuation
retirement so another Plan opens blank and returning restores its own unsent text.
Empty draft deletion affects only this known valid tab/World envelope. React Strict
Mode cannot duplicate an operation or lose a later update. No change to exact turn
IDs, idempotency/CAS recovery, selection, document JSON or undo.

## Exclusive expected writes after activation

- apps/live-control-ui/src/agentInteraction/conversationComposerDrafts.ts (new shared hook/store)
- apps/live-control-ui/src/agentInteraction/conversationComposerDrafts.test.tsx (new owning tests)
- apps/live-control-ui/src/agentInteraction/WorldAgentConversation.tsx (shared consumer only)
- apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx (page-lifetime draft owner wrapper only)
- apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx
  (concise storage warning and retain prior Plan slot; existing generation fence stays)
- apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx
- this handoff; Docs/Plans/HANDOFF-BUILD-table-construction-stream.md and
  Docs/Roadmaps/ROADMAP-demo.md (truthful predecessor settlement/priority)

PRIME owns protected UI5202 delivery, frozen dist artifact, current API3ce378df,
APP0061/native0017 and retained state. No shared dependency environment mutation.

## Proof gates

Before activation: independent critique of tab/World/work isolation, submission
settlement, failure/invalid storage and React lifecycle. Then prove complete text
survives shared-provider remount/reload for all three surfaces, switching Worlds
and work targets does not leak/erase drafts, old callbacks cannot cross Worlds,
separate browser session stores do not clobber, empty slots clear only themselves,
malformed/foreign bytes survive, denied/quota writes leave typing usable with a
truthful warning, and newer draft survives a terminal or uncertain older request.
Mounted conversation witnesses must exercise the actual production shared owner.
Run focused owning suite, full touched shared-conversation suite, tsc/build and
exact cumulative independent Bugbot. PRIME merge only at approved exact head.

Protected UI delivery checks owned processes, active turns and retained APP/native
state. Ordinary controls must demonstrate a next thought surviving reload during
real construction, exact original request recovery and editable proposal without
a second reload or duplicate generation/insertion. Use useful Edge trader-house
possibilities with DustWalker warning/treasure routes; preserve Meat Mind's not-yet
reacted status and separate proposed routes from played facts. Do not publish the
proposal into the author's saved Edge page as part of this proof.

Speed is now a regression guard, per operator2026-10-24 assessment. No new latency
optimization program or stand-alone timing run. Preserve original broad goal and
all adventure/recap/Play acceptance gates; this is one dependable writing slice.
