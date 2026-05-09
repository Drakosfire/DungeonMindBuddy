# Report: Embedding Scoring — Build, Implementation, and Runs

**Repo:** `DungeonMindBuddy`  
**Date:** 2026-04-07  
**Context:** Vertical-slice eval for council-room QA (`evals/mirathorn_vertical_slice/`). Goal: add optional embedding-based cosine similarity vs gold `expected_answer_summary`, smoke-test the model, survive real `.env` / Hugging Face cache layouts, and improve observability (stderr logging, timings).

**Related:** `Docs/Plans/archive/2026-05-09/handoffs/HANDOFF-embedding-scoring-refinement.md`, optional plan `.cursor/plans/embedding_similarity_scoring_20d81fe3.plan.md` (if present).

---

## 1. What was built (artifacts)


| Area                   | Description                                                                                                                                                                                                                                                                                |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Embedding module**   | `evals/mirathorn_vertical_slice/embedding_scorer.py` — load `perplexity-ai/pplx-embed-v1-0.6B` via SentenceTransformers, L2-normalize outputs, `score_batch()` for per-question cosine similarity.                                                                                         |
| **Runner integration** | `evals/mirathorn_vertical_slice/run_council_room_question_set.py` — third scoring dimension gated by `DMB_EMBEDDING_SCORING=1`; results include `embedding_similarity`; summary includes `overall_embedding` (counts, mean/min/median/max, below-threshold count, `watch_threshold` 0.70). |
| **Gold data**          | `evals/mirathorn_vertical_slice/gold/gold_questions.json` — all questions carry `expected_answer_summary` (required for embedding pass).                                                                                                                                                   |
| **Unit tests**         | `tests/evals/test_embedding_scorer.py` — cosine math, mocks, gold loader checks, env gating; plus **live smoke test** (see below).                                                                                                                                                         |
| **Council room tests** | `tests/evals/test_council_room_question_set.py`, `tests/evals/test_council_room_scoring.py` — still pass after changes.                                                                                                                                                                    |
| **Dependencies**       | `pyproject.toml` — `[project.optional-dependencies] embedding = ["sentence-transformers>=3.0", "numpy>=2.0.0"]`; pytest marker `embedding_smoke` registered.                                                                                                                               |


---

## 2. What was implemented (technical)

### 2.1 Hugging Face / dotenv robustness (`embedding_scorer.py`)

**Problem observed:** `DungeonBuddyCLI` loads `.env.development` with `load_dotenv(..., override=True)`, often setting `HF_HOME` to a removable path (e.g. under `/media/...`). Transformers and the HF xet stack still write under that tree. `embedding_available()` imported `sentence_transformers` *before* any cache fix, so dynamic module init could fail with `Permission denied: '/media/...'` even when weights cache was overridden manually.

**Mitigations:**

- `**_ensure_hf_runtime_caches()`** — Ensures under-repo `.cache/embedding_hf/{home,modules,hub}`. If `HF_HOME` is set but **not writable** (probe file), `**HF_HOME` is repointed** to `.cache/embedding_hf/home`. Sets `HF_MODULES_CACHE` / `HF_HUB_CACHE` via `setdefault` when unset.
- `**embedding_available()`** calls `_ensure_hf_runtime_caches()` **before** importing `sentence_transformers`.
- `**load_embedding_model()`** calls `_ensure_hf_runtime_caches()` again before load (idempotent).
- `**_resolve_cache_folder()`** — Tries `EMBEDDING_MODEL_PATH`, `SENTENCE_TRANSFORMERS_HOME`, `HUGGINGFACE_HUB_CACHE`, `HF_HOME` in order; **only uses a candidate if `mkdir` succeeds**; otherwise falls back to `.cache/embedding_hf/sentence_transformers`.

**Operational note:** First full run may download ~600MB from Hugging Face; optional `HF_TOKEN` reduces rate-limit warnings.

### 2.2 Live smoke test

- **Test:** `tests/evals/test_embedding_scorer.py::test_smoke_embedding_model_load_and_encode`  
- **Marker:** `@pytest.mark.embedding_smoke`  
- **Gate:** `DMB_SMOKE_EMBEDDING_MODEL=1` (default CI skips).  
- **If flag set but deps missing:** raises `AssertionError` with install hint (`uv sync --extra embedding`), not a silent skip.  
- **Command (documented in handoff):**  
`DMB_SMOKE_EMBEDDING_MODEL=1 uv run pytest tests/evals/test_embedding_scorer.py::test_smoke_embedding_model_load_and_encode -v`

**Evidence from run (outside sandbox, with embedding extra):** test **PASSED** (~57s first-time including model work; subsequent runs faster).

### 2.3 Logging and telemetry (handoff items)

**Runner (`run_council_room_question_set.py`):**

