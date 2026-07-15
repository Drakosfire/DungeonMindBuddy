# Hermes Phase 0 — Code Demolition Map

**Date:** 2026-07-15
**Status:** Evidence-backed cleanup gate; initial removal set approved
**Scope:** `DungeonMindBuddy` backend/runtime and owning tests
**Product contract:** [`../Plans/PLAN-hermes-campaign-authoring-foundation-reset.md`](../Plans/PLAN-hermes-campaign-authoring-foundation-reset.md) §0C/§0E
**Re-anchor:** [`../Plans/REANCHOR-hermes-campaign-authoring-foundation-2026-07-15.md`](../Plans/REANCHOR-hermes-campaign-authoring-foundation-2026-07-15.md)

This map records the reference-checked code cleanup boundary. It is intentionally
stricter than a broad “old-looking code” sweep: a path is removable now only when
its production references are absent or its replacement already owns the same
product boundary. Deferred candidates remain explicit compatibility adapters.

## Retained S0 foundation

The following paths are protected from this cleanup:

- `src/graph_memory/kernel/world_retrieval.py` — revision-pinned graph retrieval and
  admitted source-anchor reads.
- `apps/live_control_server/services/world_graph_retrieval.py` — server-side retrieval
  wrapper.
- `src/graph_memory/interaction/` — `GraphRetrievalSession`, bounded expansion,
  authority classification, answer validation, source-read integrity, and session
  hydration/store.
- `apps/live_control_server/services/hermes_graph_agent.py`,
  `hermes_graph_agent_host.py`, `hermes_graph_agent_contract.py`, and
  `hermes_graph_interaction_tools.py` — the current two-tool process-isolated graph
  agent path.
- `apps/live_control_server/services/hermes_graph_query.py` — graph turn translation,
  scope enforcement, claim acceptance, trace projection, and product envelope.
- `apps/live_control_server/services/agent_world_graph_query_context.py` — server-owned
  scope, admissibility, revision, and preflight resolution.
- Bounded visible-prose continuity in
  `hermes_graph_query.py`, `routes/live.py`, and the Plan interaction state.
- `src/statblocks/` and the v2 statblock workbench/lifecycle services — retained as
  the first future authoring-domain adapter, not yet promoted into a generic kernel.

The S0 smoke boundary is:

```text
Plan/API request
  → server-owned graph context
  → hermes_graph_agent_host
  → two interaction tools
  → GraphRetrievalSession
  → world retrieval/source-anchor read
  → claim-validated response
```

## Approved removal set

These paths are approved for removal in this cleanup pass because the reference scan
found no production consumer on the current graph-agent product route.

### A. Dead Hermes conversation/CLI slice

Remove the CLI-only and pre-graph Hermes block from
`apps/live_control_server/services/live_agent_loop.py`:

- `HERMES_CLI_*` environment constants;
- `_context_summary_from_packet`;
- `_safe_command_summary`;
- `_prompt_context_from_packet`;
- `_extract_usage_from_session_blob`;
- `_collect_hermes_home_artifacts`;
- `_build_agent_trace`;
- `_hermes_in_process_steps`;
- `_run_dungeon_context_lookup_for_cli`;
- `run_hermes_conversation`;
- `_process_hermes_context_query`;
- `_hermes_cli_timeout_seconds`;
- `_process_hermes_cli_query`;
- `_hermes_cli_error_response`;
- imports used only by that slice (`json`, `shutil`, `subprocess`, `time`,
  `load_dungeonmindbuddy_dotenv`).

Keep `process_live_query`, its `live` manifest/dice route, and
`_should_route_context_lookup`; those are still compatibility adapters until S1
replaces the Live backend. Keep the graph branch exactly as the S0 route.

Owning stale tests to remove or update with the slice:

- `tests/test_live_control_server.py` — CLI-env “must not invoke subprocess” tests;
- `tests/test_live_query_hermes_graph.py` — monkeypatches for deleted legacy helpers.

### B. Superseded five-tool model adapter

Remove:

- `apps/live_control_server/services/hermes_graph_read_tool_adapter.py`;
- `apps/live_control_server/services/hermes_graph_read_tools.py`;
- `tests/test_hermes_graph_read_tool_adapter.py`;
- `tests/test_hermes_graph_read_tools.py`.

The active model-facing catalog is
`hermes_graph_interaction_tools.py` plus
`src/graph_memory/hermes_graph_plugin.py`. The two-tool catalog is the current
replacement; the five-tool modules have no non-test production imports.

The active graph-agent test must continue to assert the current two-tool catalog,
not import the deleted five-tool registry.

### C. Dead Plan toolbar component

Remove `apps/live-control-ui/src/planSurface/components/PlanToolBar.tsx`.
The reference scan found no imports. The active shell uses its current toolbar
composition directly.

## Deferred candidates

These are not approved for deletion in this pass:

| Candidate | Current action | Gate before removal |
|---|---|---|
| `src/live_play/live_query_context.py` and `manifest_context_query.py` | Retain as Live/eval compatibility adapter | S1 latest-recap acceptance and migration of remaining Live consumers |
| `integrations/hermes/plugins/dungeonbuddy/` | Retain for the Live compatibility path and negative graph-agent tests | Remove only after all Live/legacy plugin consumers are migrated |
| `src/agent/planner.py` `generate_statblock` and planner prompts | Quarantine as legacy/eval-only | S2 statblock `CreativeOperationSession` and adapter proof |
| `hermes_graph_query.py` no-session classification and legacy citation projection | Retain as defensive compatibility behavior | Prove every host result hydrates a retrieval session; update contract tests first |
| `hermes_graph_plugin.py` `HERMES_GRAPH_READ_TOOL_NAMES` alias | Naming cleanup only | Rename in a focused compatibility-safe change |
| `Graph Review` and v2 statblock UI/modules | Retain as secondary inspection/domain adapters | Governed draft review and promotion path |

## Deletion gates

After the approved removal set:

```text
rg 'run_hermes_conversation|_process_hermes_context_query|_process_hermes_cli_query|HERMES_CLI_|hermes_cli_oneshot' \
  apps/live_control_server src tests apps/live-control-ui/src
```

must return no active product/test references. Archived documentation is allowed to
retain historical names.

The S0 verification command is:

```text
uv run pytest -q \
  tests/test_graph_kernel_world_retrieval.py \
  tests/test_graph_retrieval_interaction.py \
  tests/test_live_query_hermes_graph.py \
  tests/test_hermes_graph_agent.py \
  tests/test_live_control_server.py
```

The focused two-tool and statblock adapter checks are:

```text
uv run pytest -q tests/test_hermes_graph_agent.py tests/test_live_statblock_workbench_endpoint.py tests/statblocks
```

No deletion in this map authorizes changes to the retained graph retrieval,
source-anchor integrity, revision pinning, claim acceptance, or bounded continuity
contracts.
