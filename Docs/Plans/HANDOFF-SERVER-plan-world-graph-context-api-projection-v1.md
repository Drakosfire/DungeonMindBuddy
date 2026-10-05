# HANDOFF — SERVER: Plan World Graph context API projection v1

**Status:** BLOCKED — published API contract; implementation remains unleased pending the APP-STATE receipt contract and PRIME activation. This document authorizes its own publication PR only; it grants no implementation, provider, database, service, process, Graph, or runtime lease.

**Owner:** DungeonMindBuddy SERVER owns the request admission, API projection, managed-to-native binding integration, provider-envelope construction, and answer validation described here. APP-STATE owns the frozen durable receipt and completion types. DEMO owns the canonical Plan conversation client and presentation. PRIME owns activation, topology, path arbitration, and any operational authority.

**Re-anchored design base:** Buddy `main@e671784dc53e698a33a5125f08d76953faa34a19` (2026-10-04). Remote refresh was attempted; network DNS was unavailable, so this pinned checkout is the freshest verified local main ref. Re-fetch and refresh the open-PR/path census before implementation activation.

**Frozen persistence contract accepted by SERVER:**

- APP-STATE design `/tmp/DESIGN-APP-STATE-plan-world-graph-context-receipt-v1.md`, SHA-256 `ae15b1ec7a9d596d4613aa2c76033040cd0a100ef8e65a0d6155b80d41a33d4c`.
- APP-STATE handoff `/tmp/HANDOFF-APP-STATE-plan-world-graph-context-receipt-v1.md`, SHA-256 `561008c9c0eb7f946fc62aa1abf95a028aef21db0917d6629e37ef5668759eff`.

SERVER accepts these exact persisted receipt/completion semantics as its implementation foundation. This handoff defines only their SERVER-owned API and execution projection. Publication of the APP-STATE packet and implementation are separate authorizations; this contract does not claim APP-STATE types are present on current main.

**Topology:** serial: APP-STATE receipt/completion contract implementation → SERVER API/admission/binding/readiness/receipt-freeze integration → DEMO consumer. The SERVER contract publication is independently authorized and does not wait for APP-STATE implementation. PRIME owns reviews and may activate SERVER only after its exact lease is issued. #865 World conversation, #835 auth guard, and #836 managed-to-native binding are accepted reuse points; #826 provisioning is not a prerequisite. DEMO #914 and prototype #917 are not gates.

## 0. Re-anchored implementation facts

- Canonical product route is the existing #865 World conversation; do not create a parallel Plan Ask path.
- Reuse the existing server-owned `GraphRetrievalSession` and Hermes traversal/tools. Preserve the existing `#835` loopback bearer guard and `#836` fail-closed managed-to-native binding. The #826 provisioning work is not a prerequisite: readiness is evaluated per World at request time.
- Per-World readiness requires an authorized active managed binding and a readable native Graph head. If either is absent, return a typed unavailable result before provider dispatch. Do not block synthetic implementation on live readiness or silently continue Graphless.
- Current Buddy main is `e671784dc53e698a33a5125f08d76953faa34a19`. At that base the APP-STATE receipt/completion types are not present. Current open PR census and remote freshness must be rechecked before implementation activation; the attempted fetch failed because GitHub DNS was unavailable in the implementation environment.
- The exact Hermes pin in `pyproject.toml` is upstream `NousResearch/hermes-agent@861d69c7bba8d2ea6a1cd170e989c901c74d32d1` (0.18.2). Hermes `MAX_QUESTION_CHARS=8000` and SERVER `_plan_message` character cap are not token budgets. Current `pre_api_request` hooks cannot enforce a stop: Hermes invokes hooks under broad exception swallowing in `agent/conversation_loop.py`, and plugin callback exceptions are caught in `hermes_cli/plugins.py::PluginManager.invoke_hook`. See the separately bounded Hermes budget recommendation to PRIME; implementation must not assume those hooks are a veto.

## 1. Mission

Add an explicit, read-only `auto_plan_world` context policy to the existing durable World Plan conversation. The canonical consumer is `WorldPlanAgentConversation`; this is not a new conversation, a generic Graph query, the separate `PlanAgentInteractionBar`, or a Plan editor write feature.

The request remains anchored to the exact server-resolved committed Plan basis and may carry the separately typed playable-card focus already supported by #911. The SERVER resolves the managed World’s active native Graph binding and a fixed, bounded World-scope Graph context. It freezes the APP-STATE receipt before provider dispatch, returns typed answer attribution/citations, and makes the same receipt and completion envelope available in history and durable replay.

