---
document_id: dmb-plan-c2-live-control-query-pane
title: C2 Live Control Surface v0 — Query Pane
document_class: plan
plan_kind: product_sprint_plan
status: active
version: 1.6
created_at: "2026-05-25T03:11:00Z"
last_updated_at: "2026-05-28T02:18:00Z"
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
  - path: Docs/Plans/STUDY-c2-live-play-cursor-handoff-process.md
    role: product_friction_study
  - path: Docs/Plans/archive/2026-05-25/handoffs/HANDOFF-pr72-c2-live-packet-event-job-schema.md
    role: completed_l1_implementation_handoff
  - path: Docs/Plans/archive/2026-05-25/handoffs/HANDOFF-pr74-c2-l2-roll-resolver-classifier.md
    role: completed_l2_implementation_handoff
  - path: Docs/Plans/archive/2026-05-26/handoffs/HANDOFF-pr75-c2-l3-fastapi-query-loop-min.md
    role: completed_l3_min_implementation_handoff
  - path: Docs/Plans/archive/2026-05-26/handoffs/HANDOFF-pr76-c2-l3-rest-server-contract.md
    role: completed_l3_rest_implementation_handoff
  - path: Docs/Plans/archive/2026-05-26/handoffs/HANDOFF-pr77-c2-l4-react-surface-shell.md
    role: completed_l4_implementation_handoff
  - path: Docs/Plans/README-c2-live-control-ui.md
    role: l4_ui_planning_readme
product_scope:
  campaign: Longmont Campaign 2
  seed_session: 22
  surface: local runtime-configurable live-play surface shell
  autonomy: server-mediated live turn classification, file-backed events, background job queue
execution_state:
  active_slice: L5_ui_plan_projection
  milestone_progress:
    L0_plan_lock: complete
    L1_packet_event_job_schema: complete
    L2_roll_resolver_classifier: complete
    L3_fastapi_query_loop: complete
    L4_react_query_pane: complete
    L5_ui_plan_projection: in_progress
  blockers: []
  next_gate_command: "Implement and verify plan projection UI slice: add server-derived plan-view endpoint + UI timeline module + detail pane wiring; run `uv run pytest tests/test_live_control_server.py -q` and `cd apps/live-control-ui && npm test`."
  flagged_followups:
    - "Keep current C1S1-C1S3 retrieval/autonomy demo separate; cross-link only. This sprint productizes live GM interaction and consumes retrieval packet concepts when needed."
    - "Session 22 transcript examples are the seed regression set; do not generalize to all campaigns until the pane feels good on this slice."
    - "Before designing UI or classifier examples, re-read STUDY-c2-live-play-cursor-handoff-process.md to remember the Cursor friction: dashboard shape, file-name-first navigation, and slow repo-agent loops."
    - "L3 `surface_config_updated` audit event on layout PUT is deferred; core path is schema + invariant validation + atomic persist (documented in PR #76 body)."
    - "L4 v0 shell complete (PR #77): Queue/Sources modules not implemented; `LiveJob` TS type simplified vs L3 job schema; RollStack Session 22 title fallback is display-only — align server/state before Queue UI."
    - "L5 lock: projection is derived on-the-fly from corpus + live packet; no new authoritative session-plan file."
    - "L5 lock: avoid GM distraction — no mandatory beat status workflow or live reconciliation ceremony; recap remains the canonical reconciliation surface."
