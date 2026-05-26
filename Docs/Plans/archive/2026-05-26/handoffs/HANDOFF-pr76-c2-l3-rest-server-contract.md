# HANDOFF — PR 76: C2 Live Control Surface L3-rest Server Contract

**Created:** 2026-05-26 (UTC).  
**Status:** MERGED — PR #76 landed on `main` (merge commit `aae7d795`, 2026-05-26 UTC). Completes Phase L3 server contract with PR #75 L3-min spine.  
**Parent agent:** Cursor agent; parent owns review, merge, and atomic doc-sync after the PR lands.  
**Base:** `main` after PR #75 merge (`af27c47`) — L3-min FastAPI query loop landed, but full Phase L3 is not complete.  
**Plan anchor:** `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md` (`execution_state.active_slice: L3_fastapi_query_loop`).  
**Checklist anchor:** `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md` Phase L3.  
**Substrate anchors:** PR #72 L1 live substrate; PR #74 L2 live turn handler; PR #75 L3-min FastAPI spine.

---

## §0 Re-anchor Before Writing

This handoff assumes PR #75 is merged on `main` and L3-min is complete. Do not infer current state from chat history.

Read in this order:

1. `.cursor/rules/external-agent-pr-loop.mdc` — mandatory allowlist / denylist / verification contract.
2. `.cursor/rules/anchor.mdc` — re-anchor discipline for fresh agents.
3. `AGENTS.md` — repo operating policy, UV usage, RTK preference, git verification, and external-agent PR loop conventions.
4. `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md` — confirm L3 remains active until this PR lands and doc-sync runs.
5. `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md` — Phase L3 endpoint checklist is authoritative.
6. `Docs/Plans/archive/2026-05-25/handoffs/HANDOFF-pr75-c2-l3-fastapi-query-loop-min.md` — L3-min contract and explicit deferrals.
7. `Docs/Plans/README-c2-live-control-ui.md` — client-facing expectations for the future UI.
8. Current server code and tests:
   - `apps/live_control_server/config.py`
   - `apps/live_control_server/routes/live.py`
   - `apps/live_control_server/session_store.py`
   - `apps/live_control_server/schema_validation.py`
   - `apps/live_control_server/services/live_agent_loop.py`
   - `tests/test_live_control_server.py`
9. L1/L2 helpers this PR should reuse, not rewrite:
   - `src/live_play/live_store.py`
   - `src/live_play/current_state_derive.py`
   - `src/live_play/surface_layout_invariants.py`
   - `src/live_play/resolve_roll.py`
   - `src/live_play/live_turn.py`

Current-state hypothesis to carry into the PR:

- L1 live substrate is merged.
- L2 roll resolver/classifier/live-turn handler is merged.
- L3-min FastAPI query loop is merged.
- Full Phase L3 is still open.
- L4 React UI is not started.

---

## §1 Mission

Complete the non-UI FastAPI server contract that L4 needs.

PR #75 gave the UI a minimal spine:

```text
POST /api/live/query
GET  /api/live/state
GET  /api/live/events
GET  /api/live/jobs
```

PR #76 adds the remaining Phase L3 server endpoints and tests:

```text
GET  /api/live/surface
PUT  /api/live/surface/layout
POST /api/live/jobs/{job_id}/complete
POST /api/live/resolve-roll
POST /api/live/rebuild-packet
GET  /openapi.json       # FastAPI built-in, path coverage tested
```

This PR should make L4 boring: the future React shell should be able to load catalog/layout, persist layout changes, mark jobs complete, debug roll resolution, request a packet rebuild job, and rely on OpenAPI path coverage without reading repo files directly.

---

## §2 Why This Slice

L3-min proved persistence + HTTP around `handle_live_turn`. It did not complete the server contract promised by the Phase L3 checklist.

PR76 finishes that contract without starting UI work. This keeps the product boundary clean:

```text
L2: local live-turn logic
L3-min: query/state/events/jobs HTTP spine
L3-rest: surface/layout/job-control/roll-debug/rebuild-stub/OpenAPI
L4: React modular surface shell
```

The core principle remains: **server mediates authority; browser is not source of truth.**

---

