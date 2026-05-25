# HANDOFF — PR 72: C2 Live Control Surface L1 Packet + Event/Job + Surface Layout Schema

**Created:** 2026-05-25 (UTC).  
**Status:** MERGED — PR #72 landed on `main` (merge commit `7d6648d`, 2026-05-25 UTC).
**Parent agent:** Cursor agent; parent owns review and atomic doc-sync.  
**Plan anchor:** `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md` (`execution_state.active_slice: L1_packet_event_job_schema`).  
**Checklist anchor:** `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md` Phase L1.

---

## §0 Re-anchor Before Writing

This handoff is downstream of a workstream/session re-anchor. The worker should not infer current state from chat history.

Read in this order:

1. `.cursor/rules/external-agent-pr-loop.mdc` — mandatory allowlist / denylist / verification contract.
2. `.cursor/rules/anchor.mdc` — re-anchor discipline for fresh agents.
3. `AGENTS.md` — repo operating policy, UV usage, RTK preference, git verification, and external-agent PR loop conventions.
4. `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md` — Reanchor Block + Phase L1.
5. `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md` — Product Shape, **Modular Surface UI**, Minimal Architecture, Live Turn Loop, Latency Modes, PR Slices, and Acceptance Criteria.
6. `Docs/Plans/STUDY-c2-live-play-cursor-handoff-process.md` — product-friction study; prevents the substrate from turning into a dashboard/file-browser model.
7. `Docs/Plans/HANDOFF-s22-live-play-agent.md` — Session 22 dogfood contract, notes discipline, and roll-table lookup shape.

Current-state hypothesis to carry into the PR:

- `L0_plan_lock` is complete.
- `L1_packet_event_job_schema` is the active slice and has not started.
- This PR creates the local file-backed state substrate only, **including the runtime surface layout contract** (`surface_catalog` + `surface_layout.json`).
- Server, UI shell, roll resolver, live classifier, recap-write, corpus propagation, and retrieval rebuild behavior are later slices.
- The HTTP/API envelope is language-agnostic; Python helpers in this PR are storage only, not product logic.

## §1 Mission

Create the schema-validated, file-backed Session 22 live-play substrate: live packet (with **surface catalog**), **runtime surface layout**, event log, job queue, derived current state, benchmark-candidate seed file, required tiny file helpers, and focused tests for schema loading, JSON round-trip, and JSONL append behavior.

## §2 Why This Slice

The C2 Live Control Surface v0 needs durable files that a server/UI can consume without making the UI source of truth. The surface is **runtime-configurable** (GM toggles modules, reorders, moves slots at the table); layout must persist server-side starting with `surface_layout.json` in this PR.

This L1 slice deliberately stops before the agent loop and before HTTP. It defines the data contract that later slices will read and write.

This PR should make future work easier to falsify: if `current_state.json` is derived, event/job JSONL append is testable, `surface_layout.json` round-trips through `write_json`, and source/provenance fields exist from the start, later server/UI work has fewer hidden assumptions.

## §3 Authoritative Inputs

Read these before designing fields:

1. `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md`
2. `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md`
3. `Docs/Plans/STUDY-c2-live-play-cursor-handoff-process.md`
4. `Docs/Plans/HANDOFF-s22-live-play-agent.md`
5. `evals/c2_live_prep/artifacts/runs/2026-05-23/c2s22_smoke_report.md`
6. `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md`
7. `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Journey - Mireward Reach (Campaign 2).md`
8. `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_travel_to_mireward_runbook.md`
9. `schemas/v0.1/event_record.schema.json` and `schemas/v0.1/common.schema.json`
10. `tests/evals/test_schema_validation.py` and `scripts/lint_npc_registry.py`

The worker may read corpus files for field design and seed values, but must not rewrite corpus files in this PR.

## §4 Files In Scope (Allowlist)

The worker's expected `git diff --stat` must be expressible from this table.

