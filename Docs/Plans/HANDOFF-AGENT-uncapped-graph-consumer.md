# AGENT: ordinary conversation without fixed execution counts

Status: ACTIVE — PRIME implementation under standing operator approval; ARCHITECTURE independently reviews.

Base `f4f3cfb5e4e9ba75100cc41058d4f3ca3ad1ba3e`, branch `codex/agent-uncapped-graph-consumer`, isolated non-serving checkout `/tmp/prime-recap-mention-boundaries`. First pin before implementation. Serial consumer of accepted APP #1224 and SDK #1225. Open ownership inspected; no overlapping active Agent/APP/IPC lease. Gold audit completed read-only.

## Invariant and failure cases

New ordinary governed Agent and consultation turns explicitly use required nullable provider/tool/Graph count fields and accepted APP uncapped versions. Tools remain available after four requests/eight Graph/source/context calls and SDK's old90 default. Preserve strict identity/context window/output reserve, real usage and ledger accounting, deadlines, cancellation, fences, uncertainty stops, source admission, producing-envelope evidence and completion validation. No count-based forced final request or toolless summary. Finite historical policies retain their existing guards and representations.

## Exclusive write set

- `Docs/Plans/HANDOFF-AGENT-uncapped-graph-consumer.md`
- `Docs/Plans/HANDOFF-AGENT-nullable-harness-iterations.md` — predecessor settlement
- `apps/live_control_server/services/agent_turn_service.py`
- `apps/live_control_server/services/hermes_graph_agent_contract.py`
- `apps/live_control_server/services/hermes_graph_agent.py`
- `apps/live_control_server/services/plan_action_consultation.py`
- `src/application_state/agent_conversation/types.py` — related-context count guard only
- `tests/test_hermes_graph_agent_contract.py`
- `tests/test_hermes_graph_agent.py`
- `tests/test_graph_parent_page_reservation.py`
- `tests/test_agent_turn_service.py`
- `tests/test_agent_uncapped_graph_execution.py` — owning integrated proof using existing Build fixture
- `tests/test_plan_action_consultation.py`
- `tests/application_state/test_agent_conversation_service.py`

## Contract and exclusions

New request-budget schema `dmb_agent_request_budget_uncapped_v1` requires all three existing reservation keys explicitly null. Finite prior schema stays strict. New ordinary APP aggregate-token ceilings are null rather than multiplied count caps; per-request windows/reserves stay finite. Worker Graph/source/context counters record usage but no count retirement under uncapped schema. Parent related-context and APP related-context count guard apply only to finite historical policy. Explicitly pass nullable iteration option to accepted SDK. V2 finite source-call policies remain historical; ordinary governed source execution uses V3. Passage-character/result/event/storage capacity limits remain explicit and unchanged.

No prompt/style/output-reserve/provider-routing changes beyond removing count-specific instructions. No schema migration beyond accepted0025, provider request, serving change, corpus mutation, extraction or World publication in implementation slice. Runtime follow-through uses separately owned preview and accepted matched source/SDK only.

## Verification

Strict nullable IPC roundtrip; reject omitted/mixed/bool/string fields. Owning APP→IPC→worker/parent proof above4 provider authorizations and8 Graph/source/context operations, with exact evidence admission; actual SDK iteration proof inherited from #1225. Prove retained tools, finite refusal, window/cancellation/uncertainty/fencing behavior. Consultation shared budget must construct valid APP policy. Inspect cumulative diff, tests, Ruff/diff. Commit/push/open one assigned PR and return exact base/head/evidence for independent review before PRIME merge; ordinary live acceptance remains a subsequent required witness.
