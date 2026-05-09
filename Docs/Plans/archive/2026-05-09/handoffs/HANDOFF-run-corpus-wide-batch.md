# Handoff: Run Corpus-Wide Batch API Ingest (Full 130-File Corpus)

**Date:** 2026-04-03  
**Priority:** HIGH  
**Estimated Effort:** Small (operational — run commands, monitor, verify)  
**Goal:** Produce a full-corpus fact store via the Batch API at ~50% cost, and verify the Batch API path works end-to-end.

---

## 1) What You Are Doing

Running the full 130-file Elderwyld corpus through `tools/corpus_batch.py`, the three-phase corpus-wide Batch API pipeline. This produces a complete fact store at `out/stores/batch_api_full_corpus` and retires Concern 3 from the smoke report (Batch API path unverified).

---

## 2) Hard Rules

- **Python:** always `uv run python …` — never bare `python`.
- **Network:** all three phases that touch OpenAI (`--submit`, `--poll`, `--status`) require unrestricted network access.
- **API key:** must be available via `OPENAI_API_KEY` in environment or `.env` / `.env.development` at project root or parent.
- **Do not modify** `tools/corpus_batch.py`, `src/ingestion/`, or `src/cli.py` — this is an operational run, not a code change.

---

## 3) Commands (run in order)

All commands run from `DungeonMindBuddy/` repo root.

### Step 1: Submit

```bash
uv run python tools/corpus_batch.py --submit \
    --store out/stores/batch_api_full_corpus
```

This will:

- Chunk all 130 files (~2,500–5,300 evidence units)
- Aggregate into one JSONL of entity extraction requests
- Submit one batch job to OpenAI
- Print the `batch_id` and manifest path
- Exit immediately

**Expected output:**

```
Corpus-wide batch submit: 130 files from .../corpus/eldyrwild-markdown
  [1/130] file.md: N units
  ...
Total: XXXX evidence units from 130 files
Entity batch submitted: batch_XXXX (YYY requests)
Manifest: out/stores/batch_api_full_corpus/logs/corpus_batch/corpus_batch_manifest.json
```

**Save the manifest path** — all subsequent commands use it.

### Step 2: Check status (optional, non-blocking)

```bash
uv run python tools/corpus_batch.py --status \
    out/stores/batch_api_full_corpus/logs/corpus_batch/corpus_batch_manifest.json
```

One-shot check. Prints stage, file count, and live batch progress from OpenAI. Safe to run any time.

### Step 3: Poll (handles entity→fact transition automatically)

```bash
uv run python tools/corpus_batch.py --poll \
    out/stores/batch_api_full_corpus/logs/corpus_batch/corpus_batch_manifest.json \
    --poll-interval 300
```

This will:

- Poll entity batch every 5 minutes until complete
- Download entity output, apply to cache
- Run entity extraction from cache to get entities
- Prepare fact extraction requests, submit fact batch
- Poll fact batch until complete
- Download fact output, apply to cache
- Send desktop notification (`notify-send`) at each completion
- Exit when both batches are done (manifest stage = `ready`)

**This is the long step.** OpenAI batch SLA is up to 24 hours but often faster. The process must stay alive during polling. Use `--poll-interval 300` (5 min) for a reasonable balance.

**If interrupted:** re-run the same `--poll` command. It reads the manifest stage and resumes from wherever it left off. Fully idempotent.

### Step 4: Complete (finalize into store)

```bash
uv run python tools/corpus_batch.py --complete \
    out/stores/batch_api_full_corpus/logs/corpus_batch/corpus_batch_manifest.json
```

This will:

- Re-chunk all 130 files (deterministic, fast)
- Run entity and fact extraction from cache for each file
- Write entities, facts, evidence units, event records, claims to the store
- Record ingest fingerprints
- Print summary totals

**Expected output:**

