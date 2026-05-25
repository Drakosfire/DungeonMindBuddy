# C2 Live Control UI — README

**Status:** planning/implementation guide. The UI package does not exist yet. This README describes the UI layer we intend to build, the backing runtime it will need, and how it should consume the merged C2 L1 live substrate.

**Target future location:** once the UI package exists, keep this document as the planning anchor and copy/adapt the implementation sections into `apps/live-control-ui/README.md`.

---

## 1. Purpose

The C2 Live Control UI is the first DungeonBuddy product surface for live GM use. It should make the Session 22 Cursor dogfood loop feel like an at-table tool instead of an IDE/repo-agent workflow.

The UI is not a corpus browser, dashboard, document editor, or analytics surface. It is a runtime-configurable live-play surface where the GM can type what just happened or what they need, get the correct response mode, and see session state stay organized through event logs, derived state, and queued background work.

Product promise:

> A GM can type a live-play turn, DungeonBuddy can answer in the right mode, and the system keeps session state organized through event logs and queued jobs — in a layout the GM can change at the table and recover after refresh.

---

## 2. Current Design Anchors

Read these before implementing the UI:

1. `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md` — active sprint plan and execution state.
2. `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md` — phase checklist, UI acceptance criteria, and demo script.
3. `Docs/Plans/STUDY-c2-live-play-cursor-handoff-process.md` — product-friction study from the Cursor live-play workflow.
4. `Docs/Plans/archive/2026-05-25/handoffs/HANDOFF-pr72-c2-live-packet-event-job-schema.md` — completed L1 substrate handoff.
5. `evals/c2_live_prep/live/session_22/live_packet.json` — Session 22 live packet and `surface_catalog`.
6. `evals/c2_live_prep/live/session_22/surface_layout.json` — runtime layout seed.
7. `evals/c2_live_prep/live/session_22/current_state.json` — derived state seed, not source truth.
8. `src/live_play/live_store.py` — file-backed JSON/JSONL helpers.
9. `src/live_play/surface_layout_invariants.py` — layout/catalog invariants.
10. `src/live_play/current_state_derive.py` — derived current-state contract.

The UI should treat those files as contracts, not inspiration to reinterpret freely.

---

## 3. Product Shape

The v0 UI is a **modular surface shell**.

Required modules:

- **Chat** — live input, answer, classification/mode badge, next suggestions.
- **Record** — append-only session event stream with provenance and timestamps.

Optional catalog modules:

- **Now** — current day, position, weather, and suggested next beat.
- **Open Loops** — unresolved obligations, follow-ups, and owed table beats.
- **Roll Stack** — pending/resolved roll tables with human labels and inline expansion later.
- **Sources** — provenance, admitted/candidate context, and gaps for context lookup.
- **Queue** — background jobs such as staging append, benchmark candidates, post-session propagation, packet rebuilds, and manual review.

The GM can enable, disable, reorder, collapse, and move optional modules between slots. Required modules stay enabled. Layout changes persist through the server, not browser-only state.

---

## 4. Non-negotiable UI Invariants

1. **The UI is not source of truth.** It reads from and writes through server-mediated files/events/jobs.
2. **Record remains complete.** Disabling a module never deletes events or hides the source event stream from the data model.
3. **Layout is file-backed.** `surface_layout.json` is authoritative for runtime UI layout until a later database/storage layer replaces it.
4. **Human labels first.** Show labels like `Storm weather`, `Road encounter`, and `Gate dilemma`; keep file paths in source/provenance captions.
5. **No artifact-register dashboard as the primary surface.** The UI should feel like a session-running tool, not a file inventory.
6. **No direct corpus writes from the browser.** Canon propagation and recap work become jobs/events handled by later slices.
7. **Fast live use stays fast.** Roll lookup and common live-turn response should not trigger repo-wide search.
8. **Context lookups show provenance.** When the system answers from packet/corpus context, the user should be able to inspect sources and gaps.

---

## 5. Backing Runtime We Need

The UI depends on three backing layers.

### L1 — merged file-backed substrate

Already landed in PR #72:

```text
evals/c2_live_prep/live/schemas/live_packet.schema.json
evals/c2_live_prep/live/schemas/live_event.schema.json
evals/c2_live_prep/live/schemas/live_job.schema.json
evals/c2_live_prep/live/schemas/live_surface_layout.schema.json

evals/c2_live_prep/live/session_22/live_packet.json
evals/c2_live_prep/live/session_22/surface_layout.json
evals/c2_live_prep/live/session_22/event_log.jsonl
evals/c2_live_prep/live/session_22/job_queue.jsonl
evals/c2_live_prep/live/session_22/current_state.json
evals/c2_live_prep/live/session_22/benchmark_candidates.jsonl

src/live_play/live_store.py
src/live_play/current_state_derive.py
src/live_play/surface_layout_invariants.py
```

The important contracts:

- `live_packet.surface_catalog` declares available modules.
- `surface_layout.json` declares enabled module instances and layout slots.
- `event_log.jsonl` is the append-only event record.
- `job_queue.jsonl` holds deferred work.
- `current_state.json` is derived and must remain non-authoritative.
- Required modules `chat` and `record` must exist and remain enabled.
- Layout module IDs must be a subset of the packet catalog.

### L2 — roll resolver + live classifier

L2 should build non-HTTP Python helpers that the server can call:

```text
src/live_play/resolve_roll.py
src/live_play/classify_live_turn.py
src/live_play/live_turn.py
```

Expected responsibilities:

- Classify input into modes: `fast_live`, `context_lookup`, `prep_architect`, `post_session`.
- Resolve common Session 22 roll-table prompts without repo-wide search.
- Convert a live input into event rows and queued jobs.
- Preserve event provenance and source paths.
- Avoid corpus writes during live play.

Example inputs:

```text
Weather 7. Caelynn Nature 19.
Grobnok does not call in the morning.
What is Lysandra feeling at the gate?
Lysandro is her father.
```

### L3 — local server / API envelope

The UI should not read/write substrate files directly. It should talk to a local server.

Planned endpoints:

```text
POST /api/live/query
GET  /api/live/state
GET  /api/live/events?since=<cursor>
GET  /api/live/jobs
POST /api/live/jobs/{id}/complete
POST /api/live/resolve-roll
POST /api/live/rebuild-packet
GET  /api/live/surface
PUT  /api/live/surface/layout
```

Server responsibilities:

- Load `live_packet.json` and `surface_layout.json`.
- Validate layout writes against schema and invariant helpers.
- Persist layout updates through atomic file writes.
- Append event rows for live turns and possibly layout changes.
- Return derived state rather than letting the browser derive source truth independently.
- Publish an OpenAPI contract so the server can eventually be reimplemented without rewriting UI modules.

---

## 6. Intended UI Package Shape

Planned package path:

```text
apps/live-control-ui/
```

Proposed structure:

```text
apps/live-control-ui/
  README.md
  package.json
  index.html
  src/
    App.tsx
    api/
      liveApi.ts
      types.ts
    surface/
      SurfaceShell.tsx
      moduleRegistry.ts
      LayoutControls.tsx
      modules/
        ChatModule.tsx
        RecordModule.tsx
        NowModule.tsx
        OpenLoopsModule.tsx
        RollStackModule.tsx
        SourcesModule.tsx
        QueueModule.tsx
```

V0 only needs Chat, Record, and one optional proof module rendered from shared server state. The other modules can be skeletal if the contract is clear.

---

## 7. Runtime Data Flow

### Initial load

```text
Browser opens UI
→ GET /api/live/surface
→ GET /api/live/state
→ GET /api/live/events
→ GET /api/live/jobs
→ SurfaceShell renders modules from catalog + layout
```

### Live query

```text
GM enters text in Chat
→ POST /api/live/query
→ server classifies live turn
→ server resolves/answers or queues background work
→ server appends event_log row(s)
→ server appends job_queue row(s), if needed
→ UI refreshes state/events/jobs
→ Chat shows answer; Record shows event; optional modules reflect derived state
```

### Layout update

```text
GM changes layout
→ PUT /api/live/surface/layout
→ server validates schema + invariants
→ server writes surface_layout.json atomically
→ optional: server appends surface_config_updated event
→ UI reloads surface layout
```

---

## 8. Module Contracts

Each UI module should be small and driven by server data.

Suggested TypeScript shape:

```ts
export type SurfaceSlot = "main" | "sidebar" | "bottom" | "overlay";

export interface SurfaceModuleDefinition {
  module_id: string;
  title: string;
  default_slot: SurfaceSlot;
  required: boolean;
  enabled_by_default: boolean;
  description?: string | null;
  config_schema?: Record<string, unknown> | null;
}

export interface SurfaceModuleInstance {
  module_id: string;
  slot: SurfaceSlot;
  order: number;
  enabled: boolean;
  collapsed: boolean;
  size?: string | null;
  config?: Record<string, unknown>;
}
```

The registry should map `module_id` to a component. Unknown modules should not crash the shell; they should render an explicit unsupported-module placeholder and surface enough detail for debugging.

Required modules cannot be disabled through the UI. The server should also enforce this because browser controls are not authority.

---

## 9. UX Direction

The UI should be closer to a session control table than a data table.

Good defaults:

- Chat in the main slot.
- Record in the sidebar.
- Now/Open Loops near Record.
- Roll Stack in bottom or sidebar.
- Queue collapsed by default.
- Sources hidden or overlay by default until a context lookup occurs.

Avoid:

- file-name-first cards
- giant artifact tables
- requiring the GM to know repo paths
- persistent dashboard chrome before the core loop works
- making every module visible by default if it makes the live pane noisy

The central test is: can the GM use this while running a session without feeling like they are operating a repository?

---

## 10. Build Order

Recommended implementation order:

1. Create UI package shell.
2. Add API client and shared TypeScript types matching the L1 schema shapes.
3. Render `SurfaceShell` from mocked `GET /api/live/surface` data.
4. Add Chat and Record modules against a stubbed API.
5. Add real L3 server calls once endpoints exist.
6. Add one optional module, preferably Roll Stack or Now.
7. Add LayoutControls for enable/disable, order, slot, collapsed state.
8. Persist layout through `PUT /api/live/surface/layout`.
9. Add context-specific behavior for `fast_live` vs `context_lookup` responses.
10. Add tests for required modules, layout persistence, and event refresh.

Do not build drag-and-drop first. Toggle/reorder/slot move is enough for v0 unless the implementation is cheap and does not distort the architecture.

---

## 11. Testing Expectations

Minimum UI tests once the package exists:

- SurfaceShell renders required Chat + Record from catalog/layout.
- Required modules cannot be disabled.
- Optional modules can be hidden without deleting records/events.
- LayoutControls call `PUT /api/live/surface/layout` with valid payloads.
- Chat submit calls `POST /api/live/query`.
- Record refreshes after a successful query.
- Human labels render before paths.
- Sources/provenance are visible for context lookup responses.

Minimum server/API tests supporting UI:

- `GET /api/live/surface` returns catalog + validated layout.
- `PUT /api/live/surface/layout` rejects missing/disabled Chat or Record.
- `PUT /api/live/surface/layout` rejects unknown module IDs.
- `GET /api/live/state` returns derived current state.
- `GET /api/live/events?since=` supports Record tailing.
- `POST /api/live/query` appends event rows and returns enough data for Chat + Record refresh.

---

## 12. Definition of Done for L4 v0

The UI slice is done when:

- The app starts locally.
- It loads surface catalog + layout from the server.
- Chat and Record render from server state.
- At least one optional module renders from shared state.
- A query like `Weather 7. Caelynn Nature 19.` can be submitted through Chat.
- The response appears in Chat and the resulting event appears in Record.
- The GM can change layout and recover it after refresh.
- Required modules cannot be disabled.
- The UI never writes corpus files directly.
- The UI reads like a live-play control surface, not a repo dashboard.

---

## 13. Open Questions

- Should the first UI package be Vite + React, or should it use whatever frontend convention the repo already has by the time L4 starts?
- Should L3 live under `apps/live-control-server/` or inside `src/live_play/server.py` for the first vertical slice?
- Should layout moves use simple controls first, with drag/drop as a follow-up?
- Should `Sources` open automatically on `context_lookup`, or stay manual until the user asks for provenance?
- Should event tailing use polling in v0, or should server-sent events/websockets be introduced later?

For v0, prefer boring local technology and crisp contracts over polished interaction complexity.
