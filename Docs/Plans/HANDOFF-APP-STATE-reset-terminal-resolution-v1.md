# HANDOFF — APP-STATE: terminal reset request resolution v1

**Status:** ACTIVE authority — PRIME authorized this docs-only contract on 2026-10-08 after ARCH's explicit ruling. Implementation dispatch requires this contract PR to merge; no implementation, migration or runtime writes are authorized by the docs lane.
**Owner / steward:** APP-STATE / PRIME, with ARCH contract review.
**Repository / fresh base:** Drakosfire/DungeonMindBuddy, fetched main `0e934cba8041e40e55112c01412f03f26bd83063`.
**Topology:** serial: authority PR → one independent APP-STATE implementation PR on then-current main → independent cumulative review/merge. Merged #1034 is the predecessor, not an unmerged dependency. No atomic replacement reset or additional capability belongs here.
**Docs lane:** `codex/reset-terminal-resolution-contract`, `/tmp/dmb-plan-ask-history`; exclusive write set is this new handoff only.
**Product gate:** No operator experience invitation, fresh conversation/provider witness, live migration or activation until the selected World is fully integrated with verified binding/source proof. The preserved single runtime iteration stays unchanged. This gate permits independent source work and disposable synthetic verification.

## Mission and predecessor facts

Resolve one exact saved New Conversation request through server-backed evidence so it cannot indefinitely block deliberate user action or execute later after being locally retired. Preserve every prior successful receipt, conversation, current pointer, draft and proposal. A fresh conversation is a separate explicit user command against freshly read pointer state, never an automatic continuation of resolution.

#1034 merged at `0e934cba8041e40e55112c01412f03f26bd83063`. Its authenticated read-only exact receipt lookup and byte/scope guarded local clearing for confirmed success remain compatible. Its prepared runtime overlay is not live activation authority. Existing pointer CAS prevents an old absent request after a later revision commits, but an absent request with still-matching pointer can execute late. Existing `agent.command_receipt` requires a real conversation FK and kind new/archive/reopen; it cannot truthfully represent cancellation. Do not insert fake conversation IDs, repurpose another kind, overwrite a successful receipt or drop pending data without terminal evidence.

ARCH approved one resolution capability with these terminal outcomes:

- `confirmed`: the exact original binding already has a verified successful new-command receipt.
- `retired`: an absent original command has an immutable request-bound fence committed before it can have pointer effects.
- `submitted_binding_blocked`: the immutable World/command key is already occupied by a different canonical fingerprint or kind, proving this submitted binding cannot execute. This acknowledges the submitted request's rejection; it does not retire or modify the successful occupant.

Generic pointer CAS conflict, reused resolution-operation ID with changed input, a mismatched prior retirement binding, auth/integrity errors and unavailable state are nonterminal. They never produce a fabricated certificate or clear local recovery bytes.

## Strict request, operation identity and certificate

Use `dmb_agent_new_conversation_resolution_request_v1`: resolution operation UUID; complete original `ConversationCommand` (World, original command UUID, original expected pointer revision and nullable original conversation); and a separate expected current pointer revision/nullable active conversation from a fresh canonical history read. Route World must equal request World. Resolution has no message, draft, replacement command or provider input. The GM actor and time are server derived.

Keep original `request_fingerprint(ConversationCommand)` byte-for-byte unchanged. Separately bind World/command identity and kind. Define the resolution-operation fingerprint from all validated submitted semantic fields, including the full original command identity/basis and current pointer CAS, excluding only its own operation UUID. Pin sorted compact ASCII JSON over typed JSON-mode data (`canonical-json-ascii-v1`), matching Python ensure_ascii behavior. Never hash only partial IDs or raw query strings. Actor/time belong to the immutable record, not caller input.

Use strict nested-versioned `dmb_agent_new_conversation_resolution_record_v1` with World, original command ID/kind, original full request fingerprint and original CAS fields, resolution operation ID/fingerprint and expected current CAS, observed current pointer, outcome, server actor/time, and record serializer/version/digest. The record digest covers the complete canonical record excluding only the digest itself. Exactly one outcome-specific proof is permitted:

- Confirmed: verified exact original successful receipt; a now-archived result still confirms. No inference from today's pointer.
- Retired: durable fence identity/full binding and unchanged observed/result pointer. No created conversation.
- Blocked: occupied immutable receipt identity, kind, canonical fingerprint and digest. No occupant conversation/result payload or body is disclosed. Its canonical fingerprint or kind must actually differ. The occupied receipt/key must remain retained and immutable.

