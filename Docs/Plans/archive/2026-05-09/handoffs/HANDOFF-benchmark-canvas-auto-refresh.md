# HANDOFF — Benchmark-owned Canvas Auto-Refresh

## Mission

Make the **C1S1 benchmark canvas update part of the benchmark run itself** so each benchmark execution writes:

1. the benchmark report JSON, and
2. the updated canvas generated block(s),

without requiring a second manual command.

This handoff is for a **new conversation** to implement the remaining integration cleanly and verifiably.

---

## Current state (important)

There are currently **two canvas pipelines** in this suite:

1. **Semantic review canvas** (`breadcrumb-query-semantic-review.canvas.tsx`)
  - Already refreshable from `breadcrumb_query_run.py` via `--canvas-tsx`.
  - Uses `breadcrumb_query_canvas_payload.py` (`build_payload`, `render_generated_block`, `update_canvas_text`).
2. **C1S1 benchmark review canvas** (`c1s1-breadcrumb-query-benchmark-review.canvas.tsx`)
  - Refreshed by a separate script:
   `c1s1_benchmark_canvas_emit.py`.
  - Not yet owned directly by `breadcrumb_query_run.py` as a first-class built-in output path.

The user request is specifically to ensure the **existing canvas** gets auto-updated **with each benchmark run** and that this update is part of the benchmark contract itself.

---

## Target behavior

When running:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run ...
```

the run should (by policy/default for benchmark mode) also update the C1S1 canvas generated block, not just the report.

### Practical target contract

- If run succeeds and report JSON is written, canvas refresh should run in the same invocation.
- If canvas markers are missing or canvas path invalid, fail clearly with actionable error.
- Provide explicit terminal JSON output summarizing:
  - report path,
  - canvas updated/unchanged path(s),
  - pass/fail aggregate.

---

## Architecture recommendation

Use `breadcrumb_query_run.py` as the orchestration entrypoint and keep `c1s1_benchmark_canvas_emit.py` as the canonical C1S1 payload/patch engine.

### Why this architecture

- Keeps benchmark orchestration centralized in one entrypoint.
- Avoids duplicating C1S1 payload logic already implemented in `c1s1_benchmark_canvas_emit.py`.
- Preserves clean separation:
  - run harness computes report,
  - canvas emitter transforms report+gold into generated UI block.

### Integration pattern

After report write in `breadcrumb_query_run.py`:

1. detect whether gold/run corresponds to C1S1 canvas mode (or explicit flag),
2. call emitter logic (prefer importing a callable helper; if missing, extract one from emitter),
3. patch one or more target canvas files (Cursor-managed default and optional repo copy),
4. emit deterministic update result JSON.

---

## Files to read first

1. `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py`
  - Current report lifecycle and existing semantic canvas refresh hook (`_refresh_canvas`).
2. `evals/sentence_routing_retrieval_falsification/c1s1_benchmark_canvas_emit.py`
  - Existing C1S1 generated block production and patch logic.
3. `evals/sentence_routing_retrieval_falsification/cursor_canvas_paths.py`
  - Default Cursor canvas path resolution (`~/.cursor/projects/.../canvases`).
4. `canvases/c1s1-breadcrumb-query-benchmark-review.canvas.tsx`
  - Marker block:
   `// BEGIN GENERATED C1S1_HARNESS_DETAIL` to `// END GENERATED C1S1_HARNESS_DETAIL`.
5. `tests/test_breadcrumb_query_canvas_payload.py`
  - Existing pattern for payload/update tests.
6. `evals/sentence_routing_retrieval_falsification/README.md`
  - Commands and benchmark workflow docs (must be updated with new default behavior).

---

## Implementation steps

### Step 1 — Add explicit run-time options in `breadcrumb_query_run.py`

Add flags for C1S1 canvas refresh behavior, e.g.:

- `--c1s1-canvas-tsx` (repeatable or optional defaulted path behavior)
- `--skip-c1s1-canvas-refresh` (escape hatch)

Default should align with user request: benchmark run includes canvas update.

### Step 2 — Extract callable API from `c1s1_benchmark_canvas_emit.py` (if needed)

If emitter is CLI-only, refactor minimally to expose:

- `build_block(report: dict, gold: dict) -> str`
- `patch_canvas_paths(block: str, paths: list[Path]) -> list[dict]`

Keep CLI behavior unchanged; just make it callable from run orchestrator.

### Step 3 — Wire orchestrator call after report write

In `breadcrumb_query_run.py`, immediately after report persistence:

- call C1S1 emitter refresh,
- include outcomes in terminal JSON output and report metadata.

Suggested report field:

- `c1s1_canvas_refresh`: `{ enabled, targets, updated, unchanged, errors }`

### Step 4 — Tests

Add focused tests for:

1. run orchestrator triggers C1S1 canvas refresh when enabled.
2. missing marker block throws a clear error.
3. unchanged content reports `canvas_unchanged`.
4. marker replacement is deterministic.

Likely new tests:

- `tests/test_c1s1_benchmark_canvas_emit.py` (if not present)
- `tests/test_breadcrumb_query_run_canvas_integration.py` (new integration test with temp files)

### Step 5 — Docs update

Update:

- `evals/sentence_routing_retrieval_falsification/README.md`

with:

- benchmark run now owns C1S1 canvas refresh,
- exact command(s),
- opt-out flag (if implemented),
- troubleshooting for missing canvas markers.

---

## Verification checklist (must run)

1. Focused tests:

```bash
uv run pytest tests/test_breadcrumb_query_canvas_payload.py -q
uv run pytest tests/test_c1s1_benchmark_canvas_emit.py -q
uv run pytest tests/test_breadcrumb_query_run_canvas_integration.py -q
```

1. One smoke benchmark run (C1S1) that writes report + canvas update in one command.
2. Confirm output contains both:
  - report write confirmation
  - canvas updated/unchanged confirmation
3. Re-run same command and verify idempotent canvas behavior (`unchanged`).

---

## Non-goals

- Do not redesign canvas UI content.
- Do not change benchmark grading semantics.
- Do not hand-edit generated blocks in canvas files.
- Do not split this into a separate post-run script as the primary path; update must be benchmark-owned.

---

## Risks and mitigations

- **Risk:** path mismatch between Cursor-managed canvas and repo canvas copy.  
**Mitigation:** allow explicit `--c1s1-canvas-tsx` targets + sensible default from `cursor_canvas_paths.py`.
- **Risk:** brittle marker replacement.  
**Mitigation:** keep strict marker checks + deterministic replacement tests.
- **Risk:** benchmark run fails after report write due to canvas error.  
**Mitigation:** choose policy explicitly:
  - fail hard (strict contract), or
  - write report + emit canvas failure field (soft contract).  
  Document whichever policy is chosen.

---

## Suggested acceptance definition

A benchmark run is “complete” only when report and canvas refresh are both handled in one invocation, and the behavior is covered by automated tests plus one smoke command.