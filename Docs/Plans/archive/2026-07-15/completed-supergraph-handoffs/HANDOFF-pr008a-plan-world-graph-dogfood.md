# HANDOFF — PR008A Plan World Graph object-card dogfood migration

**Slice:** PR008A · **Branch:** `campaign-supergraph/pr008a-plan-world-graph-dogfood` · **Implementation base:** `7fc8e33b6e540afc3d1eed7b2fdee8a5b197c210`

## Mission

Make `/plan` object-card reference navigation read the current World Graph head
through `POST /api/live/world-graph/projection`. The Plan session must use one
loaded projection for reference chips, relationship traversal, Insert References,
and dogfood selection.

## Contract

Plan sends only:

```json
{
  "schema": "dmb_world_graph_projection_request_v1",
  "worldId": "eldyrwild",
  "campaignId": "longmont-c2",
  "focus": { "kind": "session", "sessionId": "session-<memory session>" },
  "admissibility": "gm"
}
```

It sends no revision pin, query text, preview source, ingest-run selector,
filesystem path, or latest-ingest selector. It adapts the World Graph node view
at the Plan card boundary; it must not fabricate a Union Supergraph response.

## Forward-only boundary

Do not add compatibility adapters selected by schema version, latest-ingest
fallback requests, preview-source selectors, or local-state migrations. If the
World Graph is unavailable or fails integrity checks, report that state honestly;
ordinary corpus fallback remains visibly marked and is not graph-backed success.

## Demolition and retention

Deleted:
- Plan reference resolver dependency on `useLatestGraphIngest`
- Plan latest-ingest graph-selection request fields
- Plan-only legacy boundary exemption

Retained temporarily:
- Generic graph-preview APIs and Graph Review consumers

Reason: Graph Review remains a named preview-workflow consumer.

Required deletion PR: the slice that replaces each remaining named consumer;
PR012 only owns genuine leftovers.

## Verification

```bash
cd apps/live-control-ui
npm test -- --run src/api/liveApi.test.ts src/planSurface/reference src/planSurface/dogfood src/planSurface/PlanSurfaceShell.test.tsx
npm run build
cd ../..
uv run pytest -q tests/test_graph_kernel_boundaries.py
rg -n "useLatestGraphIngest|use_latest_graph_ingest|previewSource|previewUnionStorePath|graphRunManifestPath|allowRecapOnly" \
  apps/live-control-ui/src/planSurface/reference \
  apps/live-control-ui/src/planSurface/dogfood \
  apps/live-control-ui/src/planSurface/components/PlanGraphRefSearch.tsx
```
