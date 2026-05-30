# Checklist — C2 Live Control Surface v0 Query Pane

## Reanchor Block

- [x] Active slice: `L5_projection_command_architecture`
- [x] L4 shell remains green on `main`
- [x] Last green artifact: PR #90 (`pr90-l5l-fresh-recap-ingestion-session-bootstrap`) — deterministic recap bootstrap CLI, planning_beats plan-view, dogfood runbook
- [x] Next gate: L5N ingestion pane shell / operator surface (PR93)
- [ ] Re-read `STUDY-c2-live-play-cursor-handoff-process.md` before UI expansion work

---

## Product Invariants

- [x] UI is not source of truth.
- [x] `surface_layout.json` is authoritative for runtime layout.
- [x] Chat + Record are required modules.
- [x] Session plan/timeline remains derived.
- [x] Every write declares a write lane.
- [x] Every command returns invalidation info.
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

- [x] Add `POST /api/live/commands`.
- [x] Add command routing.
- [x] Add audit events.
- [x] Add invalidation responses.
- [x] Add first commands:
  - [x] `append_observation`
  - [ ] `update_job_status` (deferred)
  - [ ] `pin_scene_state` (deferred)
- [x] Add command result tests.

### Verification

```bash
uv run pytest tests/test_live_command_bus.py -q
uv run pytest tests/test_live_artifact_reads.py -q
uv run pytest tests/test_live_control_server.py -q
uv run pytest tests/test_live_projection_contracts.py -q
uv run pytest tests/test_live_play_schemas.py -q
```

### Evidence (PR #85, 2026-05-29)

- Branch: `pr85-l5g-command-bus-first-write`
- Handoff: `Docs/Plans/HANDOFF-pr85-l5g-command-bus-first-write.md`
- Added command bus executor with first safe write command:
  - `src/live_play/projections/command_bus.py`
- Added `POST /api/live/commands` thin route:
  - `apps/live_control_server/routes/live.py`
- Enabled only `append_observation` capabilities for event/roll_table:
  - `src/live_play/projections/capability_registry.py`
- Exported command bus entrypoint:
  - `src/live_play/projections/__init__.py`
- Added focused command-bus tests:
  - `tests/test_live_command_bus.py`
- Updated capability behavior assertions:
  - `tests/test_live_artifact_reads.py`
- Updated OpenAPI required paths:
  - `tests/test_live_control_server.py`
- `uv run pytest tests/test_live_command_bus.py -q` → 13 passed
- `uv run pytest tests/test_live_artifact_reads.py -q` → 15 passed
- `uv run pytest tests/test_live_control_server.py -q` → 18 passed
- `uv run pytest tests/test_live_projection_contracts.py -q` → 17 passed
- `uv run pytest tests/test_live_play_schemas.py -q` → 19 passed

---

## Phase L5H — Pane Actions

### Goal

Allow UI actions to submit typed commands.

### Checklist

- [x] Pane renders server-provided capabilities with action gating.
- [x] Enabled `append_observation` renders controlled form affordance.
- [x] Disabled capabilities remain informational/non-clickable.
- [x] `patch_artifact` and `queue_canon_patch` remain non-actionable.
- [x] Submission posts typed `ProjectionCommand` to `POST /api/live/commands`.
- [x] Write result statuses render accepted/rejected/noop/error states.
- [x] Accepted/noop path refreshes selected target reads.
- [x] Accepted/noop path triggers App-level `refreshAll()` callback.
- [x] Tests cover command shape, action gating, and refresh orchestration.

### Verification

```bash
cd apps/live-control-ui && npm test
cd apps/live-control-ui && npm run build
```

### Evidence (PR #86, 2026-05-29)

- Branch: `pr86-l5h-pane-action-ui-append-observation`
- Handoff: `Docs/Plans/HANDOFF-pr86-l5h-pane-action-ui-append-observation.md`
- Added typed command/write-result contract coverage in UI:
  - `apps/live-control-ui/src/api/types.ts`
- Added command client helper:
  - `apps/live-control-ui/src/api/liveApi.ts` (`postCommand`)
- Added first scoped action component:
  - `apps/live-control-ui/src/surface/AppendObservationAction.tsx`
- Updated capability/action gating and inspector wiring:
  - `apps/live-control-ui/src/surface/CapabilityList.tsx`
  - `apps/live-control-ui/src/surface/InspectorPane.tsx`
  - `apps/live-control-ui/src/App.tsx`
- Added/updated tests:
  - `apps/live-control-ui/src/surface/AppendObservationAction.test.tsx`
  - `apps/live-control-ui/src/surface/CapabilityList.test.tsx`
  - `apps/live-control-ui/src/surface/InspectorPane.test.tsx`
  - `apps/live-control-ui/src/api/liveApi.test.ts`
  - `apps/live-control-ui/src/App.commandAccepted.test.tsx`
