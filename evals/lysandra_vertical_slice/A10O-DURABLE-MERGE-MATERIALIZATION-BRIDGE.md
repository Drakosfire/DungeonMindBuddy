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

1. Select duplicates with **Mireward Reach** as survivor (e.g. `organization_mireward_reach` ← `location_mireward_reach`).
2. Stage & commit with a live run selected.
3. After refresh: one **Mireward Reach** pill/node; duplicate location org pill filtered from normal node views.
4. Click survivor → merged identity note on selected-object card (A10n).

If commit succeeds but materialization fails, use **Advanced: backfill durable materialization** (collapsed under Stage & commit).

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

**PASS (corrected)** — Commit with a selected live run is the single operator path for identity merges. The original A10o standalone materialize panel PASS was **invalid for live UI refresh**: projection re-read a frozen manifest snapshot and ignored mutations to `preview_union_store_path`. That read-path bug is fixed; materialize-at-commit closes the Mireward Reach / Lysandra UX gap without a second ceremony.

**Deferred:** `object` / `link_existing` / `relationship` assertions still layer at read time via overlay only (not union store writes). Acceptable for this slice — they already render correctly.
