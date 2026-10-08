# HANDOFF — APP-STATE: reset receipt recovery v1

**Status:** ACTIVE — PRIME authorized this authority-only PR on 2026-10-08. Implementation dispatch requires this handoff's merge and explicit controller lease release.
**Owner/steward:** APP-STATE / PRIME.
**Repository:** Drakosfire/DungeonMindBuddy.
**Fresh design base:** `3c8ad79a2008a20b75bd7d8791d139ad1404c75b` (fetched remote main).
**Topology:** serial: docs-only authority PR → separate RECOVERY implementation PR → independent review/merge. No runtime activation is authorized.
**Lane:** `codex/reset-receipt-recovery-contract`, isolated `/tmp/dmb-plan-ask-history`; this PR writes only this file. No ports, services, databases or live browser state are owned.

## Mission and current facts

Confirm a previously submitted New Conversation command through its durable receipt without resending it, changing a World pointer, or losing conversation history or draft/proposal state.

`agent.command_receipt` already persists World/command ID, kind, canonical request fingerprint, original pointer binding and committed result. `AgentConversationService.new_conversation` locks the pointer, checks receipt replay before pointer CAS, and atomically archives/creates/updates/inserts. Preserve that POST behavior exactly. A retry with an absent receipt can create a conversation, so it is not read-only reconciliation.

The UI saves a versioned original command envelope and disables New Conversation while it remains pending. It clears that envelope after POST confirmation or rejection. History refresh does not reconcile reset receipts; current pointer alone cannot prove which command ran. Graph Ask outcomes are a separate receipt/history lifecycle and must not be relabeled or pruned by this slice.

## Exact read-only contract

Add GM-authorized `GET /api/live/agent/worlds/{world_id}/conversation/commands/{command_id}` with required original `expected_pointer_revision` and required `expected_active_conversation_id` query values. Specify a single canonical representation for null (literal `null`); reject omission, malformed UUID/revision and extra selectors. Verify World access before lookup; unauthorized or wrong-World requests must not reveal whether another World's command exists.

Construct the existing strict `ConversationCommand` with all fields. Use existing `request_fingerprint(command)` unchanged: canonical model serialization excludes command ID, while the lookup separately binds World/command ID and checks command kind `new`. Do not invent a partial-ID digest or hash HTTP query strings. Return only a verified existing receipt after exact fingerprint/kind comparison. No `ensure_world_state`, pointer lock, archive, insert, CAS, provider, current Plan/Graph resolution or implicit mutation is allowed.

Use strict versioned response `dmb_agent_new_conversation_status_v1` containing World, command ID, command kind, expected pointer revision and nullable expected conversation, canonical request fingerprint, status (`confirmed` or `absent`), and nullable nested `dmb_agent_new_conversation_receipt_v1`. Confirmed nested receipt contains created conversation ID, committed active conversation ID, committed pointer revision and recorded timestamp. It must establish a fresh created conversation, committed active ID equal to that created ID, and committed revision greater than expected. Absent has no receipt and makes no statement about execution failure. A binding/kind mismatch returns a typed conflict without disclosing unrelated receipt fields; unavailable/unauthorized remain errors.

A now-archived created conversation remains valid confirmation of the original command. Do not require its committed result to equal today's active pointer. Do not return a fabricated receipt from current pointer state.

## Client reconciliation

The client submits the existing saved envelope internally to the GET, never reconstructing its basis from current history. Verify response schema, World, command ID/kind, all original pointer fields, full canonical fingerprint and receipt result invariants before clearing anything. Client fingerprint computation must match the existing server codec; prove exact bytes with shared synthetic vectors.

Capture exact saved envelope bytes and storage key, mounted World/document scope, command generation and async generation. Clear only if all are still current and a compare-before-clear reread equals the captured bytes. Replacement, remount, World/document change, duplicate identity, parse failure or storage failure retains the record and reports honest uncertainty. Absent, conflict, unauthorized and unavailable retain it. No automatic POST/retry/new command or pointer inference.

Confirmation clears only the matching local recovery envelope and refreshes canonical history. It does not rotate current local thread, erase submitted messages, discard proposal/review state, alter editor/draft text, or prune conversation/Graph history. Existing explicit POST reset behavior stays unchanged. Expose status checking and enough diagnostic metadata for supported operator inspection; do not expose credentials or message/draft bodies.

## Implementation activation and exclusive expected write lease

Re-fetch main and inspect open PRs/leases at dispatch. DOGFOOD still owns the controller and history-test presentation lease under #1007 head `65571f526df5eb69ab104bd49f3440c24ca676ef`; PRIME must explicitly record its release before implementation writes those paths. This docs PR grants no overlapping write permission.

Preferred implementation base is then-current fetched main. If #1007 remains unmerged and its presentation code is required, PRIME must pin a stacked implementation parent at exactly `65571f526df5eb69ab104bd49f3440c24ca676ef`, record refreshed base/head, and merge #1007 before rebasing/merging RECOVERY. Do not silently consume the live UI/backend composition as a source base. If no presentation dependency exists, use main and name the released lease; serial RECOVERY authority/implementation order remains required.

Closed candidate implementation set, activated only after these gates:

- `src/application_state/agent_conversation/service.py`
- `src/application_state/agent_conversation/types.py` only if needed for strict lookup outcome
- `apps/live_control_server/models/agent_turn.py`
- `apps/live_control_server/routes/agent.py`
- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/api/liveApi.ts`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `tests/application_state/test_agent_conversation_service.py`
- `tests/application_state/test_agent_conversation_postgres.py`
- `tests/test_agent_conversation_world_retry.py`
- `tests/test_agent_turn_route.py` only for existing owning route fixtures
- `apps/live-control-ui/src/api/liveApi.worldConversation.test.ts`
- `apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx`
- This handoff for truthful activation/predecessor settlement only

No repository SQL/schema/migration, configuration, provider, unrelated presentation, Graph recovery or live corpus changes. Return to PRIME if the set or contract must expand. Use isolated checkout and disposable fixtures/output paths; no live database writes, runtime activation, browser recovery clicks or manual storage edits.

## Required boundary evidence

1. Actual durable repository/service readback through a fresh service: exact receipt confirmed; absent remains absent; changed full pointer binding, command kind, ID or World does not confirm. Prove zero writes, including missing World state; existing POST CAS/replay semantics remain unchanged.
2. Route GM/World authorization and strict versioned response, canonical full-request fingerprint vectors, null encoding and invalid/extra selectors. Wrong World cannot probe another World's command.
3. Client GET only, no POST/provider calls on confirmed/absent/conflict/unavailable; exact byte fingerprint and response binding rejection.
4. Controller confirmed receipt clears only exact unchanged envelope; archived result confirms; absent retains. Stale scope/generation and replaced envelope cannot clear; storage failure retains. Draft, proposal, current thread and history remain intact.
5. Separate completed/failed/interrupted Graph records retain their existing classification and strict V3 reconciliation behavior; no all-failed inference or blind pruning.

Run only owning affected checks plus lint/typecheck as applicable, inspect exact cumulative base→head diff, commit/push/open one implementation PR after authority merge and lease release. Record author evidence limits. PRIME/independent review owns merge; rollout is separate explicit authority. This handoff carries no private live IDs, receipt contents or operator drafts.
