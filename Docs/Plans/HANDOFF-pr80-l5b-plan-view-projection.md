---
document_id: dmb-handoff-pr80-l5b-plan-view-projection
title: PR 80 Handoff — L5B Plan View Projection
document_class: handoff
status: ready_for_implementation
version: 0.1
created_at: "2026-05-28T04:30:00Z"
related_documents:
  - path: Docs/Plans/DESIGN-c2-live-control-l5-pane-state-boundaries.md
    role: primary_design_anchor
  - path: Docs/Plans/PLAN-c2-live-control-surface-query-pane.md
    role: parent_plan
  - path: Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md
    role: execution_tracker
  - path: Docs/Plans/HANDOFF-pr79-l5a-projection-command-contracts.md
    role: prior_contract_slice
---

# PR 80 Handoff — L5B Plan View Projection

## Reanchor

PR #79 is merged. The L5A projection/command contract package now exists on `main` under:

```text
src/live_play/projections/
tests/test_live_projection_contracts.py
```

PR 80 should build the next Python-first slice: a derived Session 22 plan-view projection and a read-only FastAPI endpoint for it.

This is the first projection consumer of the L5A contracts. Keep it small, deterministic, and reviewable.

## Mission

Implement a Python plan-view read model for Session 22 and expose it over the live-control server.

The output should prove that DungeonBuddy can build a projected session timeline from known live-session state without creating a new authoritative session-plan file.

## Product Reason

The future UI timeline module needs a stable payload before React work begins. This PR gives the UI and agent layer a derived plan projection with human labels, typed refs, source references, and explicit non-authoritative status.

The PR should make this true:

```text
live packet + event log + job queue + known source refs
→ build_session_plan_projection(...)
→ plan-view payload
→ GET /api/live/plan-view
```

## Scope

Implement:

- Python plan-view projection models or dict builders.
- A deterministic `build_session_plan_projection(...)` function.
- A Session 22 sample projection payload fixture or generated fixture.
- JSON schema validation for the plan-view payload.
- `GET /api/live/plan-view` route.
- Tests for builder, schema, endpoint, and invariants.
- Checklist evidence update.

Recommended files:

```text
src/live_play/projections/plan_view.py
evals/c2_live_prep/live/schemas/plan_view.schema.json
evals/c2_live_prep/live/session_22/plan_view.sample.json
apps/live_control_server/routes/live.py
tests/test_live_plan_view_projection.py
tests/test_live_control_server.py        # only if endpoint coverage belongs here
Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md
```

You may choose a cleaner structure if the existing code points elsewhere, but keep the public contract obvious.

## Out of Scope

Do not implement:

- React timeline module.
- Universal inspector pane.
- Artifact read/write endpoints.
- Capability endpoint.
- POST `/api/live/commands`.
- Command execution.
- Retrieval service calls.
- Corpus markdown writes.
- Automatic source parsing beyond the minimal deterministic seed needed for Session 22.

This PR is read-only.

## Required Plan-View Contract

The payload must be explicitly derived and non-authoritative.

Recommended top-level shape:

```json
{
  "schema_version": "0.1.0",
  "campaign_id": "longmont-c2",
  "session": 22,
  "authoritative": false,
  "generated_at": "2026-05-28T00:00:00Z",
  "derived_from": [],
  "timeline": []
}
```

## Top-level fields

Required:

- `schema_version`
- `campaign_id`
- `session`
- `authoritative`
- `generated_at`
- `derived_from`
- `timeline`

Rules:

- `authoritative` must always be `false`.
- `timeline` must be a list.
- `derived_from` must identify source inputs at a human/debug level, not become primary UI labels.
- `generated_at` may be deterministic in tests if needed.

## Timeline row shape

Recommended row fields:

```json
{
  "id": "beat-mireward-gate-arrival",
  "label": "Mireward gate arrival",
  "status": "projected",
  "time_hint": "Day 2, ~22:00",
  "summary": "Party reaches the gate apron after forced march.",
  "table_ready_prompt": "What does the party see first?",
  "refs": [],
  "state_links": {
    "event_ids": [],
    "job_ids": [],
    "open_loop_ids": []
  }
}
```

Suggested timeline statuses:

```text
projected
active
played
skipped
blocked
unknown
```

Keep status vocabulary small and provisional. Do not build a live reconciliation workflow around it yet.

## Ref shape

Timeline refs should be compatible with L5A `ProjectionTarget` vocabulary.

Recommended ref fields:

```json
{
  "target_type": "roll_table",
  "target_id": "T-DIL-G",
  "label": "Gate dilemma table",
  "source_status": "derived",
  "role": "next_roll"
}
```

Allowed `target_type` values should match `ProjectionTargetType` from `src/live_play/projections/targets.py`.

Examples:

```text
roll_table
npc
location
runbook_section
open_loop
job
event
```

## Session 22 Seed Content

