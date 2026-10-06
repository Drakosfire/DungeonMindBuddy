# SERVER Plan/Graph synthetic answer witness

**Recorded:** 2026-10-06

**Owning repository:** DungeonMindBuddy

**Budget repair:** PR #935, merged at `08e8cbe1207b74b0e15c6f95070899c5cc7c69fd`

**Answer contract:** PR #938, exact implementation head `046e7a3833f92be3c1ab0374f0762d1924f89ac5`, merged at `b92e950cdbc68b47e202822515b13a4ba4228469`

This report preserves the unique synthetic real-provider evidence from the Plan/Graph SERVER repair. The tests used a synthetic managed World, synthetic native Graph, a committed synthetic Plan, a disposable PostgreSQL database, an isolated Hermes profile, the normal public Agent route, parent authorization, and the patched Hermes worker. They did not read or write Elderwyld, an operator database, or private campaign material. No failed turn was replayed.

## Outcome and limits

| Run | Exact head | Terminal result | What it established |
| --- | --- | --- | --- |
| Initial budget-repair witness | `76871cabcfe8e9f14376931f56164677d37d9ea4` | HTTP 502 `answer_validation_failed` | Two real calls reached the provider; the model returned unknown segment fields and a status outside the typed contract. The original witness did not retain the APP-STATE turn before teardown, so its authorization count and persistence state are **unknown**. |
| First answer-contract witness | `f1250b681dd51473adb4854c22c93617b0f9e4f8` | HTTP 502 `answer_validation_failed` | Two authorized envelopes and a validated Graph operation were durable. The model used the correct JSON shape but selected `plan_only_insufficient_evidence` after sufficient Graph evidence reached its final request. The failed turn reopened in history. |
| Graph-dependent answer witness | `046e7a3833f92be3c1ab0374f0762d1924f89ac5` | **HTTP 200, completed** | The Plan lacked the asked fact. The model used a sufficient, complete Graph operation to answer that the Tavern contains a Hidden Cellar, produced one bound citation, and the completed turn reopened exactly once in history. |

The accepted live answer was readable: “The Prancing Tavern contains a Hidden Cellar.” The cited relationship was `rel:tavern-cellar`, with evidence `ev:cellar` at the pinned Graph revision. The producing provider attempt was the second authorized attempt and included the validated operation. The server's strict completion validator was not weakened or changed. The final owning route, service, and Harness suite passed **95 tests** on isolated PostgreSQL; Ruff and `git diff --check` passed.

This is synthetic product-route evidence. It does **not** accept production Elderwyld behavior. Provider cost remains **unknown**: the Hermes ledger did not have a price source, so its zero-valued placeholders are not a $0 claim. The successful turn took 19,520 ms wall time and used two model calls. Provider credentials, request headers, private corpus text, and the full provider request body are omitted.

## Safe durable receipt for the successful turn

The following is the complete safe witness projection captured before disposable database teardown. Local temporary file paths have been removed because they are not durable evidence. `authorized_envelope_sha256` values identify the exact parent-authorized provider request bodies without exposing those bodies. The second is the producing envelope. `public_request_sha256` hashes the synthetic HTTP request, a different object.

