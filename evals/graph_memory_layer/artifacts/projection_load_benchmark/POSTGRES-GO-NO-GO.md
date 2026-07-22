# PostgreSQL go / no-go — graph load benchmark

Generated: `2026-07-22T00:11:44.356678+00:00`

## Verdict: NO-GO for PostgreSQL spike

**Do not start a PostgreSQL compatibility spike.** Cold projection is slow
(~2.7s p95), but **storage is not the bottleneck** (~1.4% of cold time).
Almost all cost is in-memory projection construction (`build_nodes` +
`build_relationships`) and shipping ~1.3MB payloads. Warm process cache
returns projections in <2ms. Revisit Postgres only if a later benchmark
shows storage/contribution I/O ≥80% of p95 **and** cardinality ≥~2000 nodes.

## Cardinality

- revision: `rev:6d78d333b7b6a0df2d65437988a31757`
- nodes: `300`
- edges: `224`
- assertion_support: `600`
- graph.json bytes: `1093365`
- contribution files: `24`

## Latency

- cold projection p50/p95: `2717.909` / `2734.766` ms
- warm projection p50/p95: `0.735` / `1.886` ms
- recap p50: `3020.619` ms
- catalog p50: `357.207` ms
- search p50: `2885.453` ms (≈98.8% `load_projection`; rank+assemble <2%)

## Decision

- **recommended_path:** `optimize_file_backed_projection_path`
- **postgres_spike_justified:** `False`

Reasons:

- cold_projection_p95_ms=2734.8 (gate >500)
- storage_like_share=0.014 (load_revision+contribution_loads; gate >=0.80)
- build_projection_share=0.986
- node_count=300 (gate >=2000 for postgres)
- warm_projection_p50_ms=0.735
- recap_p50_ms=3020.619
- catalog_p50_ms=357.207

## Next optimizations (file-backed path)

1. Collapse search/object/neighborhood so they do not rebuild a full
   projection on every cold call (tracked in `Backlog.md`).
2. Keep `DMB_WORLD_GRAPH_PROJECTION_CACHE` + request-scoped contribution memoization.
3. Profile `build_nodes` / `build_relationships` CPU hotspots before any store rewrite.
4. Re-run: `uv run python scripts/benchmark_projection_load.py --trials 5`

## Gate (from plan)

Proceed to PostgreSQL design only if measured p95 projection is >500ms,
≥80% of that time is store load + contribution file fan-out, and projected
cardinality is heading past ~2000 nodes (or contribution fan-out dominates).
Otherwise keep optimizing the file-backed projection path.

Full JSON: `evals/graph_memory_layer/artifacts/projection_load_benchmark/projection_load_benchmark--20260722T001144Z.json`