The sample projection should be small but product-shaped. Aim for 5–8 rows, enough to prove the UI contract without pretending the projection engine is complete.

Suggested rows:

- Pre-travel Silver Raven dispatch.
- Travel Day 1 weather/front beat.
- Delayed-reflection puddle / Identify beat.
- Hester Mull courier encounter.
- Grobnok callback / no-call open loop.
- Day 2 forced march to Mireward outskirts.
- Mireward gate arrival / Lysandro reveal.
- Gate dilemma next roll (T-DIL-G).

Rows should include human labels and typed refs to likely constituents:

- `roll_table:T-WX`
- `roll_table:R5`
- `roll_table:T-DIL-G`
- `npc:Lysandra` or stable slug if available
- `npc:Lysandro Ironveil` or stable slug if available
- `location:Mireward Gate` or stable slug if available
- `open_loop:grobnok-evening-contact`
- event refs only where existing event IDs are stable in fixture data

Do not invent a huge canon graph. If stable IDs are not available, use clear provisional target IDs and document that they are projection IDs, not canon IDs.

## Builder Behavior

Implement `build_session_plan_projection(...)` as a deterministic read model.

Possible signature:

```python
def build_session_plan_projection(
    packet: dict[str, Any],
    events: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]: ...
```

Acceptable v1 behavior:

- Read campaign/session from the live packet.
- Include derived source refs from packet source paths if present.
- Generate a small Session 22 timeline using deterministic known beats.
- Link runtime state where obvious: event IDs, job IDs, open loop IDs.
- Return `authoritative=false`.

Do not over-engineer source parsing. The builder can be partly seeded/manual for Session 22 in this PR, as long as the output contract is stable and clearly marked derived.

## Schema Requirements

Add `plan_view.schema.json` and validate:

- top-level required fields
- `authoritative` is `false`
- timeline rows have `id`, `label`, `status`, `summary`, `refs`, `state_links`
- refs have `target_type`, `target_id`, `label`
- state link lists default to arrays

Use existing schema/test patterns in the repo where possible.

## Endpoint Requirements

Add:

`GET /api/live/plan-view`

Behavior:

- Load active session via existing live-control server session loading.
- Build plan projection from packet/events/jobs.
- Return JSON payload.
- Do not mutate files.
- Do not append events or jobs.
- Do not invoke retrieval.

Endpoint test should verify that event/job counts do not change if the test harness makes that easy.

## Tests

Minimum tests:

1. Builder returns `authoritative` is `False`.
2. Builder uses packet campaign/session.
3. Builder returns non-empty timeline for Session 22.
4. Timeline rows have human labels and typed refs.
5. All refs use allowed `ProjectionTargetType` values.
6. Payload validates against `plan_view.schema.json`.
7. `GET /api/live/plan-view` returns valid payload.
8. Endpoint is read-only: no event/job append.
9. Sample fixture validates against schema.
10. Existing live-control server tests still pass.

Suggested commands:

```bash
uv run pytest tests/test_live_plan_view_projection.py -q
uv run pytest tests/test_live_control_server.py -q
```

Optional broader cohort:

```bash
uv run pytest tests/test_live_projection_contracts.py tests/test_live_plan_view_projection.py tests/test_live_control_server.py -q
```

## Nano-Commit Plan

Keep scrutiny high. Recommended commits:

1. docs: add PR80 L5B handoff
2. schema: add plan_view schema and sample Session 22 payload
3. feat: add plan_view projection builder
4. api: expose read-only GET /api/live/plan-view
5. test: cover builder, schema, endpoint, and read-only behavior
6. docs: update checklist evidence and next gate

Do not collapse implementation into one giant commit.

## PR Body Template

```text
## Summary

- Adds derived Session 22 plan-view projection builder.
- Adds plan-view schema + sample payload.
- Adds read-only `GET /api/live/plan-view` endpoint.
- Adds tests for non-authoritative invariant, typed refs, schema validation, and endpoint read-only behavior.

## Verification

- [ ] `uv run pytest tests/test_live_plan_view_projection.py -q`
- [ ] `uv run pytest tests/test_live_control_server.py -q`

## Out of scope

- React timeline module
- inspector pane
- artifact read/write endpoints
- command bus execution
- retrieval integration
- corpus writes
```

## Review Rubric

Reviewer should check:

- Is the projection explicitly non-authoritative?
- Does the endpoint avoid all writes?
- Are labels human-facing rather than path-first?
- Are refs typed and compatible with L5A target vocabulary?
- Is the sample projection small and honest, not pretending full automation?
- Does the builder avoid retrieval/corpus write side effects?
- Are tests proving schema + endpoint + read-only invariants?

## Design Warning

The timeline is orientation, not task management.

Do not create mandatory beat reconciliation, beat completion workflows, or timeline authoring in this PR. The projection may include statuses like `projected` or `played`, but they should be passive read-model state only.
