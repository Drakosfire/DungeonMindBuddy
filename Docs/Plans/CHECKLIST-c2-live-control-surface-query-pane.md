# Checklist — C2 Live Control Surface v0 Query Pane

**Purpose:** Operational tracker for the product-surface sprint that turns Session 22 live-play dogfood into a local server + **runtime-configurable modular UI shell** (Chat + Record first).

**Plan anchor:** `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md`

**Sibling plan:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` remains the retrieval/autonomy benchmark workstream. This checklist tracks live UX and state orchestration, not C1S1–C1S3 retrieval promotion.

---

## Reanchor Block (fill first each session)

- [x] **Active slice:** `L2_roll_resolver_classifier`
- [x] **Last green artifact (path):** L1 live substrate verified:
  - `evals/c2_live_prep/live/session_22/live_packet.json`
  - `evals/c2_live_prep/live/session_22/surface_layout.json`
  - `evals/c2_live_prep/live/session_22/current_state.json`
  - `src/live_play/live_store.py`
  - `tests/test_live_play_schemas.py`
  - Verification: `uv run pytest tests/test_live_play_schemas.py -q` → `7 passed`.
- [x] **Next command / action:** Author or dispatch L2 roll resolver + live classifier slice.
- [x] **Open product decision:** Resolved — keep as sibling sprint, not folded into the current C1 retrieval/autonomy demo.
- [x] **Blocker type:** none for L1; PLAN/CHECKLIST accepted as active sprint anchors.

---

## Sprint Contract

This sprint proves one product surface:

> A GM can type a live-play turn, DungeonBuddy can answer in the right mode, and the system keeps session state organized through event logs and queued jobs — in a **layout the GM can change at the table** and recover after refresh.

It does not build the whole control surface.

### In Scope

- Local server (first implementation may be FastAPI; contract is language-agnostic)
- **Modular surface shell** — runtime-configurable layout, module registry
- Required modules: **Chat**, **Record**
- Optional catalog modules: Now, Open Loops, Roll Stack, Sources, Queue, …
- File-backed live packet + **surface_layout**
- Event log
- Job queue
- Derived current state
- Roll resolver
- Live turn classifier
- Retrieval packet path for `context_lookup`
- Session 22 transcript examples as tests

### Out of Scope

- Auth
- Database
- Multiplayer
- Full corpus browser
- Drag/drop canvas
- Document editor
- Rich map
- Timeline authoring UI
- Full recap-write UI

---

## Product Invariants

- [x] UI is **not** source of truth.
- [x] **`surface_layout.json` is authoritative for runtime UI layout**; GM changes persist through the server (`PUT /api/live/surface/layout`), not browser-only memory.
- [x] **`live_packet.surface_catalog` declares available modules**; `chat` and `record` are required and cannot be disabled.
- [x] Disabling a surface module never deletes events; **Record** stays complete.
- [x] `current_state.json` is derived from `live_packet.json` + `surface_layout.json` + `event_log.jsonl` + `job_queue.jsonl`.
- [ ] `fast_live` does not invoke repo-wide search.
- [ ] `context_lookup` can expose admitted context, candidate context, source-derived gaps, rendered packet, provenance, lane plan, and diagnostics.
- [ ] `post_session` drains queued jobs and patches corpus surfaces later; it does not patch multiple corpus files inline during live play.
- [ ] Session 22 transcript examples remain regression fixtures for the classifier / resolver.
- [ ] UI and classifier work re-read `STUDY-c2-live-play-cursor-handoff-process.md` before implementation to avoid dashboard/file-name-first regressions.
- [ ] HTTP/API contract is documented (OpenAPI) so the server can be reimplemented outside Python without rewriting surface modules.

---

## Phase L0 — Plan Lock

**Goal:** Establish the sprint as a separate product workstream with clear boundaries.

- [x] Create `PLAN-c2-live-control-surface-query-pane.md`.
- [x] Create `CHECKLIST-c2-live-control-surface-query-pane.md`.
- [x] Review with operator: sibling sprint vs extension of existing demo.
- [x] Accepted: update PLAN status from `draft` to `active`.
- [x] Accepted: set `execution_state.active_slice` to `L1_packet_event_job_schema`.
- [ ] Decide whether to add a one-line related-doc / flagged-followup link in `PLAN-split-corpus-retrieval-to-autonomous-demo.md`.

**Evidence**

- PLAN v1 created.
- CHECKLIST v1 created.
- Backlog item captured: `Product slice — C2 Live Control Surface v0 Query Pane`.

---

## Phase L1 — Live Packet + Event/Job Schema + Surface Layout

**Goal:** Create the file-backed state substrate (including runtime surface layout contract) without a server or UI.

### Files

```text
evals/c2_live_prep/live/schemas/live_packet.schema.json
evals/c2_live_prep/live/schemas/live_event.schema.json
evals/c2_live_prep/live/schemas/live_job.schema.json
evals/c2_live_prep/live/schemas/live_surface_layout.schema.json
evals/c2_live_prep/live/session_22/live_packet.json       # includes surface_catalog
evals/c2_live_prep/live/session_22/surface_layout.json
evals/c2_live_prep/live/session_22/event_log.jsonl
evals/c2_live_prep/live/session_22/job_queue.jsonl
evals/c2_live_prep/live/session_22/current_state.json
evals/c2_live_prep/live/session_22/benchmark_candidates.jsonl
src/live_play/live_store.py
tests/test_live_play_schemas.py
```

### Checklist

- [x] Define `live_packet` schema: campaign/session, packet provenance, known roll tables, current state seed, open loops, source paths, **`surface_catalog`**.
- [x] Define `live_surface_layout` schema: layout_version, updated_at, slot enum, module instances (id, slot, order, collapsed, config).
- [x] Define `live_event` schema: id, timestamp, session clock, event_type, text, derived fields, provenance, source mode.
- [x] Define `live_job` schema: id, job_type, payload, status, dependencies, created_from_event_id.
- [x] Seed `surface_catalog` with required `chat` + `record` and Session 22 optional modules.
- [x] Seed default `surface_layout.json` (Chat + Record + at least one optional module enabled).
- [x] Author implementation handoff: `Docs/Plans/HANDOFF-pr72-c2-live-packet-event-job-schema.md`.
- [x] Seed Session 22 packet from staging + runbook + journey tracker.
- [x] Seed packet / examples include friction-study prompts from `STUDY-c2-live-play-cursor-handoff-process.md`.
- [x] Add tests that load schemas and validate seed files.
- [x] Add append tests for event/job JSONL writes.
- [x] Add round-trip test for `write_json` on `surface_layout.json`.
- [x] Mark `current_state.json` as derived in schema or metadata.

### Verification

```bash
uv run pytest tests/test_live_play_schemas.py -q
```

---

## Phase L2 — Roll Resolver + Live Classifier

**Goal:** Resolve common live turns without web transport.

### Files

```text
src/live_play/roll_table_registry.py
src/live_play/resolve_roll.py
src/live_play/classify_live_turn.py
src/live_play/live_turn.py
tests/test_live_play_resolve_roll.py
tests/test_live_play_classify_turn.py
tests/test_live_play_turn_loop.py
```

### Seed Examples

| Text | Expected behavior |
|------|-------------------|
| `Weather 7. Caelynn Nature 19.` | `fast_live`; resolve T-WX 7; event: roll_result + skill_check; suggest T-NPC/R5/T-DIL. |
| `Weather 16.` | `fast_live`; resolve T-WX 16. |
| `R5 54.` | `fast_live`; resolve road encounter row 54; mark R5 done. |
| `Grobnok does not call in the morning.` | `fast_live`; open-loop update; evening contact remains owed. |
| `Lysandro is her father.` | `fast_live`; canon correction event; queue post-session propagation. |
| `Caelynn bottles the puddle water.` | `fast_live`; canon commit event; queue staging append / benchmark candidate. |
| `What is Lysandra feeling at the gate?` | `context_lookup`; route to packet/source lookup, not roll resolver. |

### Checklist

- [ ] Registry maps table IDs to corpus paths and row shape.
- [ ] Resolver supports pipe-row tables (`T-WX`, `T-DIL-G`, etc.).
- [ ] Resolver supports R5 band/paragraph shape or emits a clear unsupported-table diagnostic until implemented.
- [ ] Classifier separates `roll_result`, `skill_check`, `canon_commit`, `open_loop_update`, `canon_correction`, `context_question`, `prep_request`.
- [ ] `handle_live_turn(packet, text) -> LiveTurnResult` runs without FastAPI.
- [ ] LiveTurnResult includes answer, classification, events_to_write, jobs_to_queue, next_suggestions, source/provenance fields.

### Verification

```bash
uv run pytest tests/test_live_play_resolve_roll.py tests/test_live_play_classify_turn.py tests/test_live_play_turn_loop.py -q
```

---

## Phase L3 — FastAPI Server

**Goal:** Expose the live turn loop over a local API.

### Files

```text
apps/live-control-server/
  main.py
  routes/live.py
  services/live_agent_loop.py
  pyproject.toml   # optional; prefer repo-integrated if cleaner
