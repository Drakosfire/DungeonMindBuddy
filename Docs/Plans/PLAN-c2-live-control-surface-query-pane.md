---
document_id: dmb-plan-c2-live-control-query-pane
title: C2 Live Control Surface v0 — Query Pane
document_class: plan
plan_kind: product_sprint_plan
status: active
version: 1
created_at: "2026-05-25T03:11:00Z"
last_updated_at: "2026-05-25T03:11:00Z"
timezone_note: "Timestamps are UTC; local work may use America/Denver."
supersedes: []
superseded_by: null
related_documents:
  - path: Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md
    role: operational_tracker
  - path: Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md
    role: sibling_retrieval_autonomy_plan
  - path: Docs/Plans/HANDOFF-s22-live-play-agent.md
    role: source_dogfood_contract
  - path: evals/c2_live_prep/artifacts/runs/2026-05-23/c2s22_smoke_report.md
    role: retrieval_prep_smoke_artifact
  - path: corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md
    role: live_play_transcript_staging
product_scope:
  campaign: Longmont Campaign 2
  seed_session: 22
  surface: local live-play query pane
  autonomy: server-mediated live turn classification, file-backed events, background job queue
execution_state:
  active_slice: L1_packet_event_job_schema
  milestone_progress:
    L0_plan_lock: complete
    L1_packet_event_job_schema: not_started
    L2_roll_resolver_classifier: not_started
    L3_fastapi_query_loop: not_started
    L4_react_query_pane: not_started
  blockers: []
  next_gate_command: "Draft the first implementation handoff: live packet + event/job schema."
  flagged_followups:
    - "Keep current C1S1-C1S3 retrieval/autonomy demo separate; cross-link only. This sprint productizes live GM interaction and consumes retrieval packet concepts when needed."
    - "Session 22 transcript examples are the seed regression set; do not generalize to all campaigns until the pane feels good on this slice."
---

# C2 Live Control Surface v0 — Query Pane

## Thesis

Cursor proved the workflow: during Session 22, the agent could answer live GM questions, resolve rolls, log canon commits, track open loops, use grounded context, and queue post-session propagation. Cursor also made the demo feel like engineering scaffolding: the GM had to work through an IDE repo-agent loop for actions that should feel like DungeonBuddy product behavior.

This sprint builds the first product-shaped pane:

> I can type what just happened or what I need, and DungeonBuddy gives me the right live-play response while quietly keeping the session state organized.

This is a sibling workstream to the retrieval/autonomy demo in `PLAN-split-corpus-retrieval-to-autonomous-demo.md`. The existing plan proves grounded planner context. This plan proves the live GM interaction loop.

## Product Shape

**Game Master Live Play Control Surface — Query Pane v0**

One pane, not the full control surface.

Flow:

```text
GM enters text
→ server classifies the live turn
→ server chooses latency mode
→ server returns the fast result
→ server appends event(s)
→ server queues slow side effects
→ UI shows answer + background state
```

The first pane answers and organizes. It does not edit the whole corpus.

## Minimal Architecture

```text
React / Vite UI
        ↓
FastAPI server
        ↓
live turn handler
        ↓
Tools:
  - roll resolver
  - live turn classifier
  - retrieval packet reader / builder
  - staging/event logger
  - job queue writer
  - source/provenance reader
```

The first version is local and file-backed.

```text
evals/c2_live_prep/live/session_22/
  live_packet.json
  event_log.jsonl
  job_queue.jsonl
  current_state.json
  benchmark_candidates.jsonl
```

`current_state.json` is derived, not authoritative. Durable facts live in `live_packet.json`, `event_log.jsonl`, `job_queue.jsonl`, corpus markdown, and retrieval artifacts.

## UI v0

```text
┌──────────────────────────────────────────────────────┐
│ Ask / Log / Roll                                     │
│ [ Weather 7. Caelynn Nature 19.                  ]   │
│ [Send]                                               │
├──────────────────────────────────────────────────────┤
│ Response                                             │
│ T-WX 7: hail dent...                                 │
│ Logged: Day 2 weather. Queued: benchmark candidate.  │
├──────────────────────────────────────────────────────┤
│ Context Windows                                      │
│ [Now] [Open Loops] [Roll Stack] [Sources] [Queue]    │
└──────────────────────────────────────────────────────┘
```

Initial panels:

| Panel | Purpose |
|-------|---------|
| **Now** | Session, current day/position, active weather, next suggested beat. |
| **Open Loops** | Grobnok evening contact, Silver Raven reply, Tealeaf/Sara leg, propagation chores. |
| **Roll Stack** | T-WX / R5 / T-DIL / T-DIL-G completion state. |
| **Sources** | When `context_lookup` runs: admitted context, candidate context, gaps, provenance. |
| **Queue** | Background jobs: append staging, benchmark candidate, post-session propagation, packet rebuild. |

## API Surface

Keep the server small.

```text
POST /api/live/query
GET  /api/live/state
GET  /api/live/events
GET  /api/live/jobs
POST /api/live/jobs/{id}/complete
POST /api/live/resolve-roll
POST /api/live/rebuild-packet
```

Primary request:

```json
{
  "campaign_id": "longmont-c2",
  "session": 22,
  "mode": "live",
  "text": "Weather 7. Caelynn Nature 19."
}
```

Primary response:

```json
{
  "answer": "T-WX 7: hail dent. Two-minute hail burst, then sleet/slush...",
  "classification": {
    "intents": ["roll_result", "skill_check", "weather_state"],
    "latency_mode": "fast_live"
  },
  "events_written": [
    {
      "event_type": "roll_result",
      "target": "event_log"
    }
  ],
  "jobs_queued": [
    {
      "job_type": "append_staging"
    },
    {
      "job_type": "benchmark_candidate"
    }
  ],
  "next_suggestions": ["T-NPC", "R5", "T-DIL"]
}
```

## Live Turn Loop

Core logic should be testable without the web server:

```python
handle_live_turn(packet, text) -> LiveTurnResult
```

Loop:

1. Load `live_packet.json`.
2. Classify user text.
3. Choose latency mode.
4. Run blocking tools only.
5. Produce answer.
6. Append event(s).
7. Queue slow jobs.
8. Return UI payload.

## Latency Modes

| Mode | Use | Constraints |
|------|-----|-------------|
| `fast_live` | Roll lookup, canon commit, open-loop update, current packet status. | No repo-wide search. Prefer deterministic tools. LLM fallback only by explicit design. |
| `context_lookup` | Grounded NPC/location/status answer from known sources or retrieval packet. | May read packet/source files; exposes admitted/candidate/gaps/provenance. |
| `prep_architect` | Slower planning output, scene proposal, or packet rebuild. | Evidence-heavy; not expected to feel instant. |
| `post_session` | Drain queued jobs, patch corpus surfaces, prepare recap inputs. | Not inline with live answer unless operator asks. |

## PR Slices

### PR 1 — Live Packet + Event/Job Schema

Files:

```text
evals/c2_live_prep/live/schemas/live_packet.schema.json
evals/c2_live_prep/live/schemas/live_event.schema.json
evals/c2_live_prep/live/schemas/live_job.schema.json
evals/c2_live_prep/live/session_22/live_packet.json
evals/c2_live_prep/live/session_22/event_log.jsonl
evals/c2_live_prep/live/session_22/job_queue.jsonl
evals/c2_live_prep/live/session_22/current_state.json
evals/c2_live_prep/live/session_22/benchmark_candidates.jsonl
```

Acceptance: tests validate schema load and append event/job writes. `current_state.json` is marked derived.

### PR 2 — Roll Resolver + Live Classifier

Files:

```text
src/live_play/roll_table_registry.py
src/live_play/resolve_roll.py
src/live_play/classify_live_turn.py
tests/test_live_play_resolve_roll.py
tests/test_live_play_classify_turn.py
```

Seed examples:

- `Weather 7`
- `Weather 16`
- `R5 54`
- `Grobnok does not call`
- `Lysandro is her father`
- `Caelynn bottles the puddle water`

Acceptance: examples produce correct intents, blocking tool choices, event types, queued job types, and next suggestions.

### PR 3 — FastAPI Server

Files:

```text
apps/live-control-server/
  main.py
  routes/live.py
  services/live_agent_loop.py
```

Acceptance: `POST /api/live/query` returns answer + classification + event/job writes. A `curl` smoke for `Weather 7. Caelynn Nature 19.` passes.

### PR 4 — Light UI Query Pane

Files:

```text
apps/live-control-ui/
  src/App.tsx
  src/components/QueryPane.tsx
  src/components/ResponsePanel.tsx
  src/components/ContextWindows.tsx
```

Acceptance: local UI sends text, displays response, and shows Now / Open Loops / Roll Stack / Sources / Queue from server state.

## What Not To Build Yet

Out of scope for v0:

- Full corpus browser
- Auth
- Multiplayer
- Database
- Drag/drop canvas
- Document editor
- Timeline authoring UI
- Rich map
- Full recap-write UI

## Retrieval Integration

Not every live query runs retrieval.

Examples:

| Query | Mode |
|-------|------|
| `Weather 7` | `fast_live` |
| `Grobnok does not call in the morning` | `fast_live` |
| `What does Lysandra know about Mireward?` | `context_lookup` |
| `Plan the next scene from here` | `prep_architect` |
| `Lysandro is her father` | `fast_live` answer + event + propagation job |

`context_lookup` is where the existing PR58–67 / `c2_live_prep` packet discipline fits: admitted context, candidate context, source-derived gaps, rendered packet, provenance, lane plan, diagnostics.

## Demo Path

The demo should show:

1. Open the Live Play Control Surface.
2. Type: `Weather 7. Caelynn Nature 19.`
3. Instant answer appears; event log updates; roll stack marks T-WX done.
4. Type: `Grobnok does not call in the morning.`
5. Open Loops updates: evening contact still owed.
6. Type: `What is Lysandra feeling at the gate?`
7. Server runs `context_lookup`, returns grounded NPC status with sources.
8. Type: `Lysandro is her father.`
9. System logs canon correction and queues post-session propagation instead of patching multiple corpus files inline.

## Acceptance Criteria

- Local server accepts GM text.
- Server classifies live turn.
- Fast roll results do not invoke repo-wide search.
- Server appends event log entries.
- Server queues background jobs.
- UI displays answer, Now, Open Loops, Roll Stack, Sources, Queue.
- Session 22 transcript examples are tests.
- Retrieval packet path remains available for `context_lookup`.
- UI is not source of truth.

## Changelog

### v1 — 2026-05-25

- Created sibling product sprint plan for C2 Live Control Surface v0 Query Pane.
- Locked scope as local server + light UI over file-backed live packet / event log / job queue.
- Kept current C1 retrieval/autonomy demo as a separate workstream.
- Accepted as an active sibling sprint; execution state moved from `planning_lock` to `L1_packet_event_job_schema`.
