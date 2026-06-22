---
document_id: dmb-handoff-pr79-l5a-projection-command-contracts
title: PR 79 Handoff — L5A Projection Command Contracts
document_class: handoff
status: ready_for_implementation
version: 0.1
created_at: "2026-05-28T04:05:00Z"
related_documents:
  - path: Docs/Plans/DESIGN-c2-live-control-l5-pane-state-boundaries.md
    role: primary_design_anchor
  - path: Docs/Plans/PLAN-c2-live-control-surface-query-pane.md
    role: parent_plan
  - path: Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md
    role: execution_tracker
---

# PR 79 Handoff — L5A Projection Command Contracts

## Mission

Implement the first Python foundation slice for DungeonBuddy's L5 projection/command architecture.

This PR creates the typed contract layer that future panes, FastAPI routes, and agent tools will share.

Do not build UI.
Do not add FastAPI endpoints.
Do not perform real corpus writes.
Do not implement plan-view projection yet.

This PR is about **contracts + validation + tests**.

## Product Reason

DungeonBuddy panes are projected read models over authoritative backing stores. Pane writes and agent writes must flow through the same semantic command layer so the system can preserve intent, auditability, invalidation, and canon safety.

The UI should eventually render projections and server-provided capabilities. The agent should eventually inspect those same capabilities and submit the same commands. Neither should bypass server-side validation or write directly to corpus files.

## Scope

Implement Python models and lightweight helpers for:

- `ProjectionTarget`
- `ProjectionCapability`
- `ProjectionCommand`
- `ProjectionWriteResult`
- `ProjectionInvalidation`
- write lane literals/enums
- command type literals/enums
- validation helpers
- serialization helpers
- tests proving contract behavior

Recommended path:

```text
src/live_play/projections/
  __init__.py
  targets.py
  capabilities.py
  commands.py
  invalidation.py
  write_results.py
```

Tests:

```text
tests/test_live_projection_contracts.py
```

You may choose a slightly different file split if it is cleaner, but keep the public conceptual model stable.

## Out of Scope

Do not implement:

- `GET /api/live/plan-view`
- `GET /api/live/artifact`
- `GET /api/live/capabilities`
- `POST /api/live/commands`
- React components
- timeline module
- inspector pane
- real artifact patching
- retrieval service integration
- corpus markdown writes
- job queue mutation logic
- event log mutation logic

This PR may define command types like `append_observation` or `patch_artifact`, but it should not execute them against backing stores.

## Design Anchors

Read and preserve these invariants from the L5 design doc:

- Projection is derived, not authoritative.
- UI is not source of truth.
- Pane interactions and agent tools share the same typed command layer.
- Every write declares a lane.
- Ambiguous edits become reviewable work rather than silent canon mutation.
- Command results eventually carry audit identity and invalidation hints.
- Any future `patch_artifact` execution path must preserve corpus write safety (preview/confirm-token CAS semantics), not direct blind writes.

## Core Types

### ProjectionTarget

Represents a thing a pane or agent can inspect or act on.

Target types for this slice:

```text
event
roll_table
npc
location
runbook_section
job
open_loop
source_packet
```

Recommended fields:

```python
class ProjectionTarget(BaseModel):
    target_type: ProjectionTargetType
    target_id: str
    label: str
    source_status: ProjectionSourceStatus = "derived"
    metadata: dict[str, Any] = Field(default_factory=dict)
```

Suggested `source_status` values:

```text
derived
authoritative
live_only
stale
missing
unknown
```

Validation expectations:

- `target_id` is non-empty.
- `label` is non-empty.
- `metadata` defaults to `{}`.
- Unknown `target_type` should fail validation.

### ProjectionCapability

Represents an action currently available for a target.

Recommended fields:

```python
class ProjectionCapability(BaseModel):
    command_type: ProjectionCommandType
    label: str
    lane: ProjectionWriteLane
    enabled: bool = True
    required_fields: list[str] = Field(default_factory=list)
    risk_level: ProjectionRiskLevel = "low"
    disabled_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
```

Suggested risk levels:

```text
low
medium
high
```

Validation expectations:

- Disabled capability may include `disabled_reason`.
- Enabled capability should not require `disabled_reason`.
- Required fields are field names expected in command payload; do not validate payload here beyond shape.

### ProjectionCommand

Represents one requested write or action from either the UI or an agent.

Recommended fields:

```python
class ProjectionCommand(BaseModel):
    command_type: ProjectionCommandType
    target: ProjectionTarget
    lane: ProjectionWriteLane
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence: list[ProjectionEvidenceRef] = Field(default_factory=list)
    requested_by: ProjectionCommandRequester
    idempotency_key: str | None = None
```

Recommended requester:

```python
class ProjectionCommandRequester(BaseModel):
    requester_type: Literal["human_ui", "agent", "system"]
    requester_id: str | None = None
```

Recommended evidence ref:

```python
class ProjectionEvidenceRef(BaseModel):
    target: ProjectionTarget
    note: str | None = None
```

Command types for this slice (v0 provisional contract surface for L5A):

```text
append_observation
queue_canon_patch
patch_artifact
create_open_loop
update_open_loop
pin_scene_state
update_job_status
record_ruling
request_retrieval_refresh
update_layout
```

Write lanes for this slice (v0 provisional contract surface for L5A):

```text
observed_play
canon_patch
prep_note
live_state_pin
job_queue
retrieval_curation
layout_config
rules_ruling
```

Validation expectations:

- Every command must declare a write lane.
- Every command must have a target.
- Every command must declare requester info.
- Unknown command type or lane should fail validation.
- Payload may be arbitrary JSON-compatible dict for now.

