# Graph Memory Project Layout

This note records the current path boundary for graph-memory work. It is intentionally short: durable contracts should be easy to find without turning evaluation directories into architecture owners.

## Boundaries

- `src/graph_memory`: reusable graph-memory contracts, validators, reports, read-model helpers, and infrastructure.
- `tests/fixtures/graph_memory`: deterministic fixture data for reusable graph-memory contracts and tests.
- `evals/graph_memory_layer`: evaluation harnesses, benchmark fixtures, prompt dogfood, comparison reports, generated previews, and static review artifacts.
- `apps/live_control_server` / `apps/live-control-ui`: runtime/API/UI consumers of graph-memory contracts.

## Current relocation proof

The union supergraph read-model validator and report live under `src/graph_memory/union_supergraph`, while the checked-in minimal contract fixture lives under `tests/fixtures/graph_memory/union_supergraph`. This keeps the durable read-model contract outside evaluation-only space while leaving benchmark and dogfood machinery in `evals/graph_memory_layer`.

## Roadmap pointer

`Docs/Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md` is the current architecture roadmap for this layout. It treats this file as the short boundary note and records the longer target hierarchy, lifecycle, and PR sequence for graduating reusable contracts into `src/graph_memory`.
