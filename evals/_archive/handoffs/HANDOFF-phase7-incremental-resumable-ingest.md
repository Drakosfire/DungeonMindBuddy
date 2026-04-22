# HANDOFF — Phase 7: Incremental / Resumable Batch Ingest

**Status:** COMPLETED
**Completed:** 2026-04-03
**Verified:** 215 passed, 2 skipped; ruff clean on touched files

---

## What was implemented

### `compute_ingest_key_for_path()` (src/cli.py)

The handoff's `source:{path}` key format did not match the store. Ingest keys are built like `_cmd_ingest`:

```
{sha256(file)}|layer=…|campaign=…|source_class=…
```

The new helper mirrors frontmatter resolution, conflict rules, and defaults (including default `source_class` for world vs campaign). Returns `None` when ingest would need inference or would fail early, so the batch runner falls through to normal ingest instead of incorrectly skipping.

### `tools/batch_ingest_corpus.py`

- **`--force`:** Forwarded on the ingest line and disables the batch fingerprint short-circuit.
- **`--resume`:** Loads `<store>/logs/batch_progress.json` and skips paths already in `completed` for the interrupted run.
- **Unchanged files:** If `compute_ingest_key_for_path()` returns a key and `store.has_ingest_fingerprint(ingest_key)` and not `--force`, prints `skipped (unchanged)` and records `status: skipped, reason: unchanged`.
- **Progress tracking:** After each successful ingest (`run_row` present), appends `str(path.resolve())` and saves JSON. On a fresh run (no `--resume`), any old progress file is removed at start.
- **Cleanup:** `batch_progress.json` is removed only when every non-skipped row has a `run_id` (no failed ingests in the main loop), so a partial failure still leaves a resumable progress file.
- **`summary["skipped_count"]`:** Count of skipped rows.
- **`_aggregate_batch_report`:** `files.skipped` uses `status == "skipped"`; `failed` is `total - succeeded - skipped`. Entity class distribution only uses rows with `run_id` so skipped reruns don't restate old artifacts.

### Tests

- `tests/test_cli.py`: `compute_ingest_key_for_path` returns a stable key for a world markdown doc; `None` when frontmatter is missing.

### Usage

```bash
# First run: ingests everything
uv run python tools/batch_ingest_corpus.py --store ./my_store

# Second run: skips unchanged files, 0 LLM calls
uv run python tools/batch_ingest_corpus.py --store ./my_store

# Force re-ingest
uv run python tools/batch_ingest_corpus.py --store ./my_store --force

# Resume after crash
uv run python tools/batch_ingest_corpus.py --store ./my_store --resume
```
