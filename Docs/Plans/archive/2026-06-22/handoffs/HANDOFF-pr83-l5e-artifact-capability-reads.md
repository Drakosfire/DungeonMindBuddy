---
document_id: dmb-handoff-pr83-l5e-artifact-capability-reads
title: PR 83 Handoff — L5E Artifact + Capability Reads
status: completed
version: 0.1
created_at: "2026-05-29T00:00:00Z"
completed_at: "2026-05-29T00:00:00Z"
related_documents:
  - path: Docs/Plans/DESIGN-c2-live-control-l5-pane-state-boundaries.md
    role: primary_design_anchor
  - path: Docs/Plans/PLAN-c2-live-control-surface-query-pane.md
    role: parent_plan
  - path: Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md
    role: execution_tracker
  - path: Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-pr82-l5d-inspector-pane-shell.md
    role: prior_ui_shell_slice
---

# PR 83 Handoff — L5E Artifact + Capability Reads

## Mission

Add read-only inspector backend contracts:

- `GET /api/live/artifact?target_type=...&target_id=...`
- `GET /api/live/capabilities?target_type=...&target_id=...`

with initial allowlisted support for target types:

- `event`
- `roll_table`

## Scope Delivered

- Added typed artifact read models and resolver in `src/live_play/projections/artifacts.py`.
- Added typed capability discovery model/registry in `src/live_play/projections/capability_registry.py`.
- Kept `apps/live_control_server/routes/live.py` thin and route-only.
- Added endpoint-level guardrail rejecting path query fields (`source_path`, `file_path`, `path`, `absolute_path`, `relative_path`).
- Added read-only state tokens for event and roll-table artifacts.
- Added coverage for success, rejection, immutability, and OpenAPI exposure.

## Hard Out of Scope (Preserved)

- No inspector UI rendering changes.
- No command execution bus.
- No write endpoints or patch endpoints.
- No retrieval integration.
- No browser-side file access.

## Verification

```bash
uv run pytest tests/test_live_artifact_reads.py -q
uv run pytest tests/test_live_control_server.py -q
uv run pytest tests/test_live_projection_contracts.py -q
uv run pytest tests/test_live_play_schemas.py -q
```