external_pull_requests:
  - pr: 77
    handoff: Docs/Plans/archive/2026-05-26/handoffs/HANDOFF-pr77-c2-l4-react-surface-shell.md
    slice: L4_react_surface_shell_v0
    verdict: accepted
    evaluated_at: "2026-05-26T03:03:06Z"
    evaluator: Cursor agent
    notes:
      - "Merged PR #77 (merge commit dc4dbf88): apps/live-control-ui/ Vite+React SurfaceShell; Chat/Record/RollStack/Now; embedded ModuleLayoutControls; enabled-only surface grid + Hidden modules panel; event_origin contract; 14 Vitest / UI build / 18 server regression."
      - "Review follow-up: event_origin not origin; disabled optional modules off primary grid; PR body full git diff --name-only (34 files)."
    verification:
      - "cd apps/live-control-ui && npm test → 14 passed"
      - "cd apps/live-control-ui && npm run build → OK"
      - "uv run pytest tests/test_live_control_server.py -q → 18 passed"
    rubric_when_we_judge:
      - "L4 stays inside HANDOFF allowlist; no server, live-play Python, schemas, corpus, or committed session seed mutation."
      - "UI consumes L3 via liveApi.ts only; required chat/record locked; layout persists via PUT /api/live/surface/layout."
      - "LiveEvent uses event_origin; disabled optional modules absent from surface grid but re-enableable via layout panel."
      - "At least one optional catalog module proves plugin path; Vitest covers Chat, Record, layout persistence, and disable-from-grid behavior."
  - pr: 76
    handoff: Docs/Plans/archive/2026-05-26/handoffs/HANDOFF-pr76-c2-l3-rest-server-contract.md
    slice: L3_rest_fastapi_server_contract
    verdict: accepted
    evaluated_at: "2026-05-26T01:44:00Z"
    evaluator: Cursor agent
    notes:
      - "Merged PR #76 (merge commit aae7d795): GET/PUT surface, job complete with schema-gated JSONL rewrite, resolve-roll debug, packet_rebuild queue (202); OpenAPI path coverage; 18 server / 62 L1+L2+L3 tests."
      - "Review follow-up: PR body audit artifact, main.py on allowlist, complete_job validates all rows before rewrite; surface_config_updated audit event deferred."
    verification:
      - "uv run pytest tests/test_live_control_server.py -q → 18 passed"
      - "uv run pytest tests/test_live_play_schemas.py tests/test_live_play_resolve_roll.py tests/test_live_play_classify_turn.py tests/test_live_play_turn_loop.py tests/test_live_control_server.py -q → 62 passed"
    rubric_when_we_judge:
      - "L3-rest stays inside HANDOFF allowlist; no React UI, schema mutation, corpus writes, or committed seed JSONL/layout mutation."
      - "L3-min endpoints remain intact; surface returns catalog+layout+derived state; layout PUT validates schema+invariants; resolve-roll does not append; rebuild-packet queues job only."
  - pr: 75
    handoff: Docs/Plans/archive/2026-05-26/handoffs/HANDOFF-pr75-c2-l3-fastapi-query-loop-min.md
    slice: L3_min_fastapi_query_loop
    verdict: accepted
    evaluated_at: "2026-05-26T00:58:15Z"
    evaluator: Cursor agent
    notes:
      - "Merged PR #75 (merge commit af27c47): FastAPI query/state/events/jobs spine over handle_live_turn; pre-append schema validation; fresh GET /state; temp-session tests."
      - "Doc-sync with PR #76 closure: L3-min + L3-rest together complete Phase L3 checklist."
    verification:
      - "uv run pytest tests/test_live_control_server.py -q (L3-min cohort; expanded to 18 after PR #76)"
    rubric_when_we_judge:
      - "L3-min does not claim full Phase L3; defers surface/layout/job-complete/resolve-roll/rebuild to L3-rest."
      - "POST /api/live/query persists validated events/jobs; GET /state recomputes; unknown events since returns empty."
  - pr: 74
    handoff: Docs/Plans/archive/2026-05-25/handoffs/HANDOFF-pr74-c2-l2-roll-resolver-classifier.md
    slice: L2_roll_resolver_classifier
    verdict: accepted
    evaluated_at: "2026-05-25T19:14:00Z"
    evaluator: Cursor agent
    notes:
      - "Merged PR #74 (merge commit 3f2cabd): roll registry/resolver, rule-based classifier, handle_live_turn without HTTP; Session 22 seed tests; live_job rows returned at top level for L3 append path."
      - "Review follow-up: classifier/resolver punctuation alignment, job schema tests, pipe-row delimiter strip, canon correction preserves input text; PR body lists complete diff vs allowlist."
    verification:
      - "uv run pytest tests/test_live_play_resolve_roll.py tests/test_live_play_classify_turn.py tests/test_live_play_turn_loop.py -q → 25 passed"
      - "uv run pytest tests/test_live_play_schemas.py tests/test_live_play_resolve_roll.py tests/test_live_play_classify_turn.py tests/test_live_play_turn_loop.py -q → 44 passed"
    rubric_when_we_judge:
      - "L2 stays inside HANDOFF allowlist; no server, UI, schema mutation, corpus writes, or committed seed JSONL mutation."
      - "Weather 7/16 and R5 54 resolve with provenance; classifier matches resolver punctuation tolerance."
      - "handle_live_turn returns schema-valid events and top-level live_job rows without writing JSONL inline."
      - "context_lookup classifies without roll resolution; canon correction/commit queue jobs only."
  - pr: 72
    handoff: Docs/Plans/archive/2026-05-25/handoffs/HANDOFF-pr72-c2-live-packet-event-job-schema.md
    slice: L1_packet_event_job_schema
    verdict: accepted
    evaluated_at: "2026-05-25T17:03:17Z"
    evaluator: Cursor agent
    notes:
      - "Merged PR #72 (merge commit 7d6648d): L1 file-backed substrate with schemas, Session 22 seeds, live_store helpers, layout/event invariants, and 19-test verification spine."
      - "Re-review gates satisfied: scope limited to allowlist; chat/record layout enforcement; event_origin for system events; derived current_state including now; catalog/layout consistency."
    verification:
      - "uv run pytest tests/test_live_play_schemas.py -q → 19 passed"
    rubric_when_we_judge:
      - "Seed JSON/JSONL and layout rows validate against schemas with format checker enabled."
      - "surface_layout.json enforces required enabled chat and record; layout module IDs ⊆ surface_catalog."
      - "current_state.json derived fields (including now) match recomputation from packet, layout, event_log, job_queue."
      - "L1 PR must not include server, UI, classifier, roll resolver, or corpus writes."
