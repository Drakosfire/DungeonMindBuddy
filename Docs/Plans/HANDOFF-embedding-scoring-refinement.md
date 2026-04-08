# Handoff: Embedding Similarity Scoring — First Run & Refinement

**Status:** Implemented, untested on live data  
**Date:** 2026-04-07  
**Prerequisite plan:** `.cursor/plans/embedding_similarity_scoring_20d81fe3.plan.md`

---

## What exists

Embedding-based cosine similarity scoring is wired into the council-room QA runner as a third scoring pass alongside strict/semantic token matching. It uses the perplexity `pplx-embed-v1-0.6B` model loaded locally via SentenceTransformers.

### Key files


| File                                                              | Role                                                                                                        |
| ----------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `evals/mirathorn_vertical_slice/embedding_scorer.py`              | Standalone module: `load_embedding_model()`, `embed_texts()`, `cosine_similarity_single()`, `score_batch()` |
| `evals/mirathorn_vertical_slice/run_council_room_question_set.py` | Runner: embedding pass gated by `DMB_EMBEDDING_SCORING=1` env var                                           |
| `evals/mirathorn_vertical_slice/gold/gold_questions.json`         | All 15 questions now include `expected_answer_summary`                                                      |
| `tests/evals/test_embedding_scorer.py`                            | 12 unit tests (mock model, cosine math, graceful skip)                                                      |
| `pyproject.toml`                                                  | Optional dep group: `[project.optional-dependencies] embedding`                                             |


### How to invoke

```bash
# Install optional deps (first time only)
uv pip install sentence-transformers numpy
# or: uv sync --extra embedding

# Smoke test the embedding model (HF download on first run; skips if env unset)
DMB_SMOKE_EMBEDDING_MODEL=1 uv run pytest tests/evals/test_embedding_scorer.py::test_smoke_embedding_model_load_and_encode -v

# Run with embedding scoring enabled
DMB_EMBEDDING_SCORING=1 DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1 \
  env PYTHONPATH=. uv run python evals/mirathorn_vertical_slice/run_council_room_question_set.py
```

The model will be downloaded from HuggingFace on first run (~600MB). To control cache location, set `HF_HOME` or `EMBEDDING_MODEL_PATH`.

---

## Known issue: no logging

The embedding scoring path is nearly silent. Here are the specific gaps and where to fix them:

### 1. Skip-reason never printed (line 348-351 in runner)

When `DMB_EMBEDDING_SCORING` is not set to `1`, the `else` branch sets `embedding_skipped_reason` but **never prints it**. The user sees nothing and doesn't know embedding scoring was skipped.

```python
# Current (silent):
else:
    embedding_skipped_reason = (
        f"{EMBEDDING_SCORING_ENV} is not set to 1; skipping embedding scoring."
    )

# Fix: add print
else:
    embedding_skipped_reason = (
        f"{EMBEDDING_SCORING_ENV} is not set to 1; skipping embedding scoring."
    )
    print(f"INFO: {embedding_skipped_reason}", file=sys.stderr, flush=True)
```

### 2. No per-question similarity logging during scoring

After `score_batch()` returns (line 342-344), the individual scores are silently stuffed into the results list. No per-question feedback is printed until the final report.

Add a per-question log line after scoring completes:

```python
# After score_batch, before the for-loop that assigns scores:
for i, score in enumerate(embedding_scores):
    flag = " (!)" if score is not None and score < EMBEDDING_WATCH_THRESHOLD else ""
    print(
        f"  [{questions[i]['id']}] embedding similarity: "
        f"{score:.3f}{flag}" if score is not None else "  (skipped)",
        file=sys.stderr, flush=True,
    )
```

### 3. No timing telemetry

Model load and scoring have no timing. The two existing `print` lines ("Loading embedding model...", "Scoring answers...") don't report elapsed time.

```python
import time

t0 = time.perf_counter()
emb_model = load_embedding_model()
print(f"Embedding model loaded in {time.perf_counter() - t0:.1f}s", file=sys.stderr, flush=True)

t1 = time.perf_counter()
embedding_scores = [float(s) for s in score_batch(emb_model, expected_summaries, answers)]
print(f"Embedding scoring completed in {time.perf_counter() - t1:.1f}s", file=sys.stderr, flush=True)
```

### 4. `embedding_scorer.py` has no logging at all

The module is entirely silent. Key places for logging:

- `load_embedding_model()`: log model ID, device, cache folder
- `embed_texts()`: log text count, vector dimension, elapsed time

### 5. Aggregate summary not printed to stderr

The `_embedding_tally()` result is written to JSON and markdown but never echoed to stderr the way strict/semantic verdicts are in `__main__`. This is already partially addressed — `__main__` prints `=== EMBEDDING ===` but only after the full run completes.

---

## Refinement areas beyond logging

### Watch threshold calibration

The current watch threshold (`EMBEDDING_WATCH_THRESHOLD = 0.70`) is a guess. After the first live run:

1. Examine the score distribution across all 15 questions.
2. Look for natural clusters (high-similarity correct answers vs low-similarity wrong/incomplete).
3. Correlate embedding scores with strict/semantic verdicts — do low embedding scores align with `fail_incomplete` verdicts?
4. Adjust the threshold based on observed data. If all passing answers are > 0.85, tighten. If some valid paraphrases score 0.65, loosen.

### Expected answer summary quality

5 legacy questions have newly authored `expected_answer_summary` values that haven't been reviewed against actual LLM output. After first run:

- Compare the expected summary against the actual LLM answer for questions where the embedding score is low.
- The expected summary may need tuning — too specific (penalizes valid paraphrase) or too vague (doesn't discriminate).

### Possible future scoring modes

- **Question+expected vs question+answer**: Embed the question concatenated with the expected summary, and the question concatenated with the answer. This grounds the similarity in the question context rather than just comparing prose.
- **Fact-anchor scoring**: Rather than comparing whole answers, embed individual fact anchors and check if each appears semantically in the answer. More granular than whole-answer similarity.
- **Multi-model comparison**: Run the same scoring with a second model (e.g., `all-mpnet-base-v2`) to validate that results aren't model-specific artifacts.

---

## Execution checklist

- Fix logging gaps (items 1-5 above)
- First live run with `DMB_EMBEDDING_SCORING=1`
- Review per-question scores and identify outliers
- Cross-reference embedding scores vs strict/semantic verdicts
- Calibrate watch threshold from observed distribution
- Review the 5 legacy `expected_answer_summary` values against actual answers
- Decide whether to promote embedding scoring from "watch" to "gate" status