Plan Ask with no context policy remains byte/fingerprint/behavior compatible. The explicit policy is never inferred from `graph_request=none`, route, owner presence, or Graph availability.

## 2. API contract

### Request

Keep the established request discriminator `schema: "dmb_agent_turn_request_v1"`. Add one optional strict field:

```json
"plan_context_policy": {
  "schema": "dmb_plan_context_policy_v1",
  "policy": "auto_plan_world"
}
```

The policy-bearing request must also satisfy all of the following:

- `surface.surface_id == "plan"`;
- `owner_scope` independently resolves to the managed World that owns the saved Plan;
- `primary_work.kind == "plan"`, `client_work_state` is `saved_clean` or `saved_dirty`, and the existing exact committed revision/digest expectations are present;
- `graph_request.mode == "none"` and `graph_selection == null` (these generic fields retain their old meaning);
- optional `playable_target` remains a separate typed `{kind,id}` focus resolved against the exact same committed Plan basis. It does not change Graph scope.

The external caller sends no native World ID, binding version, Graph revision, source root, or submitted-intent v2 object. SERVER normalizes the explicit policy plus existing World/Plan/card request fields into the APP-STATE `dmb_agent_submitted_turn_intent_v2`. Require exact consistency between policy, saved Plan coordinates, and optional card focus. Reject policy on non-Plan surfaces, unsaved/new work, generic non-none Graph request/selection, and contradictory or unsupported fields with HTTP 422 before turn claim, Graph read, or provider dispatch.

When `plan_context_policy` is absent, preserve the existing `AgentTurnRequest` v1 canonical serialization, validation, service behavior, and all legacy fingerprint bytes. Explicitly omit the new field from every no-policy fingerprint input; do not hash a default `null`. Do not add a null policy to a v1 submitted intent. Existing graphless and generic Graph request meanings remain unchanged.

### Successful response

No-policy requests retain the existing `dmb_agent_turn_response_v1` shape exactly. Policy-bearing requests use an additive `dmb_agent_turn_response_v2`, containing the existing response fields plus a required `plan_context` object:

```json
{
  "schema": "dmb_agent_plan_world_graph_context_response_v1",
  "receipt": "PlanWorldGraphContextReceiptV1",
  "completion": "PlanWorldGraphCompletionV1",
  "delivery_replay": false
}
```

`receipt` and `completion` are the APP-STATE frozen types at the accepted hashes above; SERVER must not rename, omit, rederive, or conflate their fields in storage. `delivery_replay` is response-only and is true only when projecting an already completed exact turn; it does not alter the stored completion outcome.

For v2 responses, existing `graph.status` continues to describe only the generic `graph_request`; it remains `not_requested` for this policy because `graph_request.mode` is `none`. `answer.graph_grounded` is derived from validated `graph_claim` segments, never trusted from model output. `answer.text` is rendered from the persisted ordered answer segments. `plan_context.completion.answer_context_status`, `answer_basis`, segments and map are the source of truth for citations and Plan-only labels.

### History

Legacy-only conversation history remains byte/shape compatible with `dmb_agent_conversation_history_v1`. A history page containing a policy-bearing turn uses `dmb_agent_conversation_history_v2`. For every policy-bearing turn with a frozen receipt, project `plan_context.receipt` and `plan_context.completion`, where `completion` is nullable: pending/running/interrupted turns can have the original durable receipt with `completion=null`; terminal failed turns likewise expose their receipt with `completion=null` and retain the existing truthful lifecycle/error projection. Do not require a successful completion to project a policy receipt. A pre-dispatch failure before receipt freeze creates no receipt and therefore no synthetic policy history entry. Legacy turns remain legacy and receive no synthesized receipt/completion. History reads do not resolve current Plan, binding, Graph, or provider state to reconstruct an old receipt. Completed replay returns the original stored receipt/completion with `delivery_replay=true`; it does not re-label a stored Plan-only outcome or replace its citations.

### Errors and HTTP status projection

Existing route error bodies remain unchanged for requests without `auto_plan_world`. For an execution failure with a policy-bearing request, retain the existing FastAPI `detail` envelope and add the strict `PlanWorldGraphContextFailureV1` projection:

