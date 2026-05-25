---
pr_body_template: |
  ## Summary
  Add the file-backed live-play packet, event, and job substrate for the C2 Live Control Surface v0 Query Pane.

  ## Verification
  Paste the verbatim output from every §7 command here.

  ## `git diff --stat` (§4 paths only)
  ```text
  Paste a diff stat filtered to the §4 allowlist here.
  ```
---

# HANDOFF — PR 71: C2 Live Control Surface L1 Packet + Event/Job Schema

**Created:** 2026-05-25 (UTC).
**Status:** ACTIVE — dispatch this to one fresh external/Codex agent. One PR. Do not split into multiple PRs.
**Parent agent:** Cursor agent; dispatcher owns review, merge, and atomic doc-sync after the PR lands.
**Plan anchor:** `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md` (`execution_state.active_slice: L1_packet_event_job_schema`).
**Checklist anchor:** `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md` Phase L1.

---

## §0 Re-anchor Before Writing

This handoff is downstream of a workstream/session re-anchor. The worker should not infer current state from chat history.

Read in this order:

1. `.cursor/rules/external-agent-pr-loop.mdc` — mandatory §4 allowlist / §5 denylist / §7 verification contract.
2. `.cursor/rules/anchor.mdc` — re-anchor discipline for fresh agents.
3. `AGENTS.md` — repo operating policy, especially UV usage, RTK preference, git verification, and external-agent PR loop conventions.
4. `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md` — Reanchor Block + Phase L1.
5. `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md` — the whole plan, especially Product Shape, Minimal Architecture, Live Turn Loop, Latency Modes, PR Slices, and Acceptance Criteria.
6. `Docs/Plans/STUDY-c2-live-play-cursor-handoff-process.md` — product-friction study; this prevents the substrate from turning into a dashboard/file-browser model.
7. `Docs/Plans/HANDOFF-s22-live-play-agent.md` — source dogfood contract for Session 22 live play, including notes discipline and roll-table lookup shape.

Current-state hypothesis to carry into the PR:

- `L0_plan_lock` is complete.
- `L1_packet_event_job_schema` is the active slice and has not started.
- This PR creates the local file-backed state substrate only.
- Server, UI, roll resolver, live classifier, recap-write, corpus propagation, and retrieval rebuild behavior are later slices.

## §1 Mission

Create the schema-validated, file-backed Session 22 live-play substrate: live packet, event log, job queue, derived current state, benchmark-candidate seed file, and focused tests for schema loading plus append behavior.

## §2 Why This Slice

- The whole sprint is `C2 Live Control Surface v0 — Query Pane`: a local GM-facing pane where text input produces a fast response, appends events, queues slower jobs, and displays background state.
- The Session 22 dogfood proved the workflow inside Cursor, but the next product step needs durable files that a server/UI can consume without making the UI source of truth.
- This L1 slice deliberately stops before the agent loop. It defines the data contract that later slices will read and write.
- This PR should make future work easier to falsify: if `current_state.json` is derived, event/job JSONL append is testable, and source/provenance fields exist from the start, later server/UI work has fewer hidden assumptions.

## §3 Authoritative Inputs

Read these before designing fields:

1. `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md` — the whole plan is authoritative for product scope and PR slicing.
2. `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md` — Phase L1 file list, checklist, and verification command.
3. `Docs/Plans/STUDY-c2-live-play-cursor-handoff-process.md` — concrete product-regression prompts and UI guardrails.
4. `Docs/Plans/HANDOFF-s22-live-play-agent.md` — Session 22 source package, notes discipline, roll-table conventions, and retrieval-vs-corpus lookup guidance.
5. `evals/c2_live_prep/artifacts/runs/2026-05-23/c2s22_smoke_report.md` — prior retrieval prep smoke artifact; use as evidence of existing packet discipline, not as schema target.
6. `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md` — seed live examples only; do not promote staging prose to canon.
7. `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Journey - Mireward Reach (Campaign 2).md` — travel clock/current-state seed.
8. `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_travel_to_mireward_runbook.md` — roll stack and travel procedure seed.
9. `schemas/v0.1/event_record.schema.json` and `schemas/v0.1/common.schema.json` — existing JSON Schema style to mirror where useful.
10. `tests/evals/test_schema_validation.py` and `scripts/lint_npc_registry.py` — local examples of schema validation patterns.

Important: the worker may read corpus files for field design and seed values, but must not rewrite corpus files in this PR.

## §4 Files In Scope (Allowlist)

The worker's expected `git diff --stat` must be expressible from this table.

