# DOGFOOD: conversation graph context loop

Status: first continuity/compaction slice COMPLETE — #1119 merged head `b0cd7045` as `a2b8db65fc69fa06b6e7e32bb16bcf4ecca5d6b8` on 2026-10-13. The full user goal remains ACTIVE; the context-trace successor owns its own bounded contract in `HANDOFF-DOGFOOD-context-trace.md`.
Branch: `codex/buddy-mirathorn-context-loop`.
Checkout: `/home/drakosfire/.codex/worktrees/buddy-context-loop/DungeonMindBuddy`.
Remote main anchor: `0fb4aa6e6849b614bbec9ab91e772e415354c7b3` (verified 2026-10-13).
Topology: serial, draft PR #1119 is the sole context-loop implementation lane. Predecessor #1118 head `500f27143467df1351748505ec97b996ca1fcc22` merged as `0fb4aa6e6849b614bbec9ab91e772e415354c7b3`; this successor is rebased onto that accepted main. New context-loop UI changes belong to this successor. The predecessor delivered evidence presentation and hidden pending-status diagnostics, plus a requested Backlog capture; its old handoff verification section is historical, not proof of full context-loop acceptance. Successor runtime/trace evidence is recorded separately in the report.
Ownership: Buddy owns runtime orchestration, conversation working context and inspection UX. DungeonMind owns admitted graph truth and source read contracts. Do not create a second graph authority or use arbitrary corpus files as an Agent retrieval fallback.

## Objective and acceptance

Build on-demand source-backed working knowledge about Mirathorn even from an unrelated Plan. Maintain core facts, people, places, uncertainties and recoverable source routes within the conversation. Independently expand when necessary; compact/prune bulky intermediate output without losing useful knowledge or recoverability.

In one fresh conversation from the saved Session 28 Plan, with no added background:
1. Tell me all about Mirathorn.
2. Who are its Rocky Talkie operators?
3. What happened the last time Caelynn spoke to Frank?
4. What could Sara tell us about the tainted provisions?

Answers must address the questions with sources and distinguish recorded events, reported claims, planning and uncertainty. Exercise source reads even when relationships are sparse. Coverage gaps must be explicit. Run a compaction check followed by source rehydration through retained references.

Per-turn expandable trace must show actual searches/tool calls/results/coverage, routes followed, source passages read, working context before/after, retrieved/retained/expanded/compacted/pruned items with concise recorded reasons, supporting retained facts/routes, model, input/output tokens, duration and execution failures. Distinguish present model context from retrievable route handles. No fabricated telemetry or hidden reasoning disclosure.

Completion requires live UI acceptance transcript and trace evidence, owning-boundary tests, cumulative diff review, commit/push and tested PR. Human acceptance and merge remain separate. Goal is not complete until every requirement is verified. Background node summaries and edge suggestions are follow-ups.

## Expected write ownership

- This handoff and `Docs/Reports/REPORT-DOGFOOD-mirathorn-context-loop.md`.
- `apps/live_control_server/services/{agent_context_assembler,agent_runtime,agent_turn_service,agent_turn_trace,hermes_agent_runtime,hermes_graph_agent,hermes_graph_agent_host,hermes_graph_agent_contract,hermes_graph_interaction_tools,hermes_session_store,agent_graph_policy}.py`.
- New Buddy-owned conversation context/trace service modules and their targeted tests, including `tests/test_agent_policy_continuity.py`, `tests/test_agent_conversation_context.py`, `tests/test_agent_turn_service.py` and `tests/test_hermes_graph_agent.py`.
- `apps/live_control_server/routes/agent.py`, `apps/live_control_server/models/agent_turn.py`.
- `src/graph_memory/hermes_graph_plugin.py` and its targeted tests.
- `apps/live-control-ui/src/api/{liveApi,types}.ts` and their tests.
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.{tsx,css}` and `WorldPlanAgentConversation.worldHistory.test.tsx`.

No dependency pin, lockfile, durable trace schema, canonical graph write or ingestion publication is leased implicitly. The product-facing trace is the next serial capability and is recorded as BLOCKED until this continuity/compaction slice is reviewed and merged. Its design must persist actual admitted source passages, tool outcomes and context-management decisions on the durable turn, project them through authenticated World history, and render an expandable trace without hidden reasoning. Before that successor starts, re-anchor and explicitly expand its write set to include the owning turn store/API/UI contracts and migration.

## Runtime and evidence

5202 now serves this continuity/compaction checkout at `b0cd7045`, with the exact same tree as merged main `a2b8db65`. A new first Mirathorn Ask failed after three provider responses; its saved ledger and uncertainty are documented in the report. Preserve it and never replay it. This goal authorizes fresh read-only acceptance queries and normal conversation records; preserve World facts and Plan content. Stable main server operation belongs to its existing owner.

Open PRs inspected on 2026-10-13: #1118 owns parent UI; #1014 is separate inactive runtime preparation; older rules/Build/Ingest lanes do not own the context-loop files. No other context-loop implementation PR found.
