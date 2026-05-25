# HANDOFF — PR 75: C2 Live Control Surface L3 FastAPI Query Loop

**Created:** 2026-05-25 (UTC).  
**Status:** ACTIVE — dispatch this to one fresh external/Codex agent. One PR. Do not split into multiple PRs.  
**Parent agent:** Cursor agent; parent owns review, merge, and atomic doc-sync after the PR lands.  
**Plan anchor:** `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md` (`execution_state.active_slice: L3_fastapi_query_loop`).  
**Checklist anchor:** `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md` Phase L3.  
**Substrate anchors:** PR #72 L1 file-backed substrate; PR #74 L2 `handle_live_turn`.

---

## §0 Re-anchor Before Writing

This handoff assumes PR #74 is merged on `main` and L2 is complete. Do not infer current state from chat history.

Read in this order:

1. `.cursor/rules/external-agent-pr-loop.mdc` — mandatory allowlist / denylist / verification contract.
2. `.cursor/rules/anchor.mdc` — re-anchor discipline for fresh agents.
3. `AGENTS.md` — repo operating policy, UV usage, RTK preference, git verification, and external-agent PR loop conventions.
4. `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md` — confirm `execution_state.active_slice: L3_fastapi_query_loop`.
5. `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md` — Phase L3 is authoritative for endpoints and tests.
6. `Docs/Plans/STUDY-c2-live-play-cursor-handoff-process.md` — reread the live/slow boundary and UI guardrails.
7. `Docs/Plans/archive/2026-05-25/handoffs/HANDOFF-pr72-c2-live-packet-event-job-schema.md` — L1 substrate contract.
8. `Docs/Plans/archive/2026-05-25/handoffs/HANDOFF-pr74-c2-l2-roll-resolver-classifier.md` — L2 logic contract.
9. `Docs/Plans/README-c2-live-control-ui.md` — client-facing expectations for the future UI.
10. Current L1/L2 files:
    - `src/live_play/live_store.py`
    - `src/live_play/current_state_derive.py`
    - `src/live_play/surface_layout_invariants.py`
    - `src/live_play/live_turn.py`
    - `evals/c2_live_prep/live/session_22/live_packet.json`
    - `evals/c2_live_prep/live/session_22/surface_layout.json`
    - `evals/c2_live_prep/live/session_22/event_log.jsonl`
    - `evals/c2_live_prep/live/session_22/job_queue.jsonl`
    - `evals/c2_live_prep/live/session_22/current_state.json`

Current-state hypothesis to carry into the PR:

- L1 substrate is complete and merged.
- L2 roll resolver/classifier/turn handler is complete and merged.
- L3 has not started.
- This PR creates a local FastAPI server wrapper and tests only.
- React UI, corpus writes, retrieval rebuilds, recap writes, and post-session propagation execution are later slices.

---

## §1 Mission

Implement the L3 local FastAPI query loop for Session 22:

1. Load the Session 22 live packet, surface layout, current state, event log, and job queue from the L1 file-backed substrate.
2. Expose `POST /api/live/query` that calls `handle_live_turn(packet, text)` from L2.
3. Append returned events to `event_log.jsonl` and returned jobs to `job_queue.jsonl`.
4. Expose state, events, jobs, and surface endpoints needed by L4.
5. Validate and persist surface layout updates through the accepted schema + invariant helpers.
6. Publish OpenAPI through FastAPI's native `/openapi.json`.
7. Add focused server tests and one curl-smoke-equivalent test for `Weather 7. Caelynn Nature 19.`.

This PR should make L4 boring: the future React UI should call a stable local API rather than read repo files directly.

---

## §2 Important Path Decision

The checklist uses placeholder paths like `apps/live-control-server/` and the command `uvicorn apps.live-control-server.main:app --reload`. A hyphenated package is not a valid Python import target.

Use the importable package path instead:

```text
apps/live_control_server/
```

The verification command should be:

```bash
uv run uvicorn apps.live_control_server.main:app --reload
```

Do not create `apps/live-control-server/`.

---

## §3 Files In Scope (Allowlist)

