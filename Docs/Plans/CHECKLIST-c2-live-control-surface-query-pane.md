# Checklist — C2 Live Control Surface v0 Query Pane

**Purpose:** Operational tracker for the product-surface sprint that turns Session 22 live-play dogfood into a local server + **runtime-configurable modular UI shell** (Chat + Record first).

**Plan anchor:** `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md`

**Sibling plan:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` remains the retrieval/autonomy benchmark workstream. This checklist tracks live UX and state orchestration, not C1S1–C1S3 retrieval promotion.

---

## Reanchor Block (fill first each session)

- [x] **Active slice:** `L4_react_query_pane` (v0 shell **complete** on `main`)
- [x] **Last green artifact (path):** L4 merged on `main` (PR #77 merge `dc4dbf88`):
  - `apps/live-control-ui/` (`SurfaceShell`, `liveApi.ts`, Chat/Record/RollStack modules, `ModuleLayoutControls`, `SurfaceLayoutPanel`)
  - `Docs/Plans/archive/2026-05-26/handoffs/HANDOFF-pr77-c2-l4-react-surface-shell.md`
  - Verification: `cd apps/live-control-ui && npm test` → `14 passed`; `npm run build` → OK; `uv run pytest tests/test_live_control_server.py -q` → `18 passed`.
- [x] **Next command / action:** CHECKLIST Demo Script — start server + UI dev, manual Session 22 browser smoke; optional follow-ups: Queue/Sources modules, `LiveJob` type alignment, server-driven roll titles.
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
- [x] Session 22 transcript examples remain regression fixtures for the classifier / resolver (L2 tests on `main`, PR #74).
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

- [x] Registry maps table IDs to corpus paths and row shape.
- [x] Resolver supports pipe-row tables (`T-WX`, `T-DIL-G`, etc.).
- [x] Resolver supports R5 band/paragraph shape (PR #74); unsupported shapes return structured diagnostics.
- [x] Classifier separates `roll_result`, `skill_check`, `canon_commit`, `open_loop_update`, `canon_correction`, `context_question`, `prep_request`.
- [x] `handle_live_turn(packet, text) -> LiveTurnResult` runs without FastAPI.
- [x] LiveTurnResult includes answer, classification, events_to_write, jobs_to_queue, next_suggestions, source/provenance fields.
- [x] Merged PR #74; handoff archived: `Docs/Plans/archive/2026-05-25/handoffs/HANDOFF-pr74-c2-l2-roll-resolver-classifier.md`.

### Verification

```bash
uv run pytest tests/test_live_play_resolve_roll.py tests/test_live_play_classify_turn.py tests/test_live_play_turn_loop.py -q
```

---

## Phase L3 — FastAPI Server

**Goal:** Expose the live turn loop over a local API.

### Files

```text
apps/live_control_server/
  main.py
  routes/live.py
  session_store.py
  schema_validation.py
  services/live_agent_loop.py
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