- When `DMB_EMBEDDING_SCORING` is not `1`: `**INFO:` to stderr** with skip reason (no longer silent).
- When embedding runs: **load time** and **batch score time** via `time.perf_counter()`.
- After `score_batch`: **per-question stderr lines** `[id] embedding similarity: 0.xxx` with  `(!)` if below `EMBEDDING_WATCH_THRESHOLD` (0.70).
- `**__main__`:** `=== STRICT / SEMANTIC / EMBEDDING ===` JSON summaries printed to **stderr** (with flush), aligned with other diagnostic output.

**Module (`embedding_scorer.py`):**

- After model construction: stderr line with **model id, device, cache_folder**.
- Each `**embed_texts`**: stderr line with **n, dim, seconds** (two encodes per `score_batch`: expected summaries + answers).

### 2.4 Known upstream noise

- **FutureWarning** from bundled `modeling.py` for `pplx-embed-v1-0.6B` (`input_embeds` deprecation under future transformers). Does not fail tests; upstream model repo would need to update.

---

## 3. What was run (empirical)

Commands use `**uv run`** from `DungeonMindBuddy` root.

### 3.1 Unit / integration tests

```bash
uv run pytest tests/evals/test_embedding_scorer.py -q
# Result: 12 passed, 1 skipped (smoke skipped without DMB_SMOKE_EMBEDDING_MODEL=1)

uv run pytest tests/evals/test_council_room_question_set.py tests/evals/test_council_room_scoring.py -q
# Result: 19 passed
```

### 3.2 Live embedding smoke (with extras + env)

```bash
uv sync --extra embedding
DMB_SMOKE_EMBEDDING_MODEL=1 uv run pytest tests/evals/test_embedding_scorer.py::test_smoke_embedding_model_load_and_encode -v
# Result: PASSED (live HF load + encode)
```

### 3.3 Full council-room eval (LLM + optional embedding + artifacts)

```bash
DMB_EMBEDDING_SCORING=1 DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1 \
  uv run python evals/mirathorn_vertical_slice/run_council_room_question_set.py
```

**Before** cache/dotenv fixes, embedding failed with `Permission denied: '/media/drakosfire/Projects'` when `.env` pointed `HF_HOME` there. **After** fixes, the same command **without** manual `HF_`* overrides completed embedding.

**Example successful embedding summary (one run, ~224s wall; LLM outputs vary run-to-run):**

- **Strict:** 6 `pass_updated`, 9 `fail_incomplete` (non-deterministic across runs).
- **Semantic:** 10 `pass_updated`, 5 `fail_incomplete` (same caveat).
- **Embedding:** `scored_count: 15`, approximate stats: **mean ~0.59**, **median ~0.63**, **max ~0.80**, **13** below watch threshold **0.70**.

Earlier runs on the same codebase showed similar embedding distributions (e.g. mean ~0.594–0.595, 13 below threshold) with slightly different strict/semantic counts—**treat strict/semantic numbers as stochastic**; embedding stats are stable enough to compare shape, not as a golden baseline without pinning the LLM.

**Artifacts (when write env is set):** under the runner’s output directory (see script for `outdir`): `council_room_question_set.json`, `council_room_question_set.md` — include per-row `embedding_similarity` and markdown `emb: 0.xxx` annotations.

---

## 4. Suggested focus for the main agent

1. **Threshold calibration** — Handoff: 0.70 is a guess; most answers fell *below* it in observed runs. Correlate `embedding_similarity` with strict/semantic `pass_updated` vs `fail_incomplete` before tightening/loosening.
2. **Summary quality** — Review `expected_answer_summary` vs actual answers where embedding is low but semantic passes (or the reverse).
3. **CI policy** — Keep smoke **opt-in** (`DMB_SMOKE_EMBEDDING_MODEL=1`) to avoid HF download in default pipelines; optional job with `--extra embedding`.
4. **Secrets / env** — Full eval needs OpenAI (or configured) keys via existing CLI dotenv; embedding needs network for first-time model fetch unless fully cached under `.cache/embedding_hf/`.

---

## 5. File checklist (quick navigation)


| Path                                                              | Role                                                                                   |
| ----------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `evals/mirathorn_vertical_slice/embedding_scorer.py`              | Model load, HF cache hardening, `embed_texts`, `score_batch`, stderr diagnostics       |
| `evals/mirathorn_vertical_slice/run_council_room_question_set.py` | Orchestration, embedding gate, timings, per-question logs, `__main__` stderr summaries |
| `evals/mirathorn_vertical_slice/gold/gold_questions.json`         | Gold including `expected_answer_summary`                                               |
| `tests/evals/test_embedding_scorer.py`                            | Unit tests + `test_smoke_embedding_model_load_and_encode`                              |
| `pyproject.toml`                                                  | `embedding` optional extra; `embedding_smoke` pytest marker                            |
| `Docs/Plans/archive/2026-05-09/handoffs/HANDOFF-embedding-scoring-refinement.md`              | Original refinement backlog (logging partially addressed by this work)                 |


---

*End of report.*