## §3 Files In Scope (Allowlist)

The worker's expected diff must be expressible from this table.

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live_control_server/routes/live.py` | Add L3-rest routes. |
| Modify | `apps/live_control_server/session_store.py` | Add layout read/write, job completion, rebuild job append helpers as needed. |
| Modify | `apps/live_control_server/schema_validation.py` | Add layout schema validation helper if useful. |
| Modify | `apps/live_control_server/main.py` | Update app metadata/OpenAPI description for full L3 endpoint surface. |
| Modify if useful | `apps/live_control_server/services/live_agent_loop.py` | Add thin service functions only if route handlers would otherwise grow. |
| Create if useful | `apps/live_control_server/services/surface_service.py` | Optional surface/layout service if this keeps route code small. |
| Create if useful | `apps/live_control_server/services/job_queue.py` | Optional job queue service if this keeps rewrite/complete behavior isolated. |
| Modify | `tests/test_live_control_server.py` | Add L3-rest endpoint tests. |
| Create | `Docs/Plans/HANDOFF-pr76-c2-l3-rest-server-contract.md` | This handoff; keep on the implementation branch. |

Do not create a React app or UI package in this PR. Do not add more layers than needed; the server is still small.

---

## §4 Files Explicitly Out Of Scope (Denylist)

Do not touch any of these.

| Path | Why this PR must not touch it |
|---|---|
| `apps/live-control-ui/**` | React UI belongs to L4. |
| `apps/live_control_ui/**` | React UI belongs to L4. |
| `src/live_play/classify_live_turn.py` | L2 classifier is accepted; do not change it for server convenience. |
| `src/live_play/live_turn.py` | L2 live-turn handler is accepted; do not change it for server convenience. |
| `src/live_play/resolve_roll.py` | Use the resolver; do not rewrite it unless a blocker is documented. |
| `evals/c2_live_prep/live/schemas/**` | L1 schemas are accepted; do not mutate them for server convenience. |
| `evals/c2_live_prep/live/session_22/*.jsonl` | Tests must use temp session dirs only. |
| `evals/c2_live_prep/live/session_22/surface_layout.json` | Tests may copy and mutate temp layout only. |
| `corpus/**` | No corpus promotion, correction, recap, or canon writes in L3. |
| `evals/c2_live_prep/artifacts/**` | Do not rebuild retrieval/c2 smoke artifacts. |
| `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md` | Parent doc-sync owns plan updates after review/merge. |
| `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md` | Parent doc-sync owns checklist updates after review/merge. |
| `Docs/Plans/README-c2-live-control-ui.md` | UI planning README is read-only for this PR. |

If a denylisted path appears necessary, stop and report the blocker in the PR body instead of editing it.

---

## §5 Implementation Contract

### Existing L3-min behavior must remain intact

Do not regress:

- `POST /api/live/query`
- `GET /api/live/state`
- `GET /api/live/events?since=`
- `GET /api/live/jobs`
- pre-append event/job schema validation
- temp session isolation in tests
- no committed seed JSONL mutation

### `GET /api/live/surface`

Return catalog + layout + current derived state.

Required response keys:

```text
catalog
layout
state
```

Source rules:

- `catalog` comes from `live_packet.json` → `surface_catalog`.
- `layout` comes from `surface_layout.json`.
- `state` comes from `refresh_current_state(session_dir())`, not stale file trust.
- Human labels from the catalog should be preserved. File paths may appear in provenance/source fields, not as primary labels.

### `PUT /api/live/surface/layout`

Accept a full layout document matching `live_surface_layout.schema.json` and persist it to `surface_layout.json`.

Required validation:

1. Validate against `live_surface_layout.schema.json` using `Draft202012Validator.FORMAT_CHECKER`.
2. Run `validate_surface_layout_invariants(layout)` from `src/live_play/surface_layout_invariants.py`.
3. Run `validate_catalog_layout_consistency(packet, layout)` from `src/live_play/surface_layout_invariants.py`.

Behavior:

- Write valid layout atomically via `write_json` or equivalent temp-file + replace.
- Return the saved layout.
- Reject disabled required modules (`chat`, `record`) with 400 or 422.
- Reject unknown module IDs with 400 or 422.
- Optional: append a validated `surface_config_updated` event. If implemented, tests must verify it. If deferred, state that explicitly in the PR body.

### `POST /api/live/jobs/{job_id}/complete`

Mark a job complete without deleting history.

Required behavior:

- Read `job_queue.jsonl`.
- Find matching job by `id`.
- Set `status` to `complete`.
- Preserve the row and payload.
- Rewrite `job_queue.jsonl` atomically via temp-file + replace.
- Return the updated job.
- Return 404 for missing job ID.
- Do not execute job side effects.

For v0, in-place queue rewrite is acceptable. Do not implement a separate job history log unless you keep the behavior obviously simple and tested.

### `POST /api/live/resolve-roll`

Thin debug wrapper over L2 resolver.

Suggested request:

```json
{
  "command": "Weather 16"
}
```

Required behavior:

- Load packet.
- Call L2 resolver using the current repo root and packet.
- Return table ID, roll, title, row text, row locator, and provenance.
- Do not append events.
- Do not append jobs.
- Do not invoke repo-wide search.

### `POST /api/live/rebuild-packet`

Do not rebuild retrieval packets in this PR.

Preferred behavior:

- Append a `packet_rebuild` live job row to `job_queue.jsonl`.
- Validate it against `live_job.schema.json` before append.
- Return `202 Accepted` with job ID and status.

Acceptable alternate behavior:

- Return `501 Not Implemented` with a clear diagnostic.

Preferred: queue the `packet_rebuild` job, because the Queue module can display it in L4 and it exercises the same job surface.

### `/openapi.json`

FastAPI already provides OpenAPI. This PR must add tests that confirm all L3 endpoint paths exist.

Required path set:

```text
/api/live/query
/api/live/state
/api/live/events
/api/live/jobs
/api/live/jobs/{job_id}/complete
/api/live/resolve-roll
/api/live/rebuild-packet
/api/live/surface
/api/live/surface/layout
```

---

## §6 Required Test Cases

Extend `tests/test_live_control_server.py`. Continue using temp session directories through `DUNGEONMIND_LIVE_SESSION_DIR`.

Required tests:

1. `GET /api/live/surface` returns catalog + layout + state.
   - catalog includes `chat` and `record`.
   - layout includes enabled `chat` and `record` modules.
2. `PUT /api/live/surface/layout` persists a valid layout to temp `surface_layout.json`.
3. `PUT /api/live/surface/layout` rejects disabled `chat` or `record`.
4. `PUT /api/live/surface/layout` rejects an unknown module ID.
5. `POST /api/live/jobs/{job_id}/complete` marks a queued job complete and preserves the row.
6. `POST /api/live/jobs/{job_id}/complete` returns 404 for missing job ID.
7. `POST /api/live/resolve-roll` resolves `Weather 16` and does not append events/jobs.
8. `POST /api/live/rebuild-packet` queues `packet_rebuild` or returns clear 501. If queueing, assert a job row is appended and schema-valid.
9. `/openapi.json` contains all required L3 paths.
10. Existing L3-min tests still pass: query, state, events, jobs, context lookup, invalid campaign, stale-state recompute, unknown `since`, schema validation.

Also assert committed seed files remain unchanged where practical:

```text
evals/c2_live_prep/live/session_22/event_log.jsonl
evals/c2_live_prep/live/session_22/job_queue.jsonl
evals/c2_live_prep/live/session_22/surface_layout.json
```

---

## §7 Verification Commands

The worker must run every command and paste the output into the PR body. The reviewer will rerun each.

```bash
uv run pytest tests/test_live_control_server.py -q
```

```bash
uv run pytest tests/test_live_play_schemas.py tests/test_live_play_resolve_roll.py tests/test_live_play_classify_turn.py tests/test_live_play_turn_loop.py tests/test_live_control_server.py -q
```

```bash
uv run python - <<'PY'
from apps.live_control_server.main import app
paths = set(app.openapi()["paths"])
required = {
    "/api/live/query",
    "/api/live/state",
    "/api/live/events",
    "/api/live/jobs",
    "/api/live/jobs/{job_id}/complete",
    "/api/live/resolve-roll",
    "/api/live/rebuild-packet",
    "/api/live/surface",
    "/api/live/surface/layout",
}
missing = required - paths
if missing:
    raise SystemExit(f"missing OpenAPI paths: {sorted(missing)}")
print("live control L3-rest OpenAPI paths OK")
PY
```

```bash
git diff --name-only
```

```bash
git diff --stat -- \
  Docs/Plans/HANDOFF-pr76-c2-l3-rest-server-contract.md \
  apps/live_control_server/routes/live.py \
  apps/live_control_server/session_store.py \
  apps/live_control_server/schema_validation.py \
  apps/live_control_server/main.py \
  apps/live_control_server/services/live_agent_loop.py \
  apps/live_control_server/services/surface_service.py \
  apps/live_control_server/services/job_queue.py \
  tests/test_live_control_server.py
```

Manual smoke is optional, but useful:

```bash
uv run uvicorn apps.live_control_server.main:app --reload
```

Then:

```bash
curl -s http://127.0.0.1:8000/api/live/surface
```

and:

```bash
curl -s -X POST http://127.0.0.1:8000/api/live/resolve-roll \
  -H 'Content-Type: application/json' \
  -d '{"command":"Weather 16"}'
```

---

## §8 Reporting Contract

In the PR body the worker must include:

1. Verbatim output for every required §7 command.
2. Complete `git diff --name-only` output for all changed files.
3. Filtered `git diff --stat` for the §3 allowlist.
4. One paragraph confirming no React UI, no schema mutation, no corpus writes, no retrieval rebuild execution, and no committed seed JSONL/layout mutation.
5. A short explanation of `POST /api/live/rebuild-packet`: queued `packet_rebuild` vs 501 diagnostic.
6. A short explanation of whether `PUT /api/live/surface/layout` appends `surface_config_updated` or defers that audit event.

---

## §9 Acceptance Rubric

The reviewer will accept only if every bullet below is true.

- [ ] PR76 stays inside the §3 allowlist.
- [ ] No React/UI files, schema files, corpus files, retrieval artifacts, or committed seed JSON/JSONL/layout files are modified.
- [ ] Existing L3-min endpoints still pass tests.
- [ ] `GET /api/live/surface` returns catalog + layout + derived state.
- [ ] `PUT /api/live/surface/layout` validates schema + invariants and persists valid layout atomically.
- [ ] Invalid layout updates are rejected: disabled required module and unknown module ID.
- [ ] `POST /api/live/jobs/{job_id}/complete` marks job complete without deleting history and returns 404 for missing jobs.
- [ ] `POST /api/live/resolve-roll` resolves `Weather 16` without appending events/jobs.
- [ ] `POST /api/live/rebuild-packet` queues `packet_rebuild` or returns clear 501; it does not rebuild packets.
- [ ] `/openapi.json` contains all required L3 live endpoint paths.
- [ ] L1 + L2 + L3 tests pass together.

---

## §10 Out-of-Band Notes

- This is still not L4. Do not build the React shell here.
- This PR may complete Phase L3 if all checklist endpoints and tests pass. Parent doc-sync decides after review/merge.
- Keep route handlers thin. If logic grows, move it into one small service helper rather than hiding product behavior in routes.
- Do not execute queued jobs. Completion marks state; propagation/rebuild execution belongs to later work.
- The server contract should be boring enough that L4 can be mostly a client of these endpoints.

pr_body_template: |
  ## Summary
  Complete C2 L3-rest server contract: surface endpoints, layout persistence, job completion, resolve-roll wrapper, rebuild-packet stub, and OpenAPI path coverage.

  ## Verification
  Paste the verbatim output from every §7 required command here.

  ## `git diff --name-only`
  ```text
  Paste the complete changed-file list here.
  ```

  ## `git diff --stat` (§3 paths only)
  ```text
  Paste a diff stat filtered to the §3 allowlist here.
  ```

  ## Scope confirmation
  No React UI files, schema files, corpus files, retrieval artifacts, or committed seed JSONL/layout files were modified.

  ## Endpoint notes
  Explain rebuild-packet behavior and whether surface layout updates append audit events.
