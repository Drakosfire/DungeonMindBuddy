# HANDOFF — APP-STATE: provider lifecycle failure diagnostics

**Status:** ACTIVE — implementation lease issued by PRIME for one bounded Buddy PR.

**Owner:** DungeonMindBuddy APP-STATE. PRIME owns exact-head review, funding disposition, and adoption approval.

**Base:** Buddy `main@ac46913b596ef76b73bba7a73ec8a76ecd926116` (2026-10-13; current remote-tracking main and GitHub latest merged-main commit at activation).

**Topology:** serial, one PR. Isolated nonserving checkout `/tmp/buddy-provider-lifecycle-diagnostic`, branch `codex/provider-lifecycle-diagnostic`. No live deployment, provider call, or service restart is authorized.

## Mission

Preserve bounded, truthful diagnostics for a terminal guarded Hermes provider-lifecycle failure from the pinned Hermes patch through worker-result IPC to the parent turn failure log. The current `provider_lifecycle_unavailable` code merges lifecycle acknowledgement failures and ambiguous provider/stream failures, while the parent labels it with the last host phase (which can be `host_result_decode=ok`). The new diagnostic must identify only facts the producer can prove, so a future no-answer can be traced to its actual lifecycle or transport branch.

Do not claim the retained Mirathorn/Q04 failures have a more specific cause than the evidence supports. Their raw worker payload and lifecycle acknowledgement details were not retained. The change improves deterministic evidence for reproduced/future failures; it does not retroactively resolve the cause of those old turns.

## Required behavior

- Preserve the existing terminal failure code and turn semantics. An uncertain provider outcome remains unknown, blocks redispatch, and is never replayed or cleaned up by this work.
- Carry a small, strictly validated `terminalFailure` record through the existing Hermes result and IPC contract, then into existing runtime metadata/parent logging. Keep `host_result_decode=ok` as a successful phase; report the terminal lifecycle failure separately as `phase=provider_lifecycle`, `phase_status=error`.
- Include only allowlisted lifecycle transition, acknowledgement boolean, deterministic reason category, and—only for known transport exception classes—one allowlisted class name. Do not include exception text, unknown class names, response/request bodies, prompts, source, reasoning, provider credentials, or arbitrary worker values.
- Keep reason categories bounded to producer-observable branches: lifecycle acknowledgement denied, known transport ambiguity, other provider exception ambiguity, or non-completed provider response. Preserve the transition and whether its parent acknowledgement succeeded whenever known. Do not infer a transport/ack cause not proved by execution.
- Reuse the existing host phase collection and serialized Hermes result path. Do not add a trace framework, alter budget/controller policy, broaden retries, or edit generated `out/hermes-agent` alone.
- Add producer transition/ack fixtures against the checked-in patch and a serialized worker-error → host/runtime/parent owning-boundary regression. Prove unknown outcome remains unknown and no answer is fabricated.

## Exact write lease

- `Docs/Plans/HANDOFF-APP-STATE-provider-lifecycle-diagnostics.md` — this active lease and implementation evidence.
- `patches/hermes-agent/0001-pre-dispatch-budget-veto.patch` — safe producer diagnostic from the pinned Hermes provider lifecycle branches; no exception text.
- `apps/live_control_server/services/hermes_graph_agent_contract.py` — strict additive result field validation/serialization for the bounded diagnostic.
- `apps/live_control_server/services/hermes_graph_agent.py` — validate and carry the bounded worker diagnostic into the typed result.
- `apps/live_control_server/services/hermes_agent_runtime.py` — map the typed diagnostic through the existing runtime metadata boundary.
- `apps/live_control_server/services/agent_turn_service.py` — report truthful terminal failure fields while preserving durable unknown-outcome behavior.
- `tests/hermes_patch/test_pre_dispatch_budget_veto.py` — producer branch fixtures through the prepared pinned Hermes source.
- `tests/test_hermes_graph_agent_contract.py` — strict diagnostic wire round trip and rejection cases.
- `tests/test_hermes_graph_agent.py` — typed worker-result mapping and malformed diagnostic rejection.
- `tests/test_hermes_agent_runtime.py` — runtime metadata propagation.
- `tests/test_hermes_graph_agent_host.py` — serialized worker error result crosses host decode with safe diagnostic intact and decode phase still successful.
- `tests/test_agent_turn_service.py` — parent failure log and persistence retain unknown outcome without leaking private payload.

No other paths are leased. If the implementation needs another path or a new public/runtime contract, stop and return to PRIME before editing it.

## Re-anchor facts at activation

