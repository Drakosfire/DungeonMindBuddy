# DOGFOOD: conversation graph context loop

Status: ACTIVE — explicitly authorized by the user's active thread goal, 2026-10-13.
Branch: `codex/buddy-mirathorn-context-loop`.
Checkout: `/home/drakosfire/.codex/worktrees/buddy-context-loop/DungeonMindBuddy`.
Remote main anchor: `ec1da1b7872fe6d4f9fee0b501510a5137677eea`.
Topology: stacked on PR #1118 at exact head `500f27143467df1351748505ec97b996ca1fcc22`; parent merges first, then rebase this successor. Parent presentation lane is frozen for this task. New context-loop UI changes belong to this successor.
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
- New Buddy-owned conversation context/trace service modules and their targeted tests.
- `apps/live_control_server/routes/agent.py`, `apps/live_control_server/models/agent_turn.py`.
- `src/graph_memory/hermes_graph_plugin.py` and its targeted tests.
- `apps/live-control-ui/src/api/{liveApi,types}.ts` and their tests.
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.{tsx,css}` and `WorldPlanAgentConversation.worldHistory.test.tsx`.

Persistence and public contracts must be designed from actual owning boundaries before expanding this allowlist. No dependency pin, lockfile, canonical graph write, ingestion publication or migration is leased implicitly. Any necessary expansion is recorded coherently here before implementation under the user's goal authority.

## Runtime and evidence

5202 currently serves the parent presentation checkout; successor is not deployed. Preserve existing submitted Asks and never replay them. This goal authorizes fresh read-only acceptance queries and normal conversation records; preserve World facts and Plan content. Coordinate deployment only for the dogfood UI/API loop; stable main server operation belongs to its existing owner.

Open PRs inspected on 2026-10-13: #1118 owns parent UI; #1014 is separate inactive runtime preparation; older rules/Build/Ingest lanes do not own the context-loop files. No other context-loop implementation PR found.
