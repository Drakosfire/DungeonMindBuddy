# Handoff: Corpus-Wide Batch API Pipeline (Submit / Poll / Complete)

**Date:** 2026-04-03  
**Priority:** HIGH  
**Estimated Effort:** Medium (~4-6 hours implementation + testing)  
**Precondition:** Read this file, then read all referenced code before writing anything.

---

## 1) Problem Statement

The current Batch API path (`--use-batch-api` / `--use-openai-batch-api`) operates **per-file**: each of the 130 corpus files submits its own entity batch job, polls until complete, applies results, then submits its own fact batch job, polls again. That's up to **260 batch job submissions** with blocking 30-second poll loops — hours of wall time requiring an active process.

### Goal

Replace this with a **corpus-wide** three-phase workflow:

1. `**--submit`** — Chunk all files locally, aggregate all entity extraction requests into one JSONL, submit one batch job to OpenAI, write a manifest with `batch_id` → exit immediately.
2. `**--poll <manifest>**` — Read manifest, check batch status, notify on completion, download output, apply to cache. If entity batch done, prepare+submit the fact batch and update manifest. Idempotent and resumable.
3. `**--complete <manifest>**` — Run the cache-only pipeline for all files into the store (entity extraction + fact extraction with `openai_client=None`, store writes, recap artifact collection).

**Result:** 2 batch submissions total (one entity, one fact). Submit, walk away, come back to retrieve.

---

## 2) Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   --submit                               │
│  for each file:                                          │
│    chunk_document() → evidence_units                     │
│    frontmatter metadata (layer, campaign, source_class)  │
│  aggregate all units                                     │
│  prepare_entity_batch_requests(all_units, known=[])      │
│  write JSONL → files.create → batches.create             │
│  save corpus_batch_manifest.json:                        │
│    { batch_id, stage: "entity", file_metadata[], ... }   │
│  exit                                                    │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   --poll <manifest>                       │
│  read manifest → batch_id                                │
│  loop: batches.retrieve(batch_id)                        │
│    if terminal:                                          │
│      download output JSONL                               │
│      if stage == "entity":                               │
│        apply_entity_batch_outputs_to_cache()             │
│        run entity extraction (cache-only) → entities     │
│        prepare_fact_batch_requests(all_units, entities)   │
│        submit fact batch → update manifest stage="fact"   │
│      if stage == "fact":                                  │
│        apply_fact_batch_outputs_to_cache()                │
│        update manifest stage="ready"                     │
│      notify-send "Batch {stage} done"                    │
│    else: sleep(poll_interval), print progress            │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   --complete <manifest>                   │
│  read manifest (stage must be "ready")                   │
│  for each file in manifest:                              │
│    run_entity_extraction(units, openai_client=None)       │
│    run_fact_extraction(units, entities, client=None)      │
│    store.add_entities / add_facts / add_evidence_units   │
│    store.add_event_records / add_claims (recap)          │
│  store.save()                                            │
│  print summary report                                    │
└─────────────────────────────────────────────────────────┘
```

---

## 3) File Locations (read all before writing)

### Existing code to reuse (do not modify unless noted)


| File                                     | Lines     | Role                                                                                                                                                                                                                     |
| ---------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `src/ingestion/openai_batch_pipeline.py` | 131–200   | `run_batch_job` — upload, create, poll, download. **Reuse** `write_jsonl`, `build_jsonl_request_line`, `build_responses_batch_request_body`, `read_jsonl_bytes`. The polling loop can be extracted or called directly.   |
| `src/ingestion/entity_extractor.py`      | 1554–1625 | `prepare_entity_batch_requests` — builds JSONL lines + manifest from evidence units. Already handles cache-hit skipping, recap vs standard routing, batched grouping. **Reuse as-is** — call once with all corpus units. |
| `src/ingestion/entity_extractor.py`      | 1628–1705 | `apply_entity_batch_outputs_to_cache` — parses batch output rows into per-unit cache files. **Reuse as-is.**                                                                                                             |
| `src/ingestion/entity_extractor.py`      | 1090+     | `extract_entities_batch` / `run_entity_extraction` — the cache-only extraction path when `openai_client=None`. **Reuse as-is** for `--complete` phase.                                                                   |
| `src/ingestion/fact_extractor.py`        | 968–1039  | `prepare_fact_batch_requests` — builds fact JSONL lines + manifest. **Reuse as-is.**                                                                                                                                     |
| `src/ingestion/fact_extractor.py`        | 1041–1095 | `apply_fact_batch_outputs_to_cache` — parses fact batch output. **Reuse as-is.**                                                                                                                                         |
| `src/ingestion/chunker.py`               | 386+      | `chunk_document` — heading-based chunking, produces evidence units. **Reuse as-is.**                                                                                                                                     |
| `src/ingestion/frontmatter.py`           | —         | `load_document_frontmatter` — extracts YAML metadata (layer, campaign_id, source_class, title). **Reuse as-is.**                                                                                                         |
| `src/cli.py`                             | 668–698   | Chunking + frontmatter flow inside `_cmd_ingest`. **Pattern source** for how to derive `document_id`, `source_class`, `canon_layer`, `campaign_id`, `title`, `source_fingerprint` from a file path + frontmatter.        |
| `tools/batch_ingest_corpus.py`           | 453–534   | Argument parsing and path resolution. **Pattern source** for `--corpus-root`, `--paths-file`, `--limit`, `--batch-size`.                                                                                                 |


### File to create


| File                    | Purpose                                                                                                                                           |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tools/corpus_batch.py` | New standalone tool implementing the three-phase workflow. Separate from `batch_ingest_corpus.py` to avoid disrupting the existing per-file flow. |


