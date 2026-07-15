# HANDOFF — PR354: Single-turn Hermes backend product cutover

**Created:** 2026-07-14  
**Status:** ACTIVE — opened for review; do not begin PR355.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-pr354-hermes-single-turn-backend-cutover.md`  
**Implementation base:** `d4fdb6c8f7b9fe855f1d0062883ce56521986fb6` — merge of GitHub PR #353  
**Reviewed PR353 head:** `5281973bc42a4722a17c42b67ec398ea55535175`  
**Branch:** `agent/pr010b4b-hermes-single-turn-cutover`  
**Suggested PR title:** `feat(agent): route Plan Hermes queries through graph runtime`

> **Dispatch rule**
>
> Branch from the accepted PR353 merge SHA. Consume the merged host as a stable predecessor. Do not reopen worker lifecycle, multiprocessing, queue, retry, transcript, or shutdown design.
>
> Opening PR354 is the final repository action for this dispatch. Stop after opening it and do not begin PR355.

## Mission

`POST /api/live/query` with `query_backend="hermes"` dispatches one authoritative, revision-pinned `HermesGraphAgentTurnRequest` through the global PR353 host and returns a grounded answer, qualified answer, stable abstention, or typed error without invoking any legacy factual retrieval or fallback path.

## Invariant

The server, not the browser or model, owns graph scope, revision, capability, grounding state, and fallback policy. A Hermes answer is never represented as graph-grounded unless bounded PR353 tool events prove successful graph retrieval and admitted source-anchor evidence at the resolved scope and revision.

## Implementation paths

| Action | Path |
| --- | --- |
| Create | `apps/live_control_server/services/hermes_graph_query.py` |
| Modify | `apps/live_control_server/services/live_agent_loop.py` |
| Modify | `apps/live_control_server/routes/live.py` |
| Create | `tests/test_live_query_hermes_graph.py` |
| Modify | `tests/test_live_control_server.py` |
| Sync | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` |
| Sync | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` |

Inspection-only predecessor paths (unchanged): `hermes_graph_agent_host.py`, `hermes_graph_agent_contract.py`, `hermes_graph_agent.py`, host/Rung 3 tests, `main.py`.

## Call path

```text
POST /api/live/query
  -> Hermes-only request validation
  -> resolve authoritative AgentWorldGraphQueryContext
  -> translate resolved scope into HermesGraphAgentTurnRequest
  -> get_hermes_graph_agent_host()
  -> host.execute(request)  # once; no route-level retry
  -> classify result from status + final_response + tool_events
  -> return dmb_live_query_response_v1 product envelope
```

## Pause gate

```text
STOP.
REQUEST REVIEW.
DO NOT BEGIN PR355.
```

PR355 may begin only from the accepted PR354 merge SHA.