- Added fixture builders and styling support:
  - `apps/live-control-ui/src/test/fixtures.ts`
  - `apps/live-control-ui/src/styles.css`
- `cd apps/live-control-ui && npm test` → 13 files passed / 49 tests passed
- `cd apps/live-control-ui && npm run build` → build succeeded

---

## Phase L5I — Scoped Artifact Writes

### Goal

Enable first safe direct artifact patch flow.

### Checklist

- [x] Implement `patch_artifact` in existing command bus path (`POST /api/live/commands`).
- [x] Restrict to `target_type=roll_table` and `lane=prep_note`.
- [x] Resolve source path only from `live_packet.known_roll_tables`.
- [x] Reject client payload path fields and unknown payload fields.
- [x] Require `expected_file_state_token`, `old_text`, `new_text`.
- [x] Enforce stale-token conflict (`status=conflict`) with no write.
- [x] Enforce exactly-once `old_text` replacement semantics.
- [x] Validate patched markdown using roll-table parser before write.
- [x] Support `dry_run` preview (`status=noop`) with metadata and no writes.
- [x] Write accepted patch via temp-file + replace.
- [x] Append one patch audit `state_note` event on accepted patch.
- [x] Add additive `metadata` to `ProjectionWriteResult` for patch details.
- [x] Enable `patch_artifact` capability for roll_table only.
- [x] Keep non-roll-table patching disabled/inert.
- [x] Add tests for success, dry-run, stale token, rejection, idempotency, path safety, and mutation boundaries.

### Verification

```bash
uv run pytest tests/test_live_artifact_patching.py -q
uv run pytest tests/test_live_command_bus.py -q
uv run pytest tests/test_live_artifact_reads.py -q
uv run pytest tests/test_live_control_server.py -q
uv run pytest tests/test_live_projection_contracts.py -q
```

### Evidence (PR #87, 2026-05-29)

- Branch: `pr87-l5i-scoped-roll-table-patch-command`
- Handoff: `Docs/Plans/HANDOFF-pr87-l5i-scoped-roll-table-patch-command.md`
- Added scoped roll-table patch command engine:
  - `src/live_play/projections/artifact_patching.py`
- Updated command bus dispatch to support `patch_artifact` while preserving `append_observation`:
  - `src/live_play/projections/command_bus.py`
  - `apps/live_control_server/routes/live.py`
- Added parser reuse helper and token helper reuse:
  - `src/live_play/roll_table_registry.py`
  - `src/live_play/projections/artifacts.py`
- Added additive write-result metadata contract:
  - `src/live_play/projections/write_results.py`
- Enabled roll-table `patch_artifact` capability metadata:
  - `src/live_play/projections/capability_registry.py`
- Added focused artifact patching tests:
  - `tests/test_live_artifact_patching.py`
- Updated related command/capability expectations:
  - `tests/test_live_command_bus.py`
  - `tests/test_live_artifact_reads.py`
  - `tests/test_live_control_server.py`
- `uv run pytest tests/test_live_artifact_patching.py -q` → 15 passed
- `uv run pytest tests/test_live_command_bus.py -q` → 13 passed
- `uv run pytest tests/test_live_artifact_reads.py -q` → 15 passed
- `uv run pytest tests/test_live_control_server.py -q` → 18 passed
- `uv run pytest tests/test_live_projection_contracts.py -q` → 17 passed

---

## Phase L5J — Roll-table Patch UI Preview

### Goal

Expose backend-safe roll-table patch semantics through preview-first inspector UI.

### Checklist

- [x] UI `ProjectionWriteResult` contract includes additive `metadata`.
- [x] Inspector passes current artifact into capability actions.
- [x] `patch_artifact` action gated to enabled `roll_table` + `prep_note` capability only.
- [x] Added preview-first `PatchArtifactAction` state flow:
  - [x] dry-run preview submission (`dry_run: true`)
  - [x] confirm gated on successful server preview
  - [x] confirm submission (`dry_run: false`) uses previewed values only
  - [x] confirm idempotency key reused on retry for same preview
  - [x] new preview after edit generates new confirm idempotency key
- [x] Preview metadata (including diff/tokens when present) rendered defensively.
- [x] Accepted/conflict/rejected/noop/error outcomes rendered honestly.
- [x] Accepted confirm reuses existing selected-target + App refresh seam.
- [x] Pane remains open after accepted confirm.
- [x] `append_observation` remains supported.
- [x] `queue_canon_patch` and unsupported enabled capabilities remain inert.
- [x] No generic capability runner introduced.
- [x] No markdown editor introduced.

### Verification