---

## 4) Manifest Format

The manifest is the coordination artifact between phases. It must be self-contained — everything needed to resume from any point.

```json
{
  "version": 1,
  "created_at": "2026-04-03T...",
  "store_dir": "out/stores/batch_api_full_corpus",
  "corpus_root": "corpus/eldyrwild-markdown",
  "entity_model": "gpt-5.4-nano",
  "fact_model": "gpt-5.4-nano",
  "batch_size": 5,
  "stage": "entity_submitted",
  "entity_batch": {
    "batch_id": "batch_abc123",
    "input_file_id": "file-xyz",
    "request_count": 847,
    "submitted_at": "2026-04-03T...",
    "status": null,
    "output_file": null
  },
  "fact_batch": null,
  "files": [
    {
      "source_path": "/absolute/path/to/file.md",
      "relative_path": "Elderwyld/Cities and Towns/Mirathorn/The Council Room.md",
      "document_id": "doc_the_council_room",
      "canon_layer": "world",
      "campaign_id": null,
      "source_class": "seed_reference",
      "title": "The Council Room",
      "source_fingerprint": "sha256:...",
      "evidence_unit_count": 12
    }
  ],
  "cache_dir": "out/stores/batch_api_full_corpus/.cache",
  "work_dir": "out/stores/batch_api_full_corpus/logs/corpus_batch"
}
```

**Stage progression:** `entity_submitted` → `entity_complete` → `fact_submitted` → `fact_complete` → `ready`

---

## 5) Implementation Plan

### Phase 1: Submit (`--submit`)

1. Parse args: `--store`, `--corpus-root`, `--paths-file`, `--limit`, `--batch-size`
2. Resolve file paths (reuse pattern from `batch_ingest_corpus.py` lines 546–567)
3. For each file:
  - Load frontmatter (`load_document_frontmatter`)
  - Derive `document_id`, `canon_layer`, `campaign_id`, `source_class`, `title` (reuse pattern from `cli.py` lines 616–626)
  - Call `chunk_document()` → evidence units
  - Record file metadata + unit count in manifest
4. Concatenate all evidence units from all files into one list
5. Call `prepare_entity_batch_requests(all_units, known_entities=[], model=entity_model, batch_size=batch_size, cache_dir=cache_dir)` → `(lines, entity_manifest)`
6. If no lines (all cache hits): set stage to `entity_complete`, skip submission
7. Otherwise:
  - `write_jsonl(work_dir / "entity_requests.jsonl", lines)`
  - `client.files.create(file=..., purpose="batch")`
  - `client.batches.create(input_file_id=..., endpoint="/v1/responses", completion_window="24h")`
  - Save `batch_id`, `input_file_id`, `request_count` to manifest
  - Set stage to `entity_submitted`
8. Save `entity_manifest` as a separate file (`work_dir / "entity_extraction_manifest.json"`) — needed by `apply_entity_batch_outputs_to_cache`
9. Write `corpus_batch_manifest.json` to `work_dir`
10. Print `batch_id` and exit

