# World Graph surface experience benchmark (OPT-BENCH02)

**Measured at:** 2026-08-07T03:34:53.015Z  
**Base URL:** http://127.0.0.1:5174  
**Code SHA:** 9ac6d3aa4ab3b532571db1fa7c9eb08409cc75fd  
**Latency scope:** browser experience (navigation + `dmb:wg-surface:*` / `dmb:wg-projection:*` marks). Service-level warm-path numbers remain OPT-BENCH01.

## Navigation timing

| Surface | DOMContentLoaded (ms) | loadEventEnd (ms) |
| --- | ---: | ---: |
| Plan (cold) | 314 | 317 |
| Build (after switch) | 238 | 241 |

## Stage summary

| Stage | count | avg durationMs | last t |
| --- | ---: | ---: | ---: |
| projection_fetch | 2 | — | 442.2 |
| client_cache_miss | 2 | — | 367.9 |
| client_cache_coalesced | 1 | — | 442.3 |
| projection_ready | 1 | 65 | 507.9 |
| surface_switch_start | 1 | — | 8550.1 |
| build_projection_fetch | 1 | — | 367.8 |
| build_projection_ready | 1 | 27 | 394.7 |

## Stage detail (ring buffer order)

| Stage | durationMs | t (perf.now) | meta |
| --- | ---: | ---: | --- |
| projection_fetch | — | 435.9 | `{"surface":"plan","generation":1}` |
| client_cache_miss | — | 436.3 | `{"endpoint":"projection"}` |
| projection_fetch | — | 442.2 | `{"surface":"plan","generation":2}` |
| client_cache_coalesced | — | 442.3 | `{"endpoint":"projection"}` |
| projection_ready | 65 | 507.9 | `{"surface":"plan","campaignId":"longmont-c2","scopeMode":"campaign","focusSessionId":null,"outcome":"unavailable","mark":"dmb:wg-surface:projection_ready"}` |
| surface_switch_start | — | 8550.1 | `{"from":"plan","to":"build","href":"/build","navigation":"full_document_anchor"}` |
| build_projection_fetch | — | 367.8 | `{"surface":"build","campaignId":"longmont-c2","revisionKind":"head","revisionPin":null}` |
| client_cache_miss | — | 367.9 | `{"endpoint":"projection"}` |
| build_projection_ready | 27 | 394.7 | `{"surface":"build","outcome":"error","campaignId":"longmont-c2","revisionKind":"head"}` |

## Projection / surface performance marks

- `dmb:wg-surface:build_projection_fetch`
- `dmb:wg-surface:client_cache_miss`
- `dmb:wg-surface:build_projection_ready`

## Notes

- No graph-node-chip on Plan; glance/expand stages omitted for this session doc.
- Build required campaign pick (longmont-c2) after surface switch.

## Cleanup candidates (measurement only — do not fix in OPT-BENCH02)

1. Plan↔Build uses full-document `<a href>` navigation (`navigation: full_document_anchor`); SPA routing would retain the client projection TTL cache across surfaces.
2. Cold path observed client_cache_miss with no client_cache_hit in this run — warm client TTL and/or OPT03 server completed-cache should be re-measured on a second pass without clear.
3. No first_chip_paint — Plan document in this session may lack graph-native TipTap chips; seed a chip or use a session with refs before attributing chip-path latency.
4. Surface switch → build_projection_ready includes full reload + Build campaign/document admission; split admission UI cost from projection fetch in a follow-up mark if needed.

JSON artifact: `report/world-graph-surface-experience-bench.json`.