```json
{
  "detail": {
    "code": "<failure_code>",
    "message": "<safe user-facing message>",
    "plan_context_failure": {
      "schema": "dmb_plan_world_graph_context_failure_v1",
      "status": "pre_dispatch_failed",
      "failure_code": "<failure_code>",
      "provider_dispatched": false,
      "automatic_downgrade": false
    }
  }
}
```

This exact frozen APP-STATE failure type is used for an **initial policy-bearing attempt** that fails before provider dispatch and before any valid receipt was frozen. It must report `provider_dispatched=false` and `automatic_downgrade=false`; the response contains no receipt because none exists. It does not describe malformed provider output, citation validation failure, or completion persistence failure after dispatch. A retry with an already-frozen receipt follows the distinct stale-retry rule below; it must not imply that its original receipt disappeared.

The API projection maps the frozen pre-dispatch failure codes as follows:

| `failure_code` | HTTP | Meaning |
| --- | ---: | --- |
| `managed_world_unresolved` | 404 | Managed World/Plan authority could not be resolved. |
| `native_binding_invalid` | 409 | No valid active managed-to-native binding can support this request or retry. |
| `graph_revision_unavailable` | 409 | The requested/original pinned revision is unavailable; do not substitute a newer head. |
| `graph_read_failed` | 503 | Native Graph read failed before a receipt could be frozen. |
| `graph_evidence_invalid` | 502 | Retrieved evidence failed SERVER validation against the admitted projection/pin. |
| `provider_envelope_over_budget` | 413 | The complete provider-boundary input plus output reserve exceeds the model limit. |
| `receipt_freeze_failed` | 503 | APP-STATE did not durably freeze the exact receipt before provider dispatch. |

Request-model contradiction remains the existing 422 validation response, not a graph-context failure receipt. Authentication/authorization errors preserve existing 401/403 behavior and run before owner, receipt, Graph, or provider work. Same-key intent conflicts preserve the existing durable conflict behavior (409). A successful, valid pinned receipt with insufficient evidence is not an HTTP error; it follows the Plan-only completion rule below.

For a failure after the provider request is known dispatched, use a separate SERVER-owned `PlanWorldGraphDeliveryFailureV1` in the existing `detail` envelope; never mislabel it as `pre_dispatch_failed` or `receipt_freeze_failed`:

```json
{
  "detail": {
    "code": "<existing truthful failure code>",
    "message": "<safe user-facing message>",
    "plan_context_delivery_failure": {
      "schema": "dmb_agent_plan_world_graph_delivery_failure_v1",
      "status": "post_dispatch_failed",
      "failure_stage": "provider | answer_validation | completion_persistence",
      "provider_dispatched": true,
      "durable_lifecycle_status": "failed",
      "receipt_persisted": true,
      "automatic_provider_redispatch": false
    }
  }
}
```

If it is uncertain whether the request crossed the provider boundary, project `status: "outcome_indeterminate"`, `provider_dispatched: null`, and the actual durable lifecycle status (`interrupted` or the known stored state). If dispatch is known but durable terminal persistence is uncertain, retain `provider_dispatched: true` and report the actual uncertain/known lifecycle state. Do not claim `failed` if APP-STATE outcome is uncertain; do not redispatch automatically. Existing error/status conventions remain authoritative for HTTP status and outer code: provider failure or malformed/invalid structured answer is 502; completion persistence failure is 503; uncertain durable outcome is 503. The typed object adds truthful stage/dispatch/receipt facts without changing the existing outer `detail.code` contract.

**Stale pending/interrupted retry with an original receipt:** binding change, unavailable original revision, or inability to reproduce the frozen packet is a 409 stale/conflict on the current retry attempt, before that attempt dispatches a provider. Return the existing stale/conflict error envelope with additive response-only `plan_context_retry` metadata containing `status: "rejected_stale"`, `provider_dispatched: false` (for this attempt only), `original_receipt_preserved: true`, and the original `context_receipt_sha256`. Where useful to the caller, project the exact original receipt and its existing nullable completion as read-only fields; do not create a completion for a pending/interrupted/failed turn. The durable receipt, lifecycle and null completion remain unchanged. Keep the original receipt visible in ordinary history. This metadata is an HTTP projection, not a new stored APP-STATE type. Do not use the initial no-receipt `PlanWorldGraphContextFailureV1` rule for a retry whose receipt was already frozen.

## 3. SERVER execution and projection invariants

