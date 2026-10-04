# HANDOFF — DEMO: cut over Plan conversation to World history (Slice A)

**Status:** The Slice A and Slice B implementations are merged in PRs #900 and #902; both implementation leases are released. This records code integration only. It does not assert J1–J6 or operator/product acceptance.

**Steward:** DEMO task 01a0efc8-f3a8-7be2-a556-33eb338338e8

**Repository:** Drakosfire/DungeonMindBuddy

**Settlement base:** Buddy main at `3d27a0550cb0ffa74fb7ce9cb301435fcaef1eb2` (PR #902 merge). PR #902 merged from independently reviewed head `c5d96dd2ad066fe30e9dcbc90fac7263e8a70ce4`; PR #900 remains recorded at `f8712198848598c5ce83248eb66a54d93c1fd044`. The Slice B design pin is PR #901 head `eb5b7a679c0aad71eb71582649a3f193dd295fa2`, now closed as superseded; its committed design remains preserved at that exact head.

**Topology:** serial. Slice A and the Slice B proposal-context merger are integrated → the next Plan/Graph product acceptance remains a separate, unleased capability recorded in the DEMO roadmap. No implementation or runtime lane is currently active for it.

**Completed Slice A PR:** DEMO: cut over Plan conversation to World history (#900)

**Completed Slice B PR:** DEMO: merge server-owned Plan proposal context (#902)

**Slice A settlement:** PRIME cleared the final review holds on `30f4f36549ece68c173fd577c119a2ab88ceebed` and merged PR #900 at `f8712198848598c5ce83248eb66a54d93c1fd044`. The Slice A branch and seven-path write lease are released. No runtime, provider, database, service, or port was leased for Slice A.

## Accepted predecessor state

The prior #857 handoff treated several dependencies as pending. They are now delivered and must not be represented as open blockers:

- Buddy #857 accepted the original DEMO consumer design at merge 41fe2944468327da852a987685992fc50f91f059, from reviewed head de08a3cc2f24406d1440b771f047ba0b8398a6e8.
- Buddy #859 accepted the separate Plan action-dialogue design at merge 43c4c4daa8e1c17b22953681fe817e6881242b36, from reviewed head c78feb94f37f7612200e2d0962d26d0f5a1326cf.
- Buddy #865 adopted the production World conversation runtime and merged at 1c0320d18c53037308cd7412719fb3e2f0610d99.
- Buddy #897 delivered the Plan-owned exact-basis action/status and completed-context projection and merged at d5de2072f90c27b031f9f55157504915f98a189f, from reviewed head 7da39e47327d8dd941ecb7eb1074a2c8ec028544. Its future cross-source order is accepted_at, source rank Ask=0 / PlanAction=1, source-specific sequence, source record UUID. Each source filters exact-basis eligibility before its own cap; the proposal boundary applies the total cap of six after merge.
- Buddy #898 delivered the APP-STATE exact-basis completed Ask projection and merged at 402390ca051553a09e844ea57ddf8be3f6217fef, from reviewed head 5b8daaa6c8d8fcc825da626de3c0499539cafadd. Its 8 PostgreSQL projection tests and 2 adjacent regressions passed; PRIME independently reran the 8 projection tests and accepted the review.
- Buddy #900 completed the DEMO Plan consumer cutover and merged at `f8712198848598c5ce83248eb66a54d93c1fd044`, from reviewed head `30f4f36549ece68c173fd577c119a2ab88ceebed`. Its seven-path lease is released; the Slice A evidence is recorded below and does not claim product acceptance.
- Buddy #902 delivered the server-owned merger of exact-basis completed Plan-action and Ask pairs, with typed receipt compatibility, a six-pair cap and fail-closed context reads. PRIME independently reviewed and merged head `c5d96dd2ad066fe30e9dcbc90fac7263e8a70ce4` at `3d27a0550cb0ffa74fb7ce9cb301435fcaef1eb2`. The three-path lease is released. PRIME reports 39 proposal tests and 16 owner-projection regressions passed; no provider, live product or Graph acceptance is claimed.
- Existing APP-STATE World conversation identity, visible turn storage, idempotency receipts, and the accepted #865 retry/replay contract remain the owner authority. Browser thread IDs are correlation values, not conversation identity.

These are code-integration facts, not J1–J6, live-demo, or operator acceptance. Slice A consumes these accepted capabilities. It adds no APP-STATE, AGENT-INTERACTION, proposal-service, route, schema, or migration behavior.

## Slice A — one bounded capability

A saved Plan in a verified managed World displays and continues the server-owned World conversation. The UI can start a New Conversation using the existing server command/CAS contract. An Ask whose response is uncertain can be resumed after reload by replaying its exact original durable request identity and intent.

The client consumes these existing routes and their currently accepted wire contracts:

- GET /api/live/agent/worlds/{world_id}/conversation
- POST /api/live/agent/worlds/{world_id}/conversation/new
- POST /api/live/agent/turn

The first two paths include the existing Agent router prefix. At activation, read the exact current route schemas and reuse them. Do not invent a second conversation API or derive server authority from a browser key. The server-issued conversation ID and durable turn receipt remain canonical. The accepted Plan Ask contract continues to resolve the verified World, saved Plan, committed WorkRevision, and exact content digest on the server; mounted draft bytes stay excluded and Graph remains not requested.

### Local operator Agent/Graph authorization

Implementation inspection confirmed that the existing #865 server boundary applies `enforce_native_graph_gm` to `POST /api/live/agent/turn`, World conversation history reads, and New Conversation commands. This authorization is required for graphless Plan Ask as well as Graph-enabled requests. Keep the token in module memory only; attach it only to the matching protected Agent, World conversation, and existing Graph routes. Retain loopback destination validation before fetch and `redirect: error` for protected calls. Do not inject bearer headers globally or include the token in request bodies, recovery envelopes, URLs, logs, history, or exports. A missing or rejected credential must give an actionable UI message and preserve the exact pending Ask/command for explicit retry. The graphless request contract remains unchanged (`graph_request.mode = none`, `graph_selection = null`); local operator authorization does not imply Graph use.

### Canonical history and New Conversation

- On entry to a verified World Plan, load the latest bounded visible World transcript page from the server. Render its accepted surface and work provenance; do not flatten turns from another surface into Plan-owned turns.
- Use the existing limit, before_sequence, and next_before_sequence paging fields. Clearly identify that only the latest page is loaded and offer an Older turns action when next_before_sequence is present. Older-page reads use that cursor. Merge by server sequence and deduplicate by durable server turn identity. Do not claim the page is the full transcript while older turns remain.
- Fence each history-page response against the current World, active server conversation pointer/revision, and mounted request generation. A pointer change while an older page is loading discards that stale page. Switching Plans within the same World does not relabel World-wide history as Plan-owned.
- New Conversation sends the existing expected pointer revision, expected active conversation identity, and durable command ID required by the server CAS contract. Persist and replay the exact command envelope after an uncertain transport result. Do not silently mint a replacement command ID. On a pointer conflict, retain visible current state, fetch the current server state, and require a deliberate new command.
- A confirmed new conversation hydrates from the server response or a fresh server history read. It does not create a parallel browser conversation or clear unrelated pending envelopes.

### Ask and durable uncertain retry

- Resolve the current committed Plan basis using the existing server read before preparing a turn.
- Persist the exact normalized wire request plus its separate local origin metadata before dispatch. The current WorldPlanAgentTurnRequestV1 wire body keeps its accepted fields: client_thread_id, turn_id, surface, owner_scope, primary_work (object_id, expected_revision, expected_revision_n, expected_content_sha256), client_work_state, graph_request=none, graph_selection=null, and message. Do not add a WorkRevision UUID or other field to the public request. Store the server-read WorkRevision ID and full basis tuple (World, document, object revision, WorkRevision ID, revision number, content digest) only as local origin metadata.
- Key pending envelopes by verified World, Plan document, full local basis tuple, and original durable turn identity. Keep distinct envelopes for other Worlds, Plans, bases, or turns. Store any server-issued origin conversation/pointer ID as metadata; never treat a client thread ID as canonical conversation identity.
- If exact request persistence fails or browser storage is unavailable, show an actionable error and do not dispatch the turn. A malformed pending envelope is not repaired by minting a new request.
- After an uncertain result or reload, show an explicit recovery action and replay the exact stored wire request. Do not automatically create a fresh turn ID, client thread ID, or changed intent. A deliberate new user question gets a new durable turn identity.
- Reconcile a confirmed result under the canonical conversation returned by the durable server receipt. The pre-dispatch conversation pointer is observation metadata, not a CAS constraint. Navigation, basis advance, or New Conversation cannot overwrite the pending envelope or inject a result into a different active transcript; refresh World history and explain when the receipt belongs to another conversation. If the server cannot resolve an old receipt, return the contract gap to PRIME; do not expand the Buddy client lease into server changes.
- Remove a pending envelope only after the durable server receipt/result is confirmed. An unavailable history service or ambiguous result has an actionable pending/error state; it never falls back to browser transcript as canonical history.

This envelope is local transport-recovery state, not a second conversation store: it contains only the exact outbound request and separate origin key, is not rendered as a completed transcript, and is not sent as extra context.

The existing Plan action request remains an independent durable operation. Empty history applies only when preparing a new Slice A proposal. If a proposal request is already in flight, preserve its captured request body, original idempotency key, and retry intent across conversation changes. Do not rewrite that submitted request or automatically redispatch it.

### Legacy browser history

Existing browser-local Plan conversation bytes may contain turns without exact server provenance and Plan edit rows with proposal data. Preserve those bytes unchanged and exportable. Clearly mark any surfaced copy as legacy and local-only. Keep it separate from server history; never use it for current Ask or Compose/Revise model context.

This slice does not delete rows, auto-import, dual-write transcript turns, or fall back to local history when a server read fails. Do not call the APP-STATE legacy importer. A local export is a copy for user recovery; exporting does not change storage.

### Compose/Revise during Slice A

Preserve the current Compose/Revise instruction, mounted-draft and selection capture, proposal validation, Review, Apply-to-editor, and ordinary Save behavior. Slice A does not implement a context merger. Until Slice B, send an empty conversation_history to the proposal boundary; do not pass any legacy local rows, local Ask turns, or the World transcript. This temporarily pauses conversational carry-over for Compose/Revise while keeping the editing action usable. State this behavior clearly in the Plan UI.

Slice B restores the six-pair behavior only through the authoritative proposal boundary: merge the exact-basis completed Plan-action projection from #897 with the exact-basis Ask projection from #898; filter each source before its cap; sort by accepted time, source rank (Ask=0, PlanAction=1), source-local sequence and source UUID; then enforce six total pairs. Client history cannot add, remove, or reorder that context. This capability is integrated in #902; the merge does not establish a live provider, Graph retrieval, or end-to-end Plan acceptance witness.

### Explicit exclusions

Slice A did not include browser-to-server legacy import; deletion, migration, or dual-write of old conversation bytes; a proposal-context merger; a new route, backend schema, database migration, provider runtime, Agent framework, Graph request, automatic Plan/Graph context, visual/card redesign, PlanSurfacePage/AppChrome work, CSS refresh, J1–J6 claim, or product-acceptance claim. It did not edit the #886 navigation shell paths.

## Slice A implementation write set (released at merge)

PRIME adopted the pinned design at `b1a2babeb0fff109d3625e30ca6785749ab8f332`, re-anchored Buddy main and open PRs/leases, and issued the serial Slice A lease from base `402390ca051553a09e844ea57ddf8be3f6217fef`. The isolated lane was `codex/demo-plan-world-conversation-slice-a`; PR #900 merged at `f8712198848598c5ce83248eb66a54d93c1fd044` and the lease is released. This section is historical, not a current write lease.

The initial exclusive source write set was:

1. apps/live-control-ui/src/api/types.ts — typed shapes for the existing World conversation and New Conversation responses.
2. apps/live-control-ui/src/api/liveApi.ts — typed GET/POST wrappers for the existing routes.
3. apps/live-control-ui/src/api/liveApi.worldConversation.test.ts — new route/method/body/response wrapper tests.
4. apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx — server transcript hydration, New Conversation, durable pending Ask recovery, isolated legacy export/presentation, and empty Slice A proposal history.
5. apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx — new mounted consumer tests for history, scope fences, retries, New Conversation, and legacy/context boundaries.

PRIME subsequently amended this ACTIVE lease to add one path for the confirmed #865 authorization boundary and its regression evidence:

6. apps/live-control-ui/src/api/liveApi.test.ts — correct obsolete graphless/remote expectations and cover in-memory Agent/World conversation credentials, loopback rejection, token clearing, and no bearer leakage to unrelated routes. This addition does not change server authorization policy.

The documentation path in the completed Slice A implementation PR was:

- Docs/Plans/HANDOFF-DEMO-plan-world-conversation-cutover.md — sync this handoff to the authorized ACTIVE lease, actual merged predecessor facts, exact implementation evidence, and actual current status. Never pre-mark Slice A complete or invent a merge SHA.

Docs/Roadmaps/ROADMAP-demo.md is not in the Slice A write set. Its predecessor/status truth-sync is deferred to a separately cleared path lease after the current #869 roadmap edit settles. That unrelated documentation collision does not block the client capability.

No other paths are included. In particular, do not edit routes/agent.py, APP-STATE storage/projection code, Plan action service code, migrations, shared Agent providers, PlanSurfacePage.tsx or its tests, AppChrome, shared CSS, or any path owned by another lane. If source inspection shows the exact client implementation needs an unlisted path or an owner contract change, stop before editing and return to PRIME for a transfer or split.

### Slice A activation-time collision check

At Slice A activation, the source paths and handoff were checked against open PRs and active leases. Before PR #900 creation, remote main and its branch were rechecked at `402390ca051553a09e844ea57ddf8be3f6217fef`. PR #899 was the pinned design artifact at `b1a2babeb0fff109d3625e30ca6785749ab8f332` and shared only this handoff path; its merge was not an activation gate. The then-open PRs #886, #887, #869, #844, #826, #798, #781, #765, #764, #763, #761, and #760 had no source-path overlap. This is historical clearance, not current PR clearance.

### Slice B implementation lease (released at merge) and collision settlement

PRIME accepted the design contract in PR #901 at head `eb5b7a679c0aad71eb71582649a3f193dd295fa2`, then issued the Slice B ACTIVE implementation lease from `origin/main` `f8712198848598c5ce83248eb66a54d93c1fd044`. The isolated lane was branch `codex/demo-plan-proposal-context-merger`; PR #902 merged at `3d27a0550cb0ffa74fb7ce9cb301435fcaef1eb2`, releasing this lease. The exact former write set was:

1. `apps/live_control_server/services/plan_document_edit_proposal.py`
2. `tests/test_world_plan_edit_proposal.py`
3. `Docs/Plans/HANDOFF-DEMO-plan-world-conversation-cutover.md` — this backward-looking record of the completed Slice A and current Slice B lease.

PR #901 was closed as superseded after #902 merged; its exact design head remains preserved as the pin. It shared this handoff path, and #902 settled the current predecessor and implementation status here. At settlement, PR #869 remains open at head `1a720db429f5e6d1e13181cd19f6f02f78e3480e` and adds 33 roadmap lines for movement/J4. PRIME has placed that work on HOLD and serialized roadmap ownership for this settlement. The exact 33-line addition is preserved in the roadmap; PR #869 must be restacked on the settlement merge and drop its already-integrated roadmap hunk before any later review or merge. No #869 source files were edited. Other refreshed open PRs were #887, #886, #844, #826, #798, #781, #765, #764, #763, #761 and #760; none overlaps the former Slice B source/test paths. No new implementation lane is active.

## Slice A verification and acceptance record

The completed implementation owning boundary was the Plan UI consumer of the existing server APIs. It changed no server owner behavior. Wrapper tests prove exact endpoint/method/body handling; mounted tests prove the visible consumer behavior and scope fencing. They do not replace the already accepted server-owned storage/runtime tests or prove product acceptance.

Slice A focused verification checklist, satisfied for PR #900:

- Run apps/live-control-ui/src/api/liveApi.worldConversation.test.ts and apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx with the repository Vitest runner.
- Run apps/live-control-ui/src/api/liveApi.test.ts for the amended authorization path. Prove graphless Plan Ask, World history, New Conversation, and existing Graph calls use the in-memory bearer credential and loopback-only transport; prove non-loopback rejection happens before fetch, clearing removes the token, and unrelated endpoints receive no bearer header. Prove an HTTP 401/403 gives actionable recovery guidance without replacing or automatically replaying the pending request.
- Prove the wrappers call the exact /api/live/agent/worlds/{world_id}/conversation and /api/live/agent/worlds/{world_id}/conversation/new routes with the accepted limit/before_sequence and CAS command fields.
- Prove the latest page is clearly identified, older-page retrieval uses next_before_sequence, turns remain in server order without duplicates, and a pointer change during paging fences the stale response.
- Prove server history is the sole source of canonical visible turns after reload/remount; each turn retains historical provenance.
- Prove New Conversation uses the current server pointer/CAS command and hydrates server state. An uncertain command retry reuses the same command identity and expected pointer snapshot.
- Prove Ask pending-envelope persistence precedes dispatch and reload recovery sends byte-for-byte equivalent normalized wire intent, client_thread_id, turn_id, and accepted committed-basis fields. Verify the WorkRevision UUID stays in local origin metadata and is not added to the request body. A changed intent cannot reuse the old key.
- Simulate unavailable or throwing local recovery storage and prove no Ask dispatch occurs.
- Prove World A → World B → World A, Plan/basis changes, and deferred responses cannot cross the visible active conversation. A completed receipt follows the canonical conversation returned by that durable receipt and is not inserted in a different active conversation.
- Prove history/API failure does not show local history as canonical or dispatch a local-history fallback.
- Prove pre-existing local bytes are unchanged, explicitly labelled local-only and exportable; neither Ask nor proposal requests contain legacy rows. Prove every newly prepared Slice A proposal request has empty conversation_history while Review/Apply/Save behavior remains.
- Hold an existing PlanAction request across a conversation change. Prove its captured body and idempotency key are unchanged, no automatic second dispatch occurs, and the existing same-key uncertain retry reuses the original request.
- Run targeted TypeScript validation and cumulative base-to-head diff checks. Report the known inherited full-app TS2503 error at ThreatPublicationPanel.tsx:553 if it remains; do not modify outside the lease to clear it.
- Report test commands, exact base/head, all failures and whether they are inherited. Do not describe mocked client tests as a live backend or configured-provider witness.

### Slice A final implementation evidence (before merge)

- Exact implementation base: `402390ca051553a09e844ea57ddf8be3f6217fef`. The assigned remote branch was still at that base during the final pre-PR re-anchor; the implementation commit/head is recorded by its PR metadata.
- From `apps/live-control-ui`, `/home/drakosfire/.local/bin/rtk npm test -- src/api/liveApi.test.ts src/api/liveApi.worldConversation.test.ts src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx src/planSurface/WorldPlanAgentReviewedEdit.integration.test.tsx` passed: 4 files, 124 tests.
- The Ask recovery regression loses the first response after a receipt is accepted in conversation B, then moves the active pointer to C and advances the Plan before retry. Exact replay B is accepted from the durable-receipt trace and original request/Plan origin; the pre-dispatch conversation A is observation metadata, not a server CAS constraint. The saved request and turn ID are reused, no current Plan basis is read on retry, and B's answer is not inserted into active C. A null-basis response built from the actual request but lacking replay proof remains pending.
- The paging regression starts an older-page fetch, confirms a coherent New Conversation receipt while it is in flight, discards the stale page, and then loads a positive-sequence row through the refreshed cursor.
- A provider-backed consumer test seeds a full-cap legacy Agent thread, composes and applies through the real `AgentInteractionProvider` storage, reloads the proposal thread, and verifies the original legacy thread bytes stay unchanged and export byte-for-byte.
- `/home/drakosfire/.local/bin/rtk npm run typecheck` reports only the inherited `src/statblocks/publication/ThreatPublicationPanel.tsx(553,77): error TS2503: Cannot find namespace 'JSX'.` No out-of-lease file was changed to address it. `git diff --check` passes.
- The API and World transcript tests use deterministic fakes. The provider-backed test exercises actual local Agent storage with a deterministic proposal API/edit bridge. None is a live server, configured-provider, or product-acceptance witness.

### Slice A independent review checkpoint

PRIME first returned HOLD on `dde188505056f73373165c462aaf485971ac832e` for completed-receipt replay handling, stale paging lock recovery, and proposal writes into the legacy Agent thread. After the first repair, PRIME cleared the paging and legacy-preservation findings and identified the remaining replay-pointer issue on `b5340fb9b8724bd2b55c204ead70aebc47151c89`. The final head `30f4f36549ece68c173fd577c119a2ab88ceebed` treated the server receipt conversation as authority and added A→B replay while C is active, a request-correlated null-basis negative case, and coherent positive-sequence paging fixtures. PRIME cleared the holds and merged PR #900 at `f8712198848598c5ce83248eb66a54d93c1fd044`. This does not imply Slice B design acceptance or product acceptance.

## Runtime, database, and provider resources

Slice A leased no runtime resource. Slice B used PRIME's disposable PostgreSQL 16.15 fixture at loopback port 55461 for tests only; the owner fixture created/migrated/dropped unique test databases. PRIME released the fixture after the independent review; SERVER owns container cleanup. Do not use port 55461 again. No provider or live application service was used by #902. Persistent ports 54330, 54331 and 55460 remain outside this lane.

## Failure cases Slice A must preserve

- A removed, foreign, changed, unavailable, or contradictory World/Plan binding fails closed before Ask dispatch.
- Editor draft bytes remain excluded from Ask; only the exact server-resolved committed basis is submitted.
- A delayed history or Ask response from the old World/Plan/basis cannot overwrite the current selection or enter a new conversation.
- New Conversation pointer conflicts never silently clear or replace current history.
- An uncertain retry reuses the exact envelope; it never silently mints a new turn or command identity.
- A pending request for another World, Plan, basis, or conversation remains recoverable without overwriting the active origin.
- Server history unavailability is visible and actionable. Local browser rows are never an implicit transcript fallback.
- Legacy data remains byte-preserved and exportable, with no import, delete, or transcript dual-write. New Compose/Revise proposal turns use their own marked browser thread; the provider never prepends them into the prior legacy record.
- Completed receipt replay with a null `content_basis` is accepted only with the existing durable-receipt trace, exact request/turn correlation, a reused server conversation ID, and saved World/Plan/content origin matching the original request. The pre-dispatch conversation pointer is metadata, not an acceptance constraint; the client never treats a current Plan read as historical provenance or inserts the result into a different active conversation.
- A World-history generation change clears older-page loading state; a prior in-flight page cannot block a later request on the refreshed cursor.
- Compose/Revise can still produce a reviewable proposal against the captured draft/selection, but receives no conversation history in Slice A. Apply still edits only the draft; ordinary Save remains the commit boundary.
- Graph remains not_requested. No graph retrieval/citation or J1–J6 completion is implied.

## Slice A and Slice B implementation settlement

PRIME independently reviewed and merged Slice A PR #900 at `f8712198848598c5ce83248eb66a54d93c1fd044`. PRIME then reviewed Slice B head `c5d96dd2ad066fe30e9dcbc90fac7263e8a70ce4` and merged PR #902 at `3d27a0550cb0ffa74fb7ce9cb301435fcaef1eb2`. The Slice B implementation lease is released. PR #901 was closed as superseded, retaining design head `eb5b7a679c0aad71eb71582649a3f193dd295fa2` as immutable history. No merge claims product acceptance.

PRIME reports that its independent review passed 39 proposal tests and 16 owner-projection regressions; the author run also passed Ruff and cumulative diff checks. These are code-level witnesses. No provider call, live active-surface conversation, Graph retrieval/citation, reviewed Apply→ordinary Save→reload flow, or J1–J6/operator acceptance was performed for #902.

The Slice B design remains preserved at closed [PR #901](https://github.com/Drakosfire/DungeonMindBuddy/pull/901), head `eb5b7a679c0aad71eb71582649a3f193dd295fa2`. The next product acceptance slice and its missing Graph/runtime contracts are recorded in the DEMO roadmap; that work has no implementation or runtime lease.
