# Hermes Phase 0 — Reference Scan and Cleanup Gate

**Date:** 2026-07-15
**Status:** Initial approved cleanup set removed; S0 verification green
**Related maps:** [`HERMES-PHASE-0-CODE-DEMOLITION-MAP.md`](HERMES-PHASE-0-CODE-DEMOLITION-MAP.md), [`HERMES-PHASE-0-UI-CLEANUP-MAP.md`](HERMES-PHASE-0-UI-CLEANUP-MAP.md)

## Scan results

### Backend demolition symbols

The following scan was run over active backend and test paths:

```text
run_hermes_conversation
_process_hermes_context_query
_process_hermes_cli_query
HERMES_CLI_
hermes_cli_oneshot
hermes_graph_read_tool_adapter
hermes_graph_read_tools
```

Result: **no matches** under `apps/live_control_server/` or `tests/`.
Archived planning documents may retain these names as historical evidence.

The deleted five-tool modules had no remaining non-test production imports. The active
graph plugin registers the two interaction tools from
`hermes_graph_interaction_tools.py`.

### Plan UI references

The backend picker and dead toolbar scans returned:

- `plan-agent-backend-picker`: no component or stylesheet matches;
- `PlanToolBar.tsx`: no file and no import;
- `Live retrieval` / `Hermes tools`: no picker labels in the active Plan component;
- the only remaining Plan references are a compatibility-thread test title and the
  retained `LiveQueryBackend` state/request path.

Retained references confirmed:

- `LiveQueryBackend` and `query_backend` remain in the API and thread model for
  persisted Live threads;
- new Plan state initializes `queryBackend` to `hermes`;
- graph evidence/source-anchor inspection still uses
  `WorldGraphQueryContextPanel`, `TraceDetailsPanel`, and
  `postWorldGraphSourceAnchorRead`;
- bounded continuity remains provided by `hermesConversationHistory` and the thread
  state.

### Retained adapters

| Adapter | Why retained | Removal gate |
|---|---|---|
| `src/live_play/live_query_context.py` / `manifest_context_query.py` | Current Live compatibility/eval path | S1 latest-recap acceptance |
| `integrations/hermes/plugins/dungeonbuddy/` | Legacy plugin still supports the retained Live path and negative-path tests | Migrate all Live consumers |
| `src/agent/planner.py` statblock generation | Legacy/eval authoring consumer | S2 typed statblock workflow |
| v2 statblock workbench/lifecycle | First future domain adapter | Creative draft/review/promotion proof |
| Graph Review workbench | Secondary inspection/authoring surface | Governed conversational promotion |
| `hermes_graph_query.py` defensive no-session/citation branches | Contract compatibility and fail-closed behavior | Prove session hydration invariant first |

## Test evidence

### Backend and S0

```text
uv run pytest -q tests/test_live_query_hermes_graph.py tests/test_hermes_graph_agent.py tests/test_live_control_server.py
122 passed, 10 warnings

python -m compileall -q apps/live_control_server/services
exit 0
```

The warnings are existing Pydantic field-shadowing warnings; no new failure was
introduced by the demolition.

The complete retained foundation gate was also run:

```text
uv run pytest -q tests/test_graph_kernel_world_retrieval.py tests/test_graph_retrieval_interaction.py tests/test_live_query_hermes_graph.py tests/test_hermes_graph_agent.py tests/test_live_control_server.py
200 passed, 10 warnings
```

The retained v2 statblock adapter gate was:

```text
uv run pytest -q tests/test_live_statblock_workbench_endpoint.py tests/statblocks
75 passed, 10 warnings
```

### Plan UI cleanup

```text
cd apps/live-control-ui
npm test -- --run src/planSurface/PlanSurfaceShell.test.tsx
55 passed
```

The full UI suite remains red independently of this cleanup:

```text
7 test files failed; 27 tests failed
```

Observed failure families:

- `ExistingObjectResolverPanel.test.tsx`: `overridePhrase` receives a mouse event
  instead of a string;
- `IngestionModule.test.tsx`: ingest flow/graph-flag expectations;
- `App.test.tsx`: Plan/Tiptap route expectations;
- `projectionRegistry.test.tsx`: graph object card expectation;
- Graph Review author-draft/workbench tests: tab/relationship staging expectations;
- `tiptapRunbookDescriptors.test.ts`: stale North Gate starter content.

These failures are outside the approved Plan picker/toolbar slice and are recorded as
stale/broken follow-up work rather than masked by the cleanup.

The UI typecheck is also already red across unrelated files, including
`IngestionModule.tsx`, `TraceDetailsPanel.tsx`, `agentInteractionHistory.ts`,
Graph Review modules, and `worldGraphProjectionAdapter.ts`. The two existing
`PlanAgentInteractionBar.tsx` diagnostics are unchanged by this slice.

## Final approval record

Approved and removed in this pass:

1. dead Hermes CLI/context implementation from `live_agent_loop.py`;
2. superseded five-tool adapter and its whole-module skipped tests;
3. unreferenced `PlanToolBar.tsx`;
4. primary Plan Live/Hermes backend picker and its dedicated CSS;
5. obsolete picker-dependent assertions/interactions in the owning Plan shell test;
6. stale dogfood wording that instructed the operator to select the removed picker.

Not approved for deletion:

- the retained S0 graph retrieval, source-anchor, claim validation, revision, and
  bounded continuity paths;
- Live compatibility, planner statblock generation, Graph Review, or v2 statblock
  adapters;
- secondary evidence/trace surfaces;
- legacy thread-storage migration behavior.

The Phase 0 gate is therefore **partially closed for the approved low-risk removal
set**. The remaining stale-test inventory and deferred adapter migrations stay open
until S1/S2 evidence exists.