```

### Endpoints

```text
POST /api/live/query
GET  /api/live/state
GET  /api/live/events              # ?since= for record tail
GET  /api/live/jobs
POST /api/live/jobs/{id}/complete
POST /api/live/resolve-roll
POST /api/live/rebuild-packet
GET  /api/live/surface
PUT  /api/live/surface/layout
```

### Checklist

- [ ] Server loads Session 22 live packet + surface layout from file.
- [ ] `POST /api/live/query` calls `handle_live_turn`.
- [ ] Event/job writes are atomic enough for local single-user use.
- [ ] `GET /api/live/state` returns derived current state.
- [ ] `GET /api/live/events` returns recent events (`?since=` supported for Record module).
- [ ] `GET /api/live/jobs` returns queued jobs.
- [ ] `GET /api/live/surface` returns catalog + current layout.
- [ ] `PUT /api/live/surface/layout` validates against schema and writes `surface_layout.json` atomically.
- [ ] Layout updates may append `surface_config_updated` to the event log.
- [ ] `POST /api/live/jobs/{id}/complete` marks job complete without deleting history.
- [ ] OpenAPI schema published for live endpoints.
- [ ] Curl smoke for `Weather 7. Caelynn Nature 19.` passes.

### Verification

```bash
uv run pytest tests/test_live_control_server.py -q
uv run uvicorn apps.live-control-server.main:app --reload
```

Curl smoke:

```bash
curl -s -X POST http://127.0.0.1:8000/api/live/query \
  -H 'Content-Type: application/json' \
  -d '{"campaign_id":"longmont-c2","session":22,"mode":"live","text":"Weather 7. Caelynn Nature 19."}'
