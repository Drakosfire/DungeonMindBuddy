# Checklist — C2 Live Control Surface v0 Query Pane

**Purpose:** Operational tracker for the product-surface sprint that turns Session 22 live-play dogfood into a local server + light UI query pane.

**Plan anchor:** `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md`

**Sibling plan:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` remains the retrieval/autonomy benchmark workstream. This checklist tracks live UX and state orchestration, not C1S1–C1S3 retrieval promotion.

---

## Reanchor Block (fill first each session)

- [x] **Active slice:** `L1_packet_event_job_schema`
- [x] **Last green artifact (path):** Session 22 dogfood artifacts exist and are usable as seed evidence:
  - `Docs/Plans/HANDOFF-s22-live-play-agent.md`
  - `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md`
  - `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_travel_to_mireward_runbook.md`
  - `evals/c2_live_prep/artifacts/runs/2026-05-23/c2s22_smoke_report.md`
  - `Docs/Plans/STUDY-c2-live-play-cursor-handoff-process.md`
- [x] **Next command / action:** Dispatch `Docs/Plans/HANDOFF-pr71-c2-live-packet-event-job-schema.md`.
- [x] **Open product decision:** Resolved — keep as sibling sprint, not folded into the current C1 retrieval/autonomy demo.
- [x] **Blocker type:** none for L1; PLAN/CHECKLIST accepted as active sprint anchors.

---

## Sprint Contract

This sprint proves one product surface:

> A GM can type a live-play turn, DungeonBuddy can answer in the right mode, and the system keeps session state organized through event logs and queued jobs.

It does not build the whole control surface.

### In Scope

- Local FastAPI server
- Light React / Vite query pane
- File-backed live packet
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

- [ ] UI is **not** source of truth.
- [ ] `current_state.json` is derived from `live_packet.json` + `event_log.jsonl` + `job_queue.jsonl`.
- [ ] `fast_live` does not invoke repo-wide search.
- [ ] `context_lookup` can expose admitted context, candidate context, source-derived gaps, rendered packet, provenance, lane plan, and diagnostics.
- [ ] `post_session` drains queued jobs and patches corpus surfaces later; it does not patch multiple corpus files inline during live play.
- [ ] Session 22 transcript examples remain regression fixtures for the classifier / resolver.
- [ ] UI and classifier work re-read `STUDY-c2-live-play-cursor-handoff-process.md` before implementation to avoid dashboard/file-name-first regressions.

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

## Phase L1 — Live Packet + Event/Job Schema

**Goal:** Create the file-backed state substrate without a server or UI.

### Files

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

### Checklist

- [ ] Define `live_packet` schema: campaign/session, packet provenance, known roll tables, current state seed, open loops, source paths.
- [ ] Define `live_event` schema: id, timestamp, session clock, event_type, text, derived fields, provenance, source mode.
- [ ] Define `live_job` schema: id, job_type, payload, status, dependencies, created_from_event_id.
- [x] Author implementation handoff: `Docs/Plans/HANDOFF-pr71-c2-live-packet-event-job-schema.md`.
- [ ] Seed Session 22 packet from staging + runbook + journey tracker.
- [ ] Seed packet / examples include friction-study prompts from `STUDY-c2-live-play-cursor-handoff-process.md`.
- [ ] Add tests that load schemas and validate seed files.
- [ ] Add append tests for event/job JSONL writes.
- [ ] Mark `current_state.json` as derived in schema or metadata.

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
GET  /api/live/events
GET  /api/live/jobs
POST /api/live/jobs/{id}/complete
POST /api/live/resolve-roll
POST /api/live/rebuild-packet
```

### Checklist

- [ ] Server loads Session 22 live packet from file.
- [ ] `POST /api/live/query` calls `handle_live_turn`.
- [ ] Event/job writes are atomic enough for local single-user use.
- [ ] `GET /api/live/state` returns derived current state.
- [ ] `GET /api/live/events` returns recent events.
- [ ] `GET /api/live/jobs` returns queued jobs.
- [ ] `POST /api/live/jobs/{id}/complete` marks job complete without deleting history.
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

## Phase L4 — Light UI Query Pane

**Goal:** Make the loop feel like DungeonBuddy instead of a repo-agent chat.

### Files

```text
apps/live-control-ui/
  src/App.tsx
  src/components/QueryPane.tsx
  src/components/ResponsePanel.tsx
  src/components/ContextWindows.tsx
```

### Checklist

- [ ] Query pane sends text to `POST /api/live/query`.
- [ ] Response panel shows answer, classification, events written, jobs queued, next suggestions.
- [ ] Context windows show Now, Open Loops, Roll Stack, Sources, Queue.
- [ ] UI labels are human-first (`Storm weather`, `Road encounter`, `Gate dilemma`) with file paths only in source/provenance captions.
- [ ] Roll tables expand inline; no artifact-register dashboard as the primary surface.
- [ ] UI refreshes state after query.
- [ ] UI handles `fast_live` and `context_lookup` responses differently enough to see sources/gaps when present.
- [ ] UI does not write source files directly.

### Verification

```bash
npm test
npm run build
```

Use the repo's actual package manager / app conventions once the UI package exists; commands above are placeholders until Phase L4 decides package shape.

---

## Demo Script

1. Start server and UI.
2. Type: `Weather 7. Caelynn Nature 19.`
3. Observe: immediate T-WX answer, event log write, Roll Stack marks T-WX done.
4. Type: `Grobnok does not call in the morning.`
5. Observe: Open Loops keeps evening contact owed.
6. Type: `What is Lysandra feeling at the gate?`
7. Observe: `context_lookup` answer with sources / provenance.
8. Type: `Lysandro is her father.`
9. Observe: canon correction event + queued propagation job, not inline corpus patching.

---

## Evidence Log

Append dated entries here as PRs land.

### 2026-05-25 — Plan/Checklist Created

- Created `PLAN-c2-live-control-surface-query-pane.md`.
- Created this checklist.
- Added `STUDY-c2-live-play-cursor-handoff-process.md` as the product-friction anchor from the Cursor export.
- Accepted as active sibling sprint.
- Starting implementation state: `L1_packet_event_job_schema`; no code yet.

### 2026-05-25 — L1 Handoff Authored

- Added `Docs/Plans/HANDOFF-pr71-c2-live-packet-event-job-schema.md`.
- The handoff points a fresh agent through the anchor route: root rules, PLAN, CHECKLIST, STUDY, Session 22 dogfood handoff, staging notes, journey tracker, runbook, and C2 smoke artifact.
- Next action: dispatch the handoff for the L1 substrate PR.

---

## Open Questions

- [ ] Should server live under `apps/live-control-server/` or integrated under `src/live_play/server.py` first?
- [ ] Should UI live under `apps/live-control-ui/` or a demo/evals UI folder first?
- [ ] Does PR 1 include `benchmark_candidates.jsonl` schema, or defer until classifier can emit candidates?
- [ ] Should R5 paragraph-table resolution land in PR 2 or be a follow-up after pipe-row tables?
- [ ] Should `context_lookup` initially read an existing packet only, or be allowed to rebuild packet in PR 3?
