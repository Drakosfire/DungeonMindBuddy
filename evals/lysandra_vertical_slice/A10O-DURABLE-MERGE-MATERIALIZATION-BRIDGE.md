# A10o durable merge materialization bridge — Session 23 Lysandra

**Date:** 2026-07-08 (updated after commit-time materialization fold)  
**Feature:** Identity merge commits update the preview union store; projection reads the live store

## Environment

- Backend: `PYTHONPATH=src:apps/live_control_server uv run uvicorn apps.live_control_server.main:app`
- Frontend: live-control-ui dev server against the API above
- Automated harness: `uv run python evals/lysandra_vertical_slice/a10m_durable_identity_dogfood.py`

## Operator path (primary — no separate materialize step)

1. Open Graph Review for Session 23 with a **live ingest run** selected (`preview_union_store_path` available).
2. Author Draft → stage a `merge_objects` proposal (Merge candidates or Existing object search).
3. **Stage & commit** tab → **Prepare staged memory** → **Commit authored graph memory**.
4. On success, confirm copy: **"Merged directly into the union graph …"** (when a live run is selected).
5. Graph review refreshes; survivor node appears with merged identity / collapsed duplicates.

**What commit does now**

- Writes the assertion to the authored overlay (audit trail).
- When `previewUnionStorePath` is set on the selected live run, immediately plans and applies **all actionable** committed merges into that preview union store (skips already-materialized assertions).
- Projection reload prefers the **live preview union store** over the frozen ingest manifest snapshot.

## Mireward Reach dogfood (Campaign 2)

**Status:** COMPLETE (2026-07-08) — verified against live preview union store + overlay reload.

| Step | Observed outcome |
|------|------------------|
| Merge `node:mireward-reach`, `loc_mireward_reach`, `organization_mireward_reach` → `location_mireward_reach` | Survivor in union store; active redirects for all three merged-away ids |
| Commit with live run selected | Overlay written + event log appended + union store materialized |
| Refresh projection | `location_mireward_reach` in `node_views` with `merged_away_ids` listing all three duplicates; duplicate pills absent from normal views |
| Relationship `located_in` (the wall → Mireward Reach) | Projects after overlay redirect resolution: `location_the_wall` adjacency → `location_mireward_reach` |
| Selected-object card | Survivor visible; merged identity note (A10n) available on click |

**Store path:** `out/graph_memory/runs/longmont-c2/session-23/20260629T183113Z/preview_union_supergraph.json`

## Lysandra dogfood (Campaign 2)

**Status:** COMPLETE (2026-07-08) — same session/run as Mireward.

| Step | Observed outcome |
|------|------------------|
| Merge `node:lysandra` → `character_captain_lysandra_ironveil` | Active redirect; survivor in projection with `merged_away_ids: ['node:lysandra']` |
| `link_existing` alias "Lysandra" | Resolves through durable redirect; alias propagation applies without unresolved-ref diagnostics |
| Refresh after commit | Single Lysandra survivor node; no phantom `node:lysandra` in `node_views` |

## Advanced backfill (edge cases)

When commit ran without a live run, or materialization failed non-fatally:

1. Author Draft → **Stage & commit** → expand **Advanced: backfill durable materialization**.
2. **Prepare identity materialization** → **Apply durable identity merge** (token-guarded A10o API path unchanged).

## API path (backfill / scripts)

Prepare/apply endpoints remain at `/api/live/graph-authoring/merge-reconciliation/prepare` and `/apply`. Commit-time materialization uses the same A10m/A10o primitives internally.

Reload projection (live store wins when both manifest and store path are given):

```bash
curl -s "http://127.0.0.1:8000/api/live/graph-preview/union-supergraph/projection?session_id=session-23&campaign_id=longmont-c2&preview_union_store_path=<path>&graph_run_manifest_path=<manifest>" \
  | jq '.node_views["organization_mireward_reach"] // .node_views["party:captain_lysandra_ironveil"] | {label, merged_away_ids, evidence: (.evidence_badges|length)}'
```

## Before / after

| State | Duplicate pill visible? | Survivor card |
|-------|----------------------|---------------|
| Before commit | Both survivor + duplicate may appear | Separate thin nodes |
| After commit + refresh (live run selected) | Duplicate filtered | Merged identity note + evidence |

## Test commands

```bash
PYTHONPATH=src:apps/live_control_server pytest \
  tests/test_graph_object_authoring_commit.py \
  tests/test_graph_merge_reconciliation_materialize_api.py \
  tests/test_live_union_supergraph_projection_adapter.py::test_adapter_prefers_preview_union_store_over_persisted_manifest_snapshot \
  -q

cd apps/live-control-ui && npm test -- \
  GraphObjectAuthoringPrepareCommitPanel \
  GraphMergeReconciliationMaterializationPanel
```

## Verdict

**PASS** — Mireward Reach and Lysandra dogfood complete (2026-07-08). Commit with a selected live run is the single operator path for identity merges: overlay + event log + union store materialization succeed together; event-log failure does **not** mutate the union store. Projection reload prefers the live preview union store over the frozen manifest snapshot.

**Product note:** PR 305 shifts identity merge durability from explicit prepare/apply (PR 304) to automatic commit-time materialization when `previewUnionStorePath` is present. Manual backfill remains under Advanced.
