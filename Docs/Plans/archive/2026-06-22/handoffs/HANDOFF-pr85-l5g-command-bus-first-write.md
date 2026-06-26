---
document_id: dmb-handoff-pr85-l5g-command-bus-first-write
title: PR 85 Handoff — L5G Command Bus First Write
status: completed
version: 0.1
created_at: "2026-05-29T15:00:00Z"
completed_at: "2026-05-29T15:00:00Z"
related_documents:
  - path: Docs/Plans/DESIGN-c2-live-control-l5-pane-state-boundaries.md
    role: primary_design_anchor
  - path: Docs/Plans/PLAN-c2-live-control-surface-query-pane.md
    role: parent_plan
  - path: Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md
    role: execution_tracker
  - path: Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-pr84-l5f-read-only-pane-renderers.md
    role: prior_read_renderer_slice
  - path: src/live_play/projections/commands.py
    role: command_contract
  - path: src/live_play/projections/write_results.py
    role: write_result_contract
---

# PR 85 Handoff — L5G Command Bus First Write

## Mission

Add `POST /api/live/commands` command intake with one safe command (`append_observation`) for `event` and `roll_table` targets, lane-locked to `observed_play`, returning `ProjectionWriteResult` envelopes with invalidations.

## Scope Delivered

- Added command bus executor:
  - `src/live_play/projections/command_bus.py`
- Added thin route for command submission:
  - `apps/live_control_server/routes/live.py` (`POST /api/live/commands`)
- Kept schema contracts on existing models:
  - request: `ProjectionCommand`
  - response: `ProjectionWriteResult`
- Implemented semantic handling:
  - accepted path for `append_observation` + `observed_play` + known target
  - rejected path for unsupported command/target/lane/payload
  - noop path for duplicate `idempotency_key`
- Mutation boundary enforced:
  - append-only write to `event_log.jsonl`
  - no job queue writes
  - no layout/state/packet writes
  - no roll-table or corpus file writes
- Enabled only `append_observation` capability for supported targets:
  - `src/live_play/projections/capability_registry.py`
- Added tests:
  - `tests/test_live_command_bus.py`
  - updated `tests/test_live_artifact_reads.py`
  - updated `tests/test_live_control_server.py`

## Out of Scope (Preserved)

- No React command UI
- No capability buttons
- No `patch_artifact` execution
- No `queue_canon_patch` execution
- No retrieval refresh execution
- No artifact/prep/corpus write paths

## Verification

```bash
uv run pytest tests/test_live_command_bus.py -q
uv run pytest tests/test_live_artifact_reads.py -q
uv run pytest tests/test_live_control_server.py -q
uv run pytest tests/test_live_projection_contracts.py -q
uv run pytest tests/test_live_play_schemas.py -q
```
