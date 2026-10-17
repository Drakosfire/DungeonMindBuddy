# Build Harness insertion tool

Status: ACTIVE — explicit operator request, PRIME implementation; ARCHITECTURE review.
Base: 659652ae (remote main, fetched 2026-10-16). Serial, one implementation PR.
Checkout: /tmp/prime-recap-mention-boundaries; branch codex/build-harness-insertion.

## Outcome and critique
Discuss in the managed World conversation, ask the Agent to put agreed content on
this saved Build page, inspect an inline proposal, approve insertion, explicitly
Save/reopen. Real Harness tool selection replaces the UI writing regex. No
conversation alone edits a page. Reuse the existing durable proposal generator,
its own provider authorization, raw response, prompt capture and insertion bridge.

First adoption: governed Build with explicitly requested World Graph. Graph On
alone never grants editing: require a separately captured exact mounted editor
basis. Graph Off remains discussion-only, stated honestly; never silently enable
Graph. ARCHITECTURE accepts this bounded adoption; graphless tools are a successor.

Host binds World, current document revision/hash/visibility, draft hash and caret
and generations. Model supplies instruction only. Bind durable proposal origin to
conversation, client/durable turn, tool invocation and arguments hash. Exact replay
returns its existing action; changed intent or uncertain generation never starts
another provider call. Tool may prepare an inert proposal, never insert/save,
publish Graph facts, choose another document, or gain filesystem tools.

Preserve source/Graph authority and existing durable answer validation. Keep prior
proposals readable in subsequent conversation. Fail closed on stale or foreign
basis; keep preview only until operator approval. Refresh proposal receipts after
turn completion, including failed/uncertain Agent delivery; old UI generations
cannot retarget insertion. No partial provider events invented from other calls.

## Exclusive expected write set
- this handoff
- apps/live_control_server/routes/agent.py (reject client-forged tool origins)
- apps/live_control_server/models/agent_turn.py
- apps/live_control_server/models/build_document_proposal.py
- apps/live_control_server/services/agent_runtime.py
- apps/live_control_server/services/agent_turn_service.py
- apps/live_control_server/services/hermes_agent_runtime.py
- apps/live_control_server/services/hermes_graph_interaction_tools.py
- apps/live_control_server/services/hermes_graph_agent_host.py
- apps/live_control_server/services/hermes_graph_agent.py
- apps/live_control_server/services/build_document_proposal.py
- apps/live_control_server/services/build_insertion_tool.py (new)
- src/graph_memory/hermes_graph_plugin.py
- src/application_state/agent_conversation/types.py
- src/application_state/build_proposal/service.py (atomic live Agent origin claim at reservation/authorization/SDK entry)
- src/application_state/build_proposal/types.py
- apps/live-control-ui/src/api/types.ts
- apps/live-control-ui/src/api/buildDocumentProposalApi.ts
- apps/live-control-ui/src/planSurface/components/BuildComposeProposal.tsx
- apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx
- apps/live-control-ui/src/buildSurface/BuildCompose.integration.test.tsx
- tests/test_build_insertion_tool.py (new)
- tests/test_hermes_agent_runtime.py
- tests/test_hermes_graph_agent_contract.py

No Ingest edits or Graph/database schema publication. Existing JSON payload store
carries additive origin metadata; preserve null-absent historical fingerprints.
5202/8000 final rollout after independent exact-head review. Both API readers
8000/8002 adopt the new optional origin JSON before new Harness writes because
they share APP state; 5876 UI may remain stable. No schema migration.
Temporary previews may use 5208/8008 and disposable APP54329 with cleanup.
Private synthetic evidence under local research state, never credentials in logs.

## Verification / completion
Mounted ordinary discussion→tool proposal→preview→insert→manual Save/reopen;
real process-isolated Harness tool selection and live synthetic provider witness;
negative stale target/cross-World, duplicate/changed tool calls, uncertain provider,
no mutation before approval. Exact cumulative diff + independent ARCHITECTURE
review; commit/push/open PR, merge under PRIME and settle/roll out 5202.

Independent review repair: origin includes the Agent claim attempt. Actual APP
locks validate the live unexpired running claim and exact World/conversation/source
and client idempotency identity before reservation and both provider gates. Cached
worker state alone grants no provider authority. Generator receipts remain separate.
