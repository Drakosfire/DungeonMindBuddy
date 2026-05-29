# Checklist — C2 Live Control Surface v0 Query Pane

## Reanchor Block

- [x] Active slice: `L5_projection_command_architecture`
- [x] L4 shell remains green on `main`
- [x] Last green artifact: PR #83 (`pr83-l5e-artifact-capability-reads`) — artifact/capability read contracts with target validation
- [x] Next gate: L5G command bus
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

- [x] Define `ProjectionTarget`.
- [x] Define `ProjectionCapability`.
- [x] Define `ProjectionCommand`.
- [x] Define `ProjectionWriteResult`.
- [x] Define `ProjectionInvalidation`.
- [x] Define write lanes.
- [x] Add schema/tests for contracts.
- [x] Add command validation tests.

### Verification

```bash
uv run pytest tests/test_live_projection_contracts.py -q
```

### Evidence (PR #79, 2026-05-28)

- Branch: `pr79-l5a` → `main` ([PR #79](https://github.com/Drakosfire/DungeonMindBuddy/pull/79))
- Handoff: `Docs/Plans/HANDOFF-pr79-l5a-projection-command-contracts.md`
- `uv run pytest tests/test_live_projection_contracts.py -q` → 16 passed
- `uv run pytest tests/test_live_control_server.py tests/test_live_play_turn_loop.py -q` → 25 passed
- Scope held: contracts + tests only; no FastAPI routes, UI, command bus execution, or corpus writes

### L5A follow-ups (non-blocking; track in L5B–L5G)

1. Preserve nano-commit discipline on future L5 slices (this PR landed as one commit).
2. Tighten `ProjectionCapability`: reject `disabled_reason` when `enabled=True` (or document permissiveness explicitly).
3. Add command/lane compatibility matching before command execution (L5G command bus).
4. Add projection-key constants/registry before invalidation drives UI refresh.
5. Add JSON-compatibility checks for `payload`/`metadata` before FastAPI exposure.
6. Document `make_target(..., **metadata)` collision risk if helper gains named args.

---

## Phase L5B — Plan View Projection

### Goal

Build derived session projection endpoint.

### Checklist

- [x] Add `build_session_plan_projection(...)`.
- [x] Add `plan_view.schema.json`.
- [x] Add Session 22 sample projection payload.
- [x] Add `GET /api/live/plan-view`.
- [x] Validate `authoritative=false` invariant.
- [x] Add typed refs and human labels.

### Verification

```bash
uv run pytest tests/test_live_plan_view_projection.py -q
uv run pytest tests/test_live_control_server.py -q
```

### Evidence (PR #80, 2026-05-28)

- Branch: `pr80-l5b-plan-view` → `main`
- Handoff: `Docs/Plans/HANDOFF-pr80-l5b-plan-view-projection.md`
- Added schema: `evals/c2_live_prep/live/schemas/plan_view.schema.json`
- Added sample: `evals/c2_live_prep/live/session_22/plan_view.sample.json`
- Added builder: `src/live_play/projections/plan_view.py`
- Added endpoint: `GET /api/live/plan-view` in `apps/live_control_server/routes/live.py`
- Added tests: `tests/test_live_plan_view_projection.py` and OpenAPI coverage update in `tests/test_live_control_server.py`
- `uv run pytest tests/test_live_plan_view_projection.py -q` → 5 passed
- `uv run pytest tests/test_live_control_server.py -q` → 18 passed
- Scope held: read-only projection slice; no UI pane work, no command execution, no artifact writes, no retrieval integration

---

## Phase L5C — Timeline Module

### Goal

Render read-only timeline projection.

### Checklist

- [x] Add `timeline` module.
- [x] Add typed API client.
- [x] Render beat rows + refs.
- [x] Render empty/error states.
- [x] Add minimal timeline styling.
- [x] Add tests.

### Verification

```bash
cd apps/live-control-ui && npm test && npm run build
uv run pytest tests/test_live_play_schemas.py -q
uv run pytest tests/test_live_control_server.py -q
```

### Evidence (PR #81, 2026-05-28)

- Branch: `pr81-l5c-timeline-module` (in progress)
- Handoff: `Docs/Plans/HANDOFF-pr81-l5c-timeline-module.md`
- Added typed API contract + client helper: `apps/live-control-ui/src/api/types.ts`, `apps/live-control-ui/src/api/liveApi.ts`
- Wired `planView` load/path: `apps/live-control-ui/src/App.tsx`, `apps/live-control-ui/src/surface/SurfaceShell.tsx`, `apps/live-control-ui/src/surface/moduleRegistry.tsx`
- Added module + styling: `apps/live-control-ui/src/surface/modules/TimelineModule.tsx`, `apps/live-control-ui/src/styles.css`
- Added tests/fixtures: `apps/live-control-ui/src/surface/modules/TimelineModule.test.tsx`, `apps/live-control-ui/src/surface/SurfaceShell.test.tsx`, `apps/live-control-ui/src/surface/ModuleLayoutControls.test.tsx`, `apps/live-control-ui/src/test/fixtures.ts`
- Updated seed catalog/layout + schemas for timeline module and synced derived state:
  - `evals/c2_live_prep/live/session_22/live_packet.json`
  - `evals/c2_live_prep/live/session_22/surface_layout.json`
  - `evals/c2_live_prep/live/session_22/current_state.json`
  - `evals/c2_live_prep/live/schemas/live_packet.schema.json`
  - `evals/c2_live_prep/live/schemas/live_surface_layout.schema.json`
- `cd apps/live-control-ui && npm test && npm run build` → 5 files passed / 18 tests passed; build succeeded
- `uv run pytest tests/test_live_play_schemas.py -q` → 19 passed
- `uv run pytest tests/test_live_control_server.py -q` → 18 passed

---

## Phase L5D — Universal Inspector Pane

### Goal

Introduce shared pane shell and pane state.

### Checklist

- [x] Add pane target state domain.
- [x] Add InspectorPane shell.
- [x] Timeline refs open pane.
- [x] Add open-empty and selected-target placeholder states.
- [x] Keep selection metadata-only (no artifact reads/actions).
- [x] Add tests.

### Verification

```bash
cd apps/live-control-ui && npm test && npm run build
```

### Evidence (PR #82, 2026-05-28)

- Branch: `pr82-l5d-inspector-pane-shell` (in progress)
- Handoff: `Docs/Plans/HANDOFF-pr82-l5d-inspector-pane-shell.md`
- Added target model helpers: `apps/live-control-ui/src/surface/targetTypes.ts`
- Added selectable/inert chip helper: `apps/live-control-ui/src/surface/TargetChip.tsx`
- Added shared pane shell + state type: `apps/live-control-ui/src/surface/InspectorPane.tsx`
- Wired app-level inspector state + chrome: `apps/live-control-ui/src/App.tsx`
- Wired selection callback through module seam:
  - `apps/live-control-ui/src/surface/SurfaceShell.tsx`
  - `apps/live-control-ui/src/surface/moduleRegistry.tsx`
  - `apps/live-control-ui/src/surface/modules/TimelineModule.tsx`
- Added tests:
  - `apps/live-control-ui/src/surface/InspectorPane.test.tsx`
  - `apps/live-control-ui/src/surface/TargetChip.test.tsx`
  - updated `apps/live-control-ui/src/surface/modules/TimelineModule.test.tsx`
  - updated `apps/live-control-ui/src/surface/SurfaceShell.test.tsx`
  - added `apps/live-control-ui/src/App.test.tsx`
- Updated styles for inspector pane/chips/app chrome: `apps/live-control-ui/src/styles.css`
- `cd apps/live-control-ui && npm test && npm run build` → 8 files passed / 26 tests passed; build succeeded

---

## Phase L5E — Artifact + Capability Reads

### Goal

Allow panes and agents to inspect targets safely.

### Checklist

- [x] Add allowlisted artifact read endpoint.
- [x] Add capability discovery endpoint.
- [x] Support `event` target.
- [x] Support `roll_table` target.
- [x] Add token/etag safety.
- [x] Add allowlist rejection tests.

### Verification

```bash
uv run pytest tests/test_live_artifact_reads.py -q
uv run pytest tests/test_live_control_server.py -q
uv run pytest tests/test_live_projection_contracts.py -q
```

### Evidence (PR #83, 2026-05-29)

- Branch: `pr83-l5e-artifact-capability-reads`
- Handoff: `Docs/Plans/HANDOFF-pr83-l5e-artifact-capability-reads.md`
- Added artifact read contracts + resolvers:
  - `src/live_play/projections/artifacts.py`
  - `apps/live_control_server/routes/live.py` (`GET /api/live/artifact`)
- Added capability discovery contracts + registry:
  - `src/live_play/projections/capability_registry.py`
  - `apps/live_control_server/routes/live.py` (`GET /api/live/capabilities`)
- Exported projection helpers in `src/live_play/projections/__init__.py`
- Added focused endpoint contract tests: `tests/test_live_artifact_reads.py`
- Updated OpenAPI required paths coverage in `tests/test_live_control_server.py`
- `uv run pytest tests/test_live_artifact_reads.py -q` → 12 passed
- `uv run pytest tests/test_live_control_server.py -q` → 18 passed
- `uv run pytest tests/test_live_projection_contracts.py -q` → 17 passed

---

## Phase L5F — Read-only Pane Renderers

### Goal

Render artifact targets in inspector.

### Checklist

- [x] Event artifact renderer.
- [x] Roll-table artifact renderer.
- [x] Loading/error states.
- [x] Human-first labels.
- [x] Provenance disclosure.
- [x] Tests.

### Verification

```bash
cd apps/live-control-ui && npm test
cd apps/live-control-ui && npm run build
```

### Evidence (PR #84, 2026-05-29)

- Branch: `pr84-l5f-read-only-pane-renderers`
- Handoff: `Docs/Plans/HANDOFF-pr84-l5f-read-only-pane-renderers.md`
- Added typed artifact/capability contracts:
  - `apps/live-control-ui/src/api/types.ts`
- Added read-only client helpers:
  - `apps/live-control-ui/src/api/liveApi.ts` (`getArtifact`, `getCapabilities`)
- Added read-only renderer components:
  - `apps/live-control-ui/src/surface/ArtifactRenderers.tsx`
  - `apps/live-control-ui/src/surface/CapabilityList.tsx`
- Wired Inspector pane read states/fetch behavior:
  - `apps/live-control-ui/src/surface/InspectorPane.tsx`
- Added/updated tests:
  - `apps/live-control-ui/src/api/liveApi.test.ts`
  - `apps/live-control-ui/src/surface/InspectorPane.test.tsx`
  - `apps/live-control-ui/src/surface/ArtifactRenderers.test.tsx`
  - `apps/live-control-ui/src/surface/CapabilityList.test.tsx`
  - `apps/live-control-ui/src/test/fixtures.ts`
- Updated styling for read-only inspector renderers/capability rows:
  - `apps/live-control-ui/src/styles.css`
- `cd apps/live-control-ui && npm test` → 11 files passed / 37 tests passed
- `cd apps/live-control-ui && npm run build` → build succeeded

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