| Action | Path | Purpose |
|---|---|---|
| Create | `evals/c2_live_prep/live/schemas/live_packet.schema.json` | JSON Schema for the loaded live-play packet, seed context, and **surface_catalog**. |
| Create | `evals/c2_live_prep/live/schemas/live_event.schema.json` | JSON Schema for one event-log JSONL row. |
| Create | `evals/c2_live_prep/live/schemas/live_job.schema.json` | JSON Schema for one job-queue JSONL row. |
| Create | `evals/c2_live_prep/live/schemas/live_surface_layout.schema.json` | JSON Schema for GM runtime layout (`surface_layout.json`). |
| Create | `evals/c2_live_prep/live/session_22/live_packet.json` | Seed packet for C2 Session 22, with source paths, **surface_catalog**, and initial state. |
| Create | `evals/c2_live_prep/live/session_22/surface_layout.json` | Default GM runtime layout seed (Chat + Record required; at least one optional module enabled). |
| Create | `evals/c2_live_prep/live/session_22/event_log.jsonl` | Seed event log; may start empty if tests cover append behavior. |
| Create | `evals/c2_live_prep/live/session_22/job_queue.jsonl` | Seed job queue; may start empty if tests cover append behavior. |
| Create | `evals/c2_live_prep/live/session_22/current_state.json` | Derived current-state snapshot, explicitly marked derived. |
| Create | `evals/c2_live_prep/live/session_22/benchmark_candidates.jsonl` | Seed or empty review queue for future benchmark-candidate harvesting. |
| Create | `src/live_play/__init__.py` | Package marker for live-play helpers. |
| Create | `src/live_play/live_store.py` | Minimal helpers for loading/writing JSON and appending event/job JSONL rows. |
| Create | `tests/test_live_play_schemas.py` | Tests that schemas load, seed files validate, JSON round-trip works, and append helpers write valid rows. |

Do not add a different package path for live-play storage helpers. If `src/live_play/live_store.py` cannot support the append tests, stop and report the blocker in the PR description instead of widening scope.

## §5 Files Explicitly Out Of Scope (Denylist)

Do not touch any of these.

| Path | Why this PR must not touch it |
|---|---|
| `apps/live-control-server/**` | FastAPI server belongs to L3. |
| `apps/live-control-ui/**` | React/Vite query pane belongs to L4. |
| `src/live_play/resolve_roll.py` | Roll resolver belongs to L2. |
| `src/live_play/classify_live_turn.py` | Live classifier belongs to L2. |
| `src/live_play/live_turn.py` | End-to-end turn loop is out of scope for L1. |
| `corpus/**` | This PR seeds eval/live files only; it must not promote, correct, or rewrite corpus lore. |
| `evals/c2_live_prep/artifacts/**` | Existing smoke artifacts are inputs/evidence, not regenerated outputs. |
| `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md` | Parent doc-sync owns plan updates after review/merge. |
| `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md` | Parent doc-sync owns checklist updates after review/merge. |
| `Docs/Plans/STUDY-c2-live-play-cursor-handoff-process.md` | Product-friction study is read-only for this PR. |
| `evals/sentence_routing_retrieval_falsification/**` | Sibling retrieval/autonomy workstream. |
| `evals/lysandra_vertical_slice/gold/step0_environment.json` | No corpus edits should happen, so fingerprint updates are out of scope. |

If the worker thinks a denylisted path is required, stop and say so in the PR description instead of editing it.

## §6 Implementation Contract

Use JSON Schema Draft 2020-12. Prefer `additionalProperties: false` for top-level records and core nested objects. Keep enums closed for stable product modes.

`live_packet` must include: `schema_version`, `campaign_id`, `session`, `packet_id`, `created_at`, `source_paths`, `latency_modes`, `known_roll_tables`, `current_state_seed`, `open_loops`, `roll_stack`, **`surface_catalog`**, and optional context/retrieval packet references.

**`surface_catalog`** — array of module definitions available for this session. Each entry must include at minimum: `module_id`, `title`, `default_slot`, `required` (boolean). Required v0 modules: `chat`, `record` (`required: true`). Seed optional modules aligned with PLAN: `now`, `open_loops`, `roll_stack`, `sources`, `queue`.

**`live_surface_layout`** (`surface_layout.json`) must include: `schema_version`, `layout_version`, `updated_at`, `campaign_id`, `session`, and `modules` (array of runtime instances). Each instance must include: `module_id`, `slot`, `order`, `enabled`, `collapsed` (boolean). Optional: `config` object for module-specific settings. Slot enum: `main`, `sidebar`, `bottom`, `overlay`.

`live_event` must include: `schema_version`, `id`, `created_at`, `campaign_id`, `session`, `session_clock`, `event_type`, `latency_mode`, `input_text`, `summary`, `derived_fields`, `provenance`, and `jobs_to_queue`.

`live_job` must include: `schema_version`, `id`, `created_at`, `job_type`, `status`, `payload`, `created_from_event_id`, `dependencies`, and `provenance`.

Minimum enum values:

- `latency_mode`: `fast_live`, `context_lookup`, `prep_architect`, `post_session`
- `event_type`: `roll_result`, `skill_check`, `canon_commit`, `canon_correction`, `open_loop_update`, `context_question`, `prep_request`, `state_note`, `surface_config_updated`
- `job_type`: `append_staging`, `benchmark_candidate`, `post_session_propagation`, `packet_rebuild`, `recap_input`, `manual_review`
- `job.status`: `queued`, `in_progress`, `blocked`, `complete`, `cancelled`

