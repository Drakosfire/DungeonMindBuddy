# HANDOFF — APP-STATE: bounded Plan World Graph execution record v1

**Status:** ACTIVE — local APP-STATE implementation lease activated 2026-10-05 by PRIME. External push/publication remains paused pending the operator’s direct approval after automatic review rejected the previous push.
**Branch/worktree:** `codex/app-state-graph-context-execution` at `/tmp/app-state-graph-context-execution`.
**Pinned base:** Buddy `main@6319ff30466dd9ab2e3e0752fce31ac8a71b7d4b` (merged PR #924).
**Schema head:** `20261004_0016`; candidate migration `20261005_0017` with `down_revision=20261004_0016`.
**Topology:** serial APP-STATE persistence → SERVER integration. The write set excludes SERVER’s active #924 Hermes patch/runtime paths.
**Fresh PR census:** #922 (SERVER Graph-context contract, head `067a34db6e3bcff55d6ffdd2333e4433fbcb04f4`), #917, and #914 remain open; #924 is merged at `6319ff30466dd9ab2e3e0752fce31ac8a71b7d4b`. No open PR writes this APP-STATE allowlist.
**Authority:** PRIME’s local activation selects nullable `agent.turn.graph_context_execution` JSONB; no new event table, hash chain, receipt v2, or completion v2.

## Mission

Persist the authorized, actual execution of a Plan World Graph turn in Buddy’s Agent Harness, including its conversation lifecycle, parent-brokered Graph tools, provider authorization, evidence, and replay boundaries. This persistence contract is runtime-neutral; Hermes is the current concrete adapter. Preserve the accepted `PlanWorldGraphContextReceiptV1` and `PlanWorldGraphCompletionV1` contracts. Keep legacy turns unchanged when the new field is null.

This record is an APP-STATE-owned execution/evidence adjunct. `agent.turn` remains the lifecycle authority. APP-STATE does not rebuild turn status from events, resolve Graph facts, or authorize source-body access. This reconciles with `ARCHITECTURE-application-state-layer.md`’s event-sourcing non-goal: the JSONB is a bounded typed record on the existing domain row, not a general event store or replay engine.

## Durable field and typed shape

Add one nullable `agent.turn.graph_context_execution JSONB` field to the existing `agent.turn` row. For a new execution-bearing turn, `accept_turn` persists this strict v1 root with the receipt; legacy and receipt-only v1 turns keep it null:

```json
{
  "schema": "dmb_agent_plan_world_graph_execution_v1",
  "context_receipt_sha256": "<existing PlanWorldGraphContextReceiptV1 digest>",
  "policy": { "...": "..." },
  "events": []
}
```

The root policy is immutable after acceptance and references the receipt by digest; it does not duplicate Plan basis, World identity, native/managed binding, or Graph revision already pinned by that receipt. It contains:

- `policy_version` and a strict allowlist of parent-brokered, read-only Graph operations;
- explicit per-turn `max_provider_attempts`, `max_graph_operations`, `max_results_per_operation`, `max_total_provider_input_tokens`, and `max_total_provider_output_tokens`;
- `provider_input_accounting: { kind, estimator }`, where kind is `exact_token_count` or `conservative_upper_bound`;
- `source_opened: false`.

These are explicit server-selected operational limits, not fixed defaults of 64 provider calls or 128 tools. A separate serialization safety ceiling bounds the JSONB text representation to 1 MiB and the ordered `events` array to 2,048 entries per turn; these are storage guards, not normal job budgets. Enforce both in the typed model and with nullable-column checks in PostgreSQL. Each event payload and each returned-ID list is also schema-bounded. Exceeding a policy or storage bound fails closed before another provider dispatch.

For the current SERVER #924 guard, `provider_input_accounting` is `{kind: "conservative_upper_bound", estimator: "utf8_json_bytes_plus_64_per_node_v1"}`. Use that exact estimator identifier; do not alias it or silently coerce its output. In a new receipt, `tokenizer_name` identifies that estimator, `tokenizer_version` is `v1`, and `provider_envelope_input_tokens` stores its conservative upper bound `payload_utf8_bytes + 64 * (1 + count_nodes(payload))`—not UTF-8 byte count presented as exact tokens. The context-window check uses this upper bound plus the provider output reserve. The bound is computed from #924’s final `ApiRequestBudgetView` payload after its `_json_snapshot` and sorted compact UTF-8 JSON serialization, excluding only SDK `timeout`/`http_client`; use its `payload_sha256` for the envelope digest, not a second serializer. Existing receipt values and hashes retain their prior meanings; do not reinterpret populated receipts or change the v1 digest algorithm.

Each event has `event_id` (UUID), contiguous `sequence`, `kind`, and a strict kind-specific payload. Events are appended to the JSONB under the existing locked turn/claim transaction; the policy is never rewritten. No hash chain is added. At acceptance the root has an empty `events` array. Event appends do not change the v1 receipt or submitted-intent digest.

### Event kinds

1. **`validated_graph_operation`** — `operation_id`, allowlisted operation name, digest of canonical request arguments, pinned Graph revision, result-packet digest, admitted assertion/relationship/evidence-ref IDs, evidence-sufficiency status, coverage/truncation, and `source_opened: false`. Do not store query arguments or result prose.
2. **`provider_attempt_authorized`** — `provider_attempt_id`, exact final-envelope SHA-256 and serializer version, provider/model/API mode, tool-schema digest, input accounting kind/estimator/result, output reserve, included initial assertion/relationship/evidence-ref IDs, and the ordered `validated_graph_operation` event IDs actually present in that envelope. It is committed before SDK entry.
3. **`provider_outcome`** — the attempt ID and one ordered state: `sdk_entered`, `response_received`, `known_not_sent`, or `outcome_unknown`; include bounded status/request metadata and response digest when available, never the provider response body. An authorized attempt with no final outcome is unresolved and treated as potentially sent.
4. **`completion_binding`** — appended atomically with turn completion; contains the final producing provider-attempt ID, canonical digest of the existing completion v1 JSON, and a per-claim list of the validated Graph-operation event IDs that support that claim. It does not add fields to, reserialize, or change the digest semantics of the stored completion.

`event_id` and operation/attempt IDs are unique within the turn. Repeating a validated operation ID with the same request digest returns its stored event; a changed digest conflicts. Repeating an already-authorized provider-attempt ID never returns a second dispatch permission: it returns `already_authorized`/deny, even if the original permission response may have been lost.

## Bootstrap and exact initial receipt ordering — SERVER prerequisite

The #923 receipt is not redefined. For each newly accepted Graph turn, its existing `assembled_input_sha256` must equal the canonical digest of the **first actual provider envelope at the final SDK boundary**, including system/history messages, tool schema, and provider options included in the request. A hash of a preassembled prompt alone does not meet the contract.

SERVER must preserve the completed/idempotent replay preflight (`reconcile_turn`) before mutable Plan, Graph, or provider reads. The existing multi-transaction APP-STATE APIs are sufficient; no atomic bootstrap API or provisional turn state is needed. For a genuinely new key, the required order is:

1. `reconcile_turn` checks exact idempotency/submitted intent before mutable reads. If it finds an existing turn, return its stored state/receipt/execution record or pending disposition; do not prepare a new envelope. For a genuinely new key, resolve and validate the committed Plan, World binding, Graph revision, and initial evidence packet.
2. Have the parent build, or have the worker prepare and return without dispatch, the exact first final SDK envelope. The worker blocks at a parent-controlled dispatch gate; it cannot call the provider yet.
3. Parent reads the exact first-envelope `ApiRequestBudgetView` at the pinned #924 final boundary, uses its `payload_sha256` and named-estimator upper bound, builds the unchanged #923 v1 receipt plus strict execution-policy root with an empty event list, and calls `accept_turn` with both. APP-STATE persists them on the canonical turn. The execution root is internal server-produced submission data, not a client-controlled field.
4. Parent claims that turn, commits the unique `provider_attempt_authorized` event for the first envelope, then issues a single-use allow and enters the SDK call. Record `provider_outcome:sdk_entered` only after actual SDK entry is observed; record response/unknown afterward. Every later provider retry/continuation uses a new attempt ID and the same gate.

An accepted turn left between steps 3 and 4 has no authorized provider attempt and is safe to reclaim under the existing claim/attempt fence. A race loser finds the exact idempotent receipt and policy and does not dispatch. Same-key acceptance compares the frozen receipt and immutable policy; changed values conflict. Mutable event arrays are never part of that comparison. No new atomic bootstrap method is required: current `accept_turn` → `claim_turn` → authorization transactions are safe because every provider request remains behind the fresh authorization commit. A duplicate authorization, or uncertainty about whether its transaction committed, never yields a second `allow_once`; the worker/parent fails closed. Do not write an observed-entry outcome before SDK entry. If the process dies after the call begins but before that observation is durable, the committed authorization is treated as potentially sent/unknown and cannot be redispatched. This ordering must reuse the terminal final-boundary veto in SERVER PR #924 rather than a new generic broker framework. The fail-open Hermes observer is not an authorization gate. Do not weaken the receipt digest to accommodate a late or approximate envelope hash.

## Parent-brokered Graph traversal

In the current Hermes adapter, the child’s hydrated Graph retrieval session is child-local. Child-reported results are not admissible evidence. A child tool request is only a request: the Agent Harness parent checks it against the execution policy, executes the read through the authoritative Graph service against the receipt’s exact managed/native binding and frozen Graph revision, validates the returned IDs and packet, appends `validated_graph_operation`, then returns the admitted result to the child. A changed revision, binding, disallowed operation, over-budget result, or persistence failure denies the operation and cannot produce a later provider envelope.

`read_source`, source opening, Graph writes, arbitrary child-local Graph queries, and raw source/result bodies remain outside this contract. No validated event is appended from a worker claim alone.

## Completion, citations, replay, and retry

- Keep `PlanWorldGraphCompletionV1` exactly as stored today. For a turn with a non-null execution record, `complete_turn` accepts the final producing attempt ID, validates that the attempt has a durable `response_received` outcome, appends `completion_binding`, validates each claim’s target/evidence refs against the original receipt’s dispatched IDs or named validated operation events **and** requires every cited target and evidence ref to be present in the final producing provider envelope. Initial-receipt membership alone never authorizes a citation. The sidecar records `claim_id → validated_graph_operation event IDs`; the final attempt records which initial IDs and tool-event IDs it actually included. It stores completion + final execution JSON + completed lifecycle in one transaction. No completion v2, citation-shape change, or change to receipt/completion digest algorithms is proposed.
- The execution-aware validator applies the existing status meanings to the actual supporting packet(s): a cited initial packet uses its frozen receipt sufficiency/coverage; a cited tool result uses that event’s validated sufficiency/coverage/truncation. `graph_grounded` requires each cited source to be sufficient, complete, untruncated, and present in the producing envelope; `graph_grounded_partial` applies when a cited source is incomplete or truncated. With no sufficient evidence in the final request, use `plan_only_insufficient_evidence`; with sufficient evidence available but no Graph claims, use `plan_only_graph_unused`. When `graph_context_execution` is null, retain the current v1 validator and its exact initial-packet semantics.
- Completion v1 turns without `graph_context_execution` use the existing validator byte-for-byte and do not require a producing-attempt binding. Graphless legacy turns retain a null field, old fingerprints, and current replay behavior.
- Completed replay returns the stored receipt, unchanged completion v1, and execution record before current Plan/Graph/provider reads. No provider/tool dispatch is repeated.
- The current Hermes SDK adapter disables automatic retries or routes them through the Agent Harness gate one wire attempt at a time. A retry after a definite provider response requires a new attempt event and consumes policy budget. If a dispatch was authorized but the caller/parent lost the result, persist `outcome_unknown` when observed; on recovery, an unresolved or already-entered provider attempt blocks same-turn redispatch. Surface recovery/new user turn rather than silently replaying the initial envelope. An accepted/failed/interrupted turn with no authorized provider attempt may be claimed again under the existing lifecycle fence.

## APP-STATE active path allowlist

The exclusive APP-STATE implementation write set is:

- `src/application_state/agent_conversation/types.py` — strict root, policy, event union, optional field on `Turn`/`TurnSubmission`, and completion-binding validator inputs. Execution policy must be absent with a null execution field; when present it must bind the stored receipt and estimator metadata.
- `src/application_state/agent_conversation/repository.py` — JSONB column mapping and atomic append/readback under row lock.
- `src/application_state/agent_conversation/service.py` — `append_validated_graph_operation`, `authorize_provider_attempt`, `record_provider_outcome`, typed execution readback, and atomic completion binding. Existing `accept_turn` persists the immutable root policy with the receipt; `claim_turn` blocks reclaim after any provider authorization in an earlier attempt.
- `src/application_state/migrations/versions/20261005_0017_agent_turn_graph_context_execution.py` — nullable JSONB column plus database size/event-count checks; no new table or data backfill. `down_revision=20261004_0016` only if confirmed current at activation.
- `tests/application_state/test_agent_conversation_service.py`
- `tests/application_state/test_agent_conversation_postgres.py`
- `tests/application_state/test_agent_conversation_provenance_migration.py`
- `tests/application_state/test_plan_action_dialogue_postgres.py` — current migration-head assertion.

No other path is included. If implementation needs another file, stop and return the exact deviation to PRIME before editing.

Expected method behavior:

- `accept_turn(TurnSubmission(..., graph_context_execution=...))` accepts the execution root only with submitted intent v2 and a matching frozen receipt. On idempotent retry it returns the same receipt/root or conflicts; it never replaces a stored policy or envelope hash.
- `append_validated_graph_operation(..., expected_revision, expected_attempt, operation_event)` appends in sequence after SERVER’s parent Graph validator; exact duplicate operation ID/digest is idempotent, mismatch conflicts.
- `authorize_provider_attempt(..., expected_revision, expected_attempt, provider_attempt_event)` checks running/claim expiry, receipt/policy digest, next unique attempt, envelope accounting, included evidence membership, and cumulative limits; a fresh committed append may return `allow_once`; duplicate authorization never does. The server calls the SDK only after that fresh result.
- `record_provider_outcome(..., expected_revision, expected_attempt, provider_attempt_id, outcome)` enforces legal state order and exact attempt identity.
- Extend `TurnSubmission` and `Turn` with nullable typed `graph_context_execution`; extend `TurnResult`/`complete_turn` with the final producing attempt ID and claim-to-event citation membership only when the execution field is present. Append `completion_binding` and persist the unchanged v1 completion atomically.
- `claim_turn` may only reclaim an execution-bearing failed/interrupted turn if no provider authorization occurred in an earlier claim. An unresolved authorized attempt is marked unknown/interrupted and returned as non-claimable; it never gets a new permit.

The new nullable field is omitted from legacy request-fingerprint serialization when null, preserving graphless and receipt-only v1 fingerprint bytes. For a same-key race after a new execution root is constructed, `accept_turn` compares the typed immutable policy and v1 receipt directly; it ignores the empty submitted event array and never overwrites persisted events. Existing v1 turns with a null execution field are not upgraded in place.

## SERVER contract and candidate paths

SERVER owns the Agent Harness contract for exact-envelope preparation/hash/accounting, replay preflight, first-receipt bootstrap, provider authorization, parent execution of Graph tools, evidence validation, and supplying the producing-attempt ID at completion. Reuse the current SERVER proposals: API/context admission and Graph traversal ownership in `Docs/Plans/HANDOFF-SERVER-plan-world-graph-context-api-projection-v1.md` (#922), and the pinned Hermes adapter final-envelope veto in `Docs/Plans/HANDOFF-SERVER-hermes-pre-dispatch-budget-veto-v1.md` (#924). Keep authorization at that adapter boundary while preserving the runtime-neutral Agent Harness contract. Extend those specific seams; do not introduce a general-purpose broker framework. Candidate Buddy runtime paths are:

- `apps/live_control_server/services/agent_turn_service.py`
- `apps/live_control_server/services/hermes_agent_runtime.py`
- `apps/live_control_server/services/hermes_graph_agent_contract.py`
- `apps/live_control_server/services/hermes_graph_agent.py`
- `apps/live_control_server/services/hermes_graph_agent_host.py`
- `apps/live_control_server/services/managed_world_graph_projection.py` and `tests/test_managed_world_graph_projection.py` only where the #922-owned projection is the current parent Graph-read boundary; preserve its binding and revision checks rather than creating a second Graph client.
- `patches/hermes-agent/0001-pre-dispatch-budget-veto.patch` — preserve the exact pinned final-boundary veto; only amend the existing patch if its guard needs the synchronous parent authorization round-trip.
- Existing GraphRetrievalSession/Hermes traversal and parent projection seam named by the #922 handoff; the current child-local hydrated `GraphRetrievalSession`/session store is not itself authority. Pin the exact integration paths in SERVER’s activated lease.
- `tests/test_agent_turn_service.py`, `tests/test_hermes_agent_runtime.py`, `tests/test_hermes_graph_agent.py`, and `tests/test_hermes_graph_agent_host.py` (adjust the owning boundary tests as needed)

DungeonMind Graph remains authority for Graph reads/revision semantics. APP-STATE validates typed receipt/event relationships and citation membership; it does not claim to independently certify Graph truth.

## Required verification before implementation acceptance

- Populated-0016 to 0017 PostgreSQL migration preserves every existing turn with `graph_context_execution IS NULL`; golden tests compare legacy receipt/completion JSON, fingerprints, and replay behavior unchanged.
- Acceptance tests prove null execution omission keeps graphless and receipt-only v1 fingerprints byte-for-byte stable; same-key changed execution policy or receipt conflicts, while exact policy/receipt retry returns the stored row without replacing its mutable events.
- Fresh-service readback preserves policy and ordered events. Tests reject wrong receipt, revision, attempt, event order, policy mutation, event/byte ceiling overflow at both typed/database boundaries, changed duplicate IDs, cumulative budget overflow, and citation IDs absent from the initial packet/validated events.
- Postgres tests prove append and final completion binding are atomic, stale claim/attempt writes fail, duplicate operation retries return the original event, and duplicate provider-attempt authorization never grants another SDK call.
- Recovery tests prove authorized-without-outcome becomes unknown/non-claimable; known-not-sent is distinguished; provider response/retry attempts each have separate IDs/outcomes; no completed replay dispatches.
- SERVER’s fake-provider witness proves the first receipt hash equals the exact final initial request; no SDK call occurs before committed authorization; `sdk_entered` is appended only after actual entry is observed; every wire retry re-enters the gate; and no SDK call occurs after denied, stale, duplicate, over-budget, or unavailable persistence. A crash before entry observation leaves an authorized attempt potentially sent/unknown, never an invented entry event. The #924 estimator `utf8_json_bytes_plus_64_per_node_v1` is recorded as a conservative upper bound, never as exact tokens or as raw byte count.
- Parent-broker tests prove a child-local Graph session/result is ignored, the parent itself reads at the pinned revision, the validated operation event is durable before its result is returned or cited, and `read_source` is denied.
- Completion tests prove the existing v1 object remains unchanged while its `completion_binding` ties citations to the final producing attempt’s included evidence; graphless and receipt-only v1 turns keep existing behavior.
- Execution-aware status tests cover an initially omitted/insufficient packet followed by parent-validated sufficient evidence, complete versus truncated tool results, mixed initial/tool citations, Plan-only outcomes, and rejection when cited IDs are absent from the named events included in the final producing envelope. No-execution v1 status tests remain behavior-compatible.

## Activation gates and stop rules

This implementation lease is active on `main@6319ff30466dd9ab2e3e0752fce31ac8a71b7d4`, with migration head 0016 and the exact APP-STATE write set above. The APP-STATE implementation may proceed locally; the serial SERVER integration remains a separate owner/lease. Preserve the parent bootstrap contract: `reconcile_turn` precedes mutable reads, the exact first envelope is frozen before `accept_turn`, and no provider call occurs before a fresh authorization. Existing multi-transaction `accept_turn` → `claim_turn` → authorization is sufficient because an accepted row without authorization is safe to reclaim. If implementation requires any path outside the allowlist, if the schema head changes, or if a required invariant cannot be enforced within the current row transaction, stop and return the exact deviation to PRIME before editing outside the lease.

The implementation is one APP-STATE slice with the paths above, followed by the separately owned SERVER integration. No new event table, hash chain, receipt/completion v2, generic replay/tracing facility, source-opening capability, provider/Graph live call, operator database, or merge authority is included.
