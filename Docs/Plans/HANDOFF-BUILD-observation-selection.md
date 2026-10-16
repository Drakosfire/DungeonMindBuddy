# Build exact reviewed observation batch read

Status: ACTIVE; PRIME solo implementation; ARCHITECTURE independent review.
Base: Buddy origin/main `76db867872aa793fbad2e81163d41d11c3375219`.
Accepted Core prerequisite: #127 merge `f28000d557d97639dca65978fc237bbadc691c5f`.
Branch/checkout: `codex/build-observation-selection`, `/tmp/prime-recap-mention-boundaries`.
Topology: serial successor to merged #1253; current DOGFOOD Ingest #1235/#1237/#1244/#1251 paths inspected and disjoint. No serving/process lease in implementation.
Authority: active Mirathorn lifecycle goal, Core #127 contract and ARCHITECTURE batch-read guidance.

## Outcome and authority boundary

A governed Build turn can select 1–8 exact reviewed observation IDs from its frozen saved-source discovery basis through `expand_graph_retrieval` operation `observations`. Model supplies IDs only; World, Graph revision and exact native source pair come from the verified parent. No target fallback, new scope, source path, source admission, latest selection or automatic body opening. Other surfaces/legacy executor reject this operation. One atomic Core read returns full qualified observations, subject identities and complete disjoint anchor closure; unavailable selection and aggregate overflow return explicit tool feedback with no event/claim/source-pin admission.

Reuse V3 validated Graph events, source-scope extension, transport paging and exact producing-envelope per-target citation derivation. Add an explicit typed diagnostic observation request rather than misrepresenting a batch as an object/neighborhood read. No APP database migration or durable execution version change. Complete records and their exact source pins must actually reach the producing request; omitted pages cannot authorize claims. Existing source opening remains separate, batch opening allowed through existing tool.

## Exclusive expected write set

- This handoff; `Docs/Plans/HANDOFF-BUILD-source-discovery.md` (settle predecessor).
- `pyproject.toml`, `uv.lock` (accepted Core pin).
- `apps/live_control_server/integrations/dungeonmind/selected_observation_reads.py`.
- `apps/live_control_server/services/agent_turn_service.py`.
- `apps/live_control_server/services/graph_tool_presentation.py`.
- `apps/live_control_server/services/agent_graph_policy.py`.
- `apps/live_control_server/services/hermes_graph_interaction_tools.py`.
- `apps/live_control_server/services/agent_context_trace_projection.py`.
- `src/graph_memory/retrieval/models.py`.
- `src/graph_memory/interaction/expansion_executor.py`.
- `src/graph_memory/interaction/session.py`.
- `src/application_state/agent_conversation/context_trace.py`.
- `apps/live-control-ui/src/api/buddyContextTraceTypes.ts`.
- `tests/test_selected_observation_reads.py`.
- `tests/test_agent_build_governed_graph.py`.
- `tests/test_graph_tool_presentation.py`.

## Verification and follow-through

Prove schema/worker serialization, exact frozen source and revision, mixed subjects/disjoint refs, missing selection/overflow with zero admission, unsupported surface, real APP event/source-pin/trace persistence, source opening, complete/partial paged final-envelope authority and durable replay. Existing Plan paths unchanged. Inspect cumulative diff, commit/push/open one PR and dispatch independent review promptly. No provider/retained World/runtime changes before accepted merge and separately verified rollout. Keep worker deadline unchanged; then run one fresh ordinary Council case, retain cost/latency/coverage and compare against the two failed baselines. No unchanged retry or automatic answer acceptance.