`current_state.json` does not receive its own JSON Schema in this PR. It must parse as JSON and tests must assert its derived/source-of-truth invariants. Do not add `current_state.schema.json` unless the parent explicitly re-scopes L1.

Seed Session 22 from existing sources, but keep the packet concise. This is a substrate, not a recap. `source_paths` should point to the whole route for later design: plan, checklist, study, Session 22 handoff, staging notes, journey tracker, runbook, and the relevant eval smoke artifact.

Seed `surface_layout.json` with Chat + Record in sensible default slots and at least one optional catalog module enabled (e.g. `roll_stack` in `sidebar`). Tests must assert `chat` and `record` instances are present and enabled.

Empty JSONL files are allowed if tests append representative rows into temp copies. If seed JSONL rows are included, every row must validate against its schema.

`src/live_play/live_store.py` is required for this PR. Keep it tiny and deterministic:

```python
from pathlib import Path
from typing import Any

def load_json(path: Path) -> dict[str, Any]: ...
def write_json(path: Path, data: dict[str, Any]) -> None: ...
def iter_jsonl(path: Path) -> list[dict[str, Any]]: ...
def append_jsonl(path: Path, row: dict[str, Any]) -> None: ...
```

Rules: use UTF-8; `write_json` writes pretty or compact JSON deterministically (pick one and test it); append one JSON object per line for JSONL; preserve key order from the input dict; do not silently swallow JSON decode errors; do not implement server behavior, classifier behavior, roll resolver behavior, layout HTTP endpoints, or corpus writes.

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
    schemas / "live_surface_layout.schema.json",
    base / "live_packet.json",
    base / "surface_layout.json",
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
git diff --name-only
```

```bash
git diff --stat -- \
  evals/c2_live_prep/live/schemas/live_packet.schema.json \
  evals/c2_live_prep/live/schemas/live_event.schema.json \
  evals/c2_live_prep/live/schemas/live_job.schema.json \
  evals/c2_live_prep/live/schemas/live_surface_layout.schema.json \
  evals/c2_live_prep/live/session_22/live_packet.json \
  evals/c2_live_prep/live/session_22/surface_layout.json \
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

1. Verbatim output for every §7 command.
2. Complete `git diff --name-only` output for all changed files.
3. `git diff --stat` filtered to §4 paths only.
4. One paragraph describing which later slices stayed untouched: no server, no UI shell, no classifier, no roll resolver, no corpus writes.
5. Any schema design judgment that was not obvious from the PLAN, especially if a field was deferred.
6. One sentence confirming `surface_catalog` lists required `chat` + `record` and default `surface_layout.json` seeds a runtime-configurable layout.

## §9 Acceptance Rubric

The reviewer will accept only if every bullet below is true.

- [ ] All seed JSON and non-empty JSONL rows parse and validate against the new schemas.
- [ ] `live_packet.json` points to the whole design route: PLAN, CHECKLIST, STUDY, S22 handoff, staging notes, journey tracker, runbook, and C2 smoke artifact.
- [ ] `live_packet.surface_catalog` includes required `chat` and `record` plus Session 22 optional modules.
- [ ] `surface_layout.json` validates against `live_surface_layout.schema.json` and seeds Chat + Record enabled with at least one optional module.
- [ ] `write_json` round-trip test passes for layout persistence (L3 will expose this via `PUT /api/live/surface/layout`).
- [ ] `current_state.json` is explicitly marked as derived and does not become the authoritative source of truth.
- [ ] Event/job append behavior writes valid JSONL rows through `src/live_play/live_store.py` without invoking server/UI/classifier/roll-resolver behavior.
- [ ] No corpus files, eval artifacts, server files, UI files, or sibling retrieval workstream files are touched.
- [ ] The PR remains L1-scoped: no FastAPI endpoint, no React app, no roll-table resolver, no live classifier.

## §10 Out-of-Band Notes

- This is a product-substrate slice, not a lore/corpus slice.
- Do not paste long corpus excerpts into the PR body. Summarize seed choices and cite paths.
- If `jsonschema` is unavailable in the local environment, check `pyproject.toml` before adding dependencies. Prefer existing dependencies and test patterns first.
- PR #68 is currently open in the sibling C1S4 workstream. Avoid touching anything under `evals/sentence_routing_retrieval_falsification/**`.

pr_body_template: |
  ## Summary
  Add the file-backed live-play packet, event, job, and **runtime surface layout** substrate for the C2 Live Control Surface modular shell.

  ## Verification
  Paste the verbatim output from every §7 command here.

  ## `git diff --name-only`
  ```text
  Paste the complete changed-file list here.
  ```

  ## `git diff --stat` (§4 paths only)
  ```text
  Paste a diff stat filtered to the §4 allowlist here.
  ```
