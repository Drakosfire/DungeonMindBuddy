# HANDOFF — PR 75: C2 Live Control Surface L3-min FastAPI Query Loop

**Created:** 2026-05-25 (UTC).  
**Status:** ACTIVE — L3-min spine only; **does not complete** full CHECKLIST Phase L3.  
**Parent agent:** Cursor agent; parent owns review, merge, and atomic doc-sync after the PR lands.  
**Plan anchor:** `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md` (`execution_state.active_slice: L3_fastapi_query_loop` remains `not_started` for full L3 until L3-rest lands).  
**Checklist anchor:** `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md` — this PR satisfies the L3-min spine subset only.  
**Substrate anchor:** PR #72 L1 merged; PR #74 L2 `handle_live_turn` merged on `main`.  
**Follow-on:** L3-rest (PR #76 or next) — `GET/PUT /api/live/surface`, job complete, resolve-roll, rebuild-packet stub, OpenAPI path tests.

---

## §0 Re-anchor Before Writing

Read in this order:

1. `.cursor/rules/external-agent-pr-loop.mdc`
2. `Docs/Plans/archive/2026-05-25/handoffs/HANDOFF-pr74-c2-l2-roll-resolver-classifier.md` — **L3 integration contract** (dual job channel, seed examples, purity).
3. `src/live_play/live_turn.py` — `handle_live_turn`, `LiveTurnResult`.
4. `src/live_play/live_store.py` — `load_json`, `write_json`, `append_jsonl`, `iter_jsonl`.
5. `src/live_play/current_state_derive.py`
6. `evals/c2_live_prep/live/session_22/` — seed paths (tests must not append to committed seeds).

**L3-min hypothesis:** L2 is complete. This PR is a thin HTTP adapter only — no re-classification, no retrieval, no UI.

---

## §1 Mission

Expose the L2 live turn loop over a local FastAPI server (**L3-min spine**):

1. `POST /api/live/query` — load packet, call `handle_live_turn`, append **all** `events_to_write` and **all** top-level `jobs_to_queue` rows, refresh `current_state.json`, return JSON for Chat.
2. `GET /api/live/state` — return derived current state from session files.
3. `GET /api/live/events` — optional `?since=<event_id>` tail for Record.
4. `GET /api/live/jobs` — list queued jobs from `job_queue.jsonl`.
5. `GET /api/live/state` — **always** recomputes via `refresh_current_state` (never serves stale `current_state.json` as authoritative).
6. Pre-append validation of event/job rows against L1 schemas before JSONL append.

**Explicitly deferred to L3-rest:** `GET/PUT /api/live/surface`, `POST /api/live/jobs/{id}/complete`, `POST /api/live/resolve-roll`, `POST /api/live/rebuild-packet`, OpenAPI export tests.

Make L4 boring: UI talks HTTP only; never reads `session_22/*.jsonl` directly.

---

## §2 Why This Slice

L2 proved classify → resolve → structured events/jobs in-process. L3-min proves **persistence + HTTP boundary** before optional endpoints (surface PUT, job complete, resolve-roll, OpenAPI polish, UI).

**In scope:** wrap L2; append JSONL; derive state; pytest + curl smoke path.

**Out of scope (L3-rest / L4):** React UI, `PUT /api/live/surface/layout`, `POST /api/live/jobs/{id}/complete`, `rebuild-packet`, `context_lookup` retrieval execution, corpus writes, L2 logic changes.

---

## §3 Files In Scope (Allowlist)

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/__init__.py` | Package marker. |
| Create | `apps/live_control_server/config.py` | Repo root + `DUNGEONMIND_LIVE_SESSION_DIR` session path. |
| Create | `apps/live_control_server/session_store.py` | Load session files, append events/jobs, rebuild `current_state.json`. |
| Create | `apps/live_control_server/schema_validation.py` | Validate `live_event` / `live_job` rows before JSONL append. |
| Create | `apps/live_control_server/services/live_agent_loop.py` | `process_live_query(text)` orchestration. |
| Create | `apps/live_control_server/routes/live.py` | FastAPI routes under `/api/live`. |
| Create | `apps/live_control_server/main.py` | `create_app()` factory + `app` for uvicorn. |
| Modify | `pyproject.toml` | Add `fastapi`, `httpx`, `uvicorn` dependencies. |
| Create | `tests/test_live_control_server.py` | HTTP boundary tests (isolated temp session dir). |

Python import path: `apps.live_control_server.main:app` (underscore package; hyphens invalid in module names).

---

## §4 Files Explicitly Out Of Scope (Denylist)

| Path | Why |
|---|---|
| `apps/live-control-ui/**` | L4 |
| `src/live_play/*.py` (except import) | L2 frozen unless blocking bug with HANDOFF justification |
| `evals/c2_live_prep/live/schemas/**` | L1 accepted |
| `evals/c2_live_prep/live/session_22/*.jsonl` | Tests use temp session dirs only |
| `corpus/**` | No writes |
| `Docs/Plans/PLAN-*.md`, `CHECKLIST-*.md` | Parent doc-sync after merge |

---

## §5 Implementation Contract

### Session directory layout

Default: `<repo>/evals/c2_live_prep/live/session_22/`. Override: env `DUNGEONMIND_LIVE_SESSION_DIR`.

Files: `live_packet.json`, `surface_layout.json`, `event_log.jsonl`, `job_queue.jsonl`, `current_state.json`.

### `POST /api/live/query`

Request body (JSON):

```json
{
  "campaign_id": "longmont-c2",
  "session": 22,
  "mode": "live",
  "text": "Weather 7. Caelynn Nature 19."
}
```

Must validate `campaign_id` and `session` match loaded packet or return 400.

Flow:

1. `result = handle_live_turn(packet, text, root=repo_root, created_at=utc_z, event_id_factory=uuid-based)`
2. `append_jsonl(event_log, event)` for each `result.events_to_write`
3. `append_jsonl(job_queue, job)` for each `result.jobs_to_queue` — **full `live_job` rows**, not only embedded event proposals
4. Rebuild and `write_json(current_state.json, …)` using `derive_current_state_fields`
5. Return response including `answer`, `classification` (dict), `events_written` (ids), `jobs_queued` (ids), `next_suggestions`, `diagnostics`, `provenance`

### `GET /api/live/state`

Return `current_state.json` contents (reload from disk after query).

### `GET /api/live/events?since=<id>`

Return events after `since` id (exclusive), or all events if omitted.

### `GET /api/live/jobs`

Return all job rows from `job_queue.jsonl`.

### L2 contract (non-negotiable)

- Do not re-implement classify/resolve in routes.
- `context_lookup` stays stubbed via L2 (no retrieval).
- Do not execute queued jobs inline.

---

## §6 Required Test Cases

`tests/test_live_control_server.py` must use a **temporary session directory** (copy packet + layout from seeds; empty JSONL).

- `POST /api/live/query` with `Weather 7. Caelynn Nature 19.` → 200, `answer` contains `Hail dent`, `events_written` length ≥ 1, `jobs_queued` length ≥ 1.
- After query, temp `event_log.jsonl` has one more line; temp `job_queue.jsonl` has benchmark job.
- Committed `evals/c2_live_prep/live/session_22/event_log.jsonl` byte-unchanged when tests run (env points at temp dir).
- `GET /api/live/state` returns `derived: true` and `recent_event_count` ≥ 1 after query.
- `GET /api/live/events` returns the written roll_result event.
- `What is Lysandra feeling at the gate?` → 200, no roll resolution in answer (`Hail dent` absent).
- Invalid `campaign_id` → 400.

Validate appended event/job rows against schemas where practical (reuse Draft202012Validator pattern from L2 tests).

---

## §7 Verification Commands

```bash
uv run pytest tests/test_live_control_server.py -q
uv run pytest tests/test_live_play_schemas.py tests/test_live_play_resolve_roll.py tests/test_live_play_classify_turn.py tests/test_live_play_turn_loop.py tests/test_live_control_server.py -q
git diff --name-only
git diff --stat -- apps/live_control_server/ tests/test_live_control_server.py pyproject.toml
```

Curl smoke (manual, optional in PR body):

```bash
uv run uvicorn apps.live_control_server.main:app --reload
curl -s -X POST http://127.0.0.1:8000/api/live/query \
  -H 'Content-Type: application/json' \
  -d '{"campaign_id":"longmont-c2","session":22,"mode":"live","text":"Weather 7. Caelynn Nature 19."}'
```

---

## §8 Reporting Contract

1. Verbatim §7 pytest output.
2. Complete `git diff --name-only`.
3. Filtered `git diff --stat` for §3 allowlist.
4. Confirm: no UI, no corpus/schema/seed JSONL mutation, no L2 behavior duplication in routes.
5. Confirm both `events_to_write` and top-level `jobs_to_queue` are appended.

---

## §9 Acceptance Rubric

- [ ] Allowlist-only diff.
- [ ] `POST /api/live/query` calls `handle_live_turn` and appends events **and** top-level jobs.
- [ ] `GET /api/live/state` and `GET /api/live/events` work after a query.
- [ ] Tests use isolated session dir; committed seed JSONL unchanged.
- [ ] L1+L2 regression still passes with new server tests.
- [ ] Session 22 curl smoke example returns weather answer (manual or documented).

---

## §10 Out-of-Band Notes

- Package dir is `apps/live_control_server/` (underscore) even though PLAN prose says `live-control-server`.
- L3-rest adds surface PUT, job complete, OpenAPI export — not this PR.
- Re-read HANDOFF-pr74 §5 jobs: embedded event proposals ≠ substitute for `result.jobs_to_queue`.

pr_body_template: |
  ## Summary
  L3-min FastAPI adapter: POST /api/live/query wraps handle_live_turn and persists events/jobs; GET state/events/jobs.

  ## Verification
  Paste §7 pytest output here.

  ## Scope confirmation
  No UI, corpus writes, schema edits, or committed seed JSONL mutation.