```
Finalizing 130 files into store at .../out/stores/batch_api_full_corpus
  [1/130] path/to/file.md... X entities, Y facts
  ...
============================================================
Corpus batch complete!
  Files:           130
  Evidence units:  XXXX
  Entities:        XXXX (deduplicated in store: XXX)
  Facts:           XXXX
  Event records:   XX
  Claims:          XX
  Store:           .../out/stores/batch_api_full_corpus
============================================================
```

---

## 4) What to Report After Completion

Your response should include:

1. **Submit output:** `batch_id`, request count, total evidence units
2. **Poll output:** entity batch final status + usage, fact batch final status + usage, any warnings about failed rows
3. **Complete output:** full summary block (files, evidence units, entities, facts, event records, claims)
4. **Comparison to prior baselines** from `evals/smoke_results/HANDOFF-benchmark-sample-e2e-report-2026-04-03.md`:

  | Baseline                     | Entities | Facts  | Evidence Units |
  | ---------------------------- | -------- | ------ | -------------- |
  | `cheapest_full` (130 files)  | 1,759    | 22,548 | 3,867          |
  | `escalation_full_mini_to_54` | 2,779    | 21,964 | 5,299          |
  | `nano_full`                  | 4,845    | 15,359 | 2,526          |
  | **This run**                 | ?        | ?      | ?              |

5. **Any errors or warnings** from any phase

---

## 5) Failure Modes and Recovery


| Symptom                                          | Cause                                           | Fix                                                                                    |
| ------------------------------------------------ | ----------------------------------------------- | -------------------------------------------------------------------------------------- |
| `Error: OPENAI_API_KEY not set`                  | Missing API key                                 | Set `OPENAI_API_KEY` in environment or `.env`                                          |
| `Error: corpus root not found`                   | Wrong working directory                         | Run from `DungeonMindBuddy/` repo root                                                 |
| `Error: manifest already exists at stage 'X'`    | Prior run exists                                | Add `--force` to `--submit`, or use `--poll`/`--complete` to continue the existing run |
| `Error: Entity batch failed/expired`             | OpenAI batch failure                            | Check `entity_batch_error.json` in `work_dir`. May need to re-submit with `--force`    |
| Poll interrupted                                 | Process killed / network drop                   | Re-run `--poll` with same manifest — idempotent resume                                 |
| `Error: manifest stage is 'X', expected 'ready'` | Running `--complete` too early                  | Run `--poll` first to finish batch processing                                          |
| DNS / connection errors during `--submit`        | Sandboxed environment                           | Request `full_network` permissions                                                     |
| Cache miss during `--complete`                   | Corpus file changed between submit and complete | Re-submit with `--force`                                                               |


---

## 6) File Reference


| File                                                                                 | Purpose                                               |
| ------------------------------------------------------------------------------------ | ----------------------------------------------------- |
| `tools/corpus_batch.py`                                                              | The tool you are running                              |
| `corpus/eldyrwild-markdown/`                                                         | Source corpus (130 .md files)                         |
| `out/stores/batch_api_full_corpus/`                                                  | Output store (created by `--submit`)                  |
| `out/stores/batch_api_full_corpus/.cache/`                                           | Per-unit extraction cache                             |
| `out/stores/batch_api_full_corpus/logs/corpus_batch/corpus_batch_manifest.json`      | Coordination manifest                                 |
| `out/stores/batch_api_full_corpus/logs/corpus_batch/entity_extraction_manifest.json` | Entity batch request→unit mapping                     |
| `out/stores/batch_api_full_corpus/logs/corpus_batch/fact_extraction_manifest.json`   | Fact batch request→unit mapping (created during poll) |
| `evals/smoke_results/HANDOFF-benchmark-sample-e2e-report-2026-04-03.md`              | Prior baselines for comparison                        |


---

## 7) Scope Boundary

This handoff is **operational only** — run commands, monitor, report results. Do NOT:

- Modify any source code
- Change MODEL_POLICY.json
- Run the per-file `batch_ingest_corpus.py` (different tool, different flow)
- Interpret quality results beyond basic count comparison (that's a separate investigation)

