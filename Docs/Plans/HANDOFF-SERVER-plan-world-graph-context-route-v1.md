# HANDOFF — SERVER: Plan World Graph context route v1

**Status:** ACTIVE — PRIME activated this route successor on 2026-10-05 after independent acceptance and merge of #924.
**Owner:** DungeonMindBuddy SERVER owns route admission, the runtime-neutral Agent Harness integration, managed/native Graph binding, parent Graph execution, answer validation, and API/history projection. APP-STATE owns the durable execution-ledger types and transactions. PRIME owns cross-repository path arbitration and independent review.
**Pinned base:** Buddy `main@6319ff30466dd9ab2e3e0752fce31ac8a71b7d4b` (merge of accepted #924 head `0e716a0ec3f9f479d7202f9ca48411cbdd0558ef`).
**Branch:** `codex/plan-world-graph-context-route`.
**Topology:** one serial SERVER implementation PR on the refreshed base. APP-STATE execution-ledger implementation is committed locally but still needs tests/PostgreSQL verification and publication approval. SERVER uses an in-memory fake persistence port until an exact APP-STATE producer head is reviewed and accepted; actual cross-repository integration acceptance and final dependency merge remain outstanding.
**Current candidate state:** implementation remains in progress at checkpoint `9ad634b587d015d7caa03d4da8cfd16a0358c4da`. The stream/retry and lifecycle amendments have focused owning-boundary evidence, but the full route lifecycle and actual APP-STATE integration remain incomplete. PRIME confirmed #917 is a preserved prototype with no active reservation; production SERVER owns the overlapping route/service paths, and prototype reconciliation follows production. A draft candidate PR may proceed with the incomplete implementation clearly disclosed.

## Mission

Add explicit `auto_plan_world` context to the existing durable World Plan conversation. Reconcile idempotent replay before mutable reads; pin the committed Plan, active managed-to-native World binding, and exact Graph revision; then admit every provider request only after a parent-owned durable authorization of the exact final Agent Harness request. Broker model-requested Graph expansion to the parent, persist validated evidence events, and bind completion/citations to the final producing provider attempt and evidence actually present in that request.

Keep policy-absent Plan Ask and existing generic Graph turns byte-compatible. This is not a new endpoint, general Graph gateway, Plan mutation, UI change, or new runtime framework. SERVER owns a runtime-neutral Agent Harness integration contract; Hermes is its current concrete adapter, running in the existing process isolation boundary.

### Agent Harness boundary

Treat conversation execution, tool and context handling, parent authorization,
provider lifecycle, evidence admission, and replay as Agent Harness capabilities.
The SERVER integration contract should describe those responsibilities without
binding product semantics to Hermes. The current implementation adapter uses
the existing Hermes worker, host IPC, provider dispatcher, and patch; its
adapter-specific request shaping and stream behavior are recorded explicitly
where they affect verification. This work does not introduce a new harness
framework or replace the current adapter.

### Product request and projection

Keep request discriminator `dmb_agent_turn_request_v1` and add optional strict `plan_context_policy: {schema: "dmb_plan_context_policy_v1", policy: "auto_plan_world"}`. Require the Plan surface, verified managed World owner, saved clean/dirty Plan with exact committed revision/content digest, generic `graph_request.mode=none`, and no generic Graph selection. Optional typed playable-card focus remains separate and must resolve against that same committed Plan. Clients never send native World ID, binding version, Graph revision, source root, or submitted-intent v2. Normalize the existing fields and explicit policy into submitted intent v2. When the policy is absent, omit it from every fingerprint input and preserve request v1 bytes exactly.

No-policy turns keep response `dmb_agent_turn_response_v1` and history `dmb_agent_conversation_history_v1` unchanged. A policy-bearing response uses additive `dmb_agent_turn_response_v2` and `plan_context: {schema: "dmb_agent_plan_world_graph_context_response_v1", receipt, completion, execution, delivery_replay}`. The existing `receipt` and `completion` payloads keep their exact APP-STATE v1 schemas and digests. `completion` is null until successful completion. `execution` is null only when no execution ledger is available (legacy receipt-only record); otherwise it is the safe nullable-to-consumers projection below. History containing a policy turn uses `dmb_agent_conversation_history_v2`; a frozen receipt and execution projection may be projected with nullable completion for accepted/running/interrupted/failed lifecycle states. Completed replay returns the stored receipt/completion and execution projection before current Plan/binding/Graph/provider reads. Keep `graph.status=not_requested` because generic `graph_request` remains none. Derive `answer.graph_grounded` and rendered answer text from validated completion segments.

The execution consumer projection schema is `dmb_agent_plan_world_graph_execution_projection_v1` and contains only:

```json
{
  "schema": "dmb_agent_plan_world_graph_execution_projection_v1",
  "claimability": "safe_to_reclaim_without_dispatch",
  "authorization_state": "none",
  "automatic_redispatch": false
}
```

`claimability` is one of `safe_to_reclaim_without_dispatch`, `explicit_new_attempt_required`, `blocked_unknown_or_sent`, or `completed`. `authorization_state` is one of `none`, `authorized`, `sdk_entered`, `response_received`, `known_not_sent`, or `outcome_unknown`. This is a SERVER-derived view of the durable ledger, not the raw JSONB event list. Never expose attempt/event IDs, event or envelope digests, normalized raw arguments, tool/provider bodies, or prompt content in this projection or ordinary answer prose. `outcome_unknown` and unresolved authorization map to `blocked_unknown_or_sent`; no event maps to `safe_to_reclaim_without_dispatch`; a definite known-not-sent outcome maps to `explicit_new_attempt_required`; terminal success maps to `completed`. `automatic_redispatch` is always false. DEMO may show the typed disposition and offer user-directed recovery but must never automatically redispatch a turn.

Initial failures before receipt freeze use the accepted typed pre-dispatch failure with `provider_dispatched=false`, `automatic_downgrade=false`, and no fabricated receipt; preserve existing outer `detail` errors and map the established failure codes to 404/409/503/502/413 as specified by the pinned #922 API contract. Failures after known SDK dispatch use separate truthful post-dispatch or outcome-indeterminate metadata and never masquerade as pre-dispatch errors. A stale retry with an original receipt preserves and may return the exact original receipt, reports this retry attempt as undispatched/stale, and never repins or clears the stored record.

## Pinned persistence and provider-boundary contracts

- Accepted APP-STATE design authority: `/tmp/app-state-graph-execution-ledger-design` at `e907c904c95854ce539c919bac8e868a5fe4f69d`, `Docs/Plans/HANDOFF-APP-STATE-plan-world-graph-execution-v1.md`. PRIME accepted this portable design authority. It selects nullable bounded ordered `agent.turn.graph_context_execution` JSONB on the existing turn, transactional append under the current attempt fence, and no new table, hash chain, receipt v2, or completion v2. Its publication is still awaiting operator approval; publication/merge is not a gate to this SERVER candidate.
- Product request/response/history/error wire contract: Buddy `origin/codex/server-plan-world-graph-context-contract@067a34db6e3bcff55d6ffdd2333e4433fbcb04f4`, `Docs/Plans/HANDOFF-SERVER-plan-world-graph-context-api-projection-v1.md`. Use its explicit policy and typed projections; its open docs PR is not runtime acceptance evidence and need not merge before this implementation candidate.
- APP-STATE implementation is a separate active slice. This Buddy PR must use a strict injectable persistence port and deterministic in-memory fake; it must not edit or duplicate APP-STATE types, SQL, migration, or implementation. Adapt to the exact accepted producer head before claiming integrated acceptance. Do not infer method names or compatibility from the design alone.
- Buddy #924 is merged at `6319ff30466dd9ab2e3e0752fce31ac8a71b7d4b`; its exact final request view and terminal pre-SDK veto are the provider-boundary authority. Reuse `ApiRequestBudgetView` and the existing `agent.api_request_budget_guard`. Do not add another serializer, estimator, SDK wrapper, or provider path. A parent callback may return allow only after fresh fenced APP-STATE authorization commits. Missing callback, failed/uncertain persistence, stale fence, duplicate authorization, or malformed view denies before SDK entry.
- For this guard, account with estimator `utf8_json_bytes_plus_64_per_node_v1` over the canonical `payload_json` after Hermes shaping. Use `payload_sha256` from the boundary view; compute the upper bound as `payload_utf8_bytes + 64 * (1 + count_nodes(payload))`. Preserve the existing output-reserve/context-limit rule. Never label this conservative upper bound as exact tokens.

## Bootstrap and dispatch ordering

1. Run `reconcile_turn` with the canonical idempotency key and normalized submitted intent before current Plan, binding, Graph, or provider reads. Completed replay returns stored answer/receipt/execution before those reads. Existing pending/running/failed disposition is handled by the frozen attempt and policy; never repin.
2. For a genuinely new key, resolve saved Plan and its exact revision/content digest, verified managed World binding, native World ID, and one exact Graph revision. Resolve/build the bounded initial parent Graph session and source-free packet. Validate the candidate evidence IDs against parent-known session data.
3. Start the current Hermes-backed Agent Harness worker, but do not accept/claim the new durable turn or permit a provider call yet. Allow only pure setup and request construction. At the first actual post-middleware/pre-SDK guard, the adapter sends a bounded correlated authorization request containing the actual `ApiRequestBudgetView` plus its final serialized request, then blocks. No provider SDK or child-local Graph operation may run before the parent responds.
4. The parent validates the request/view and parses actual envelope membership with a trusted strict parser against parent-known initial packet IDs. Candidate IDs alone do not prove inclusion. Derive the existing v1 receipt from that actual first envelope: exact boundary digest, model/mode, estimator/version, input upper bound, output reserve, and exact dispatched initial evidence IDs. Call existing APP-STATE `accept_turn` with immutable receipt, submitted v2 intent, and execution-policy root with empty events; then claim the turn under the normal fence; then append a unique `provider_attempt_authorized` event under that fence. Only a fresh committed authorization response produces one `allow_once` to the blocked worker.
5. A race loser or same-key retry must use the stored receipt/policy and never dispatch the locally reconstructed envelope unless it exactly matches the frozen initial envelope and a new safe attempt is permitted by the lifecycle contract. An accepted turn with no authorized attempt may be reclaimed. A committed authorization whose result is uncertain, duplicated, stale, or already authorized must never produce a second SDK allow.
6. Every later SDK attempt follows the same final-boundary handshake and appends exact envelope digest/accounting, provider/model/mode, included initial evidence IDs, and validated Graph-operation events present in that envelope before SDK entry. Disable hidden automatic SDK retries or prove that each individual wire attempt re-enters this gate. Record `sdk_entered` only after actual entry; record response/known-not-sent/unknown truthfully. An authorized attempt without a proven response is potentially sent and cannot be automatically repeated.

The first exact final envelope—not `_plan_message`, route assembly, retrieval packet, or invocation hash—sets `assembled_input_sha256`. The source-free v1 receipt remains unchanged after freeze. Execution events are bounded, ordered, unique, and append-only in the typed persistence contract; do not store prompt, provider response, query prose, or raw Graph result bodies in execution JSONB.

## Parent-brokered Graph operations and completion

- All child-requested Graph reads in this policy turn go through a correlated parent IPC request/result on the existing Agent Harness host (currently the Hermes host implementation). The only currently allowed operation is existing `expand_graph_retrieval`, executed against the parent-held retrieval session and the receipt’s exact native World/revision/binding. Validate operation schema/arguments, normalized digest, policy budget, exact pin, result schema, IDs, and returned evidence against the parent authority before appending `validated_graph_operation`.
- Deny `read_graph_source`, source opening, arbitrary Graph reads/writes, and any child-local Graph fallback. A missing/malformed broker is terminal. Other enabled products retain their existing policy behavior; this policy’s model-visible Graph surface contains only the allowlisted operation.
- Return the parent-validated result and updated bounded retrieval-session projection to the child. The child needs that updated packet for answer validation and final result serialization; its original hydrated session is never evidence authority.
- On completion, require the final producing attempt to have a durable `response_received` outcome. Validate typed Plan/Graph/proposal/connective answer segments and citations. Every Graph citation must refer to evidence in the initial packet or a parent-validated operation event that was actually included in the producing provider envelope, at the receipt’s frozen revision, with `source_opened=false`. Bind claim IDs to supporting operation event IDs in the atomic completion event; never cite an ID merely because it was a candidate or appeared in a different provider attempt.
- Preserve the existing completion v1 shape and digest. Use APP-STATE’s execution-aware validation/transaction when that implementation is accepted. Until then, the fake persistence contract must verify the same semantics and the route must fail closed if the production service lacks the required execution methods.

## Path lease

**PRIME-approved bounded amendment (2026-10-05):** The accepted #924 guard is
not yet the final boundary for Codex streaming in this policy path. The pinned
Hermes stream runtime adds `stream=true` after the guard view and retries a
streaming SDK request internally without a fresh parent authorization. This
successor may update the existing pinned Hermes patch and its owning tests only
to include the actual `stream` request field in the guarded canonical view and
to prevent a hidden guarded streaming retry. Prefer disabling that internal
retry when the parent guard is active; each later individual provider attempt
must obtain a fresh single-use parent authorization. Preserve legacy retry
behavior when the guard is absent. Prove exact guarded-view/SDK-body equality,
zero SDK entry on denial, no second SDK call after a guarded stream failure,
and legacy retry parity. This does not authorize a new serializer, SDK wrapper,
provider path, or installed-package edits.

**PRIME-approved bounded lifecycle amendment (2026-10-05):** A durable
authorization must be followed by correlated lifecycle callbacks before a
guarded worker may continue to another tool/provider authorization. Within the
same pinned Hermes patch and existing host IPC, `conversation_loop.py`,
`codex_runtime.py`, and the already-used request helper may report SDK-entry
observation and definite complete-response observation for that same
single-use attempt. The parent must acknowledge each transition after durable
persistence before the worker proceeds. SDK invocation observation is not
response proof; `response_received` is appended only after a definite complete
response. Stream interruption, transport exceptions, IPC loss, or persistence
uncertainty remain unknown unless a specific known-not-sent fact is independently
proven. A persistence/channel failure after SDK entry aborts continuation and
leaves the authorized attempt potentially sent. It must not trigger an
automatic repeated request. These guarded callbacks do not replace or wrap the
existing Hermes provider dispatcher, and the unguarded legacy path remains
unchanged. Add actual subprocess witnesses for authorize→entry→complete response
→next authorization, and prove that persistence or transport failure causes
zero follow-up provider requests. No other Hermes source path is leased.

Exclusive write lease for this PR:

- `Docs/Plans/HANDOFF-SERVER-plan-world-graph-context-route-v1.md`
- `apps/live_control_server/models/agent_turn.py`
- `apps/live_control_server/routes/agent.py`
- `apps/live_control_server/services/agent_turn_service.py`
- `apps/live_control_server/services/hermes_agent_runtime.py`
- `apps/live_control_server/services/hermes_graph_agent_host.py`
- `apps/live_control_server/services/hermes_graph_agent_contract.py`
- `apps/live_control_server/services/hermes_graph_agent.py`
- `apps/live_control_server/services/hermes_graph_interaction_tools.py`
- `src/graph_memory/hermes_graph_plugin.py`
- `tests/test_agent_turn_route.py`
- `tests/test_agent_turn_service.py`
- `tests/test_hermes_agent_runtime.py`
- `tests/test_hermes_graph_agent_host.py`
- `tests/test_hermes_graph_agent_contract.py`
- `tests/test_hermes_graph_agent.py`
- `patches/hermes-agent/0001-pre-dispatch-budget-veto.patch` (only the PRIME-approved stream-field, guarded-retry, and correlated guarded-lifecycle changes described above)
- `tests/hermes_patch/test_pre_dispatch_budget_veto.py`
- `scripts/prepare_patched_hermes.py` only if a pinned manifest/source identity constant must change as a direct result of the patch

No APP-STATE, GenerationEngine, DungeonMind, DEMO, migration, dependency/lock, generic `agent_runtime.py`, or other path is leased. The Hermes patch lease is limited to the PRIME-approved amendment above.

## Re-anchored collision and authority facts

- The route branch was rebased on fetched Buddy `origin/main@6319ff30466dd9ab2e3e0752fce31ac8a71b7d4b`; the prior two handoff commits are preserved above that base.
- PR #924 is merged at the pinned base and its guard correction is present.
- Open PR #922 is docs-only and is not backend acceptance evidence. #917 is a preserved focused Plan/context prototype with no active reservation; production SERVER owns route and service paths, and prototype reconciliation follows production. Preserve #917’s branch and do not edit it. #925 is UI-only; no open PR reserves the Hermes host/agent paths.
- APP-STATE contract commit `e907c904c95854ce539c919bac8e868a5fe4f69d` is accepted portable design authority. Its local execution implementation now exists at `/tmp/app-state-graph-context-execution@da99c20e9fd3acfe45a22496cc1f43337adddfeb`, with public methods `append_validated_graph_operation`, `authorize_provider_attempt`, and `record_provider_outcome`. Tests/PostgreSQL verification and publication approval remain pending, so it is not yet an accepted producer implementation. SERVER may implement its candidate against a local fake port; it may not claim actual persistence integration until the producer head is reviewed and accepted. Final dependency merge follows ordinary review/merge authority.

## Acceptance witnesses

Use deterministic Plan, binding, Graph session, fake APP-STATE execution ledger, and provider/SDK fakes. No live provider, Graph, operator database/process, external service, private data, or runtime rollout.

1. Preserve no-policy request/response/history schemas and golden request, idempotency, and v1 submitted-intent fingerprints byte-for-byte. Reject policy contradictions and non-saved/non-Plan inputs before Graph read, turn claim, or provider dispatch.
2. Test managed World ID distinct from native ID, active binding and binding/version/source-root drift, exact revision pin, fixed World/null-campaign scope, foreign/duplicate evidence rejection, and retries that never repin.
3. At the actual Agent Harness subprocess boundary, prove the initial request reaches the final request produced by the current Hermes adapter; receipt and authorization persist before mocked SDK entry; captured SDK request matches the stored digest, accounting, and evidence membership. For streaming, `stream=true` must be included in that same guarded view and SDK body; do not normalize it away.
4. Prove initial call → parent `expand_graph_retrieval` → follow-up provider call with the updated parent-admitted session in the child. Prove child-local Graph fallback is impossible. Denied/invalid expansion produces zero follow-up SDK calls.
5. Prove no SDK on stale attempt, persistence deny/uncertainty, duplicate authorization, or unknown dispatch; duplicate permission is never reusable; hidden provider retry cannot bypass the gate. For guarded streaming, prove one fresh authorization per actual wire attempt, no internal retry can repeat SDK entry under one authorization, denial produces zero SDK requests, and unguarded legacy streaming retains its retry behavior. Preserve truthful `known_not_sent`, `sdk_entered`, `response_received`, and `outcome_unknown` states.
6. Completion cites only evidence included in the producing envelope, including initial evidence; test rejecting an initial candidate not actually included, evidence only present in an earlier/different attempt, and child-claimed unadmitted evidence. Bind claim IDs to supporting operation events.
7. Exercise all APP-STATE statuses and replay/lifecycle semantics with the fake port: completed replay performs zero Plan/binding/Graph/provider reads; pending retry uses original pins; answer/receipt/execution completion is atomic in the fake contract witness. Clearly label these tests as fake persistence, not actual cross-repo integration.
8. Run the existing leased owning suites (`test_agent_turn_route`, `test_agent_turn_service`, `test_hermes_agent_runtime`, `test_hermes_graph_agent_host`, `test_hermes_graph_agent_contract`, `test_hermes_graph_agent`, and the Hermes patch wrapper), changed-path Ruff, relevant repository gates, patch/lock verification only if dependencies remain untouched, and exact cumulative base→head diff/allowlist checks. There is no `tests/test_hermes_graph_interaction_tools.py` at the pinned base; broker handlers and behavior are covered by `test_graph_operation_round_trips_through_correlated_parent_broker` and the subprocess witness `test_parent_authorization_and_graph_broker_guard_real_provider_requests`, including updated-session follow-up and child-local fallback rejection. No separate Graph-tools test file is needed for this candidate.

### Provider-boundary amendment evidence checkpoint

- Checked-in patch SHA-256: `b86a45648bd323eaf58f73550725c2fb8d0442e58bc5471ee2c369fe82a53ada`.
- Prepared patched-Hermes tree SHA: `0430126a406c559bb38b86990f513e19c2ec938e` (also recorded as `expected_tree_sha` in `out/hermes-agent-manifest.json`; upstream commit `861d69c7bba8d2ea6a1cd170e989c901c74d32d1`).
- `pytest -q out/hermes-agent/tests/agent/test_pre_dispatch_budget_veto.py`: 12 passed, including terminal guarded transport failure with `outcome_unknown` and one SDK invocation.
- `pytest -q tests/hermes_patch/test_pre_dispatch_budget_veto.py`: 1 passed after updating the owning expected upstream count to 12.
- Actual subprocess authorization/lifecycle witness: 1 passed. Two parent authorizations each received and acknowledged `sdk_entered` then `response_received`; exact authorized JSON and SHA-256 match captured `responses.create` kwargs, including `stream=true`.
- Actual subprocess persistence-rejection witness: 1 passed. Parent rejected the `sdk_entered` append, worker attempted `outcome_unknown`, exactly one SDK request occurred, and neither Graph nor another provider request followed.
- Actual subprocess transport-failure witness: 1 passed. The parent recorded `outcome_unknown`, exactly one SDK request occurred, and no follow-up Graph/provider request ran.
- Exact owning-suite command (route, service, runtime, host, contract, graph-agent, and Hermes patch wrapper): 240 passed, 1 deselected in 170.08 seconds. The deselected `test_app_lifespan_shuts_down_global_host` stalls at ASGI startup on both candidate and clean base, as previously documented.
- The named leased test file `tests/test_hermes_graph_interaction_tools.py` is absent at the pinned base. `tests/test_graph_retrieval_interaction.py` exists but cannot collect because `graph_memory.interaction.digest_audit` is absent; it is not a usable substitute for this slice.
- Changed-path Ruff passed. `pyproject.toml` and `uv.lock` remain unchanged; patched Hermes was reinstalled from the prepared source. `scripts/prepare_patched_hermes.py --verify` and reverse-apply check of the checked-in patch passed.
- Lifecycle plumbing is implemented through the existing worker IPC and verified at the subprocess boundary, but the route candidate remains incomplete. APP-STATE has a local implementation at `da99c20e9fd3acfe45a22496cc1f43337adddfeb`; tests/PostgreSQL verification, publication approval, and producer acceptance remain pending. SERVER currently has no integration code against those methods, so no compatibility claim is made yet.

## Stop conditions and pending integration

Stop and report the smallest concrete blocker to PRIME if the final Agent Harness request cannot synchronously reach the parent before SDK entry; any child-local Graph operation can bypass the broker; lifecycle methods cannot prevent duplicate/uncertain dispatch; evidence membership cannot be derived from the actual producing request; or a required path/API/storage change falls outside this lease. Amend this handoff before any path expansion.

The current SERVER candidate must explicitly report APP-STATE integration as pending until the exact producer implementation head is accepted. Fake-persistence tests are evidence for route/IPC behavior only. Record exact base/head, cumulative diff, tests, deviations, unresolved risks, and the integration boundary before requesting PRIME’s independent review. Do not merge or deploy.