```json
{
  "answer_text_bytes": 45,
  "answer_text_sha256": "b52a3947a6c052f1146aa9deda17b3b02e36bb05f3837bd9f83084c7e403e5c1",
  "assembled_input_sha256": "bd9318d2f6936da88a8e3382991fa5b94b82b10c957ee0041d510793da0da4ec",
  "authorized_attempt_ids": [
    "1a485a4b-1e96-4409-81dd-0ccda65b5a14",
    "2fef1b83-218c-4463-a6f3-43eab6730363"
  ],
  "authorized_envelope_sha256": [
    "bd9318d2f6936da88a8e3382991fa5b94b82b10c957ee0041d510793da0da4ec",
    "52cd1bde41e64e2d4cf8e55b12914f3b6ab684b6e64e248ef9c96d95b2280ec8"
  ],
  "citation_count": 1,
  "completion_binding_attempt_ids": [
    "2fef1b83-218c-4463-a6f3-43eab6730363"
  ],
  "completion_present": true,
  "completion_segment_kinds": [
    "graph_claim"
  ],
  "completion_status": "graph_grounded",
  "conversation_id": "94ffc40c-9af9-4b95-84ea-56e210a47a9e",
  "elapsed_ms": 19520,
  "endpoint": "https://api.openai.com/v1/",
  "final_included_operation_counts": [
    0,
    1
  ],
  "head": "046e7a3833f92be3c1ab0374f0762d1924f89ac5",
  "history_completion_present": [
    true
  ],
  "history_schema": "dmb_agent_conversation_history_v2",
  "history_status": 200,
  "history_turn_count": 1,
  "history_turn_statuses": [
    "completed"
  ],
  "http_status": 200,
  "model": "gpt-6-luna",
  "operation_coverage": [
    "complete"
  ],
  "operation_sufficiency": [
    "sufficient"
  ],
  "persisted_failure_code": null,
  "persisted_status": "completed",
  "provider_outcomes": [
    "sdk_entered",
    "response_received",
    "sdk_entered",
    "response_received"
  ],
  "public_code": null,
  "public_request_sha256": "fdd61c19288f698aef10a70b1ebe9eea40c84f34ad32bfdbf28c08acf7b77a65",
  "receipt_sha256": "0dd4a1a344178ef9412e597b8cdd891489123cba2272aedb3c07c4e90ef07a50",
  "turn_id": "ff4d3686-4eba-4107-8c51-e5b5ea213aaf",
  "usage": [
    {
      "actual_cost_usd": 0.0,
      "api_call_count": 2,
      "billing_base_url": "https://api.openai.com/v1/",
      "billing_provider": "openai-api",
      "cache_read_tokens": 4999,
      "cache_write_tokens": 0,
      "cost_source": "none",
      "cost_status": "unknown",
      "estimated_cost_usd": 0.0,
      "input_tokens": 7041,
      "model": "gpt-6-luna",
      "output_tokens": 325,
      "reasoning_tokens": 89
    }
  ],
  "validated_operation_count": 1,
  "world_id": "synthetic-graph-cellar-world"
}
```

## Exact synthetic final model outputs

These are the model final-answer JSON bytes, before server-owned receipt fields were inserted. They contain only the synthetic fixture. SHA-256 values hash each JSON string without a trailing newline.

### Budget repair: unknown typed fields

SHA-256: `4913c51e2c0b86504192ae57171fde6844029be262d0fa3990ff3100b741cc97`; UTF-8 bytes: 500.

```json
{"answer_context_status":"graph_used_insufficient_evidence","answer_segments":[{"type":"graph_claim","text":"The graph identifies the tavern as The Prancing Tavern, but provides no information about where it is.","claim_ids":["identity:obj:tavern"],"evidence_ids":[]},{"type":"plan_claim","text":"The committed Plan says the keeper waits by the tavern."}],"citation_map":{"graph_claims":[{"segment_index":0,"claim_ids":["identity:obj:tavern"],"evidence_ids":[]}],"plan_claims":[{"segment_index":1}]}}
```

### Answer contract: wrong Plan-only status

SHA-256: `1483326c0fa8948227dfbd76eda2e61b9e49c522781e9fab50995cece1d63236`; UTF-8 bytes: 228.

```json
{"answer_context_status":"plan_only_insufficient_evidence","answer_segments":[{"kind":"plan_claim","text":"The committed Plan says the keeper waits by the tavern, but does not specify where the tavern is."}],"citation_map":null}
```

### Accepted Graph-dependent answer

SHA-256: `a9a8952be71f16db1b30a5f0af07e0d03182c2bb04e1e59dce8ea8f1b8e9c38a`; UTF-8 bytes: 555.

```json
{"answer_context_status":"graph_grounded","answer_segments":[{"kind":"graph_claim","claim_id":"rel:tavern-cellar","text":"The Prancing Tavern contains a Hidden Cellar.","target_kind":"relationship","target_id":"rel:tavern-cellar","graph_revision":"rev:ece79240119cd07dfbc09d461ac6cd74","evidence_ref_ids":["ev:cellar"]}],"citation_map":{"entries":[{"claim_id":"rel:tavern-cellar","target_kind":"relationship","target_id":"rel:tavern-cellar","graph_revision":"rev:ece79240119cd07dfbc09d461ac6cd74","evidence_ref_ids":["ev:cellar"],"source_opened":false}]}}
```

The successful public response projected `answer_basis=committed_plan_plus_world_graph`, `answer_context_status=graph_grounded`, one `graph_claim`, and a citation map bound to receipt `0dd4a1a344178ef9412e597b8cdd891489123cba2272aedb3c07c4e90ef07a50`. Its history response was `dmb_agent_conversation_history_v2` with one `completed` turn and the same completion.