- [x] Server loads Session 22 live packet + surface layout from file.
- [x] `POST /api/live/query` calls `handle_live_turn`.
- [x] Event/job writes are atomic enough for local single-user use.
- [x] `GET /api/live/state` returns derived current state (recomputes on read).
- [x] `GET /api/live/events` returns recent events (`?since=` supported for Record module).
- [x] `GET /api/live/jobs` returns queued jobs.
- [x] `GET /api/live/surface` returns catalog + current layout + derived state.
- [x] `PUT /api/live/surface/layout` validates against schema and writes `surface_layout.json` atomically.
- [ ] Layout updates append `surface_config_updated` to the event log. *(deferred — PR #76; validation+persist path is live.)*
- [x] `POST /api/live/jobs/{id}/complete` marks job complete without deleting history.
- [x] `POST /api/live/resolve-roll` debug wrapper (no append).
- [x] `POST /api/live/rebuild-packet` queues `packet_rebuild` job (no inline rebuild).
- [x] OpenAPI paths covered for live endpoints (`/openapi.json` tested).
- [ ] Curl smoke for `Weather 7. Caelynn Nature 19.` passes. *(optional manual; pytest boundary green.)*

### Verification

```bash
uv run pytest tests/test_live_control_server.py -q
uv run pytest tests/test_live_play_schemas.py tests/test_live_play_resolve_roll.py tests/test_live_play_classify_turn.py tests/test_live_play_turn_loop.py tests/test_live_control_server.py -q
uv run uvicorn apps.live_control_server.main:app --reload
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
  src/api/liveApi.ts
  src/surface/SurfaceShell.tsx
  src/surface/SurfaceLayoutPanel.tsx
  src/surface/ModuleLayoutControls.tsx
  src/surface/moduleRegistry.tsx
  src/surface/modules/ChatModule.tsx
  src/surface/modules/RecordModule.tsx
  src/surface/modules/RollStackModule.tsx
```

### Checklist

- [x] SurfaceShell loads catalog + layout from `GET /api/live/surface`.
- [x] Chat module sends text to `POST /api/live/query` and shows answer, classification, next suggestions.
- [x] Record module displays events from parent refresh (`GET /api/live/events` on bootstrap / post-query).
- [x] At least one optional catalog module renders from shared server state (`roll_stack` proof).
- [x] Embedded `ModuleLayoutControls` let GM enable/disable optional modules, reorder, and move between slots; disabled optional modules in Hidden modules panel (not primary grid).
- [x] Layout changes persist via `PUT /api/live/surface/layout` (not localStorage-only).
- [x] Required modules `chat` and `record` cannot be disabled.
- [x] UI labels are human-first (`Storm weather`, etc.) with Session 22 roll-title fallback (v0 debt — prefer server/state payload next).
- [x] Roll stack lists pending tables inline; no artifact-register dashboard as the primary surface.
- [x] UI refreshes module data after query (`App.tsx` callback).
- [x] UI handles `fast_live` and `context_lookup` responses differently (classification badge + diagnostics/provenance).
- [x] UI does not write session source files directly (layout goes through server API).
- [ ] **Follow-up:** Queue and Sources modules (catalog entries exist; UI placeholders only).
- [ ] **Follow-up:** Manual browser smoke per Demo Script below.

### Verification

```bash
cd apps/live-control-ui && npm test
cd apps/live-control-ui && npm run build
uv run pytest tests/test_live_control_server.py -q
```

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

### 2026-05-26 — L4 v0 React Surface Shell Complete (PR #77)

- Merged PR #77 to `main` (merge `dc4dbf88`): `apps/live-control-ui/` — Vite + React + TypeScript; `SurfaceShell` with enabled-only grid; Chat, Record, RollStack (+ Now when enabled); embedded `ModuleLayoutControls`; `SurfaceLayoutPanel` for hidden optional modules; `event_origin` on `LiveEvent`.
- Verification on `main`: `cd apps/live-control-ui && npm test` → `14 passed`; `npm run build` → OK; `uv run pytest tests/test_live_control_server.py -q` → `18 passed`.
- `execution_state.L4_react_query_pane` → `complete`; next gate = Demo Script / manual browser smoke. v0 debt: simplified `LiveJob` type, Session 22 roll-title fallback, Queue/Sources not implemented.

### 2026-05-26 — L3 FastAPI Server Complete (PR #75 + PR #76)

- Merged PR #75 to `main` (merge `af27c47`): L3-min — `POST /api/live/query`, `GET /state|events|jobs`, schema validation before append, fresh state recompute.
- Merged PR #76 to `main` (merge `aae7d795`): L3-rest — `GET/PUT /api/live/surface`, job complete, resolve-roll, rebuild-packet queue, OpenAPI path tests.
- Verification on `main`: `tests/test_live_control_server.py` → `18 passed`; L1+L2+L3 → `62 passed`.
- `execution_state.active_slice` advanced to `L4_react_query_pane`; Phase L3 checklist complete except deferred `surface_config_updated` audit event.

### 2026-05-25 — L2 Roll Resolver + Classifier Merged (PR #74)

- Merged PR #74 to `main` (merge commit `3f2cabd`): `roll_table_registry`, `resolve_roll`, `classify_live_turn`, `live_turn`, L2 test trio.
- Verification on `main`: L2 `25 passed`; L1+L2 `44 passed`.
- `execution_state.active_slice` advanced to `L3_fastapi_query_loop`.

### 2026-05-25 — L1 Live Substrate Merged (PR #72)

- Merged PR #72 to `main` (merge commit `7d6648d`): schemas, Session 22 seeds, `live_store.py`, layout/event invariants, `tests/test_live_play_schemas.py`.
- Verification on `main`: `uv run pytest tests/test_live_play_schemas.py -q` → `19 passed`.
- `execution_state.active_slice` advanced to `L2_roll_resolver_classifier`.

### 2026-05-26 — L1 Live Substrate Proposed in PR #72

- PR #72 opened with file-backed substrate; review rounds addressed scope, layout/event contracts, and derived `current_state.now`.

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

- [x] Should server live under `apps/live-control-server/` or integrated under `src/live_play/server.py` first? **Resolved:** `apps/live_control_server/` (PR #75/#76).
- [ ] Should UI live under `apps/live-control-ui/` or a demo/evals UI folder first?
- [x] Runtime surface configurability: **yes** — `surface_layout.json` + server persistence (locked 2026-05-26).
- [x] Does PR 1 include `benchmark_candidates.jsonl` schema, or defer until classifier can emit candidates? Resolved for L1: defer dedicated schema; file parses as JSONL and classifier will define candidate row shape later.
- [x] Should R5 paragraph-table resolution land in PR 2 or be a follow-up after pipe-row tables? **Resolved:** R5 band/paragraph resolution shipped in PR #74 (L2).
- [ ] Should `context_lookup` initially read an existing packet only, or be allowed to rebuild packet in PR 3?
- [x] Drag-and-drop layout polish: deferred — toggle/reorder/slot-move + per-module Save shipped in L4 v0 (PR #77).