1. Resolve and verify the managed World and exact committed Plan basis using existing SERVER ownership checks. Keep managed identity in `owner_scope`, `graph` product scope, and legacy `HistoricalReference` fields. Resolve native identity/binding only from the verified managed record; no client native authority is accepted.
2. Admit only the MIND R.3 fixed World scope (`scope_mode=WORLD`, `campaign_id=null`) with its authorized admissibility and exact revision pin. Use the existing native primitive; no new MIND endpoint, source-body API, or predecessor PR is required. Preserve the current supported Plan/card focus and complete committed Plan input. Never submit mounted dirty editor bytes.
3. Recheck the active managed/native binding and version after projection, and validate returned revision, scope, admissibility, objects/relationships/assertions, and stable `evidence_ref_ids` against the same admitted projection. Reject drift or invalid evidence before accepting a receipt.
4. Build the deterministic bounded packet and provider envelope described by the accepted receipt contract. Keep retrieved/admitted candidate digest/IDs separate from dispatched packet digest/IDs and the whole assembled-input digest. The assembled-input digest must match the exact provider-boundary request, including all full Plan/history/policy instructions/schema/tool overhead, optional card focus, model/tokenizer/version, output reserve, and exactly the graph payload or insufficiency diagnostic actually sent. Do not persist prompts or raw source bodies.
5. Derive `context_receipt_sha256` over the complete typed pre-dispatch receipt using the exact accepted `canonical-json-utf8-v1` rule, excluding only the digest field itself. Submit that receipt plus normalized policy intent to APP-STATE and prove the returned durable receipt is identical before provider dispatch. No provider call occurs if freeze/claim fails.
6. If authority, binding stability, exact pin, evidence validation, receipt freeze, or total context budget fails before a valid receipt exists, emit the typed error above. No receipt, provider call, or implicit graphless retry/downgrade is allowed. A separate policy-absent Plan-only Ask requires explicit user action and a new idempotency key.
7. With a valid frozen pin but `evidence_sufficiency_status=insufficient`, retain the retrieval receipt, set `packet_disposition=omitted_insufficient`, send the full committed Plan/history/question plus explicit Plan-only diagnostic, and omit all Graph claim payload. A resulting completion may be `plan_only_insufficient_evidence`, with `answer_basis=committed_plan`, `graph_grounded=false`, and null citation map. The response/history visibly label it Plan-only and show truthful retrieval/coverage status.
8. With sufficient evidence and an included packet but no validated `graph_claim` output, completion is `plan_only_graph_unused`, not insufficient. This describes output attribution only and makes no claim about internal model attention. If sufficient truncated/incomplete evidence supports mapped claims, use `graph_grounded_partial` with visible incomplete-coverage status; truncation alone is not insufficiency. Complete sufficient mapped grounding uses `graph_grounded`.
9. Validate strict typed answer segments. `graph_claim` entries require unique claim IDs, assertion/relationship target, exact receipt revision, and nonempty evidence refs drawn from dispatched—not merely retrieved—IDs. The citation map must correspond one-to-one to all graph-claim segments. `plan_claim` must be attributed to the frozen committed Plan SHA; `proposal` must remain explicitly an idea/invention; `connective` must be nonfactual. Reject unknown/uncategorized segments and mismatched `answer_basis`, status, map, receipt digest, target, or pin. Do not require Plan-derived facts or proposals to cite Graph. Render `answer.text` from validated segments and atomically complete APP-STATE with the unchanged receipt and exact completion envelope.
10. Completed replay returns the original answer, receipt, segments, map, answer basis/status and product managed scope with no current Plan/binding/Graph/provider reads. Pending retry revalidates the original managed/native/binding tuple and exact revision; a newer head is acceptable if the original pin remains available. Binding change, missing original pin, or packet mismatch fails without receipt mutation or repinning. A same-key race may dispatch only the winning frozen context.

## 4. Supersession and compatibility

This handoff supersedes the **Plan-specific graphless-only restriction** in `Docs/Plans/HANDOFF-SERVER-managed-world-agent-graph-adapter.md` only for the explicit, versioned `auto_plan_world` policy described here. It does not change the meaning of generic `graph_request=none`, authorize generic Graph queries/selections on Plan, or alter the generic Graph adapter for non-Plan surfaces. The old handoff's managed-to-native binding/replay insights remain relevant; its original write lease/status is not reactivated.

It also does not change PR #911's optional typed card focus semantics. Card focus remains independently validated against the same exact committed Plan basis and is persisted beside, never inside, Graph `selected_object`. It does not authorize changes to Plan editing, Run admission, Graph writes, provider behavior outside this request, or the separate `PlanAgentInteractionBar`.

