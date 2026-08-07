# HANDOFF — OPT-BENCH02 World Graph surface experience latency

**Created:** 2026-08-06  
**Status:** ACTIVE — measurement only  
**Branch:** `bench/world-graph-surface-experience`  
**Base SHA:** `9ac6d3aa4ab3b532571db1fa7c9eb08409cc75fd` (`origin/main`, OPT03 merged)  
**Predecessor:** OPT-BENCH01 service-level warm-path bench (`bench/world-graph-warm-path-experience`)  
**Flow:** BENCHMARK — no production projection semantics changes

## Mission

Measure real Plan/Build World Graph **experience** latency: cold load → first chip / View → glance → full detail → surface switch. Attribute wall time to network/service vs client cache vs React commit vs host open. Document cleanup candidates; do **not** optimize inside this slice.

## Why

OPT-BENCH01 wraps `project_world_graph()` (service-level e2e only). Plan already has partial `dmb:wg-projection:*` marks; Build shares HTTP via `projectionRequestCache.ts` but has no stage marks. There is no Playwright surface bench today. Plan↔Build chrome uses `<a href>` (likely full reload).

## Deliverables

| Artifact | Path |
| --- | --- |
| Client mark helper | `apps/live-control-ui/src/worldGraph/surfaceLatencyMarks.ts` |
| Wiring | Plan resolver, chip token, AgentInteractionProvider, Build graph context, AppChrome, ProjectionHost, cache, `main.tsx` dogfood hooks |
| Playwright harness | `scripts/bench_world_graph_surface_experience.mjs` + `apps/live-control-ui/playwright.config.ts` |
| Report | `Docs/Reports/REPORT-world-graph-surface-experience-benchmark.md` |
| Unit tests | `surfaceLatencyMarks.test.ts` (+ targeted seam assertions) |

## Experience script

1. Cold `/plan` (client cache cleared) → projection ready → first graph chip paint  
2. Chip click → glance → Expand → full detail  
3. Navigate `/build` (measure switch) → projection ready → Find-existing View → detail  
4. Optional warm repeat with client TTL / server OPT03 retained

## Out of scope

Cache tuning, SPA navigation rewrite, projection semantics, new routes/schemas, OPT04 deltas, UI redesign beyond `data-testid` + dogfood hooks.

## Merge-ready invariant

One opt-in command (live stack up) produces a stage breakdown for Plan cold→chip→detail and Build after surface switch; the report lists ranked cleanup candidates with evidence.