Do not overfit command-type-to-lane compatibility yet unless the mapping is obvious and easy to test. A future command bus can enforce stricter capability matching.

### ProjectionInvalidation

Represents a projection or target that should be refreshed after a write.

Recommended fields:

```python
class ProjectionInvalidation(BaseModel):
    projection_key: str
    target: ProjectionTarget | None = None
    reason: str
```

Validation expectations:

- `projection_key` is non-empty.
- `reason` is non-empty.

Useful projection keys to seed as constants or examples:

```text
plan_view
current_state
record
queue
open_loops
roll_stack
sources
artifact
npc_focus
location_context
surface_layout
```

### ProjectionWriteResult

Represents the result of executing a command. In this PR, this is only a data contract.

Recommended fields:

```python
class ProjectionWriteResult(BaseModel):
    write_id: str
    status: ProjectionWriteStatus
    events_appended: list[str] = Field(default_factory=list)
    jobs_queued: list[str] = Field(default_factory=list)
    artifacts_changed: list[ProjectionTarget] = Field(default_factory=list)
    invalidations: list[ProjectionInvalidation] = Field(default_factory=list)
    conflicts: list[ProjectionConflict] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
```

Suggested statuses:

```text
accepted
rejected
conflict
noop
```

Recommended conflict:

```python
class ProjectionConflict(BaseModel):
    conflict_type: str
    message: str
    target: ProjectionTarget | None = None
    recoverable: bool = True
```

Validation expectations:

- `write_id` is non-empty.
- Conflict result should be representable without throwing.
- Result must serialize cleanly to JSON-compatible dict.

## Helper Functions

Implement small helpers only where they reduce repetition.

Examples:

```python
def make_target(target_type: ProjectionTargetType, target_id: str, label: str, **metadata: Any) -> ProjectionTarget: ...

def make_invalidation(projection_key: str, reason: str, target: ProjectionTarget | None = None) -> ProjectionInvalidation: ...
```

Do not implement a real `execute_command` yet unless it is a stub that raises `NotImplementedError` and is not wired to anything.

## Serialization Contract

All models should support:

```python
model.model_dump(mode="json")
model.model_validate(payload)
```

Tests should prove round-trip validation for a representative target, capability, command, invalidation, and write result.

## Test Plan

Create `tests/test_live_projection_contracts.py`.

Minimum tests:

1. `ProjectionTarget` validates known target types and rejects unknown target type.
2. `ProjectionCapability` serializes enabled and disabled capabilities.
3. `ProjectionCommand` requires lane, target, requester, and valid command type.
4. `ProjectionCommand` supports both `human_ui` and `agent` requesters.
5. `ProjectionInvalidation` requires projection key and reason.
6. `ProjectionWriteResult` can represent accepted result with events/jobs/invalidations.
7. `ProjectionWriteResult` can represent conflict result without raising.
8. Defaults use empty lists/dicts instead of shared mutable defaults.
9. JSON round-trip works with `model_dump(mode="json")` and `model_validate(...)`.
10. Public imports from `src.live_play.projections` expose the primary model classes.
11. Blank-string rejects are enforced for required identity/reason fields (`target_id`, `label`, `projection_key`, `reason`, `write_id`).

Suggested command:

```bash
uv run pytest tests/test_live_projection_contracts.py -q
```

Also run a nearby existing smoke cohort if cheap:

```bash
uv run pytest tests/test_live_control_server.py tests/test_live_play_turn_loop.py -q
```

If those tests are unrelated or fail for pre-existing reasons, document the result in the PR body.

## PR Body Requirements

The PR body should include:

```text
## Summary

- Adds Python projection/command contract models for L5 pane + agent write architecture.
- Adds tests for target/capability/command/write-result validation and JSON round-trip.
- No FastAPI endpoints, React UI, retrieval integration, or real corpus writes in this PR.

## Nano-commit map

1. Add projection package skeleton and target/enum models.
2. Add capability and command models.
3. Add invalidation/write-result/conflict models.
4. Add tests and public imports.
5. Update CHECKLIST evidence log.

## Verification

- `uv run pytest tests/test_live_projection_contracts.py -q`
- optional: `uv run pytest tests/test_live_control_server.py tests/test_live_play_turn_loop.py -q`

## Out of scope

- plan-view endpoint
- command bus execution
- artifact read/write endpoints
- UI pane rendering
```

## Nano-Commit Guidance

Keep commits small and reviewable.

Recommended sequence:

```text
1. docs: add/confirm L5A handoff and checklist note
2. feat: add projections package and target/write lane enums
3. feat: add capability and command contract models
4. feat: add invalidation, conflict, and write result models
5. test: cover projection command contract validation
6. docs: update checklist evidence and verification commands
```

Do not mix code, tests, and docs in one giant commit.

## Review Rubric

A reviewer should be able to answer yes to all of these:

- Are the contracts generic enough for UI panes and agent tools?
- Does every command require a write lane?
- Does the design avoid raw corpus-edit authority?
- Are mutable defaults handled safely?
- Can all models round-trip through JSON-compatible dumps?
- Are target and command type vocabularies explicit?
- Is there no real write execution hidden in this PR?
- Are future FastAPI and React layers able to consume these models cleanly?

## Important Design Boundary

This PR is not about deciding every future pane behavior. It is about giving all future pane behavior one shared substrate.

The hard problem is preserving semantic intent across projection and write boundaries. This PR should make that intent explicit in the data model without prematurely implementing the command bus.
