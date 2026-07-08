# A10o durable merge materialization bridge — Session 23 Lysandra

**Date:** 2026-07-08  
**Branch:** `codex/a10o-durable-merge-materialization-bridge` (base: `main` after PR #303)  
**Feature:** Graph Review prepare/apply bridge for durable identity merge materialization

## Environment

- Backend: `PYTHONPATH=src:apps/live_control_server uv run uvicorn apps.live_control_server.main:app`
- Frontend: live-control-ui dev server against the API above
- Automated harness: `uv run python evals/lysandra_vertical_slice/a10m_durable_identity_dogfood.py`

## Setup (Lysandra committed merge overlay)

1. Ensure Campaign 2 authored overlay contains a committed `merge_objects` assertion for Lysandra (`node:lysandra` → `party:captain_lysandra_ironveil`). This may already exist from prior graph authoring dogfood under `corpus/.../Campaign 2/_graph_authoring/overlays/authored_graph_overlay.json`.
2. Select a live ingest run for Session 23 with `preview_union_store_path` populated (normal Graph Review ingest path).

## API path (no bespoke Python glue)

```bash
# Prepare (writes nothing)
curl -s -X POST http://127.0.0.1:8000/api/live/graph-authoring/merge-reconciliation/prepare \
  -H 'Content-Type: application/json' \
  -d '{
    "campaignId": "longmont-c2",
    "sessionId": "session-23",
    "previewUnionStorePath": "<preview_union_store_path from selected live run>"
  }' | jq '{prepared, summary, confirm_token: (.confirm_token|length), materialization_pass_id}'

# Apply (uses tokens from prepare response)
curl -s -X POST http://127.0.0.1:8000/api/live/graph-authoring/merge-reconciliation/apply \
  -H 'Content-Type: application/json' \
  -d '{
    "campaignId": "longmont-c2",
    "sessionId": "session-23",
    "previewUnionStorePath": "<same path>",
    "materializationPassId": "<from prepare>",
    "confirmToken": "<from prepare>",
    "overlayToken": "<from prepare>",
    "unionStoreToken": "<from prepare>"
  }' | jq '{applied, backup_path, applied_assertion_ids, summary}'
```

Then reload projection:

```bash
curl -s "http://127.0.0.1:8000/api/live/graph-preview/union-supergraph/projection?session_id=session-23&preview_union_store_path=<same path>" \
  | jq '.node_views["party:captain_lysandra_ironveil"] | {label, merged_away_ids, evidence: (.evidence_badges|length), adjacency: [.adjacency[].label]}'
```

## Browser path (Graph Review)

1. Open Graph Review for Session 23 with a live run selected.
2. Author Draft → **Stage & commit**.
3. Commit any pending authored merge if not already committed (existing overlay prepare/commit panel).
4. In **Durable identity materialization** panel:
   - **Prepare identity materialization**
   - Review counts (redirects, edge rewires)
   - **Apply durable identity merge**
5. Graph review auto-refreshes after apply (or click refresh if needed).
6. Click **Captain Lysandra Ironveil** survivor card.
7. Confirm A10n merged identity note, relationship chips, collapsed technical provenance.

## Before / after

| State | `node:lysandra` in projection | Survivor provenance on card |
|-------|------------------------------|-----------------------------|
| Before materialization (overlay-only merge) | May appear as separate node | No durable merged identity note |
| After materialization + refresh | Filtered from normal node views | A10n merged identity note + evidence count |

## Test commands (automated)

```bash
PYTHONPATH=src:apps/live_control_server pytest \
  tests/test_graph_merge_reconciliation_materialize_api.py \
  tests/test_graph_memory_merge_reconciliation_planner.py \
  tests/test_graph_memory_merge_reconciliation_apply.py \
  tests/test_graph_memory_union_projection_identity_redirects.py -q

cd apps/live-control-ui && npm test -- \
  GraphMergeReconciliationMaterializationPanel \
  GraphReviewAuthoringRail \
  GraphObjectAuthoringPrepareCommitPanel
```

## Verdict

**PASS** — explicit prepare/apply API + Graph Review Stage & commit panel closes the PR #303 UI gap. No bespoke `apply_union_supergraph_merge_plan_to_file` script required for the operator path when a committed merge overlay and preview union store exist on the selected live run.

**Setup note:** First-time Lysandra dogfood still requires a committed `merge_objects` assertion in authored overlay (A10i–A10l authoring path). That is expected product setup, not Python script glue.
