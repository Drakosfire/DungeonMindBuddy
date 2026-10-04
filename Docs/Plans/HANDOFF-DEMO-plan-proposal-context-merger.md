# HANDOFF — DEMO: merge server-owned Plan proposal context

**Status:** BLOCKED — this is a concrete design contract only. It grants no source write lease, implementation branch, provider, database, service, port, or runtime authority.

**Steward:** DEMO task 01a0efc8-f3a8-7be2-a556-33eb338338e8

**Repository:** Drakosfire/DungeonMindBuddy

**Authority base:** Buddy `main@f8712198848598c5ce83248eb66a54d93c1fd044` (PR #900 merge). PRIME reviewed implementation head `30f4f36549ece68c173fd577c119a2ab88ceebed` and merged #900 at this base.

**Accepted source contracts:**

- PR #897 delivered the Plan-owned action/status and completed-context projection. Reviewed head: `7da39e47327d8dd941ecb7eb1074a2c8ec028544`; merge: `d5de2072f90c27b031f9f55157504915f98a189f`.
- PR #898 delivered APP-STATE's exact-basis completed Ask projection. Reviewed head: `5b8daaa6c8d8fcc825da626de3c0499539cafadd`; merge: `402390ca051553a09e844ea57ddf8be3f6217fef`.
- PR #900 delivered the DEMO Plan consumer cutover. Reviewed head: `30f4f36549ece68c173fd577c119a2ab88ceebed`; merge: `f8712198848598c5ce83248eb66a54d93c1fd044`. Its seven-path lease is released.
- PR #899's accepted Slice A design remains pinned at `b1a2babeb0fff109d3625e30ca6785749ab8f332`; PRIME closed it as superseded after #900 merged.

**Topology:** serial — #897 Plan-action context and #898 Ask context → #900 Plan consumer cutover (complete) → this separate server-owned proposal-context merger. Later automatic Plan/Graph context remains a distinct capability. No implementation lane is active.

**Future implementation PR title:** `DEMO: merge server-owned Plan proposal context`

## One bounded capability

For a saved Plan in a verified managed World, the existing Plan proposal boundary supplies Compose/Revise with at most the six newest completed dialogue pairs for the exact current committed Plan basis. It obtains those pairs from the existing Plan-action completed-context projection and APP-STATE completed-Ask projection, merges them on the server, and converts them to the existing role/content provider-history field.

Plan remains the active surface instance for this request. The context merger is surface-aware through the verified World, current Plan work identity and committed basis; the existing client response fence keeps the action attached to its originating surface instance, draft/selection capture and action identity. It does not introduce a privileged “Plan Agent” identity, a new conversation engine, or a general Agent framework. Existing authorization and allowed-tool behavior remain unchanged; Graph stays unrequested.

The committed basis selects historical context. The current mounted draft, caret/selection and instruction remain explicit captured proposal inputs under the existing request contract; they do not become committed context. Ask and Plan-action context are inputs to one proposal action, not new World transcript turns.

## Current baseline and owner boundary

PR #897 provides `PlanActionDialogueService.completed_context(basis, limit=6)`. Each returned action carries its full basis plus a safe assistant summary, source sequence, accepted time and action identity. The proposal boundary checks each returned action basis against the exact requested basis before use. The owner projection returns only completed eligible rows in chronological order; pending, failed and indeterminate actions do not consume the source cap.

PR #898 provides `AgentConversationService.list_completed_plan_ask_context(verified_world_id, basis, limit=6)`. Pass the full `PlanAskContextBasis` constructed from the same server-resolved basis and verified World. The owner query requires that basis, filters eligibility before its own cap and returns visible completed Ask pairs in chronological source order. `CompletedPlanAskPair` contains source kind, sequence, record ID, accepted time, question and answer; it does not carry a basis field. The proposal boundary proves it supplied the exact basis to the owner projection, and relies on that owner's filtering contract rather than checking a nonexistent basis on each Ask pair. The projection contains no hidden provider history.

The existing World Plan proposal service already reserves a durable Plan action before provider dispatch and checks an existing idempotency key before rebinding to current committed Plan content. The current request model still accepts `conversation_history`, and the current action fingerprint and provider prompt include it. Slice B changes that behavior at the Plan proposal service boundary: client history remains syntactically accepted for current wire compatibility, but the server neither trusts it as context nor treats it as part of submitted intent.

No owner projection, APP-STATE schema, Plan-action schema, public route, request model, or database migration is added by this design. The proposal service calls the already merged source-owner projections.

## Submitted intent and receipt-first retries

For a newly reserved action, the idempotency key and fingerprint identify explicit action inputs:

- server-resolved full basis: World ID, Plan document ID, object revision, WorkRevision ID and number, and content SHA-256;
- action type and target kind;
- exact instruction;
- captured draft SHA-256; and
- selected-text SHA-256 (the existing empty-text digest for a caret target).

For a new action, the service resolves the full basis before reservation. The request carries World ID, Plan document ID, object revision and content digest; WorkRevision UUID and revision number remain server-owned. A receipt hit compares those incoming wire fields to the saved basis and uses that receipt's WorkRevision UUID/revision number, without resolving the current Plan.

The new fingerprint excludes `conversation_history`, projection results, active conversation pointer, timestamps, provider state, and other mutable history. The fingerprint does not contain draft or selected-text bytes; their existing digests and request validation remain the input witness. Same key plus the same explicit intent is the same action even if client history changes. Reusing the key with a changed instruction, draft/selection digest, target or wire basis conflicts before context reads or provider work.

**Receipt-first compatibility across fingerprint versions:** #897 rows may have a stored fingerprint produced by the old algorithm, which included client history. On any existing-key hit, use the saved receipt basis for its immutable WorkRevision UUID and revision number, then compare incoming wire World ID, document ID, object revision and content digest with that saved basis. The request has no WorkRevision UUID or revision-number field; do not resolve current Plan content or require client values for those saved coordinates on a receipt hit. Compare remaining explicit intent directly with persisted typed action type, target kind, instruction and draft digest.

Selection comparison follows the target's persisted representation. For `replace_selection`, require the validated selected-text digest to equal the receipt's persisted `selected_text_sha256`. For `insert_at_caret`, require the validated selected text to be empty and the receipt's persisted `selected_text_sha256` to be `None`; #897 intentionally stores no digest for a caret target even though the old fingerprint included SHA-256 of the empty string. Treat `None` as the empty selection only for `insert_at_caret`, never as a wildcard or a match for nonempty selection. Do not require a new history-free fingerprint to equal an old history-bearing fingerprint. This preserves pending and terminal receipts when a retry's mutable history differs, without schema change, current-Plan read or context read. If a receipt lacks or contradicts a field needed for the comparison, return the existing conflict/error path before context reads or provider work; do not guess from unavailable original history. New reservations use the new history-free fingerprint.

On a retry, the service first looks up the existing action receipt and compares the explicit intent against its saved basis and persisted typed fields as described above. It does not resolve current committed Plan content, read either context projection or call the provider on an idempotency hit:

- `pending`: report pending, do not redispatch;
- `completed`: preserve the accepted #897 completed-action response semantics; the proposal payload is not replayable;
- `failed` or `indeterminate`: report the truthful terminal state and require a deliberate fresh user intent/key;
- changed explicit intent for the same key: return the existing conflict.

Only a newly reserved action may read Ask/PlanAction context and make one provider operation. A concurrent same-key loser follows the existing reservation/reconciliation contract and cannot read context or dispatch. A context-projection failure fails closed before provider dispatch and records a truthful terminal action failure through the existing action CAS; an ambiguous persistence result follows #897 recovery semantics. There is no client-history fallback.

## Exact-basis source reads and deterministic merge

After resolving the verified World and exact current committed Plan basis, and after the new action reservation succeeds:

1. Call `PlanActionDialogueService.completed_context(basis, limit=6)`.
2. Build `PlanAskContextBasis` from that same server-resolved basis and call `AgentConversationService.list_completed_plan_ask_context(world_id, ask_basis, limit=6)`.

Each owner projection applies its own completed/visible eligibility before its maximum-six source cap. PlanAction rows carry basis and must be checked against the requested full basis. Ask context basis is enforced by the exact `PlanAskContextBasis` input and the #898 owner query; returned Ask pairs do not repeat it. Do not query the status/recovery projection for model context. Do not pass local legacy rows, the full World transcript, non-Plan Ask turns, client-provided pairs, replacement Markdown, Apply/Save receipts, provider traces or hidden state.

Tag each eligible pair for sorting:

- Ask: `(accepted_at_utc, 0, source_sequence, source_record_uuid)`;
- PlanAction: `(accepted_at_utc, 1, action_sequence, action_uuid)`.

Sort the combined rows by this tuple in ascending order. The source rank is Ask=0, PlanAction=1. UUID comparison uses the canonical source record UUID. Keep the last six rows after sorting, preserving that ascending chronological order; these are the six newest eligible pairs across both sources. Flatten each Ask pair to user question / assistant answer and each PlanAction pair to user instruction / assistant summary. Do not deduplicate equal text across distinct source records.

Convert the six pairs to at most twelve existing `PlanEditHistoryMessage` role/content messages. Leave messages of 4,000 or fewer Python Unicode code points unchanged. For a longer message, retain the longest leading prefix that fits with the visible suffix ` …[truncated]`, so the complete output is at most 4,000 code points. Apply the same deterministic rule to Ask questions/answers and PlanAction instructions/summaries, without changing any stored source record. The server-built list replaces client `conversation_history` for provider input. No source metadata or idempotency fields are sent as dialogue text.

The accepted cross-source ordering comes from #897: `(accepted_at, source rank Ask=0 / PlanAction=1, source-specific sequence, source record UUID)`. Each owner projection uses its own database unit of work. The reads are independent exact-basis reads; the combined context is not a globally atomic cross-owner snapshot. This is accepted for generation context, which is not authoritative state. A future requirement for “newest six as of one instant” needs a shared snapshot or watermark and is a separate capability. If either read fails, if the server-built Ask basis differs from the exact resolved basis, or if a returned PlanAction row carries a different basis, fail the reserved action before provider dispatch; never generate from one source alone or fall back to client history.

## Surface, work and response origin

Keep the existing Plan surface instance and proposal-action path. The merger uses server-verified World and exact committed Plan work as the eligibility basis. The separately captured mounted draft and selection remain explicit current request inputs. No surface registry, tool policy, Agent identity, route, provider or transcript lifecycle is changed.

The durable PlanAction ID, idempotency key, World, Plan identity and committed basis remain the proposal's origin. A late response stays attached to that original action/surface/work basis and cannot attach to a newly selected Plan or surface. A Plan action is not an APP-STATE Ask turn and never writes to the World transcript.

The operator is evaluating Of Conks & Cons / A Wild Sheep Chase through the existing card presentation. That is a presentation lens only: this contract changes no cards and grants no card implementation lease. Preserve the current Compose/Revise → Review → Apply-to-editor → ordinary Save workflow.

## Failure cases and owning-boundary evidence

The implementation must prove at the Plan proposal service/route boundary:

1. The PlanAction reader receives the exact server-resolved basis and `limit=6`; every returned PlanAction row is checked against that basis. The Ask reader receives a `PlanAskContextBasis` exactly matching that basis and `limit=6`. Its returned `CompletedPlanAskPair` has no basis field, so verify the call argument and preserve the #898 owner projection boundary instead of asserting a nonexistent result field. The merged prompt uses no source outside those readers.
2. Equal timestamps, source-rank ties, source-local sequence ties and UUID tie-breaks produce the accepted deterministic order.
3. The merger retains the newest six pairs after merging up to six eligible pairs from each source, emits at most twelve chronological messages, and enforces the existing 4,000-code-point message bound. Overlong Ask and PlanAction fields receive the exact visible suffix ` …[truncated]`; source records remain unchanged.
4. A request carrying a validly shaped poisoned `conversation_history` sentinel cannot add, remove or reorder provider context; the sentinel is absent and provider input equals only the server-projected merge. Empty source projections result in empty provider history even when the client supplies poison.
5. Same-key retries with changed client history but unchanged explicit intent are receipt-first: no current-Plan read, source read, provider call or history-based conflict. Cover both legacy history-bearing and new history-free fingerprints. For each, unchanged typed intent returns the same truthful receipt/status; changes to instruction, draft digest, wire basis, target or selection conflict. For `insert_at_caret`, prove an empty validated selection matches persisted `selected_text_sha256=None`, while nonempty selection does not; for `replace_selection`, compare the computed selected-text digest. Completed, pending, failed and indeterminate outcomes retain #897 semantics.
6. Same-key reservation losers do not read either source or dispatch; identical typed intent with different client history reconciles to the winner's receipt, while changed typed intent conflicts. Either projection read failure, an Ask input-basis construction mismatch, or a returned PlanAction row with mismatched basis dispatches no provider request and records a truthful failure for the reserved action; persistence ambiguity cannot cause automatic redispatch.
7. A newer ineligible/pending/failed/indeterminate source record cannot crowd an older eligible pair out before that source's limit. #897/#898 already prove their owner projections filter before limiting; the merger calls those completed-context methods rather than the status read or general history.
8. Existing proposal response/action correlation, exact Plan-basis validation, tool/authorization behavior, Review/Apply/Save, and late-response surface fencing continue to pass.

Use deterministic fake provider inputs for the focused service tests and an owning-boundary test through the existing proposal route/service. Keep source-owner regression suites green; do not claim the merger tests replace #897/#898 storage tests.

## Proposed future implementation paths — not an active lease

The bounded expected future write set is:

- `apps/live_control_server/services/plan_document_edit_proposal.py` — exclude mutable client history from the World action fingerprint; build prompt history from the two exact-basis completed-context projections after receipt lookup and new reservation; merge, total-cap and bound the server-owned pairs.
- `tests/test_world_plan_edit_proposal.py` — prove merge order/caps, poisoned client history, receipt-first retry identity, duplicate reservation behavior, projection failure and route/service/provider boundary behavior.
- `Docs/Plans/HANDOFF-DEMO-plan-world-conversation-cutover.md` — include in the future activation write lease for a truthful transition record: retain Slice A's COMPLETE facts and record Slice B's actual ACTIVE lane/PR metadata when authorized, without marking the in-flight slice complete. At later settlement, record only actual merge/review/evidence facts.

No UI/API wrapper, request model, route, APP-STATE projection, PlanAction repository/service, migration, shared unit-of-work, global fixture, lockfile, roadmap, card, or provider/runtime path is in this proposed set. If implementation inspection requires any other path or owner contract, stop before editing and return the exact expansion to PRIME. PRIME must issue a separate exclusive three-path ACTIVE lease before any proposed path may be edited.

## Test resources

Use the existing uniquely disposable `application_state_dsn` PostgreSQL fixture and isolated worktree assigned by PRIME for owning-boundary integration evidence. Use the fake generation client; no live provider/model, production database, persistent port (including 54330/54331), shared service, or product runtime is required or authorized by this design. Do not edit global DB fixtures or the shared unit-of-work layer.

## Re-anchor and collision check

At authority base `f8712198848598c5ce83248eb66a54d93c1fd044`, PR #900 is merged and its seven-path lease is released; PR #899 is closed as superseded. Open PR filenames were inspected. The proposed service/test paths do not overlap open PRs #887, #886, #869, #844, #826, #798, #781, #765, #764, #763, #761 or #760. In particular #886 is the Plan navigation shell, #887 is the DOGFOOD card prototype, and #869 edits the DEMO roadmap/movement controls. This is a point-in-time check, not activation clearance; PRIME must re-anchor open PRs and active leases at any later activation.

## Activation gates

This handoff remains BLOCKED until all applicable gates are satisfied:

1. ARCHITECTURE's ruling is recorded: independent exact-basis reads are acceptable generation context, are not globally atomic, and need no new shared snapshot/watermark. A future strict same-instant recency requirement is a separate capability.
2. PRIME adopts the exact design head, confirms the settled #897/#898/#900 owner contracts and typed-field receipt comparison still apply, re-anchors current main/open PRs/active leases/resources, and issues the exclusive three-path ACTIVE lease for the service, owning-boundary tests and Slice A handoff sync.
3. The implementation verifies the current server request/fingerprint and response-receipt behavior against the exact activation base. It must use the saved receipt basis for WorkRevision UUID/number, compare incoming wire World/document/object-revision/content-digest against that basis, and apply the target-aware caret/selection rule above without resolving current Plan content. If these typed fields cannot safely compare legacy or new receipts, stop before editing and return the compatibility gap to PRIME rather than expanding schema or introducing a migration within this slice.
4. Required disposable database evidence and no-shared-service setup are assigned in the implementation lease.

No implementation activation, merge, configured-provider run, visual/operator acceptance, or J1–J6 completion is implied by this prepared contract.
