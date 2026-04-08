# Report: Answer Accuracy Measurement Execution

**Date:** 2026-04-07  
**Scope:** Execute `Docs/Plans/HANDOFF-answer-accuracy-measurement.md` phases A-E (initial prototype level) and report empirical results.

---

## 1) What We Implemented

### A. Gold data reshaping (`core_claims`)

Updated `evals/mirathorn_vertical_slice/gold/gold_questions.json`:

- Added `core_claims` arrays to all 15 questions.
- Kept existing `expected_answer_summary` for backward compatibility.
- Runner now prefers concatenated `core_claims` for embedding reference text, falling back to `expected_answer_summary` if needed.

### B. Synthesis prompt tightening

Updated `src/agent/synthesis.py` `SYSTEM_PROMPT`:

- Added required leading `TL;DR:` line (1-2 sentences).
- Strengthened concision target to 100-200 words (except conflict-heavy cases).
- Relaxed `Key Attributes` contract to list only notable attributes present in context (no forced absent-attribute enumeration).

### C. Embedding calibration + TL;DR mode

Updated `evals/mirathorn_vertical_slice/run_council_room_question_set.py`:

- Set `EMBEDDING_WATCH_THRESHOLD = 0.55`.
- Added `DMB_EMBEDDING_USE_TLDR_ONLY=1` mode.
  - Extracts `TL;DR:`/`tldr:` line for embedding scoring.
  - Falls back to full answer when TL;DR is missing.
  - Emits mode/fallback stats in logs and summary.

### D. Claim verification prototype

Added new module: `evals/mirathorn_vertical_slice/claim_verifier.py`:

- Claim extraction:
  - Heuristic splitter (default path when LLM extractor disabled).
  - Optional LLM JSON-schema extractor (`DMB_CLAIM_VERIFICATION_USE_LLM_EXTRACTOR=1`).
- Claim verification against projection store:
  - `grounded`
  - `unsupported`
  - `contradicted`
  - `provenance_mismatch`
- Aggregate metrics:
  - `hallucination_rate`
  - `completeness`
  - `provenance_accuracy`

### E. Runner integration (4th scoring dimension)

Updated runner integration in `evals/mirathorn_vertical_slice/run_council_room_question_set.py`:

- New env gate: `DMB_CLAIM_VERIFICATION=1`.
- Writes `overall_accuracy` into JSON/markdown artifacts.
- Stores per-question `claim_verification` blocks.

---

## 2) Test and Lint Validation

Executed targeted tests after code changes:

- `uv run pytest tests/evals/test_claim_verifier.py tests/evals/test_council_room_question_set.py tests/evals/test_embedding_scorer.py tests/test_synthesis.py`
  - **25 passed, 1 skipped**
- `uv run pytest tests/evals/test_council_room_scoring.py tests/evals/test_council_room_question_set.py tests/evals/test_embedding_scorer.py`
  - **35 passed, 1 skipped**

Lint checks on touched files returned no errors.

---

## 3) Run Results Observed

## 3.1 Embedding after `core_claims` + threshold calibration (full-answer mode)

Observed run (user-provided):

- Mean: **0.6671**
- Min/Max: **0.5141 / 0.7926**
- Below threshold (0.40): **0/15** (too permissive, no triage signal)

Interpretation:

- Embedding distribution improved significantly vs the prior baseline.
- 0.40 threshold under-flags, so threshold raised to 0.55.

## 3.2 Embedding with TL;DR-only mode

Observed run with:

- `DMB_EMBEDDING_USE_TLDR_ONLY=1`
- `DMB_EMBEDDING_SCORING=1`
- `DMB_CLAIM_VERIFICATION=1`

Key metrics:

- Mean: **0.6540**
- Min/Max: **0.4153 / 0.8175**
- Below threshold (0.55): **3/15**
- TL;DR fallback to full answer: **0**

Interpretation:

- TL;DR mode reduced answer-side embedding time dramatically (from ~44s to ~4-5s).
- Threshold behavior became practical (small outlier set instead of all/none).

## 3.3 Full run with LLM claim extractor enabled

Command used:

`DMB_EMBEDDING_SCORING=1 DMB_EMBEDDING_USE_TLDR_ONLY=1 DMB_CLAIM_VERIFICATION=1 DMB_CLAIM_VERIFICATION_USE_LLM_EXTRACTOR=1 DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1 uv run python evals/mirathorn_vertical_slice/run_council_room_question_set.py`

Run summary:

- **Strict:** `pass_updated=7`, `fail_incomplete=8`
- **Semantic:** `pass_updated=13`, `fail_incomplete=2`
- **Embedding:** mean `0.6595`, min `0.3357`, below watch threshold `2` at `0.55`
- **Accuracy (`overall_accuracy`, extractor=`llm`):**
  - `total_factual_claims=208`
  - `hallucination_rate=0.5192`
  - `completeness=0.4231`
  - `provenance_accuracy=0.3152`

Compared to heuristic claim extraction run:

- Hallucination improved from ~`0.75 `to ~`0.52`
- Completeness improved from ~`0.23 `to ~`0.42`

Interpretation:

- LLM-based claim extraction materially improves the usefulness of accuracy metrics.
- Metrics are still noisy/harsh (especially provenance), but directionally better than heuristic extraction.

---

## 4) Files Changed

- `src/agent/synthesis.py`
- `evals/mirathorn_vertical_slice/gold/gold_questions.json`
- `evals/mirathorn_vertical_slice/run_council_room_question_set.py`
- `evals/mirathorn_vertical_slice/claim_verifier.py` (new)
- `tests/evals/test_claim_verifier.py` (new)
- `tests/evals/test_embedding_scorer.py`
- `tests/evals/test_council_room_question_set.py`
- `tests/evals/test_council_room_scoring.py`
- `tests/test_synthesis.py`

Runtime artifacts updated by eval runs:

- `evals/mirathorn_vertical_slice/output/council_room_question_set.json`
- `evals/mirathorn_vertical_slice/output/council_room_question_set.md`

---

## 5) Main Observations

- `core_claims` solved the biggest embedding-shape mismatch issue.
- TL;DR embedding mode improved speed and triage signal quality.
- Strict token scoring remains a low-recall metric by design.
- Semantic scoring is currently the most stable quick quality proxy (`13/15` in latest run).
- Claim verification prototype is operational but still prototype-grade:
  - Heuristic extractor is too pessimistic.
  - LLM extractor is better, but still needs calibration and noise controls.

---

## 6) Recommended Next Steps for Main Agent

1. **Promote LLM extractor as default for claim verification**
  Keep heuristic as fallback only.
2. **Reduce claim noise before scoring**
  Add stricter claim filtering (drop structural/meta/process lines; enforce minimum factual density).
3. **Improve contradiction detection**
  Current contradiction logic is narrow and mostly catches explicit opposites; expand lexical/attribute-aware negation handling.
4. **Stabilize provenance scoring**
  Only score provenance when claim explicitly provides a provenance assertion; do not penalize absent labels.
5. **Add visibility in console output**
  Print `overall_accuracy` block to stderr at script end (matching strict/semantic/embedding print behavior) to reduce JSON spelunking.
6. **Keep threshold at 0.55 for now**
  Current behavior flags a small outlier set and provides useful watch-list signal.

---

## 7) Repro Commands

Embedding + TL;DR + heuristic claim verifier:

`DMB_EMBEDDING_SCORING=1 DMB_EMBEDDING_USE_TLDR_ONLY=1 DMB_CLAIM_VERIFICATION=1 DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1 uv run python evals/mirathorn_vertical_slice/run_council_room_question_set.py`

Embedding + TL;DR + LLM claim verifier:

`DMB_EMBEDDING_SCORING=1 DMB_EMBEDDING_USE_TLDR_ONLY=1 DMB_CLAIM_VERIFICATION=1 DMB_CLAIM_VERIFICATION_USE_LLM_EXTRACTOR=1 DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1 uv run python evals/mirathorn_vertical_slice/run_council_room_question_set.py`

---

**Status:** Implemented and empirically validated at prototype level.  
**Recommendation:** Continue on LLM-claim-verifier calibration path; keep embedding as watch metric, not gate.