A versioned response wraps this stored record unchanged. Absent records and nonterminal errors are distinct from these terminal outcomes. Clients verify schema, all original and resolution fields/fingerprints, outcome-specific invariants and record digest before offering acknowledgement. No generic 409, missing receipt or changed pointer is a terminal certificate.

## Durable APP-STATE storage and retention

Introduce one append-only `agent.command_resolution` ledger rather than changing successful-receipt meaning. Proposed rows are keyed `(world_id, resolution_operation_id)` and persist strict versioned record plus its explicit identity/fingerprint/outcome fields. An immutable partial unique index on `(world_id, original_command_id)` for outcome retired provides the one durable fence. Confirmed/blocked records may retain separate operation identities, supporting idempotent acknowledgements of different submitted bindings without overwriting a prior certificate. An occupied-receipt reference on confirmed/blocked rows protects the original World/command key with FK retention; absent retirement rows have no fake occupied receipt.

Repository reads/append methods and typed codecs validate consistency between indexed identity/outcome fields and the versioned record. No update/delete method or expiry/pruning is introduced. Persist metadata only; no browser bytes, message/draft bodies, provider response or copied old conversation payload. Failed transaction writes roll back fully. A changed input under the same resolution operation UUID conflicts; it must not obtain another request's stored result.

Verified source inventory at this design base: the only Alembic head is `20261007_0018`, down-revision `20261005_0017`. Candidate next path is `src/application_state/migrations/versions/20261008_0019_agent_command_resolution.py`, down-revision `20261007_0018`. This is not migration activation: re-inventory heads/open migration leases at dispatch. If the head changed, return to PRIME to repin the exact next path/revision before edits. Disposable migration tests are allowed after the implementation lease activates; live migration is held.

## Transaction ordering and delayed request races

Resolution and New Conversation must serialize through the same existing World pointer transaction lock. A missing verified World's logical pointer is 0/null; existing ensure_world_state may create only that lock carrier in a successful resolution transaction. Its visible pointer must remain 0/null, and failed resolution must roll back any carrier/ledger write.

Under that lock:

1. Resolve a stored resolution operation first and compare its full operation fingerprint before checking today's pointer CAS. Exact replay returns the immutable original result after later pointer changes.
2. Inspect original successful receipt and retirement fence before any archive/create/update. Exact successful receipt yields confirmed; immutable different-kind/fingerprint occupancy yields submitted_binding_blocked, preserving its receipt. These are evidence-only outcomes and may confirm a request that won before resolution; never retroactively cancel success because today's pointer changed. A mismatched retired binding yields nonterminal conflict.
3. Only the absent, unfenced retirement path requires the separate current pointer CAS to match. Commit the original request-bound retired record/fence without advancing or redirecting the pointer. Reuse an already verified matching retirement safely, with explicit resolution-operation identity binding; never reinterpret a changed original fingerprint as the same request.
4. Existing New Conversation checks the terminal fence under the same lock before any archive/create/pointer effect. A matching retired request returns a typed terminal rejection; a changed fingerprint conflicts. The original successful receipt path remains exact and immutable. Both success and retirement for the same absent command would be integrity failure, never a fabricated success.

If the old reset wins first, resolution returns its actual confirmation. If retirement wins first, the delayed reset is terminal before all pointer effects. The race must never yield both. Pointer CAS also protects an explicit later fresh command; retries of the retired original cannot redirect that fresh conversation. No provider work exists in resolution.

## API and guarded client settlement

SERVER owns GM/World verification before existence lookup, strict selector/request parsing, request-bound versioned union and nonterminal error mapping. Proposed mutating metadata endpoint: `POST /api/live/agent/worlds/{world_id}/conversation/commands/{command_id}/resolve`, accepting only the versioned resolution request. Add a distinct authenticated read-only exact operation-record GET at `/conversation/commands/{command_id}/resolutions/{resolution_operation_id}` with full original and resolution request binding; no ensure/lock/write/provider in that GET. Preserve #1034's v1 success-receipt lookup contract; absence of a success receipt never means execution failure. Add only exact route patterns to native auth/destination guards; no unsafe automatic replay allowlist expansion.