| Action | Path | Purpose |
|---|---|---|
| Create | `evals/c2_live_prep/live/schemas/live_packet.schema.json` | JSON Schema for the loaded live-play packet and seed context. |
| Create | `evals/c2_live_prep/live/schemas/live_event.schema.json` | JSON Schema for one event-log JSONL row. |
| Create | `evals/c2_live_prep/live/schemas/live_job.schema.json` | JSON Schema for one job-queue JSONL row. |
| Create | `evals/c2_live_prep/live/session_22/live_packet.json` | Seed packet for C2 Session 22, with source paths and initial state. |
| Create | `evals/c2_live_prep/live/session_22/event_log.jsonl` | Seed event log; may start empty if tests cover append behavior. |
| Create | `evals/c2_live_prep/live/session_22/job_queue.jsonl` | Seed job queue; may start empty if tests cover append behavior. |
| Create | `evals/c2_live_prep/live/session_22/current_state.json` | Derived current-state snapshot, explicitly marked derived. |
| Create | `evals/c2_live_prep/live/session_22/benchmark_candidates.jsonl` | Seed or empty review queue for future benchmark-candidate harvesting. |
| Create | `src/live_play/__init__.py` | Package marker for live-play helpers. |
| Create | `src/live_play/live_store.py` | Minimal file-backed helpers for loading JSON and appending event/job JSONL rows atomically enough for local single-user use. |
| Create | `tests/test_live_play_schemas.py` | Tests that schemas load, seed files validate, and event/job append helpers write valid rows. |

If the worker can satisfy append tests without `src/live_play/live_store.py`, it may omit that file, but it must not add a different package path without explaining why in the PR body.

## §5 Files Explicitly Out Of Scope (Denylist)

Do not touch any of these.

| Path | Why this PR must not touch it |
|---|---|
| `apps/live-control-server/**` | FastAPI server belongs to L3, after the live-turn loop exists. |
| `apps/live-control-ui/**` | React/Vite query pane belongs to L4. |
| `src/live_play/resolve_roll.py` | Roll resolver belongs to L2. |
| `src/live_play/classify_live_turn.py` | Live classifier belongs to L2. |
| `src/live_play/live_turn.py` | End-to-end turn loop belongs to L2 unless the parent explicitly re-scopes. |
| `corpus/**` | This PR seeds eval/live files only; it must not promote, correct, or rewrite corpus lore. |
| `evals/c2_live_prep/artifacts/**` | Existing smoke artifacts are inputs/evidence, not regenerated outputs for this slice. |
| `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md` | Parent doc-sync owns plan updates after review/merge. |
| `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md` | Parent doc-sync owns checklist updates after review/merge. |
| `Docs/Plans/STUDY-c2-live-play-cursor-handoff-process.md` | Product-friction study is read-only for this PR. |
| `evals/sentence_routing_retrieval_falsification/**` | Sibling retrieval/autonomy workstream; not part of C2 live-control L1. |
| `evals/lysandra_vertical_slice/gold/step0_environment.json` | No corpus edits should happen, so fingerprint updates are out of scope. |

If the worker thinks a denylisted path is required, stop and say so in the PR description instead of editing it.

## §6 Implementation Contract

### Schema Design

Use JSON Schema Draft 2020-12. Prefer `additionalProperties: false` for top-level records and core nested objects. Keep enums closed for stable product modes.

Required conceptual contracts:

- `live_packet` must include:
  - `schema_version`
  - `campaign_id`
  - `session`
  - `packet_id`
  - `created_at`
  - `source_paths`
  - `latency_modes`
  - `known_roll_tables`
  - `current_state_seed`
  - `open_loops`
  - `roll_stack`
  - optional context/retrieval packet references
- `live_event` must include:
  - `schema_version`
  - `id`
  - `created_at`
  - `campaign_id`
  - `session`
  - `session_clock`
  - `event_type`
  - `latency_mode`
  - `input_text`
  - `summary`
  - `derived_fields`
  - `provenance`
  - `jobs_to_queue`
- `live_job` must include:
  - `schema_version`
  - `id`
  - `created_at`
  - `job_type`
  - `status`
  - `payload`
  - `created_from_event_id`
  - `dependencies`
  - `provenance`

Minimum enum values to include now:

- `latency_mode`: `fast_live`, `context_lookup`, `prep_architect`, `post_session`
- `event_type`: `roll_result`, `skill_check`, `canon_commit`, `canon_correction`, `open_loop_update`, `context_question`, `prep_request`, `state_note`
- `job_type`: `append_staging`, `benchmark_candidate`, `post_session_propagation`, `packet_rebuild`, `recap_input`, `manual_review`
- `job.status`: `queued`, `in_progress`, `blocked`, `complete`, `cancelled`

### Seed Data Rules

