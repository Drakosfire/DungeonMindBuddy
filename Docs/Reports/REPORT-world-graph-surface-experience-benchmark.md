# World Graph surface experience benchmark (OPT-BENCH02)

**Measured at:** 2026-08-07T14:52:16.009Z  
**Base URL:** http://127.0.0.1:5173  
**Code SHA:** 63a216e2b1b5bb24230142ea8aa02439b0c740e6 (clean)  
**Contract:** PASS  
**Latency scope:** browser experience (navigation + `dmb:wg-surface:*` / `dmb:wg-projection:*` marks). Service-level warm-path numbers remain OPT-BENCH01.

## Navigation timing

| Surface | DOMContentLoaded (ms) | loadEventEnd (ms) |
| --- | ---: | ---: |
| Plan (cold) | 231 | 234 |
| Build (after switch) | 415 | 418 |

## Stage summary

| Stage | count | avg durationMs | last t |
| --- | ---: | ---: | ---: |
| projection_fetch | 2 | — | 351.1 |
| client_cache_miss | 2 | — | 559.6 |
| client_cache_coalesced | 1 | — | 351.2 |
| projection_ready | 1 | 60 | 411.3 |
| first_chip_paint | 1 | — | 454.7 |
| detail_glance_open | 1 | — | 617.7 |
| detail_full_open | 3 | — | 1110.2 |
| surface_switch_start | 1 | — | 750.0 |
| build_projection_fetch | 1 | — | 559.4 |
| build_projection_ready | 1 | 28 | 587.3 |
| surface_switch_end | 1 | 588 | 587.4 |
| build_detail_open | 1 | — | 1110.3 |

## Stage detail (ring buffer order)

| Stage | durationMs | t (perf.now) | epochMs | meta |
| --- | ---: | ---: | ---: | --- |
| projection_fetch | — | 344.1 | 1786114334468.4 | `{"surface":"plan","generation":1}` |
| client_cache_miss | — | 344.7 | 1786114334469.0 | `{"endpoint":"projection"}` |
| projection_fetch | — | 351.1 | 1786114334475.3 | `{"surface":"plan","generation":2}` |
| client_cache_coalesced | — | 351.2 | 1786114334475.5 | `{"endpoint":"projection"}` |
| projection_ready | 60 | 411.3 | 1786114334535.6 | `{"surface":"plan","campaignId":"longmont-c2","scopeMode":"campaign","focusSessionId":null,"outcome":"ready","mark":"dmb:wg-surface:projection_ready"}` |
| first_chip_paint | — | 454.7 | 1786114334579.0 | `{"nodeId":"event:longmont-c2:session-22:mireward-road","surface":"chip"}` |
| detail_glance_open | — | 617.7 | 1786114334742.0 | `{"glanceOnly":true,"key":"graph-node","title":"Mireward Road"}` |
| detail_full_open | — | 669.3 | 1786114334793.6 | `{"via":"expandContent","key":"graph-node","title":"Mireward Road"}` |
| detail_full_open | — | 669.6 | 1786114334793.9 | `{"via":"expandContent","key":"graph-node","title":"Mireward Road"}` |
| surface_switch_start | — | 750.0 | 1786114334874.3 | `{"from":"plan","to":"build","href":"/build","navigation":"full_document_anchor","switchId":"759ab3ab-bf1e-475a-a580-91ea1ec0164a","epochMs":1786114334874.3}` |
| build_projection_fetch | — | 559.4 | 1786114335434.1 | `{"surface":"build","campaignId":"longmont-c2","revisionKind":"head","revisionPin":null}` |
| client_cache_miss | — | 559.6 | 1786114335434.3 | `{"endpoint":"projection"}` |
| build_projection_ready | 28 | 587.3 | 1786114335462.0 | `{"surface":"build","outcome":"ready","campaignId":"longmont-c2","revisionKind":"head","revisionId":"rev:3413bf6f5044cf2680233f5e37c90dcf"}` |
| surface_switch_end | 588 | 587.4 | 1786114335462.1 | `{"surface":"build","outcome":"ready","revisionId":"rev:3413bf6f5044cf2680233f5e37c90dcf","switchId":"759ab3ab-bf1e-475a-a580-91ea1ec0164a","startEpochMs":1786114334874.3,"endEpochMs":1786114335462.0999,"clock":"wall_epoch","from":"plan","to":"build","href":"/build"}` |
| detail_full_open | — | 1110.2 | 1786114335984.9 | `{"glanceOnly":false,"key":"graph-node","title":"Commanding Shout"}` |
| build_detail_open | — | 1110.3 | 1786114335985.0 | `{"surface":"build","nodeId":"item-006","label":"Commanding Shout"}` |

## Projection / surface performance marks

- `dmb:wg-surface:build_projection_fetch`
- `dmb:wg-surface:client_cache_miss`
- `dmb:wg-surface:build_projection_ready`
- `dmb:wg-surface:surface_switch_end`
- `dmb:wg-surface:detail_full_open`
- `dmb:wg-surface:build_detail_open`

## Notes

- Used SurfaceLatencyBenchChipHost (Plan doc had no native graph chip).
- Plan checkpoint stages: projection_fetch,client_cache_miss,projection_fetch,client_cache_coalesced,projection_ready,first_chip_paint,detail_glance_open,detail_full_open,detail_full_open
- Build required campaign pick (longmont-c2) after surface switch.

## Cleanup candidates (measurement only — do not fix in OPT-BENCH02)

1. Plan↔Build uses full-document `<a href>` navigation (`navigation: full_document_anchor`); SPA routing would retain the client projection TTL cache across surfaces.
2. Cold path observed client_cache_miss with no client_cache_hit in this run — warm client TTL and/or OPT03 server completed-cache should be re-measured on a second pass without clear.
3. Chip glance → Expand path is instrumented; compare detail_glance_open vs detail_full_open wall deltas vs projection re-fetch marks to see if Expand re-resolves unnecessarily.
4. Surface switch wall time (588ms) dwarfs Build projection fetch (28ms) — admission UI / full reload dominate over projection build.

JSON artifact: `report/world-graph-surface-experience-bench.json`.
