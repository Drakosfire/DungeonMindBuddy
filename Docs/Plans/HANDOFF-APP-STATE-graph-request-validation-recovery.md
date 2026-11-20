# HANDOFF — APP-STATE: recover invalid Graph tool requests

**Status:** SETTLED — exact-head independent PRIME review accepted this capability; PR #1137 merged.

**Owner:** DungeonMindBuddy. During the operator-directed solo foundational phase, PRIME personally owns further work. Delegated implementation, review and DOGFOOD assignments are stopped.

**Base:** `main@f2964c12e82c149c3d69a9798626a90164303707`.

**Predecessor:** accepted diagnostic PR #1135, reviewed head `f64fbb3f48ebad218969c3e67b0814a486273023`, merged `d0c2b32e273d39c84d481f3186992fc5a35a1cb1`.

**Topology:** serial, one implementation PR on `codex/graph-request-validation-recovery`. Durable nonserving checkout: `/home/drakosfire/.codex/visualizations/2026/09/26/01a0dbd8-4d8d-7372-a9bc-ea25c2d59a19/buddy-provider-lifecycle-diagnostic-review`. No ports, services, live database, provider calls, or restart belong to this lane.

## Primary invariant

A Pydantic failure constructing `ExpandGraphRetrievalRequest` before any native Graph IO is a known rejected input. Return safe, actionable `422 invalid_arguments` feedback through the existing exact parent-denial path. Leave the turn's failure unset, admit no Graph evidence or operation, and permit a corrected operation through a fresh authorized request. Validation or uncertainty after IO must retain the existing fail-closed behavior.

## Proved failure and limits

The DGF case at deployed `d0c2b32` completed one provider response, then logged `plan_graph_parent_failure stage=request_validation error_code=validation_error`. Parent request construction at `agent_turn_service.py` (`ExpandGraphRetrievalRequest.model_validate(normalized)`, activation line 1814) feeds a blanket exception handler which marks `graph_operation_indeterminate`. That poisons the next request guard and surfaces as `request_budget_exceeded` during response normalization. No native retrieval or result-size gate was reached.

A read-only synthetic parent fixture on the exact deployed source reproduced `503 graph_operation_unavailable`, parent failure `graph_operation_indeterminate`, zero validated Graph events, and denied next authorization for an invalid operation. The exact live malformed field was not retained in the supplied trace/history; do not invent it or infer a provider cause. Private receipts stay outside Git.

Current remote main and open PRs were refreshed. Open #1014, #869, #844, #826, #798 and the paused RLH #763–765 lanes do not activate this Graph request-validation seam; no active overlapping APP-STATE lease was found.

## Exact write lease

- `Docs/Plans/HANDOFF-APP-STATE-graph-request-validation-recovery.md` — scope and evidence.
- `apps/live_control_server/services/agent_turn_service.py` — isolated pre-IO request-validation handling and safe static input guidance.
- `tests/test_agent_turn_service.py` — parent-boundary recovery and uncertainty regressions.

## Non-goals and stop conditions

Preserve World/revision/source authority, exact denial matching, provider authorization, no local retry, persistence fences, and existing count/context/storage/deadline contracts. No cap change, provider plumbing, new trace framework, source/result projection change, or schema weakening. Do not catch all Pydantic errors: result validation after IO remains uncertain. Never return raw invalid values, exception text, private extra-field names, source prose, or credentials. A needed fourth path or new durable/public contract returns to PRIME.

## Acceptance witness

1. Invalid request fixtures produce known 422 feedback before any Graph IO; no failure, Graph event, evidence, or count admission occurs.
2. Static field guidance is actionable and leaks no invalid value or private extra-field name.
3. Exact feedback can inform the next authorized request; corrected input reaches the existing parent native-read adapter with a synthetic result and permits provider continuation. Forged/altered denial feedback remains rejected.
4. Native transport, post-read validation, and persistence failures remain indeterminate; World/revision mismatch still fails closed.
5. Run focused parent tests, relevant owning-boundary gates, Ruff, and cumulative base→head inspection. Commit/push/open one PR; no merge or live probe.

## Evidence

- Handoff pin: `dc957dc61c399a793210c4404ef27aefa198b5a9`; implementation commit: `cb1744826a01ee6a1ab8dd81d157d7eb48e4f105`.
- The new catch surrounds only pre-IO `ExpandGraphRetrievalRequest.model_validate`. It returns 422 through the existing exact-denial recorder; static published-field guidance excludes invalid values, extra-field names, exception text, and source content. The native-read/result/persistence exception handler is unchanged.
- Focused owning-boundary suite: **23 passed**, covering four malformed input cases, corrected request through the native adapter with an honest empty synthetic result and subsequent provider authorization, post-IO transport/response-validation/persistence uncertainty, revision denial, forged-denial rejection, V3 source admission, and provider lifecycle/persistence fences.
- Expanded owning module (one known stalled HTTP case deselected): **127 passed, 2 failed, 5 setup errors**. Both `test_reconciled_turn_context_policy_before_provider_freeze` failures (`unfrozen`, `frozen-v1`) reproduce identically on deployed base `d0c2b32`. Five real-PostgreSQL mounted tests could not connect to a disposable test database; their bodies were not verified here. The excluded HTTP history test was reproduced on the base under a 15-second timeout (exit 124), with its stack blocked in `TestClient.__enter__`/AnyIO.
- Ruff and `git diff --check` passed. `uv sync --locked --offline` synchronized current-main dependencies from local caches in this nonserving lane.
- Cumulative base→head inspection contains exactly the three leased paths. Existing structural target cardinality and technical context/count/storage/deadline contracts are unchanged. No Graph/provider execution, live edit, restart, or fresh product probe occurred.
- The supplied live artifacts prove request-schema validation failed before native IO. They do not preserve which model-supplied field was invalid; no claim is made that this synthetic input is the live input. DGF retains any later live validation/adoption authority.
- Acceptance token: `APP_STATE_GRAPH_REQUEST_RECOVERY_ACCEPTED` (pending PRIME review).

## Acceptance and operator-directed takeover

- Reviewed implementation head: `7c223f37f06085340d795717bcef44269995389a`.
- PR: [#1137](https://github.com/Drakosfire/DungeonMindBuddy/pull/1137), merged at `8134b1c9bb0592131b14a999297541d4c80f09b8`.
- PRIME personally inspected the cumulative three-path diff and independently ran 17 focused parent-boundary cases: passed in 1.03 seconds. The implementation was authored by SERVER before the solo transition; do not attribute it to solo implementation.
- [Independent acceptance record](https://github.com/Drakosfire/DungeonMindBuddy/pull/1137#issuecomment-6159051792). Acceptance token: `APP_STATE_GRAPH_REQUEST_RECOVERY_ACCEPTED`.
- The operator made foundational value the sole priority and directed PRIME to work without other agents. The earlier DGF rollout assignment is suspended. No live rollout, model call or full-World acceptance is claimed by this merge.