The worker's expected diff must be expressible from this table.

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/__init__.py` | Package marker if needed for imports. |
| Create | `apps/live_control_server/__init__.py` | Server package marker. |
| Create | `apps/live_control_server/main.py` | FastAPI app factory / app instance. |
| Create | `apps/live_control_server/routes/__init__.py` | Routes package marker. |
| Create | `apps/live_control_server/routes/live.py` | Live API endpoint definitions. |
| Create | `apps/live_control_server/services/__init__.py` | Services package marker. |
| Create | `apps/live_control_server/services/live_agent_loop.py` | File-backed service layer wrapping L1/L2 helpers. |
| Create if useful | `apps/live_control_server/models.py` | Pydantic request/response models, if not kept inside route/service files. |
| Modify | `pyproject.toml` | Add minimal FastAPI/TestClient/Uvicorn dependencies only if absent. Current `pyproject.toml` does not list FastAPI/Uvicorn. |
| Modify if dependency resolution requires | `uv.lock` | Lockfile update if dependency changes are made through `uv`. |
| Create | `tests/test_live_control_server.py` | FastAPI endpoint tests using temp session files. |
| Create | `Docs/Plans/HANDOFF-pr75-c2-l3-fastapi-query-loop.md` | This handoff; keep on the implementation branch. |

Do not add a React app or UI package in this PR.

---

## §4 Files Explicitly Out Of Scope (Denylist)

Do not touch any of these.

| Path | Why this PR must not touch it |
|---|---|
| `apps/live-control-server/**` | Hyphenated placeholder path; use `apps/live_control_server/**` instead. |
| `apps/live-control-ui/**` | React UI belongs to L4. |
| `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md` | Parent doc-sync owns plan updates after review/merge. |
| `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md` | Parent doc-sync owns checklist updates after review/merge. |
| `Docs/Plans/STUDY-c2-live-play-cursor-handoff-process.md` | Product-friction study is read-only. |
| `Docs/Plans/README-c2-live-control-ui.md` | UI planning README is read-only for L3. |
| `evals/c2_live_prep/live/schemas/**` | L1 schemas are accepted; do not mutate them for server convenience. |
| `evals/c2_live_prep/live/session_22/live_packet.json` | Seed packet is input; do not rewrite it. |
| `evals/c2_live_prep/live/session_22/surface_layout.json` | Server code may write temp copies in tests, but must not mutate the committed seed layout during tests. |
| `evals/c2_live_prep/live/session_22/event_log.jsonl` | Server tests must use temp copies; do not append to committed seed logs. |
| `evals/c2_live_prep/live/session_22/job_queue.jsonl` | Server tests must use temp copies; do not append to committed seed queue. |
| `corpus/**` | No corpus promotion, correction, or recap writes in L3. |
| `evals/c2_live_prep/artifacts/**` | Existing smoke artifacts are inputs/evidence, not regenerated outputs. |
| `evals/sentence_routing_retrieval_falsification/**` | Sibling retrieval/autonomy workstream. |

If a denylisted path appears necessary, stop and report the blocker in the PR body instead of editing it.

---

## §5 Implementation Contract

### Server construction

Prefer an app factory so tests can inject temp paths:

```python
def create_app(config: LiveServerConfig | None = None) -> FastAPI: ...

app = create_app()
```

Suggested config:

```python
@dataclass(frozen=True)
class LiveServerConfig:
    root: Path
    session_dir: Path
    schema_dir: Path
    campaign_id: str = "longmont-c2"
    session: int = 22
```

Default paths should point at the accepted L1 Session 22 substrate under `evals/c2_live_prep/live/session_22/`.

Tests must construct temp session directories by copying seed files, then call `create_app(temp_config)`. Do not let tests append to committed seed JSONL files.

### File persistence rules

- Use `src/live_play.live_store.load_json`, `iter_jsonl`, `append_jsonl`, and `write_json` where they fit.
- For local single-user use, `append_jsonl` is acceptable for event/job append.
- Surface layout writes must use `write_json` or equivalent temp-file + replace.
- `POST /api/live/jobs/{id}/complete` may rewrite `job_queue.jsonl` through temp-file + replace, but must not delete the job row. The simplest acceptable behavior is: read rows, update the matching row's `status` to `complete`, and rewrite the queue atomically.
- If the implementation wants append-only job history instead, it must clearly document and test how `GET /api/live/jobs` chooses the latest status per job ID.

### Validation rules

- Validate events returned by `handle_live_turn` against `live_event.schema.json` before appending.
- Validate jobs returned by `handle_live_turn` against `live_job.schema.json` before appending.
- Validate `PUT /api/live/surface/layout` against `live_surface_layout.schema.json` with `Draft202012Validator.FORMAT_CHECKER`.
- Run `validate_surface_layout_invariants(layout)` and `validate_catalog_layout_consistency(packet, layout)` before writing the layout.
- Reject invalid layout updates with HTTP 422 or 400. Prefer FastAPI/Pydantic 422 for request-shape errors and 400 for domain invariant failures.

### Endpoint contract

Implement these endpoints in this PR.

#### `POST /api/live/query`

Request body:

```json
{
  "campaign_id": "longmont-c2",
  "session": 22,
  "mode": "live",
  "text": "Weather 7. Caelynn Nature 19."
}
```

Required behavior:

- Reject wrong campaign/session with 404 or 400.
- Call `handle_live_turn(packet, text, root=config.root)`.
- Append every returned event to `event_log.jsonl`.
- Append every returned job to `job_queue.jsonl`.
- Return answer, classification, events, jobs, next suggestions, diagnostics, and provenance.
- Refresh/return derived state or enough metadata for the UI to refresh state/events/jobs.

The response shape may be Pydantic-defined, but tests must assert stable keys:

```text
answer
classification
events_written
jobs_queued
next_suggestions
diagnostics
provenance
```

`classification` should include at least `latency_mode`, `event_type`, `intent`, `table_id`, and `roll` where present.

#### `GET /api/live/state`

Required behavior:

- Load packet, layout, event log, and job queue.
- Return derived current state from `derive_current_state_fields(packet, layout, events, jobs)` plus explicit metadata that it is derived.
- Do not trust stale `current_state.json` over recomputation.
- It is acceptable to include the committed `current_state.json` metadata, but computed fields must come from current files.

#### `GET /api/live/events`

Required behavior:

- Return JSONL events from `event_log.jsonl`.
- Support `?since=` for the Record module.
- Define `since` as event ID cursor for v0 unless a timestamp cursor is easier; document it in code/test names.
- Return recent events in stable append order.

#### `GET /api/live/jobs`

Required behavior:

- Return jobs from `job_queue.jsonl`.
- Support optional status filter if cheap, but not required.
- Preserve queued/completed rows; do not delete jobs when completing them.

#### `POST /api/live/jobs/{id}/complete`

Required behavior:

- Mark a queued job complete.
- Return the updated job row.
- Return 404 for missing job ID.
- Do not execute the job's side effects.

#### `GET /api/live/surface`

Required behavior:

- Return `surface_catalog` from `live_packet.json` and the current `surface_layout.json`.
- Return enough state for L4 to render Chat/Record and optional modules.
- Do not expose file paths as primary labels; paths may appear in provenance/source fields.

#### `PUT /api/live/surface/layout`

Required behavior:

- Accept a full layout document matching `live_surface_layout.schema.json`.
- Validate schema and invariants.
- Write `surface_layout.json` atomically.
- Optionally append a `surface_config_updated` event to `event_log.jsonl`; if you do, validate it against `live_event.schema.json`.
- Return the saved layout.

#### `POST /api/live/resolve-roll`

Required behavior:

- Thin HTTP wrapper over the L2 resolver for direct testing/debugging.
- It must not append events or jobs.
- It must not invoke repo-wide search.

#### `POST /api/live/rebuild-packet`

Do not rebuild retrieval packets in L3. Implement one of these two safe behaviors:

1. Return `202 Accepted` and append/return a `packet_rebuild` job row; or
2. Return `501 Not Implemented` with a clear diagnostic.

Preference: `202 Accepted` that queues a `packet_rebuild` job, because the endpoint then participates in the same queue surface L4 will show. Do not actually rebuild packets.

### OpenAPI

FastAPI's built-in `/openapi.json` is enough for L3 if it includes the live endpoints and request/response schemas. Add a test that `/openapi.json` contains `/api/live/query` and `/api/live/surface`.

---

## §6 Required Test Cases

Create `tests/test_live_control_server.py`.

Tests must use temp copies of Session 22 live files. Suggested fixture:

1. Copy `evals/c2_live_prep/live/session_22/*.json` and `*.jsonl` into `tmp_path / "session_22"`.
2. Build `LiveServerConfig(root=ROOT, session_dir=temp_session, schema_dir=ROOT / "evals/c2_live_prep/live/schemas")`.
3. Create `TestClient(create_app(config))`.

Required tests:

- `POST /api/live/query` with `Weather 7. Caelynn Nature 19.` returns `fast_live` / `roll_result`, answer contains `Hail dent`, appends one event, appends at least one job, and persisted rows validate against L1 schemas.
- Query endpoint does not mutate committed `evals/c2_live_prep/live/session_22/event_log.jsonl` or `job_queue.jsonl`.
- `GET /api/live/events` returns appended events; `?since=<event_id>` returns events after that ID.
- `GET /api/live/jobs` returns appended queued jobs.
- `POST /api/live/jobs/{id}/complete` marks a job complete and does not delete it.
- `GET /api/live/state` recomputes derived state from temp event/job files and shows changed event/job counts after a query.
- `GET /api/live/surface` returns `catalog` and `layout`, with required `chat` and `record` present/enabled.
- `PUT /api/live/surface/layout` persists a valid layout and rejects a layout that disables `chat` or includes an unknown module ID.
- `POST /api/live/resolve-roll` resolves `Weather 16` without appending events/jobs.
- `POST /api/live/rebuild-packet` queues `packet_rebuild` or returns clear 501; test whichever behavior is implemented.
- `/openapi.json` includes `/api/live/query` and `/api/live/surface`.

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
print("live control OpenAPI paths OK")
PY
```

```bash
git diff --name-only
```

```bash
git diff --stat -- \
  Docs/Plans/HANDOFF-pr75-c2-l3-fastapi-query-loop.md \
  apps/__init__.py \
  apps/live_control_server/__init__.py \
  apps/live_control_server/main.py \
  apps/live_control_server/routes/__init__.py \
  apps/live_control_server/routes/live.py \
  apps/live_control_server/services/__init__.py \
  apps/live_control_server/services/live_agent_loop.py \
  apps/live_control_server/models.py \
  pyproject.toml \
  uv.lock \
  tests/test_live_control_server.py
```

Optional manual smoke after tests pass:

```bash
uv run uvicorn apps.live_control_server.main:app --reload
```

Then in another shell:

```bash
curl -s -X POST http://127.0.0.1:8000/api/live/query \
  -H 'Content-Type: application/json' \
  -d '{"campaign_id":"longmont-c2","session":22,"mode":"live","text":"Weather 7. Caelynn Nature 19."}'
```

Do not paste huge JSON into the PR body. Paste the command and a short excerpt showing `fast_live`, `roll_result`, and `Hail dent` if manual smoke is run.

---

## §8 Reporting Contract

In the PR body the worker must include:

1. Verbatim output for every required §7 command.
2. Complete `git diff --name-only` output for all changed files.
3. Filtered `git diff --stat` for the §3 allowlist.
4. One paragraph confirming no React UI, no schema mutation, no corpus writes, no retrieval rebuild execution, and no committed seed JSONL mutation.
5. A dependency note: whether FastAPI/Uvicorn were added to `pyproject.toml`/`uv.lock`, or which existing dependency made that unnecessary.
6. A short explanation of `POST /api/live/rebuild-packet`: queued `packet_rebuild` vs 501 diagnostic.
7. A short explanation of the `GET /api/live/events?since=` cursor semantics.

---

## §9 Acceptance Rubric

The reviewer will accept only if every bullet below is true.

- [ ] L3 files stay inside the §3 allowlist.
- [ ] No React/UI files, schema files, corpus files, retrieval artifacts, or committed seed JSON/JSONL files are modified.
- [ ] `POST /api/live/query` wraps `handle_live_turn`, appends returned events/jobs, and returns stable response keys.
- [ ] Weather curl-smoke equivalent returns `fast_live`, `roll_result`, and `Hail dent`.
- [ ] Persisted event rows validate against `live_event.schema.json`.
- [ ] Persisted job rows validate against `live_job.schema.json`.
- [ ] `GET /api/live/state` returns recomputed derived state, not stale committed `current_state.json` as authority.
- [ ] `GET /api/live/events?since=` supports Record-module tailing.
- [ ] `GET /api/live/jobs` returns queued/completed jobs without deleting history.
- [ ] `POST /api/live/jobs/{id}/complete` marks a job complete and returns 404 for missing jobs.
- [ ] `GET /api/live/surface` returns catalog + layout.
- [ ] `PUT /api/live/surface/layout` validates schema and invariants, persists valid layout, and rejects disabled required modules / unknown module IDs.
- [ ] `POST /api/live/resolve-roll` resolves a roll without appending event/job rows.
- [ ] `POST /api/live/rebuild-packet` does not actually rebuild packets; it queues a job or returns a clear not-implemented diagnostic.
- [ ] `/openapi.json` contains all L3 live endpoints.
- [ ] L1 + L2 + L3 tests pass together.

---

## §10 Out-of-Band Notes

- This is the first web transport slice. Keep it thin. Product logic belongs in `src/live_play`, not hidden inside route handlers.
- This is not a UI PR. The React shell lands in L4.
- This is not a retrieval PR. `context_lookup` may be returned/recorded, but source lookup/retrieval can remain a later implementation.
- This is not a corpus/canon write PR. Jobs describe future work; they do not execute corpus edits.
- Keep response shapes boring and stable. The UI should not need to reverse-engineer route behavior.

pr_body_template: |
  ## Summary
  Implement C2 L3 FastAPI live query loop: wrap `handle_live_turn`, append returned events/jobs, expose state/events/jobs/surface endpoints, and publish OpenAPI.

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
  No React UI files, schema files, corpus files, retrieval artifacts, or committed seed JSONL logs were modified.

  ## Dependency note
  State whether FastAPI/Uvicorn were added or already available.

  ## Endpoint notes
  Explain rebuild-packet behavior and events `since` cursor semantics.