**Important:** The `entity_manifest` from `prepare_entity_batch_requests` is a dict keyed by `custom_id` with unit metadata. It must be persisted to disk because `apply_entity_batch_outputs_to_cache` needs it later. Same for the fact manifest.

### Phase 2: Poll (`--poll <manifest>`)

1. Load manifest from path
2. Determine current stage
3. If `entity_submitted`:
  - `client.batches.retrieve(batch_id)` → check status
  - If not terminal: print progress (`completed/failed/total`), sleep `--poll-interval` (default 300s), loop
  - If terminal + completed:
    - Download output JSONL: `client.files.content(output_file_id)`
    - Save to `work_dir / "entity_output.jsonl"`
    - Load entity extraction manifest from disk
    - `apply_entity_batch_outputs_to_cache(output_rows, entity_manifest, model_id=..., cache_dir=...)`
    - Update manifest stage to `entity_complete`
    - Send desktop notification: `notify-send "DungeonMindBuddy" "Entity batch complete"`
  - If terminal + failed/expired: print error, exit 1
4. If `entity_complete`:
  - Run `run_entity_extraction` for all units with `openai_client=None` to get entities from cache
  - Call `prepare_fact_batch_requests(all_units, entities=entities, model=fact_model, batch_size=batch_size, cache_dir=cache_dir)`
  - Submit fact batch (same pattern as entity)
  - Save fact manifest to disk
  - Update corpus manifest stage to `fact_submitted`
5. If `fact_submitted`:
  - Same poll loop as entity
  - On completion: download, apply to cache, update stage to `fact_complete` → `ready`
  - Send desktop notification: `notify-send "DungeonMindBuddy" "Fact batch complete — run --complete"`
6. If `ready`: print "Already ready, run --complete"

**Idempotency:** `--poll` can be run multiple times safely. It reads the manifest stage and resumes from wherever it left off.

### Phase 3: Complete (`--complete <manifest>`)

1. Load manifest (assert stage is `ready`)
2. Initialize `DungeonBuddyCLI(store_dir=...)` or work directly with `FactStore`
3. For each file in manifest:
  - Reconstruct evidence units: `chunk_document(...)` with saved metadata
  - `run_entity_extraction(units, openai_client=None, cache_dir=..., recap_artifacts=recap_artifacts)`
  - `run_fact_extraction(units, entities=..., openai_client=None, cache_dir=...)`
  - `store.add_entities(entities)`
  - `store.add_facts(facts)`
  - `store.add_evidence_units(units)`
  - `store.add_event_records(recap_artifacts["event_records"])` if non-empty
  - `store.add_claims(recap_artifacts["claims"])` if non-empty
  - `store.record_ingest_fingerprint(ingest_key)`
4. `store.save()`
5. Print summary: total entities, facts, evidence units, event_records, claims

**Note:** Re-chunking in `--complete` is deterministic (same file + same `min_chars` = same units), so the cache keys will match. Alternatively, you could serialize the evidence units to disk during `--submit` to avoid re-chunking, but that's a lot of data. Re-chunking is fast and safer.

---

## 6) Key Design Decisions

### Why a new tool instead of modifying `batch_ingest_corpus.py`?

`batch_ingest_corpus.py` has 780+ lines of per-file orchestration, escalation logic, quality decision trees, and report generation. Grafting corpus-wide batch into it would create a tangled mess. A separate `corpus_batch.py` keeps the two approaches independent. The per-file tool remains useful for interactive/incremental work.

### Why not serialize evidence units to disk?

Evidence units from `chunk_document` are deterministic given the same file and `min_chars`. Re-chunking 130 files takes < 5 seconds. Serializing ~3,000+ evidence units as JSON is larger than re-running the function, and introduces a staleness risk if files change between submit and complete.

### Why does `--poll` handle the entity→fact transition?

The fact batch depends on entity results (it needs the entity list to scope prompts). So entity results must be applied and entity extraction run before fact requests can be prepared. Putting this in `--poll` means you can submit entities, walk away, and `--poll` handles the full entity→fact progression automatically.

### Why `notify-send`?

It's the standard Linux desktop notification mechanism, already available on the user's system (Ubuntu/GNOME). No dependencies needed. Falls back gracefully if not available (just prints to stdout).

---

## 7) CLI Interface

```
tools/corpus_batch.py --submit [options]
tools/corpus_batch.py --poll <manifest-path> [--poll-interval 300]
tools/corpus_batch.py --complete <manifest-path>
tools/corpus_batch.py --status <manifest-path>
```