```bash
cd apps/live-control-ui && npm test
cd apps/live-control-ui && npm run build
```

### Evidence (PR #88, 2026-05-29)

- Branch: `pr88-l5j-roll-table-patch-ui-preview`
- Handoff: `Docs/Plans/HANDOFF-pr88-l5j-roll-table-patch-ui-preview.md`
- Added roll-table preview-first patch action component:
  - `apps/live-control-ui/src/surface/PatchArtifactAction.tsx`
- Updated capability/action gating + artifact-aware action seam:
  - `apps/live-control-ui/src/surface/CapabilityList.tsx`
  - `apps/live-control-ui/src/surface/InspectorPane.tsx`
- Updated UI command/result contracts + fixtures:
  - `apps/live-control-ui/src/api/types.ts`
  - `apps/live-control-ui/src/test/fixtures.ts`
  - `apps/live-control-ui/src/api/liveApi.test.ts`
- Added/updated focused tests:
  - `apps/live-control-ui/src/surface/PatchArtifactAction.test.tsx`
  - `apps/live-control-ui/src/surface/CapabilityList.test.tsx`
  - `apps/live-control-ui/src/surface/InspectorPane.test.tsx`
  - non-regression: `apps/live-control-ui/src/surface/AppendObservationAction.test.tsx`
- Styling updates:
  - `apps/live-control-ui/src/styles.css`
- `cd apps/live-control-ui && npm test` → 14 files passed / 64 tests passed
- `cd apps/live-control-ui && npm run build` → build succeeded

---

## Phase L5K — Patch UX Hardening / Read-after-write Evidence

### Goal

Harden roll-table patch UX so accepted writes remain trustworthy even when post-write refresh fails.

### Checklist

- [x] Added structured refresh-result contract from Inspector accepted-command flow.
- [x] Added read-only `WriteEvidencePanel` for write evidence visibility.
- [x] Distinguish `accepted` write from `accepted but refresh failed`.
- [x] Verify refreshed artifact token against write-result after-token when available.
- [x] Surface token mismatch warning without claiming write failure.
- [x] Keep audit/write evidence visible across refresh failure.
- [x] Clarified stale-token conflict recovery copy.
- [x] Made patch cancel/reset semantics explicit (clear draft + preview, keep durable evidence).
- [x] Added explicit "Dismiss result" action for evidence panel lifecycle.
- [x] Preserved preview-first confirm gating and idempotency behavior from L5J.
- [x] Preserved roll-table-only patch scope and inert unsupported capabilities.
- [x] Preserved `append_observation` refresh path behavior.

### Verification

```bash
cd apps/live-control-ui && npm test
cd apps/live-control-ui && npm run build
```

### Evidence (PR #89, 2026-05-30)

- Branch: `pr89-l5k-patch-ux-hardening-read-after-write-evidence`
- Handoff: `Docs/Plans/HANDOFF-pr89-l5k-patch-ux-hardening-read-after-write-evidence.md`
- Added write-evidence component:
  - `apps/live-control-ui/src/surface/WriteEvidencePanel.tsx`
  - `apps/live-control-ui/src/surface/WriteEvidencePanel.test.tsx`
- Hardened patch action lifecycle + refresh-state handling:
  - `apps/live-control-ui/src/surface/PatchArtifactAction.tsx`
  - `apps/live-control-ui/src/surface/PatchArtifactAction.test.tsx`
- Added structured refresh-result contract wiring:
  - `apps/live-control-ui/src/api/types.ts`
  - `apps/live-control-ui/src/surface/CapabilityList.tsx`
  - `apps/live-control-ui/src/surface/InspectorPane.tsx`
  - `apps/live-control-ui/src/surface/InspectorPane.test.tsx`
  - `apps/live-control-ui/src/surface/AppendObservationAction.tsx`
- Styling updates:
  - `apps/live-control-ui/src/styles.css`
- `cd apps/live-control-ui && npm test` → tests passed
- `cd apps/live-control-ui && npm run build` → build succeeded

---

## Phase L5L — Fresh Recap Ingestion / Session Bootstrap

### Goal

Bootstrap a live session workspace from a fresh recap file for first dogfooding planning.

### Checklist

- [x] Added `session_paths`, `recap_ingestion`, `session_bootstrap` modules.
- [x] CLI: `uv run python -m src.live_play.session_bootstrap`.
- [x] Writes `recap.md`, `live_packet.json`, `event_log.jsonl`, `job_queue.jsonl`, `current_state.json`, `surface_layout.json`.
- [x] Optional `planning_beats` on live packet; plan-view uses beats when present.
- [x] Deterministic recap heuristics (headings, bullets, open-loop phrases).
- [x] No invented roll tables; empty `known_roll_tables` / `roll_stack`.
- [x] Overwrite guard + `--force`; output dir under `evals/c2_live_prep/live/`.
- [x] `--write-current-live` / `--activate` copies workspace to default live dir.
- [x] Tests: bootstrap, ingestion, plan-view, server load.
- [x] Runbook: `Docs/Plans/RUNBOOK-c2-first-dogfood-planning-round.md`.

