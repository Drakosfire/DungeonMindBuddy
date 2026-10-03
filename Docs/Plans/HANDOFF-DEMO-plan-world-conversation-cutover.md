# HANDOFF — DEMO: cut over Plan conversation to World history (Slice A)

**Status:** BLOCKED — bounded Slice A design prepared for independent review; no implementation write lease, provider, database, service, port, or runtime lease.

**Steward:** DEMO task 01a0efc8-f3a8-7be2-a556-33eb338338e8

**Repository:** Drakosfire/DungeonMindBuddy

**Authority base:** Buddy main at 402390ca051553a09e844ea57ddf8be3f6217fef (2026-10-03; PR #898 merge). Re-anchor main, all open PRs, current runtime ownership, and active leases before activation.

**Topology:** serial. Slice A below → Slice B proposal-context merger → later automatic Plan/Graph context. There is no independent parallel Plan consumer lane.

**Future implementation PR title:** DEMO: cut over Plan conversation to World history

**Current branch / approval state:** This document is a design amendment only. Its reviewed exact PR head is the proposed pinned handoff. PRIME must explicitly adopt that exact head and issue an ACTIVE lease before implementation. The handoff need not merge to main unless PRIME makes that a specific gate. A PR, review, or merged BLOCKED handoff does not itself activate code work.

## Accepted predecessor state

The prior #857 handoff treated several dependencies as pending. They are now delivered and must not be represented as open blockers:

- Buddy #857 accepted the original DEMO consumer design at merge 41fe2944468327da852a987685992fc50f91f059, from reviewed head de08a3cc2f24406d1440b771f047ba0b8398a6e8.
- Buddy #859 accepted the separate Plan action-dialogue design at merge 43c4c4daa8e1c17b22953681fe817e6881242b36, from reviewed head c78feb94f37f7612200e2d0962d26d0f5a1326cf.
- Buddy #865 adopted the production World conversation runtime and merged at 1c0320d18c53037308cd7412719fb3e2f0610d99.
- Buddy #897 delivered the Plan-owned exact-basis action/status and completed-context projection and merged at d5de2072f90c27b031f9f55157504915f98a189f, from reviewed head 7da39e47327d8dd941ecb7eb1074a2c8ec028544. Its future cross-source order is accepted_at, source rank Ask=0 / PlanAction=1, source-specific sequence, source record UUID. Each source filters exact-basis eligibility before its own cap; the proposal boundary applies the total cap of six after merge.
- Buddy #898 delivered the APP-STATE exact-basis completed Ask projection and merged at 402390ca051553a09e844ea57ddf8be3f6217fef, from reviewed head 5b8daaa6c8d8fcc825da626de3c0499539cafadd. Its 8 PostgreSQL projection tests and 2 adjacent regressions passed; PRIME independently reran the 8 projection tests and accepted the review.
- Existing APP-STATE World conversation identity, visible turn storage, idempotency receipts, and the accepted #865 retry/replay contract remain the owner authority. Browser thread IDs are correlation values, not conversation identity.

These are code-integration facts, not J1–J6, live-demo, or operator acceptance. Slice A consumes these accepted capabilities. It adds no APP-STATE, AGENT-INTERACTION, proposal-service, route, schema, or migration behavior.

## Slice A — one bounded capability

A saved Plan in a verified managed World displays and continues the server-owned World conversation. The UI can start a New Conversation using the existing server command/CAS contract. An Ask whose response is uncertain can be resumed after reload by replaying its exact original durable request identity and intent.

The client consumes these existing routes and their currently accepted wire contracts:

- GET /api/live/worlds/{world_id}/conversation
- POST /api/live/worlds/{world_id}/conversation/new
- POST /api/live/agent/turn

At activation, read the exact current route schemas and reuse them. Do not invent a second conversation API or derive server authority from a browser key. The server-issued conversation ID and durable turn receipt remain canonical. The accepted Plan Ask contract continues to resolve the verified World, saved Plan, committed WorkRevision, and exact content digest on the server; mounted draft bytes stay excluded and Graph remains not requested.

### Canonical history and New Conversation

- On entry to a verified World Plan, load the visible World transcript from the server. Render its accepted surface and work provenance; do not flatten turns from another surface into Plan-owned turns.
- Fence late history reads against the current World/Plan scope. A response from an old route cannot populate the newly selected World.
- New Conversation sends the existing expected pointer revision, expected active conversation identity, and durable command ID required by the server CAS contract. Persist and replay the exact command envelope after an uncertain transport result. Do not silently mint a replacement command ID. On a pointer conflict, retain the visible current state, fetch the current server state, and require a deliberate new command.
- A confirmed new conversation hydrates from the server response or a fresh server history read. It does not create a parallel browser conversation or clear unrelated pending envelopes.

### Ask and durable uncertain retry

- Resolve the current committed Plan basis using the existing server read before preparing a turn.
- Persist the exact normalized WorldPlanAgentTurnRequestV1 envelope before dispatch, including its original client_thread_id, turn_id, World, Plan, full expected committed basis, message, graph_request=none, and graph_selection=null.
- Key pending envelopes by verified World, Plan document, the full basis tuple (object revision, WorkRevision ID, revision number, content digest), and the original turn identity. Keep distinct envelopes for other Worlds, Plans, bases, or turns. Store any server-issued origin conversation/pointer ID as metadata; never treat a client thread ID as canonical conversation identity.
- After an uncertain result or reload, show an explicit recovery action and replay the exact stored request. Do not automatically create a fresh turn ID, client thread ID, or changed intent. A deliberate new user question gets a new durable turn identity.
- Reconcile a confirmed result under its originating conversation only. Navigation, basis advance, or New Conversation cannot overwrite the pending envelope or place an old receipt in the newly active conversation. If the accepted server contract cannot retrieve or resolve an old pending receipt after a pointer change, stop and return the contract gap to PRIME; do not expand the Buddy client lease into server changes.
- Remove a pending envelope only after the durable server receipt/result is confirmed. An unavailable history service or ambiguous result has an actionable pending/error state; it never falls back to browser transcript as canonical history.

This envelope is local transport-recovery state, not a second conversation store: it contains only the exact outbound request and origin key, is not rendered as a completed transcript, and is not sent as extra context.

### Legacy browser history

Existing browser-local Plan conversation bytes may contain turns without exact server provenance and Plan edit rows with proposal data. Preserve those bytes unchanged and exportable. Clearly mark any surfaced copy as legacy and local-only. Keep it separate from server history; never use it for current Ask or Compose/Revise model context.

This slice does not delete rows, auto-import, dual-write transcript turns, or fall back to local history when a server read fails. Do not call the APP-STATE legacy importer. A local export is a copy for user recovery; exporting does not change storage.

### Compose/Revise during Slice A

Preserve the current Compose/Revise instruction, mounted-draft and selection capture, proposal validation, Review, Apply-to-editor, and ordinary Save behavior. Slice A does not implement a context merger. Until Slice B, send an empty conversation_history to the proposal boundary; do not pass any legacy local rows, local Ask turns, or the World transcript. This temporarily pauses conversational carry-over for Compose/Revise while keeping the editing action usable. State this behavior clearly in the Plan UI.

Slice B remains a distinct later capability. It may restore the existing six-pair behavior only through the authoritative proposal boundary by merging the exact-basis completed Plan-action projection from #897 with the exact-basis Ask projection from #898, filtering each source before its cap, applying the accepted deterministic cross-source order, and enforcing six total pairs after merge. Client history cannot add, remove, or reorder that context. Do not begin Slice B in the Slice A branch or PR.

### Explicit exclusions

No browser-to-server legacy import; no deletion, migration, or dual-write of old conversation bytes; no proposal-context merger; no new route, backend schema, database migration, provider runtime, Agent framework, Graph request, automatic Plan/Graph context, visual/card redesign, PlanSurfacePage/AppChrome work, CSS refresh, J1–J6 claim, or product-acceptance claim. No edits to the #886 navigation shell paths.

## Proposed implementation lane and exact write set

There is no current implementation lane. After PRIME adopts this exact handoff and issues ACTIVE, create an isolated checkout from freshly fetched remote main, branch codex/demo-plan-world-conversation-slice-a, and deliver one serial implementation PR. Do not develop on local main or on the stale takeover checkout.

Proposed exclusive source write set:

1. apps/live-control-ui/src/api/types.ts — typed shapes for the existing World conversation and New Conversation responses.
2. apps/live-control-ui/src/api/liveApi.ts — typed GET/POST wrappers for the existing routes.
3. apps/live-control-ui/src/api/liveApi.worldConversation.test.ts — new route/method/body/response wrapper tests.
4. apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx — server transcript hydration, New Conversation, durable pending Ask recovery, isolated legacy export/presentation, and empty Slice A proposal history.
5. apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx — new mounted consumer tests for history, scope fences, retries, New Conversation, and legacy/context boundaries.

Proposed documentation write set for the implementation PR:

- Docs/Plans/HANDOFF-DEMO-plan-world-conversation-cutover.md — sync this handoff to the authorized ACTIVE lease, actual merged predecessor facts, exact implementation evidence, and actual current status. Never pre-mark Slice A complete or invent a merge SHA.
- Docs/Roadmaps/ROADMAP-demo.md — record the already-merged #865, #897, and #898 predecessor facts in the consuming implementation PR, and later record only actual Slice A status/evidence. This path is currently in open PR #869's changed-file set. Do not edit or claim it until #869 settles and the file lease is clear; re-anchor and recheck all PRs before activation. If that collision remains, PRIME must explicitly transfer/serialize the path before an ACTIVE lease is issued.

No other paths are included. In particular, do not edit routes/agent.py, APP-STATE storage/projection code, Plan action service code, migrations, shared Agent providers, PlanSurfacePage.tsx or its tests, AppChrome, shared CSS, or any path owned by another lane. If source inspection shows the exact client implementation needs an unlisted path or an owner contract change, stop before editing and return to PRIME for a transfer or split.

### Current collision check

Re-anchored to Buddy main at 402390ca051553a09e844ea57ddf8be3f6217fef. Current open PR filenames were checked against this proposed set. PR #886 touches PlanSurfacePage/AppChrome/shell paths but none of the proposed source paths. PR #887 is isolated to the DOGFOOD prototype/evidence and none of the proposed source paths. PR #869 also edits ROADMAP-demo.md and is an explicit documentation-path collision. Other currently listed open PRs have no overlap with the proposed source paths or handoff path. Recheck before activation; this is not a permanent lease clearance.

## Verification and acceptance plan

The implementation owning boundary is the Plan UI consumer of the existing server APIs. This slice changes no server owner behavior. Wrapper tests prove exact endpoint/method/body handling; mounted tests prove the visible consumer behavior and scope fencing. They do not replace the already accepted server-owned storage/runtime tests or prove product acceptance.

Required focused evidence for the implementation PR:

- Run apps/live-control-ui/src/api/liveApi.worldConversation.test.ts and apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx with the repository Vitest runner.
- Prove server history is the sole source of canonical visible turns after reload/remount; each turn retains historical provenance.
- Prove New Conversation uses the current server pointer/CAS command and hydrates server state. An uncertain command retry reuses the same command identity and expected pointer snapshot.
- Prove World A → World B → World A, Plan/basis changes, and deferred responses cannot cross the visible active conversation. A completed old receipt is reconciled only to its origin.
- Prove Ask pending-envelope persistence precedes dispatch and reload recovery sends byte-for-byte equivalent normalized intent, client_thread_id, turn_id, and committed basis. A changed intent cannot reuse the old key.
- Prove history/API failure does not show local history as canonical or dispatch a local-history fallback.
- Prove pre-existing local bytes are unchanged, explicitly labelled local-only and exportable; neither Ask nor proposal requests contain legacy rows. Prove every Slice A proposal request has empty conversation_history while Review/Apply/Save behavior remains.
- Run targeted TypeScript validation and cumulative base-to-head diff checks. Report the known inherited full-app TS2503 error at ThreatPublicationPanel.tsx:553 if it remains; do not modify outside the lease to clear it.
- Report test commands, exact base/head, all failures and whether they are inherited. Do not describe mocked client tests as a live backend or configured-provider witness.

## Runtime, database, and provider resources

No runtime resource is leased by this design. Focused Vitest tests should use deterministic API fakes and must not start services.

If PRIME requires a real-route consumer witness before implementation acceptance, PRIME must first pin a disposable Application State PostgreSQL fixture, unique port, exact migrations/source revision, Buddy API/UI ports, process owner/PIDs, and teardown procedure. Do not use persistent ports 54330 or 54331. Do not assume PR #898's prior fixture port 55459 remains free. Do not start, stop, migrate, or repoint any shared service without that exact resource pin.

No provider call is needed for the focused UI/transport witness. If a later acceptance gate requires a configured-provider Plan turn, use the established DEMO provider/model budget and record the exact model/runtime evidence; do not substitute a different provider or make an open-ended commitment.

## Failure cases Slice A must preserve

- A removed, foreign, changed, unavailable, or contradictory World/Plan binding fails closed before Ask dispatch.
- Editor draft bytes remain excluded from Ask; only the exact server-resolved committed basis is submitted.
- A delayed history or Ask response from the old World/Plan/basis cannot overwrite the current selection or enter a new conversation.
- New Conversation pointer conflicts never silently clear or replace current history.
- An uncertain retry reuses the exact envelope; it never silently mints a new turn or command identity.
- A pending request for another World, Plan, basis, or conversation remains recoverable without overwriting the active origin.
- Server history unavailability is visible and actionable. Local browser rows are never an implicit transcript fallback.
- Legacy data remains byte-preserved and exportable, with no import, delete, or transcript dual-write.
- Compose/Revise can still produce a reviewable proposal against the captured draft/selection, but receives no conversation history in Slice A. Apply still edits only the draft; ordinary Save remains the commit boundary.
- Graph remains not_requested. No graph retrieval/citation or J1–J6 completion is implied.

## Activation gates

PRIME owns activation, review, and merge coordination. Before assigning the Slice A ACTIVE lease, PRIME must:

1. Independently review and accept this exact bounded design head, including the Slice A temporary empty proposal-history behavior and the legacy preservation/export boundary.
2. Re-anchor the newest Buddy main, inspect current open PRs and all active leases, and pin the exact implementation base/head topology. The current #869 ROADMAP overlap must be cleared or explicitly transferred before including ROADMAP-demo.md in the exclusive write set.
3. Confirm the exact source allowlist above, with the conditional roadmap path handled explicitly, and confirm no server/APP-STATE owner path is needed. If an existing route cannot provide required recovery behavior, return the contract gap to the owning steward instead of expanding this lease.
4. Pin test/runtime resource owners and unique isolated ports if any real-route witness is required. Otherwise confirm the deterministic API-fake test plan and that no shared service will be started.
5. Issue one serial ACTIVE lease with verification evidence, required PR topology, and any exact provider/database/runtime pins. Until that explicit lease exists, this handoff remains BLOCKED and implementation must not start.

The existing main source/design remains useful history if this amendment is superseded. Slice B is not dispatched by Slice A completion; PRIME must re-anchor and grant its own later lease.
