---
document_id: dmb-plan-c2-live-control-query-pane
title: C2 Live Control Surface v0 — Query Pane
document_class: plan
plan_kind: product_sprint_plan
status: active
version: 1.8
created_at: "2026-05-25T03:11:00Z"
last_updated_at: "2026-05-28T03:48:00Z"
---

# C2 Live Control Surface v0 — Query Pane

## Thesis

DungeonBuddy is evolving from a repo-agent workflow into a live GM control surface.

The core architectural direction is now locked:

- The UI is projection and interaction, not source of truth.
- The server owns projections, writes, audit, invalidation, and retrieval orchestration.
- Human panes and agent tools share the same typed command/capability layer.
- Session plan/timeline views are derived from source truth, not separately authored.
- Live play prioritizes low-friction capture over immediate canon reconciliation.

## Product Shape

The product is a modular live-play cockpit:

```text
GM input
→ classify live turn
→ produce projection(s)
→ append events
→ queue slow work
→ refresh affected projections
```

v0 ships with Chat + Record as required modules.

Optional modules evolve incrementally:

- Now / Scene
- Roll Stack
- Open Loops
- Queue
- Sources
- Timeline / Projected Beats
- Inspector Pane
- NPC Focus
- Location Context

## Architectural Pivot

The major L5 shift is from module-specific logic to a shared projection/command architecture.

### Projection Model

Panes are projections over authoritative backing stores:

- event log
- job queue
- corpus markdown
- retrieval artifacts
- packet state
- layout state

Projection text itself is not authoritative.

### Command Model

Writes happen through typed commands:

```text
Projection
→ capability discovery
→ typed command
→ validation
→ audit event
→ backing-store write(s)
→ invalidation result
→ projection refresh
```

The UI and agent tools both use this command layer.

## Python-First Kernel

The next implementation center of gravity should remain Python.

Recommended domain layer:

```text
src/live_play/projections/
  targets.py
  capabilities.py
  commands.py
  invalidation.py
  write_results.py
  plan_view.py
  artifact_read.py
  command_bus.py
```

Core functions:

```python
build_projection(...)
resolve_capabilities(...)
execute_command(...)
```

FastAPI is the transport adapter.
React renders projections and submits commands.

## Pane Inventory

### Implemented

- Chat / Command
- Record
- Now
- Roll Stack
- Layout Controls

### Designed / Planned

- Queue
- Open Loops
- Sources / Evidence
- Timeline / Projected Session Plan
- Universal Inspector
- NPC Focus
- Location Context
- Rules / Mechanics
- Post-session Work

## Write Lanes

Every write must declare intent:

| Lane | Purpose |
|---|---|
| observed_play | What happened at the table |
| canon_patch | Long-term campaign memory update |
| prep_note | Future-facing prep |
| live_state_pin | Temporary live orientation |
| job_queue | Deferred work |
| retrieval_curation | Retrieval/source control |
| layout_config | Runtime UI layout |
| rules_ruling | Table ruling / house rule |

## Shared Command Bus

Prefer a unified command endpoint:

```text
POST /api/live/commands
```

Example commands:

- append_observation
- queue_canon_patch
- patch_artifact
- create_open_loop
- update_open_loop
- pin_scene_state
- update_job_status
- request_retrieval_refresh
- update_layout

## Core Contracts

### ProjectionTarget

```text
(type, id, label, source_status)
```

### ProjectionCapability

```text
(command_type, lane, enabled, required_fields)
```

### ProjectionCommand

```text
(command_type, target, lane, payload, evidence)
```

### ProjectionWriteResult

```text
(events_appended, jobs_queued, invalidations, conflicts)
```

## API Direction

```text
GET  /api/live/plan-view
GET  /api/live/artifact
GET  /api/live/capabilities
POST /api/live/commands
```

Artifact patch routes may remain internally, but panes and agents should primarily use commands.

## Delivery Sequence

### PR A — Projection Contracts

- ProjectionTarget
- ProjectionCapability
- ProjectionCommand
- ProjectionWriteResult
- ProjectionInvalidation

### PR B — Plan View Endpoint

- derived timeline projection
- Session 22 sample payload
- schema + tests

### PR C — Timeline Module

- read-only projection rendering
- ref chips
- no inspector yet

### PR D — Inspector Pane Shell

- pane target state
- shared pane chrome
- no artifact reads yet

### PR E — Artifact Read Contracts

- allowlisted artifact read endpoint
- event + roll_table support
- capability discovery

### PR F — Inspector Rendering

- event renderer
- roll-table renderer
- read-only first

### PR G — Command Bus First Writes

- append observation
- update job status
- pin scene state
- invalidation handling

### PR H — Pane Actions

- submit typed commands
- refresh invalidated projections

### PR I — Scoped Artifact Writes

- roll-table editing
- etag/file-state safety
- source refresh

## Product Invariants

- UI is not source of truth.
- Projections are derived.
- Fast-live paths avoid heavy retrieval.
- Retrieval is sibling infrastructure behind the live server.
- Agent tools do not bypass validation or corpus safety.
- Live play favors capture over reconciliation.
- Conflicts should become reviewable events/jobs rather than silent corruption.

## Risks

- Dashboard creep
- Pane-specific write logic explosion
- Intent loss across edits
- Silent canon corruption
- Retrieval latency bleeding into fast-live
- Overly broad agent write authority

## Success Criteria

- A single pane interaction model scales across future modules.
- Human and agent interactions share one command architecture.
- Projection refreshes are deterministic and explicit.
- Writes return invalidation and audit information.
- Session 22 feels like a coherent live GM surface instead of repo tooling.
