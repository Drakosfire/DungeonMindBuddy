---
document_id: dmb-plan-c2-live-control-query-pane
title: C2 Live Control Surface v0 — Query Pane
document_class: plan
plan_kind: product_sprint_plan
status: active
version: 2.0
created_at: "2026-05-25T03:11:00Z"
last_updated_at: "2026-05-30T19:30:00Z"
---

# C2 Live Control Surface v0 — Query Pane

## Thesis

DungeonBuddy is evolving from a repo-agent workflow into a live GM control surface.

The core architectural direction is locked:

- The UI is projection and interaction, not source of truth.
- The server owns projections, writes, audit, invalidation, and retrieval orchestration.
- Human panes and agent tools share the same typed command/capability layer.
- Session plan/timeline views are derived from source truth, not separately authored.
- Live play prioritizes low-friction capture over immediate canon reconciliation.

After PR90, the project has crossed from cockpit construction into dogfooding preparation. The next work is not another UI pane or a new corpus system. The next work is authority-safe planning over an activated Session 23 corpus.

See also:

```text
Docs/Plans/ROADMAP-c2s23-authority-activation-and-dogfood.md
Docs/Plans/RUNBOOK-c2-first-dogfood-planning-round.md
```

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

## Implemented L5 Spine

The first L5 spine is now substantially built:

| Slice | Result |
|---|---|
| PR79 / L5A | Projection and command contracts |
| PR80 / L5B | Plan-view projection endpoint |
| PR81 / L5C | Read-only Timeline module |
| PR82 / L5D | Universal Inspector Pane shell |
| PR83 / L5E | Artifact and capability reads |
| PR84 / L5F | Read-only pane renderers |
| PR85 / L5G | Command bus first write: append_observation |
| PR86 / L5H | Append observation pane action |
| PR87 / L5I | Scoped roll-table patch command |
| PR88 / L5J | Preview-first roll-table patch UI |
| PR89 / L5K | Patch UX hardening / read-after-write evidence |
| PR90 / L5L | Fresh recap ingestion / session bootstrap |
| PR92 / L5M | Raw recap intake + ingestion orchestrator (CLI) |
| PR93 / L5N | Ingestion operator pane + `POST /api/live/recap-ingest` |

This gives us:

```text
raw recap (CLI or ingestion pane)
→ staged notes + canonical recap preview/apply
→ normalized recap (+ breadcrumb boundary)
→ session memory when breadcrumb exists
fresh recap
→ bootstrapped live workspace
→ plan-view timeline
→ inspector artifact/capability reads
→ append observations
→ preview/confirm roll-table patch
→ write evidence and refresh
```

## Current Dogfood Boundary

L5M/L5N can drive raw recap intake through the PR92 orchestrator (CLI or live-control ingestion pane, with recap/source session decoupled from the live workspace session). PR90 can bootstrap a session workspace from a fresh recap, but neither path creates manifest-backed cross-session retrieval.

The system can now support a first planning pass, but context lookup across Session 21, Session 22, prep scaffold, live workspace files, roll tables, and hub evidence still needs an explicit activation boundary.

The next correctness risk is not UI mechanics. It is authority collapse.

Do not treat these as equivalent:

```text
raw table notes      → evidence awaiting recap-write
played recap         → canon/play memory after recap-write
session memory       → derived retrieval records from played recap
planning anchor      → GM scaffold, not canon
prep brief/runbook   → intended possibility space, not canon
roll tables          → prep tools, not happened facts
live workspace       → active planning surface / observations
```

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

The unified command endpoint is:

```text
POST /api/live/commands
```

Implemented command paths include:

- append_observation
- patch_artifact for allowlisted roll_table targets

Planned/deferred command paths include:

- queue_canon_patch
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
(events_appended, jobs_queued, invalidations, conflicts, metadata)
```

## API Direction

```text
GET  /api/live/plan-view
GET  /api/live/artifact
GET  /api/live/capabilities
POST /api/live/commands
```

Panes and agents should primarily use commands for writes.

## Forward Delivery Sequence

### Step 0 — Ingest Session 22

Run the existing content operation on staged notes:

```text
corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md
→ recap-write
→ normalized recap
→ breadcrumbed recap
→ session memory JSONL
```

This is not a code PR unless the existing content operation fails.

### PR91 — C2S23 Dogfood Planning Benchmark + Manual Baseline

Author 15–25 planning questions from GM intent, not by reverse-engineering source files.

Capture manual baseline answers and friction using the current workflow.

No automated scoring required yet.

### PR92 — C2S23 Activated Planning Corpus Manifest

Compose the existing corpus/session-memory/live-workspace machinery into one session-scoped activation manifest.

This is not a new ingestion system and not retrieval.

The manifest should define:

- in-bounds sources
- source_role
- authority
- session scope
- lifecycle state
- routes / normalized routes where available
- allowed and forbidden uses

It should emit a canonical JSON manifest and an optional generated markdown mirror.

### PR93 — Query / Admission over Activated Planning Corpus

Wire query/admission to consume the activation manifest.

The query layer should know both what is in bounds and how each source may be used.

### PR94 — Instrumented Dogfood Re-run

Re-run PR91 questions against manifest-backed query/admission.

Compare evidence recall, authority discipline, planning usefulness, and friction against the manual baseline.

## Product Invariants

- UI is not source of truth.
- Projections are derived.
- Fast-live paths avoid heavy retrieval.
- Retrieval is sibling infrastructure behind the live server.
- Agent tools do not bypass validation or corpus safety.
- Live play favors capture over reconciliation.
- Conflicts should become reviewable events/jobs rather than silent corruption.
- Prep scaffold must not be treated as canon/play fact.
- Raw table notes should be provenance-only after recap-write produces a played recap.
- Roll tables are reference tools, not evidence that something happened.

## Risks

- Dashboard creep
- Pane-specific write logic explosion
- Intent loss across edits
- Silent canon corruption
- Retrieval latency bleeding into fast-live
- Overly broad agent write authority
- Authority collapse between played recap and planning scaffold
- Question gold accidentally reverse-engineered from source files

## Success Criteria

- A single pane interaction model scales across future modules.
- Human and agent interactions share one command architecture.
- Projection refreshes are deterministic and explicit.
- Writes return invalidation and audit information.
- Session 23 can be planned from bootstrapped live workspace plus correctly activated prior context.
- The system can distinguish canon_play, planning_scaffold, planning_input, reference_tool, live_observation, and audit sources.
- DungeonBuddy feels like a coherent GM cockpit instead of repo tooling.