- Exact code base: `ac46913b596ef76b73bba7a73ec8a76ecd926116`, also the available `origin/main` ref at activation; GitHub's latest merged-main search returned the same commit.
- Open PR search by exact `agent_turn_service.py` and `hermes_graph_agent_host.py` paths returned no matches. Lifecycle-named branch search returned no active feature branch. Relevant older PRs #763–765, #798, #826, #844, #869, and #1014 do not own these runtime/trace paths; no file collision was found.
- Current deployment receipt is Buddy `ac46913b`, Hermes 0.18.2, Core `d81ed4e126c55ef8df57804c9ab7128b7499c7a1`, GenerationEngine `e8f0fec98eef1a7c1a7fc0bb0b7d867420306929`, schema 0023. Work is isolated from those serving processes and data.
- Existing tests already cover durable unknown outcome, authorization count, and non-replay. The defect is missing producer/IPC diagnostic specificity and misleading failure-phase selection.
- No raw host worker result for Mirathorn or Q04 was available in preserved trace/history/logs. The old failures remain cause-unknown.

## Acceptance witness

1. Deterministic source tests show lifecycle transition and acknowledgement facts survive each relevant producer branch; known transport exception classes use only the fixed allowlist and exception messages never cross the boundary.
2. A bounded serialized worker error decodes as `status=error` with terminal lifecycle metadata while `host_result_decode` remains `ok`; the parent reports `phase=provider_lifecycle phase_status=error` and the safe subreason/transition/ack facts.
3. Parent persistence still records the last authorized attempt as `outcome_unknown`, no assistant answer/completion is created, claimability blocks redispatch, and no provider replay/cleanup occurs.
4. Focused tests, relevant repository gates, exact base→head diff and secret/payload checks pass. The PR body records exact base/head and evidence.
5. No paid/provider calls, live edit, or restart is performed. PRIME reviews the exact PR head before adoption; this lease does not authorize merge or rollout.

## Stop conditions

Stop if the pinned producer cannot distinguish a category deterministically; if safe metadata would require raw exception or response content; if adding the diagnostic changes authorization, retry, answer, or persistence semantics; or if any required path falls outside this lease. Report the narrow blocker and preserve unknown outcome.

## Implementation evidence

- Handoff pin commit: `b5ed0004479680e5b6d95269602c10c3aed6e604`.
- Implementation commit: `972c2687c13268687392ee767f99d09eec18a41b`; intended PR base remains `ac46913b596ef76b73bba7a73ec8a76ecd926116`.
- The pinned Hermes patch applies cleanly to upstream `861d69c7bba8d2ea6a1cd170e989c901c74d32d1` (`git apply --check`). Its SHA-256 is `8142018a4898363263ecbfad6cd203d7ced5a5addfd26474f0bbc2f53d12832e`; prepared source tree is `c47ace962951bb5e58a62afe128f6656e4cff577`.
- Producer acceptance: `tests/hermes_patch/test_pre_dispatch_budget_veto.py::test_pinned_hermes_dispatch_boundary_suite` passed (the pinned-source subprocess reports 16 passed).
- New diagnostic/owning-boundary acceptance: 33 passed across the complete result-contract file and the producer-result, runtime-metadata, serialized worker IPC, and parent persistence/logging witnesses. The parent fixture proves the provider outcome remains unknown, no answer is fabricated, and redispatch stays blocked.
- `ruff check` passed on all changed Python files; `compileall` passed on those files. `git diff --check` passed on source/test/contract files. The source patch file is a unified patch whose context lines contain standard patch-format whitespace; its validity is separately proven by the exact-upstream `git apply --check` above.
- Two broader existing tests fail identically on the exact base under the same borrowed interpreter: `test_mixed_plugin_capability_policy_loads_both_surfaces` (OpenRouter model metadata cannot resolve in this network-restricted environment) and `test_lifecycle_transport_failure_is_unknown_and_never_retried` (the existing fixture receives no lifecycle events). Neither failure is changed by this diff. PRIME directed keeping both as recorded baseline failures and limiting this slice to its owned acceptance witnesses.
- `uv sync --locked` could not fetch pinned Git dependencies because DNS/network access is unavailable. Tests used the existing nonserving interpreter `/tmp/buddy-r6-json-reliability/.venv/bin/python`; no provider request, live edit, or service restart was made.
- Cumulative diff is limited to the 11 leased paths listed above; generated `out/hermes-agent` remains ignored test output and is not checked in. No deviations from the bounded diagnostic objective. The old Mirathorn/Q04 cause remains unknown; the new record improves evidence for reproduced/future failures only.
- The exact cumulative base→implementation commit diff is 11 leased paths, 691 insertions and 55 deletions. It preserves the existing terminal failure code and durable unknown/no-redispatch behavior; the only new runtime surface is an allowlisted optional `terminalFailure` record on error results.
- Final branch head and PR number: pending handoff evidence commit, push, and PR creation.
- Acceptance token: `APP_STATE_PROVIDER_LIFECYCLE_DIAGNOSTICS_ACCEPTED` (pending PRIME review).
