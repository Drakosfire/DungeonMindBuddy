# HANDOFF — APP-STATE: recover invalid Graph tool requests

**Status:** ACTIVE — PRIME authorized this proved local fix after the diagnostic checkpoint.

**Owner:** DungeonMindBuddy APP-STATE; PRIME owns exact-head review and merge. DGF owns live rollout and any fresh case.

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

Handoff pin and implementation head: pending. Acceptance token: `APP_STATE_GRAPH_REQUEST_RECOVERY_ACCEPTED` (pending PRIME review).