```

---

## Phase L4 — Modular Surface Shell

**Goal:** Make the loop feel like DungeonBuddy instead of a repo-agent chat, with a **runtime-configurable** module layout.

### Files

```text
apps/live-control-ui/
  src/App.tsx
  src/surface/SurfaceShell.tsx
  src/surface/moduleRegistry.ts
  src/surface/modules/ChatModule.tsx
  src/surface/modules/RecordModule.tsx
  src/surface/modules/RollStackModule.tsx   # or another proof optional module
  src/surface/LayoutControls.tsx
```

### Checklist

- [ ] SurfaceShell loads catalog + layout from `GET /api/live/surface`.
- [ ] Chat module sends text to `POST /api/live/query` and shows answer, classification, next suggestions.
- [ ] Record module tails `GET /api/live/events?since=` (or polls recent events).
- [ ] At least one optional catalog module renders from shared server state (proof of plugin path).
- [ ] LayoutControls let GM enable/disable optional modules, reorder, and move between slots.
- [ ] Layout changes persist via `PUT /api/live/surface/layout` (not localStorage-only).
- [ ] Required modules `chat` and `record` cannot be disabled.
- [ ] UI labels are human-first (`Storm weather`, `Road encounter`, `Gate dilemma`) with file paths only in source/provenance captions.
- [ ] Roll tables expand inline inside modules; no artifact-register dashboard as the primary surface.
- [ ] UI refreshes module data after query.
- [ ] UI handles `fast_live` and `context_lookup` responses differently enough to see sources/gaps when present.
- [ ] UI does not write session source files directly (layout goes through server API).

### Verification

```bash
npm test
npm run build
```

Use the repo's actual package manager / app conventions once the UI package exists; commands above are placeholders until Phase L4 decides package shape.

---

## Demo Script

1. Start server and UI.
2. Confirm default layout shows Chat + Record (+ seeded optional module).
3. Type: `Weather 7. Caelynn Nature 19.`
4. Observe: immediate T-WX answer in Chat; roll_result row in Record; optional Roll Stack marks T-WX done.
5. Toggle/reorder a module; refresh browser; layout persists.
6. Type: `Grobnok does not call in the morning.`
7. Observe: Open Loops module (if enabled) keeps evening contact owed.
8. Type: `What is Lysandra feeling at the gate?`
9. Observe: `context_lookup` answer with sources / provenance in Sources module when enabled.
10. Type: `Lysandro is her father.`
11. Observe: canon correction event + queued propagation job, not inline corpus patching.

---

## Evidence Log

Append dated entries here as PRs land.

### 2026-05-25 — L1 Live Substrate Implemented Locally

- Implemented the L1 file-backed substrate directly in-session (no external GitHub PR opened): four live schemas, Session 22 seed files, `src/live_play/live_store.py`, and `tests/test_live_play_schemas.py`.
- Verification:
  - `uv run pytest tests/test_live_play_schemas.py -q` → `7 passed`.
  - JSON/JSONL parse smoke → `live C2 seed JSON/JSONL parse OK`.
- Parent-owned doc-sync advanced PLAN execution state to `L2_roll_resolver_classifier`.

### 2026-05-25 — Plan/Checklist Created

- Created `PLAN-c2-live-control-surface-query-pane.md`.
- Created this checklist.
- Added `STUDY-c2-live-play-cursor-handoff-process.md` as the product-friction anchor from the Cursor export.
- Accepted as active sibling sprint.
- Starting implementation state: `L1_packet_event_job_schema`; no code yet.

### 2026-05-26 — Modular runtime surface design locked

- PLAN v1.1: reframed v0 as runtime-configurable surface shell (Chat + Record required).
- Added `surface_catalog`, `surface_layout.json`, and `GET/PUT /api/live/surface` to L1/L3/L4 contracts.
- CHECKLIST + HANDOFF-pr72 updated to include surface layout schema and seed in PR 72 scope.

### 2026-05-25 — L1 Handoff Authored

- Added `Docs/Plans/HANDOFF-pr72-c2-live-packet-event-job-schema.md`.
- The handoff points a fresh agent through the anchor route: root rules, PLAN, CHECKLIST, STUDY, Session 22 dogfood handoff, staging notes, journey tracker, runbook, and C2 smoke artifact.
- Next action: dispatch the handoff for the L1 substrate PR.

---

## Open Questions

- [ ] Should server live under `apps/live-control-server/` or integrated under `src/live_play/server.py` first?
- [ ] Should UI live under `apps/live-control-ui/` or a demo/evals UI folder first?
- [x] Runtime surface configurability: **yes** — `surface_layout.json` + server persistence (locked 2026-05-26).
- [x] Does PR 1 include `benchmark_candidates.jsonl` schema, or defer until classifier can emit candidates? Resolved for L1: defer dedicated schema; file parses as JSONL and classifier will define candidate row shape later.
- [ ] Should R5 paragraph-table resolution land in PR 2 or be a follow-up after pipe-row tables?
- [ ] Should `context_lookup` initially read an existing packet only, or be allowed to rebuild packet in PR 3?
- [ ] Drag-and-drop layout polish: required in L4 v0 or acceptable as follow-up after toggle/reorder/slot-move works?