### Verification

```bash
uv run pytest tests/test_live_session_bootstrap.py tests/test_live_recap_ingestion.py -q
uv run pytest tests/test_live_plan_view_projection.py tests/test_live_control_server.py tests/test_live_play_schemas.py -q
uv run pytest tests/test_live_command_bus.py tests/test_live_artifact_reads.py tests/test_live_artifact_patching.py -q
```

### Evidence (PR #90, 2026-05-29)

- Handoff: `Docs/Plans/HANDOFF-pr90-l5l-fresh-recap-ingestion-session-bootstrap.md`
- Fixture: `tests/fixtures/live_bootstrap/session_22_fresh_recap.md`

---

## Phase L5M — Raw Recap Intake + Ingestion Orchestrator (PR92)

### Goal

Add a deterministic, CLI-first orchestration path to ingest raw recap notes into canonical recap + derivatives while preserving explicit safety boundaries.

### Checklist

- [x] Added `src/live_play/recap_ingest_pipeline.py` CLI (`python -m src.live_play.recap_ingest_pipeline`).
- [x] Added deterministic campaign/session path derivation helper (`src/live_play/recap_stage_paths.py`).
- [x] Added machine-readable status schema envelope (`dmb_raw_recap_ingest_status_v1`) via `src/live_play/recap_ingest_status.py`.
- [x] Supports `--raw-path` and `--raw-stdin` intake.
- [x] Safe defaults: no-op flags imply `--stage --preview`.
- [x] Stage path fixed to campaign `_ingest_staging/session_<N>_raw_notes.md`.
- [x] Preview uses `src.agent.recap_ingest_helpers.assemble_recap` and reports ingest counts.
- [x] Apply requires non-generic slug/title and refuses silent overwrite without `--force-recap`.
- [x] Optional normalize step writes `_normalized/Session NN - <slug>.md`.
- [x] Session-memory step stops at `breadcrumb_required` when breadcrumb artifact is absent.
- [x] Session-memory materialization/check path uses existing deterministic materializer.
- [x] Review-only spelling variant audit surfaced in status warnings.
- [x] Added realistic fixture and orchestration tests (`tests/test_live_recap_ingest_pipeline.py`).
- [x] Runbook updated with raw recap ingestion path.
- [x] No ingestion pane, no FastAPI route, no LLM rewrite, no retrieval/manifest integration.

### Verification

```bash
uv run pytest tests/test_live_recap_ingest_pipeline.py -q
uv run pytest tests/test_live_session_bootstrap.py -q
uv run pytest tests/test_live_recap_ingestion.py -q
uv run pytest tests/test_live_play_schemas.py -q
```

---

## Phase L5N — Ingestion Pane Shell / Operator Surface (PR93)

### Goal

Expose PR92 recap ingestion as an optional live-control operator pane with explicit authority boundaries and `breadcrumb_required` stop semantics.

### Checklist

- [x] Added narrow backend route: `POST /api/live/recap-ingest`.
- [x] Backend wraps `run_pipeline(...)` directly with operation-scoped options.
- [x] API forbids browser-supplied server path fields (`extra="forbid"` request model).
- [x] Added operation modes: `stage_preview`, `apply_normalize`, `materialize_session_memory`.
- [x] Added backend route tests with mutation-boundary assertions.
- [x] Added typed UI API client for recap ingest status.
- [x] Added optional `ingestion` module renderer in module registry.
- [x] Added ingestion pane with:
  - [x] raw recap paste + stage/preview submit
  - [x] apply/normalize guard on preview + non-generic slug/title
  - [x] materialize-session-memory action with breadcrumb boundary handling
  - [x] authority transition panel with explicit anti-collapse copy
  - [x] spelling/entity audit rendered as review-only
  - [x] read-only canonical preview diff (`<pre>`)
  - [x] advanced overwrite controls behind explicit disclosure
- [x] Added UI tests for state machine actions and guardrails.
- [x] Added `ingestion` as optional module in catalog/layout schema + session bootstrap defaults.

### Verification

```bash
uv run pytest tests/test_live_recap_ingest_api.py -q
uv run pytest tests/test_live_recap_ingest_pipeline.py -q
uv run pytest tests/test_live_session_bootstrap.py -q
uv run pytest tests/test_live_play_schemas.py -q
cd apps/live-control-ui && npm test
cd apps/live-control-ui && npm run build
```

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
