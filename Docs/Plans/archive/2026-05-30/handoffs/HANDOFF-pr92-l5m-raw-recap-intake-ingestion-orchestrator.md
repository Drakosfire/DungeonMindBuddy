# PR 92 Handoff — L5M Raw Recap Intake + Ingestion Orchestrator

> **COMPLETED** — merged PR #92 (`4faf76ca`) on 2026-05-30. CLI/backend `recap_ingest_pipeline` orchestrator: stage, preview, apply, normalize, `breadcrumb_required`, session-memory materialization. Runbook authority boundaries preserved.

**Status:** ARCHIVED — merged on `main`; do not dispatch.

## Mission

Add a backend/CLI ingestion orchestrator that accepts raw recap text (file or stdin) and drives deterministic ingest stages:

- stage raw notes under campaign `_ingest_staging/`
- preview canonical recap assembly
- apply canonical recap with slug/title safety
- optional normalization
- optional session-memory materialization
- explicit `breadcrumb_required` boundary when breadcrumb artifact is missing

## Scope

- `src/live_play/recap_ingest_pipeline.py`
- `src/live_play/recap_ingest_status.py`
- `src/live_play/recap_stage_paths.py`
- `tests/test_live_recap_ingest_pipeline.py`
- `tests/fixtures/live_recap_ingest/session_22_raw_recap.md`
- `Docs/Plans/RUNBOOK-c2-first-dogfood-planning-round.md`
- `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md`

## Core Rule

This is orchestration only. Reuse existing deterministic recap assembly/materialization pieces and stop honestly at breadcrumb/session-memory boundaries.

## Out of Scope

- ingestion pane UI / browser upload
- FastAPI ingestion endpoint
- LLM recap rewriting or breadcrumb generation
- retrieval/admission/manifest integration
- embedding rebuild
- command-bus write expansion

## Verification

```bash
uv run pytest tests/test_live_recap_ingest_pipeline.py -q
uv run pytest tests/test_live_session_bootstrap.py -q
uv run pytest tests/test_live_recap_ingestion.py -q
uv run pytest tests/test_live_play_schemas.py -q
```
