# Checklist — C2 Live Control Surface v0 Query Pane

## Reanchor Block

- [x] Active slice: `L5_projection_command_architecture`
- [x] L4 shell remains green on `main`
- [ ] Next gate: projection contracts + command bus foundations
- [ ] Re-read `STUDY-c2-live-play-cursor-handoff-process.md` before UI expansion work

---

## Product Invariants

- [x] UI is not source of truth.
- [x] `surface_layout.json` is authoritative for runtime layout.
- [x] Chat + Record are required modules.
- [x] Session plan/timeline remains derived.
- [ ] Every write declares a write lane.
- [ ] Every command returns invalidation info.
- [ ] Human pane actions and agent tools share the same command layer.
- [ ] Retrieval stays off fast-live critical path.
- [ ] Projection refresh after writes is deterministic.
- [ ] Conflicts become reviewable state, not silent mutation.

---

## Phase L5A — Projection + Command Contracts

### Goal

Create the Python-first projection/command kernel shared by panes and agent tools.

### Files

```text
src/live_play/projections/
  targets.py
  capabilities.py
  commands.py
  invalidation.py
  write_results.py
```

### Checklist

- [ ] Define `ProjectionTarget`.
- [ ] Define `ProjectionCapability`.
- [ ] Define `ProjectionCommand`.
- [ ] Define `ProjectionWriteResult`.
- [ ] Define `ProjectionInvalidation`.
- [ ] Define write lanes.
- [ ] Add schema/tests for contracts.
- [ ] Add command validation tests.

### Verification

```bash
uv run pytest tests/test_live_projection_contracts.py -q
```

---

## Phase L5B — Plan View Projection

### Goal

Build derived session projection endpoint.

### Checklist

- [ ] Add `build_session_plan_projection(...)`.
- [ ] Add `plan_view.schema.json`.
- [ ] Add Session 22 sample projection payload.
- [ ] Add `GET /api/live/plan-view`.
- [ ] Validate `authoritative=false` invariant.
- [ ] Add typed refs and human labels.

---

## Phase L5C — Timeline Module

### Goal

Render read-only timeline projection.

### Checklist

- [ ] Add `timeline` module.
- [ ] Add typed API client.
- [ ] Render beat rows + refs.
- [ ] Render empty/error states.
- [ ] Add minimal timeline styling.
- [ ] Add tests.

---

## Phase L5D — Universal Inspector Pane

### Goal

Introduce shared pane shell and pane state.

### Checklist

- [ ] Add pane target state domain.
- [ ] Add InspectorPane shell.
- [ ] Timeline refs open pane.
- [ ] Record events open pane.
- [ ] Add responsive overlay behavior.
- [ ] Add tests.

---

## Phase L5E — Artifact + Capability Reads

### Goal

Allow panes and agents to inspect targets safely.

### Checklist

- [ ] Add allowlisted artifact read endpoint.
- [ ] Add capability discovery endpoint.
- [ ] Support `event` target.
- [ ] Support `roll_table` target.
- [ ] Add token/etag safety.
- [ ] Add allowlist rejection tests.

---

## Phase L5F — Read-only Pane Renderers

### Goal

Render artifact targets in inspector.

### Checklist

- [ ] Event artifact renderer.
- [ ] Roll-table artifact renderer.
- [ ] Loading/error states.
- [ ] Human-first labels.
- [ ] Provenance disclosure.
- [ ] Tests.

---

## Phase L5G — Command Bus

### Goal

Unify pane writes and agent writes.

### Checklist

- [ ] Add `POST /api/live/commands`.
- [ ] Add command routing.
- [ ] Add audit events.
- [ ] Add invalidation responses.
- [ ] Add first commands:
  - [ ] `append_observation`
  - [ ] `update_job_status`
  - [ ] `pin_scene_state`
- [ ] Add command result tests.

---

## Phase L5H — Pane Actions

### Goal

Allow UI actions to submit typed commands.

### Checklist

- [ ] Pane renders server-provided capabilities.
- [ ] Timeline submits commands.
- [ ] Queue submits commands.
- [ ] Open loops submit commands.
- [ ] UI refreshes invalidated projections.
- [ ] Tests for refresh orchestration.

---

## Phase L5I — Scoped Artifact Writes

### Goal

Enable first safe direct artifact patch flow.

### Checklist

- [ ] Roll-table patch endpoint.
- [ ] File-state/etag enforcement.
- [ ] Conflict response handling.
- [ ] Projection refresh after save.
- [ ] Read-after-write verification.
- [ ] Tests.

---

## Future Pane Expansion

Planned but not required for first L5 pass:

- NPC Focus
- Location Context
- Rules / Mechanics
- Sources / Evidence
- Post-session Work

These should reuse the same projection/capability/command architecture rather than introducing bespoke pane write systems.

---

## Success Criteria

- Projections and writes share one architecture.
- Agent tools and panes use the same commands.
- Writes are auditable and invalidate affected projections.
- The UI feels like a coherent GM cockpit instead of a repo dashboard.