## 5. Candidate SERVER path lease — not active

After APP-STATE has separately completed its authorized persistence slice, the current base/PR census is refreshed, and PRIME explicitly activates this exact path list, candidate SERVER-owned writes are:

- `apps/live_control_server/models/agent_turn.py` — strict policy request type, Plan admission rules, policy-bearing response/history projection types, and typed API error projection while retaining exact legacy serialization;
- `apps/live_control_server/routes/agent.py` — route/model/history wiring and typed error mapping; authentication order remains unchanged;
- `apps/live_control_server/services/agent_turn_service.py` — internal v2 intent normalization, managed/native authority integration, receipt/envelope/citation validation, pre-dispatch freeze and replay/retry ordering;
- `tests/test_agent_turn_route.py` — full route, status/error, history/replay, and owner-boundary witnesses;
- `tests/test_agent_turn_service.py` — service sequencing, envelope hashing, outcome/status matrix, segment validation, and winner-receipt behavior;
- `apps/live_control_server/services/managed_world_graph_projection.py` and `tests/test_managed_world_graph_projection.py` only if its existing request/response cannot preserve the accepted revision and evidence/scope requirements without a narrow service change.

No APP-STATE types/repository/service/migration/test path is included. No DEMO UI/history/test path is included. No `Docs/Roadmaps/ROADMAP-demo.md` write is included while PR #914 owns that path. No MIND/DungeonMind path or new endpoint is included. Do not edit, transplant, reset, or archive the historical `agent-world-conversation-backend` checkout. If an additional path is required, stop and return the exact need to PRIME/owner before editing.

Topology is one serial SERVER implementation PR after APP-STATE receipt/completion schema is merged and accepted, with DEMO following under its own lease. A PR branch, base SHA, checkout, test ports, databases, or runtime lease will be selected only after activation-time re-anchor; none is reserved by this document.

## 6. Required SERVER acceptance witnesses after activation

Use deterministic fake owners, projection responses, APP-STATE services, and provider runtime. No live provider, Graph service, operator port, or application database is required for SERVER code acceptance.

1. **Legacy compatibility:** golden request/response/fingerprint witnesses prove no-policy Plan Ask bytes and behavior remain exact, including typed-card graphless Ask. Existing generic Graph modes retain their current request meanings. Plan Ask with generic non-none Graph request/selection remains rejected unless it is the explicit policy as specified here (which itself still requires generic mode `none`).
2. **Full HTTP admission/translation:** use a verified saved Plan and World where managed and native IDs differ, plus optional typed card focus. Prove native read gets the native ID, fixed `WORLD/null campaign`, exact requested pin, and no client-supplied native authority; product response/provenance retain the managed ID, complete exact Plan basis, and same-basis card focus.
3. **Binding/admissibility:** fail closed on inactive/invalid binding, pre/post binding-version or native-ID drift, scope/admissibility/revision mismatch, foreign/duplicate/unvalidated evidence references, before provider dispatch and without persisted receipt. Cover requested older pin and a newer head without silently switching pins.
4. **Receipt and envelope:** prove `retrieval_packet_sha256`, candidate IDs, `dispatched_packet_sha256`, dispatched IDs and `assembled_input_sha256` identify distinct correct objects. For insufficient evidence, inspect the exact fake provider request and prove full Plan/history/question/diagnostic remain while all Graph claim payload is omitted. For included packets, prove every dispatched ID is in candidate IDs and full envelope digest matches exact captured provider input.
5. **Outcome matrix:** prove `plan_only_insufficient_evidence` with omitted payload and null map; `plan_only_graph_unused` with sufficient payload sent but no graph claims; `graph_grounded` with complete evidence and exact map; and `graph_grounded_partial` with sufficient truncated/incomplete evidence, mapped claims, and visible incomplete coverage. Do not mislabel missing authority/pin as insufficiency or truncation alone as insufficiency.
6. **Typed answer/citations:** cover every segment kind, strict no-uncategorized output, Plan SHA attribution, proposal/connective attribution, answer_basis derivation, duplicate claim IDs, missing/extra citation entries, wrong target kind/ID/pin, retrieved-but-not-dispatched references, empty/foreign evidence refs, wrong receipt digest, and `source_opened=false`.
7. **Pre-dispatch and atomicity:** receipt is durably frozen before provider call; provider is never called on typed failure, over-budget input, or failed receipt freeze. Completion persists unchanged receipt, answer text, completion segments/status/basis/map atomically. No receipt can be rewritten or answer completed with a mismatched map.
8. **Retry, race, replay, and lifecycle history:** pending retry uses original binding/revision/selection policies; changed binding or missing original pin returns the 409 stale-retry projection, dispatches no provider on this attempt, and preserves the byte-identical original receipt/hash and null completion; newer Graph head is allowed when old pin remains; winner-receipt race dispatches only winning context; completed history/replay returns original answer/receipt/completion after current Plan/binding/head changes with zero current Plan, binding, Graph, or provider reads. Also prove accepted/running/interrupted turns project a frozen receipt with null completion, and failed-after-dispatch history retains the receipt, null completion, and truthful terminal lifecycle without synthesizing an answer.
9. **Error projection:** assert exact frozen `dmb_plan_world_graph_context_failure_v1` detail schema, failure code, HTTP mapping, `provider_dispatched=false`, and `automatic_downgrade=false` only for seven proven pre-dispatch failure cases. Separately use a fake provider that records dispatch then returns malformed structured/citation output; prove the API returns the post-dispatch delivery failure, durable failure lifecycle retains the frozen receipt without completion, and no retry dispatch occurs. Add a completion-store failure after a recorded provider result and prove `receipt_persisted=true`, dispatch status truthful, completion outcome known/indeterminate as appropriate, and no automatic redispatch. Authentication and existing authorization denials precede context/receipt/runtime work.