---

# C2 Live Control Surface v0 — Query Pane

## Thesis

Cursor proved the workflow: during Session 22, the agent could answer live GM questions, resolve rolls, log canon commits, track open loops, use grounded context, and queue post-session propagation. Cursor also made the demo feel like engineering scaffolding: the GM had to work through an IDE repo-agent loop for actions that should feel like DungeonBuddy product behavior.

Product-friction anchor: `STUDY-c2-live-play-cursor-handoff-process.md` captures the Cursor export that motivated this sprint. Re-read it before implementing the classifier/UI so the pane does not regress into a dashboard or file browser.

This sprint builds the first product-shaped **modular control surface**:

> I can type what just happened or what I need, and DungeonBuddy gives me the right live-play response while quietly keeping the session state organized — in a layout I can change at the table without losing it on refresh.

This is a sibling workstream to the retrieval/autonomy demo in `PLAN-split-corpus-retrieval-to-autonomous-demo.md`. The existing plan proves grounded planner context. This plan proves the live GM interaction loop.

**Implementation language is not locked.** v0 may land on Python (FastAPI) + React first, but the durable contract is JSON/JSONL files + a small HTTP API envelope. The server adapter can be replaced later without rewriting the surface module model.

## Product Shape

**Game Master Live Play Control Surface — modular shell v0**

One **runtime-configurable surface**, not the full control surface and not a fixed dashboard layout.

Flow:

```text
GM enters text (Chat module)
→ server classifies the live turn
→ server chooses latency mode
→ server returns the fast result
→ server appends event(s) (Record module reads the stream)
→ server queues slow side effects
→ enabled surface modules refresh from server state
```

v0 ships **Chat** + **Record** as required modules. Optional modules (Now, Open Loops, Roll Stack, Sources, Queue, …) register against a catalog and are toggled, reordered, and slotted **at runtime** by the GM. Layout persists through the server, not browser-only memory.

The surface answers and organizes. It does not edit the whole corpus inline.

v0.1 UI pivot: show a **projected beat timeline** for Session 22 that is derived from source truth (runbook + packet + runtime state), not a second authored truth surface. Timeline rows must carry human labels and hyperlinks to constituent sources (NPC hubs, location hubs, runbook sections, roll tables); selecting an item opens an inspector pane for review/edit/save on the underlying source file.

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
  - session-plan projection builder (derived view)
  - retrieval packet reader / builder
  - staging/event logger
  - job queue writer
  - source/provenance reader
```

The first version is local and file-backed.

```text
evals/c2_live_prep/live/session_22/
  live_packet.json          # session seed + surface_catalog (what may be shown)
  surface_layout.json       # GM runtime layout (authoritative for UI)
  event_log.jsonl
  job_queue.jsonl
  current_state.json
  benchmark_candidates.jsonl