The UI preserves a resolution envelope/operation identity before an explicit user Resolve action. Unknown/lost response stays saved and can be reconciled by exact operation GET or an explicit same-operation retry. No automatic POST on absent/failed reads. For submitted_binding_blocked, show explicit acknowledgement wording that the submitted binding was rejected; do not claim the occupant was cancelled. Only confirmed, retired, or explicitly acknowledged verified blocked records can settle local bytes.

Capture original saved envelope/storage bytes, resolution bytes, command/operation generation and mounted World/document scope. Immediately before clearing, reread and compare both captured records byte-for-byte; stale scope, reload/remount, replacement, storage/read failure or nonterminal result retains them. Clear only matching local recovery records. Preserve current local thread, submitted message, proposal/review, editor draft and all server history. A fresh New Conversation requires separate user action and a fresh pointer snapshot after settlement; no command chaining, automatic new ID, implicit reset, provider resend or pointer guessing.

Malformed legacy data without a verifiable World/command identity cannot be fenced through invented IDs; retain it with supported diagnostics. It is not a terminal certificate. Wrong World/Plan scope cannot use another envelope's result. No hidden localStorage/React/profile inspection, manual clear or operator data repair is authorized.

## Candidate implementation lane and exclusive path lease

After authority merge, re-fetch main and inspect active leases. Use one isolated `codex/` branch from then-current main. APP-STATE owns its controller/history tests exclusively; coordinate any newly overlapping DOGFOOD lease before edits. Pin exact authority/base, isolated disposable database/output identities and implementation PR topology. The only proposed production/test writes are:

- `src/application_state/agent_conversation/types.py`
- `src/application_state/agent_conversation/repository.py`
- `src/application_state/agent_conversation/service.py`
- `src/application_state/migrations/versions/20261008_0019_agent_command_resolution.py` only after head recheck above
- `apps/live_control_server/models/agent_turn.py`
- `apps/live_control_server/routes/agent.py`
- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/api/liveApi.ts`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `tests/application_state/test_agent_conversation_service.py`
- `tests/application_state/test_agent_conversation_postgres.py`
- `tests/test_agent_conversation_world_retry.py`
- `tests/test_agent_turn_route.py`
- `tests/application_state/test_plan_action_dialogue_postgres.py` only its existing migration-head assertion if the new head is activated
- `apps/live-control-ui/src/api/liveApi.worldConversation.test.ts`
- `apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx`
- This handoff and `Docs/Plans/HANDOFF-APP-STATE-reset-receipt-recovery-v1.md` for truthful predecessor merge and activation settlement only

No root config/lockfile, Core, unrelated presentation, new framework, corpus/provider, atomic supersede-and-create, live database, current runtime or operator storage action. Return to PRIME if storage/contract/path needs exceed this set. Opening one assigned implementation PR is authorized completion after the contract lands; merge and activation remain separate.

## Required owning verification and review limits

- Actual isolated PostgreSQL concurrency in both lock orders: old POST wins → original verified confirmation; retirement wins → delayed old POST cannot archive/create/update/redirect. Assert no partial rows/effects and exact current pointer/history preservation, including no-active 0/null World state.
- Fresh-service/reload readback of all three typed outcomes; exact operation replay before current CAS; changed operation input and original fingerprint conflict; immutable occupied receipt retained with digest/kind verification and no old payload disclosure.
- Explicit later new command commits once against fresh CAS; delayed retired command remains terminal after that advance. Lost success and lost retirement responses recover their original outcomes without fresh reset/provider work.
- Disposable upgrade/downgrade, typed ledger consistency, unique retired fence and receipt FK retention; existing success/CAS and #1034 read-only tests remain valid. No live migration.
- Route GM/World authorization, exact full binding/digests/versioned outcome, wrong World/no existence leak, generic CAS/op-ID/integrity/unavailable nonterminal. Auth transport tests assert actual bearer headers, cookie bootstrap/trusted bounded renewal, origin/redirect guards, and no unsafe automatic resolution/reset replay.
- Synthetic actual controller settlement: explicit verified blocked acknowledgement; confirmed/retired exact bytes only; absent/unavailable/server/storage errors retain; stale World/Plan/mount/generation/replaced bytes cannot clear; reload recovery preserves IDs. Existing failed/interrupted Graph Ask classification, drafts/proposals/current thread and history remain intact.

Run owning affected tests/lint/typecheck, inspect exact cumulative base→head, commit/push/open one bounded implementation PR with evidence limits. Human/operator acceptance and independent review remain real gates; neither green synthetic checks nor this design lift full-World readiness or live activation holds.