At minimum, extend/reuse the existing route witnesses `test_completed_graph_receipt_replays_frozen_snapshot_projection`, `test_retry_graph_resolution_is_pinned_to_stored_snapshot`, and `test_accept_race_never_dispatches_context-different-from-winner-receipt`; their current equal-ID or generic-Graph behavior does not prove this policy. Add a full Agent-turn route test with distinct managed/native IDs and card focus. The existing projection tests `test_active_binding_reads_native_world_and_returns_unchanged_projection` and `test_binding_change_during_projection_discards_native_result` remain lower-bound witnesses, not substitutes for the integrated route tests.

Before SERVER acceptance, inspect the exact cumulative SERVER base-to-head diff and run the focused route/service/projection suites plus the current relevant repository gates. APP-STATE owns its migration/readback tests; SERVER must not run or claim that migration evidence. Preserve full failure output and report inherited failures separately. Record exact base/head, owner acceptance, tests and unclosed gates in the active handoff only after activation.

## 7. Blockers and stop conditions

This API handoff remains BLOCKED until all are true:

1. The exact APP-STATE hashes above remain stable and APP-STATE's authorized receipt/completion contract is available to SERVER with owner acceptance. Until it lands, SERVER may continue contract publication and synthetic contract/test planning, but must not invent substitute persistence semantics. No APP-STATE code path is leased here.
2. SERVER and DEMO accept this exact wire request/response/error/history projection, including the four outcome values, retrieved-versus-dispatched semantics, and policy-only response/history versioning.
3. MIND's confirmed R.3 fixed World scope, admissibility, pin and evidence-reference semantics remain available in current authority. This is not a new MIND dependency or endpoint request.
4. PRIME refreshes `main`, open PRs, active path/resource leases, and migration/runtime facts, then explicitly issues an ACTIVE exact SERVER path allowlist, branch/base, topology, and offline test-resource plan. #914/#917 are not predecessor gates; exact overlapping paths still require arbitration at activation.

Stop and return to PRIME if no-policy bytes/fingerprints cannot stay identical, managed/native identity cannot be preserved through replay, full context cannot fit without clipping, receipt/completion cannot be frozen/validated atomically, citations cannot be restricted to dispatched evidence, or the active migration/schema head differs from APP-STATE's accepted plan. Do not broaden into Graph generic query changes, source opening, Graph writes, Plan authoring, a new MIND primitive, multi-instance production rollout, or J1–J6/operator acceptance.

## 8. Operational limits

This handoff publication PR is authorized and does not activate implementation. No merge, runtime inspection/restart, database inspection/write/migration, provider call, live Graph read, credential change, or shared test fixture lifecycle is authorized by this design. All future SERVER tests use isolated deterministic fakes and only an explicitly authorized isolated fixture when needed. Do not use operator ports 5202/8000/5203 or any shared application database. PRIME owns any future operator/dogfood rollout authority.