- Seed Session 22 from existing sources, but keep the packet concise. This is a substrate, not a recap.
- `source_paths` should point to the whole route for later design: plan, checklist, study, Session 22 handoff, staging notes, journey tracker, runbook, and the relevant eval smoke artifact.
- `current_state.json` must say it is derived. Do not let later UI work mistake it for source truth.
- Empty JSONL files are allowed for `event_log.jsonl`, `job_queue.jsonl`, and `benchmark_candidates.jsonl` if tests append representative rows into temp copies.
- If seed JSONL rows are included, every row must validate against its schema.

### File Helper Rules

If `src/live_play/live_store.py` is added, keep it tiny and deterministic:

```python
from pathlib import Path
from typing import Any

def load_json(path: Path) -> dict[str, Any]: ...
def iter_jsonl(path: Path) -> list[dict[str, Any]]: ...
def append_jsonl(path: Path, row: dict[str, Any]) -> None: ...
```

Rules:

- Use UTF-8.
- Append one JSON object per line.
- Preserve key order from the input dict.
- Do not silently swallow JSON decode errors.
- Do not implement server behavior, classifier behavior, or corpus writes.

## §7 Verification Commands

The worker must run every command and paste the output into the PR body. The reviewer will rerun each.

```bash
uv run pytest tests/test_live_play_schemas.py -q
```

```bash
uv run python - <<'PY'
from pathlib import Path
import json

base = Path("evals/c2_live_prep/live/session_22")
schemas = Path("evals/c2_live_prep/live/schemas")
for path in [
    schemas / "live_packet.schema.json",
    schemas / "live_event.schema.json",
    schemas / "live_job.schema.json",
    base / "live_packet.json",
    base / "current_state.json",
]:
    json.loads(path.read_text(encoding="utf-8"))
for path in [
    base / "event_log.jsonl",
    base / "job_queue.jsonl",
    base / "benchmark_candidates.jsonl",
]:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            json.loads(line)
print("live C2 seed JSON/JSONL parse OK")
PY
```

```bash
git diff --stat -- \
  evals/c2_live_prep/live/schemas/live_packet.schema.json \
  evals/c2_live_prep/live/schemas/live_event.schema.json \
  evals/c2_live_prep/live/schemas/live_job.schema.json \
  evals/c2_live_prep/live/session_22/live_packet.json \
  evals/c2_live_prep/live/session_22/event_log.jsonl \
  evals/c2_live_prep/live/session_22/job_queue.jsonl \
  evals/c2_live_prep/live/session_22/current_state.json \
  evals/c2_live_prep/live/session_22/benchmark_candidates.jsonl \
  src/live_play/__init__.py \
  src/live_play/live_store.py \
  tests/test_live_play_schemas.py
```

## §8 Reporting Contract

In the PR body the worker must include:

1. `git diff --stat` filtered to §4 paths only.
2. Verbatim output for every §7 command.
3. One paragraph describing which later slices stayed untouched: no server, no UI, no classifier, no roll resolver, no corpus writes.
4. Any schema design judgment that was not obvious from the PLAN, especially if a field was deferred.

## §9 Acceptance Rubric

The reviewer will accept only if every bullet below is true.

- [ ] All seed JSON and non-empty JSONL rows parse and validate against the new schemas — verified by `uv run pytest tests/test_live_play_schemas.py -q` and the JSON parse smoke in §7.
- [ ] `live_packet.json` points to the whole design route: PLAN, CHECKLIST, STUDY, S22 handoff, staging notes, journey tracker, runbook, and C2 smoke artifact — verified by `uv run pytest tests/test_live_play_schemas.py -q`.
- [ ] `current_state.json` is explicitly marked as derived and does not become the authoritative source of truth — verified by `uv run pytest tests/test_live_play_schemas.py -q`.
- [ ] Event/job append behavior writes valid JSONL rows without invoking server/UI/classifier behavior — verified by `uv run pytest tests/test_live_play_schemas.py -q`.
- [ ] No corpus files, eval artifacts, server files, UI files, or sibling retrieval workstream files are touched — verified by the §7 filtered `git diff --stat` plus review.
- [ ] The PR remains L1-scoped: no FastAPI endpoint, no React app, no roll-table resolver, no live classifier — verified by review against §4/§5.

## §10 Out-of-Band Notes

- This is a product-substrate slice, not a lore/corpus slice.
- Do not paste long corpus excerpts into the PR body. Summarize seed choices and cite paths.
- If `jsonschema` is unavailable in the local environment, check `pyproject.toml` before adding dependencies. Prefer existing dependencies and test patterns first; do not add a dependency unless the tests require it and the repo does not already provide an equivalent.
- PR #68 is currently open in the sibling C1S4 workstream. Avoid touching anything under `evals/sentence_routing_retrieval_falsification/**`.
