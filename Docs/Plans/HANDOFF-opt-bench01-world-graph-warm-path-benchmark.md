# HANDOFF — OPT-BENCH01 World Graph warm-path experience benchmark

**Created:** 2026-08-06  
**Status:** IMPLEMENTED  
**Branch:** `bench/world-graph-warm-path-experience`  
**Base SHA:** `9ac6d3aa4ab3b532571db1fa7c9eb08409cc75fd` (merged OPT03)  
**Flow:** BENCHMARK — measurement only, no production semantics changes

## Dispatch

Measure Plan-like head-following World Graph projection latency across four warm-path
scenarios on the Eldyrwild `longmont-c2` fixture bundle:

| Scenario | Label | What is warm |
| --- | --- | --- |
| A | Fully cold | Nothing — resident + projection cache cleared each iteration |
| B | Resident revision (OPT01) | Exact head admitted; cache cleared each iteration |
| C | OPT02 post-publish prewarm | Coordinator + publish; cache cleared each iteration |
| D | OPT03 surface warm | Recipe registered + publish prewarm; cache retained |

Deliverables: `scripts/bench_world_graph_warm_path.py`, contract tests, measured report.

## Out of scope

Production semantics, cache tuning, new routes, UI changes, prompt/eval edits.
