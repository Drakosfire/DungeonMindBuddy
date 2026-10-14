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

- Handoff pin commit: to be recorded after this file is committed on the isolated branch.
- Implementation head, test results, cumulative diff, and deviations: pending.
- Acceptance token: `APP_STATE_PROVIDER_LIFECYCLE_DIAGNOSTICS_ACCEPTED` (pending PRIME review).