```

`current_state.json` is derived, not authoritative. Durable facts live in `live_packet.json`, `surface_layout.json`, `event_log.jsonl`, `job_queue.jsonl`, corpus markdown, and retrieval artifacts.

### Session Plan Projection Contract (L5)

The timeline/project view is constructed on demand:

```text
corpus Session Prep docs + live_packet + event/job state
→ build_session_plan_projection(...)
→ UI timeline + hyperlinks + inspector pane
```

Rules:

- Projection is **derived**; no new authoritative `session_plan*.json` source-of-truth file.
- Hyperlinks open constituent artifacts in-pane (NPC/location details, runbook sections, roll tables).
- Roll-table edits persist to the underlying table file via server write path; projection refreshes from source.
- Any reconciliation that can wait should wait: avoid interruptive beat-management workflows during live play; reconcile against recap post-session.

## Modular Surface UI

The UI is a **shell + module registry**, not a single fixed pane.

### Required v0 modules

| Module id | Purpose |
|-----------|---------|
| `chat` | Query input, classification badge, answer, next suggestions. Cannot be disabled. |
| `record` | Append-only session event stream (what happened, when, provenance). Cannot be disabled. |

### Optional catalog modules (Session 22 seed)

| Module id | Human title (example) | Purpose |
|-----------|----------------------|---------|
| `now` | Now | Session, day/position, active weather, next suggested beat. |
| `open_loops` | Open loops | Grobnok evening contact, Silver Raven reply, propagation chores. |
| `roll_stack` | Roll stack | T-WX / R5 / T-DIL / T-DIL-G completion state; inline table expand. |
| `sources` | Sources | When `context_lookup` runs: admitted/candidate context, gaps, provenance. |
| `queue` | Queue | Background jobs: staging append, benchmark candidate, propagation, rebuild. |

### Runtime layout (GM-configurable)

Slots are coarse in v0: `main`, `sidebar`, `bottom`, `overlay`.

`live_packet.surface_catalog` declares available modules (id, title, default_slot, `required`, optional `config_schema`).

`surface_layout.json` holds the GM's current choices: enabled modules, slot assignment, order within slot, collapsed/size hints, `layout_version`, `updated_at`.

When the GM changes layout at the table:

1. UI sends `PUT /api/live/surface/layout`.
2. Server writes `surface_layout.json` atomically.
3. Server may append a `surface_config_updated` event to the record for audit.
4. Refresh or reconnect restores the same layout.

Disabling a module never deletes events; **Record** stays complete.

### v0 wireframe (default Session 22 layout)

```text
┌──────────────────────────────┬─────────────────────────┐
│ Chat (required)              │ Record (required)       │
│ [ Weather 7. Caelynn …    ]  │ 10:04 roll_result T-WX 7│
│ [Send]                       │ 10:05 open_loop Grobnok │
│ Response: T-WX 7 hail dent…  │ …                       │
├──────────────────────────────┴─────────────────────────┤
│ sidebar: [Roll stack ▾] [Open loops]     [+ module]    │
└────────────────────────────────────────────────────────┘
```

Module renderers are keyed by `module_id`. New product behavior should prefer new event/job types + optional new catalog entries over new monolithic screens.

## API Surface

Keep the server small.

```text
POST /api/live/query
GET  /api/live/state
GET  /api/live/events              # ?since= for record tail / module refresh
GET  /api/live/jobs
POST /api/live/jobs/{id}/complete
POST /api/live/resolve-roll
POST /api/live/rebuild-packet
GET  /api/live/surface             # catalog + current layout
PUT  /api/live/surface/layout      # GM runtime layout (writes surface_layout.json)
```

Publish an OpenAPI schema from L3 onward. UI modules depend on the response envelope, not on Python types.

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

### PR 1 — Live Packet + Event/Job Schema + Surface Layout Contract

Files:

```text
evals/c2_live_prep/live/schemas/live_packet.schema.json
evals/c2_live_prep/live/schemas/live_event.schema.json
evals/c2_live_prep/live/schemas/live_job.schema.json
evals/c2_live_prep/live/schemas/live_surface_layout.schema.json
evals/c2_live_prep/live/session_22/live_packet.json       # includes surface_catalog
evals/c2_live_prep/live/session_22/surface_layout.json    # default GM layout seed
evals/c2_live_prep/live/session_22/event_log.jsonl
evals/c2_live_prep/live/session_22/job_queue.jsonl
evals/c2_live_prep/live/session_22/current_state.json
evals/c2_live_prep/live/session_22/benchmark_candidates.jsonl
src/live_play/live_store.py                                 # load/write JSON + JSONL append
```

Acceptance: tests validate schema load, append event/job writes, and round-trip `write_json` for `surface_layout.json`. `live_packet.surface_catalog` lists required `chat` + `record` and Session 22 optional modules. `current_state.json` is marked derived.

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
apps/live_control_server/
  main.py
  routes/live.py
  session_store.py
  schema_validation.py
  services/live_agent_loop.py
```

Acceptance: `POST /api/live/query` returns answer + classification + event/job writes. `GET/PUT /api/live/surface` read/write `surface_layout.json`. A `curl` smoke for `Weather 7. Caelynn Nature 19.` passes.

### PR 4 — Modular Surface Shell (Chat + Record + proof module)

Files:

```text
apps/live-control-ui/
  src/App.tsx
  src/surface/SurfaceShell.tsx
  src/surface/moduleRegistry.ts
  src/surface/modules/ChatModule.tsx
  src/surface/modules/RecordModule.tsx
  src/surface/modules/RollStackModule.tsx   # or another optional proof module
  src/surface/LayoutControls.tsx
```

Acceptance: local UI sends text via Chat, shows Record event stream, enables at least one optional catalog module, and persists GM layout changes through `PUT /api/live/surface/layout` (toggle, reorder, or slot move — drag-and-drop may follow in a polish pass).

## What Not To Build Yet

Out of scope for v0:

- Full corpus browser
- Auth
- Multiplayer
- Database
- Drag/drop canvas
- Document editor
- Timeline authoring/reconciliation workflow that interrupts live play
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
- `surface_catalog` + `surface_layout.json` define a runtime-configurable modular UI; Chat and Record are required and cannot be disabled.
- GM layout changes persist through the server (`PUT /api/live/surface/layout`), not browser-only state.
- UI shell renders enabled modules from layout; at least one optional catalog module proves the plugin path in v0.
- Session plan projection is computed on-the-fly from source truth (no second authored plan file).
- Timeline/project view links to constituent artifacts and opens them in an inspector pane.
- Roll-table review/edit/save operates on the underlying table file, not on copied projection text.
- Session 22 transcript examples are tests.
- Retrieval packet path remains available for `context_lookup`.
- UI is not source of truth.
- Live session does not require manual beat reconciliation steps; recap remains canonical reconciliation.
- HTTP/API contract is documented (OpenAPI) so the server implementation can move off Python later without rewriting modules.

## Changelog

### v1.6 — 2026-05-28

- Captured UI pivot decisions: on-the-fly session-plan projection (no special plan SoT file), hyperlinked project/timeline view into constituent artifacts, and no-distraction live-play posture (defer reconciliation to recap).
- Opened new active slice `L5_ui_plan_projection` for timeline + inspector pane implementation.
- Clarified out-of-scope boundary: no live timeline authoring/reconciliation workflow that burdens the GM.

### v1.5 — 2026-05-26

- Merged PR #77 (merge `dc4dbf88`): L4 v0 React surface shell — `apps/live-control-ui/`, SurfaceShell + Chat/Record/RollStack, embedded layout controls, enabled-only grid, Hidden modules panel; 14 UI tests + build OK.
- `L4_react_query_pane` → `complete`; next gate is CHECKLIST Demo Script / manual browser smoke.

### v1.4 — 2026-05-26

- Merged PR #75 (merge `af27c47`): L3-min FastAPI spine — query/state/events/jobs, schema validation before append, isolated server tests.
- Merged PR #76 (merge `aae7d795`): L3-rest — surface GET/PUT, job complete, resolve-roll, rebuild-packet queue, OpenAPI path tests; `apps/live_control_server/` on `main`.
- Advanced `execution_state.active_slice` to `L4_react_query_pane`; `L3_fastapi_query_loop` → `complete`.

### v1.3 — 2026-05-25

- Merged PR #74: L2 roll resolver, live classifier, and `handle_live_turn` (registry, pipe + R5 band tables, Session 22 tests, 25 L2 / 44 combined with L1).
- Advanced `execution_state.active_slice` to `L3_fastapi_query_loop`.

### v1.2 — 2026-05-25

- Merged PR #72: L1 live substrate (schemas, Session 22 seeds, `live_store.py`, invariants, 19 tests).
- Advanced `execution_state.active_slice` to `L2_roll_resolver_classifier`.

### v1.1 — 2026-05-26

- Reframed v0 as a **runtime-configurable modular surface shell** (Chat + Record required; optional catalog modules).
- Added `surface_catalog` (in `live_packet.json`) and authoritative `surface_layout.json` to the file-backed contract.
- Added `GET/PUT /api/live/surface` endpoints and `surface_config_updated` audit event to the API story.
- Clarified language-agnostic boundary: JSON/JSONL + HTTP envelope, not Python-specific logic in the UI.

### v1 — 2026-05-25

- Created sibling product sprint plan for C2 Live Control Surface v0 Query Pane.
- Locked scope as local server + light UI over file-backed live packet / event log / job queue.
- Kept current C1 retrieval/autonomy demo as a separate workstream.
- Accepted as an active sibling sprint; execution state moved from `planning_lock` to `L1_packet_event_job_schema`.
- Authored `HANDOFF-pr72-c2-live-packet-event-job-schema.md` as the L1 implementation handoff.
