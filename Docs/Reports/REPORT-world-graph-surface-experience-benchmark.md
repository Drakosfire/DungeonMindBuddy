# World Graph surface experience benchmark (OPT-BENCH02)

**Status:** INVALID — prior dogfood does not satisfy the experience contract  
**Superseded run:** 2026-08-07T03:34:53.015Z at misattributed SHA `9ac6d3aa…`  
**Why invalid:** Plan `projection_ready` outcome was `unavailable`, no chip/glance/full-detail path, Build `build_projection_ready` outcome was `error`, and `surface_switch_end` used Build-fetch duration after a full-document time-origin reset. The harness previously treated any non-empty stage ring as success.

Re-run after the contract + opt-in + wall-epoch fixes:

```bash
# Terminal A: L3 live control server
# Terminal B:
cd apps/live-control-ui && npm run dev
# Terminal C (repo root):
DMB_BENCH_SURFACE=1 node scripts/bench_world_graph_surface_experience.mjs
```

A merge-ready report must show **Contract: PASS** with successful Plan projection, first chip paint, glance + full detail, wall-epoch `surface_switch_end`, successful Build projection, and Build detail.

JSON artifact will be rewritten at `report/world-graph-surface-experience-bench.json` on the next successful or failed contract run.
