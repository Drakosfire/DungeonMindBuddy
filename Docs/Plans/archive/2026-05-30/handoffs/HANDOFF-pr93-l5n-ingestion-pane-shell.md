# HANDOFF — PR93 L5N Ingestion Pane Shell / Operator Surface

> **COMPLETED** — merged PR #93 (`c4299770`) on 2026-05-30. Optional `ingestion` module; `POST /api/live/recap-ingest` wraps PR92 `run_pipeline`; editable recap/source session decoupled from live workspace session. Verification: backend recap-ingest tests, PR92 pipeline regression, UI tests + build.

**Status:** ARCHIVED — merged on `main`; do not dispatch.

## Mission

Add an operator-facing ingestion pane to live control that wraps the PR92 recap ingest orchestrator through a narrow server API, without reimplementing ingest logic in React.

## Scope

- `apps/live_control_server/routes/recap_ingest.py`
- `apps/live_control_server/main.py`
- `tests/test_live_recap_ingest_api.py`
- `apps/live-control-ui/src/api/recapIngestApi.ts`
- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/modules/IngestionModule.tsx`
- `apps/live-control-ui/src/modules/IngestionStatusPanel.tsx`
- `apps/live-control-ui/src/modules/AuthorityTransitionPanel.tsx`
- `apps/live-control-ui/src/modules/SpellingAuditPanel.tsx`
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx`
- `apps/live-control-ui/src/modules/IngestionStatusPanel.test.tsx`
- `apps/live-control-ui/src/surface/moduleRegistry.tsx`
- `evals/c2_live_prep/live/schemas/live_packet.schema.json`
- `evals/c2_live_prep/live/schemas/live_surface_layout.schema.json`
- `evals/c2_live_prep/live/session_22/live_packet.json`
- `evals/c2_live_prep/live/session_22/surface_layout.json`
- `src/live_play/session_bootstrap.py`
- `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md`

## Core Boundaries

- Backend route calls `run_pipeline(...)` directly; no CLI shell-outs.
- Browser cannot send server file paths (`raw_path`, `output_dir`, corpus paths, derivative file paths).
- Allowed write surfaces remain PR92 writer surfaces only.
- UI treats spelling audit as review-only and authority transitions as explicit.
- `breadcrumb_required` is shown as a boundary, not hidden as a generic failure.

## Verification

```bash
uv run pytest tests/test_live_recap_ingest_api.py -q
uv run pytest tests/test_live_recap_ingest_pipeline.py -q
uv run pytest tests/test_live_session_bootstrap.py -q
uv run pytest tests/test_live_play_schemas.py -q
cd apps/live-control-ui && npm test
cd apps/live-control-ui && npm run build
```

## Out of Scope

- LLM recap rewriting
- Breadcrumb generation/blessing
- Activated planning corpus manifest / retrieval-admission wiring
- Embedding rebuilds
- Command-bus/event-log/live-packet mutation paths beyond PR92 ingest outputs
- Route-equivalence writes or corpus hub/timeline writes