### `--submit` options


| Flag            | Default                            | Description                            |
| --------------- | ---------------------------------- | -------------------------------------- |
| `--store`       | `out/stores/batch_api_full_corpus` | Fact store directory                   |
| `--corpus-root` | `corpus/eldyrwild-markdown`        | Root directory to scan                 |
| `--paths-file`  | None                               | Explicit file list (one path per line) |
| `--limit`       | 0 (all)                            | Max files                              |
| `--batch-size`  | 5                                  | Evidence units per LLM request         |
| `--force`       | False                              | Ignore existing cache                  |


### `--poll` options


| Flag              | Default | Description                   |
| ----------------- | ------- | ----------------------------- |
| `--poll-interval` | 300     | Seconds between status checks |
| `--no-notify`     | False   | Skip desktop notification     |


### `--status` (convenience)

Quick one-shot check: load manifest, retrieve batch status, print progress, exit. No polling loop.

---

## 8) Error Handling

- **Batch fails/expires:** Print error with `batch_id`, save error file to `work_dir`, exit 1. Manifest preserves state for debugging.
- **Partial failures in output:** `apply_*_batch_outputs_to_cache` returns `failed_custom_ids`. Log them, continue with successful results. Re-submitting only failed requests is a future enhancement.
- **Manifest not found:** Clear error message with expected path.
- **Wrong stage for command:** e.g., `--complete` when stage is `entity_submitted` → print "Run --poll first" and exit.
- **Network errors during poll:** Print error, manifest is intact, re-run `--poll` to resume.
- **Files changed between submit and complete:** `chunk_document` will produce different units with different cache keys → cache misses → `run_entity_extraction` with `openai_client=None` and `allow_heuristic_fallback=False` will raise. This is intentional — if corpus changed, re-submit.

---

## 9) Testing

### Unit tests (no API calls)

1. **Manifest round-trip:** write → read → verify all fields survive
2. **Stage progression:** verify `entity_submitted` → `entity_complete` → `fact_submitted` → `fact_complete` → `ready`
3. **Multi-file aggregation:** chunk 3 small test files → call `prepare_entity_batch_requests` with combined units → verify all units appear in JSONL lines
4. **Cache-hit skip:** pre-populate cache for some units → verify those are excluded from JSONL

### Integration test (optional, requires API key)

Submit a 1-file batch via `--submit`, poll with `--poll`, complete with `--complete`, verify store has entities and facts.

### Verification commands

```bash
uv run ruff check tools/corpus_batch.py
uv run pytest tests/tools/test_corpus_batch.py -v  # if test file created
```

---

## 10) Scope Boundary

This handoff implements **only** the three-phase corpus-wide batch workflow. It does NOT:

- Modify `batch_ingest_corpus.py` (per-file flow stays intact)
- Modify `src/cli.py` or `src/ingestion/openai_batch_pipeline.py`
- Add escalation/quality-decision logic (that stays in `batch_ingest_corpus.py`)
- Implement partial-failure resubmission (future enhancement)
- Add webhook support (polling + notify-send is sufficient for local dev)

---

## 11) Usage Example (Full Corpus Run)

```bash
# 1. Submit entity batch for all 130 files
uv run python tools/corpus_batch.py --submit \
    --store out/stores/batch_api_full_corpus

# Prints: "Entity batch submitted: batch_abc123 (847 requests)"
# Prints: "Manifest: out/stores/batch_api_full_corpus/logs/corpus_batch/corpus_batch_manifest.json"

# 2. Quick status check
uv run python tools/corpus_batch.py --status \
    out/stores/batch_api_full_corpus/logs/corpus_batch/corpus_batch_manifest.json

# Prints: "Stage: entity_submitted | Status: in_progress | Progress: 312/847 completed"

# 3. Poll (backgrounds, notifies when done, auto-submits fact batch)
uv run python tools/corpus_batch.py --poll \
    out/stores/batch_api_full_corpus/logs/corpus_batch/corpus_batch_manifest.json \
    --poll-interval 300

# ... waits ... desktop notification: "Entity batch complete"
# ... auto-submits fact batch ... waits ... notification: "Fact batch complete"

# 4. Finalize into store
uv run python tools/corpus_batch.py --complete \
    out/stores/batch_api_full_corpus/logs/corpus_batch/corpus_batch_manifest.json

# Prints summary: 130 files, X entities, Y facts, Z evidence units
```

