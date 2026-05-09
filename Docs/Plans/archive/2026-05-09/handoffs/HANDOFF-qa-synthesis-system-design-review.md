# Design Review: QA/Synthesis System — State of the World

**Date:** 2026-04-07
**Purpose:** Comprehensive report for the design agent covering what exists, what works, what's broken, and what needs design attention in the DungeonMindBuddy QA/Synthesis and evaluation pipeline.
**Prior conversation:** [Embedding scoring + accuracy measurement](a073c164-9fc1-4c03-a888-2d71dd08bc22)

---

## 1. System Overview

DungeonMindBuddy is a GM assistant that ingests tabletop RPG campaign documents, extracts structured facts into a store, and answers GM questions by projecting entity state and sending it to an LLM.

The pipeline for answering a question:

```
Question
  → FactStore.project(campaign_id)        # canon projection: latest-wins resolution
  → attach_scope_relevance_metadata()     # optional: scope filtering by document
  → format_projection_context()           # render entities + attributes as structured text
  → synthesize_answer_async()             # LLM call with SYSTEM_PROMPT + context
  → printed answer
```

The evaluation pipeline for measuring answer quality:

```
15 gold questions (gold_questions.json)
  → run each through the ask pipeline
  → score each answer four ways:
      1. Strict token matching (must_hit_tokens)
      2. Semantic token matching (equivalence groups)
      3. Embedding similarity (cosine similarity vs expected summary)
      4. Claim verification (extract claims, check against store)
  → generate JSON + markdown reports
```

---

## 2. What Exists (file inventory)

### Core pipeline


| File                              | Lines | Role                                                                                           |
| --------------------------------- | ----- | ---------------------------------------------------------------------------------------------- |
| `src/cli.py`                      | 1451  | CLI with `ask`, `ingest`, `entities`, `projection`, `compact`, `canon-decision` commands       |
| `src/store.py`                    | ~395  | JSON-backed FactStore: evidence units, entities, facts, canon decisions, event records, claims |
| `src/reducer/canon_projection.py` | ~367  | Canon projection: latest-wins fact resolution, truth state ranking, conflict detection         |
| `src/agent/context_formatter.py`  | 252   | Renders projection as structured text for the LLM, with scope annotations                      |
| `src/agent/synthesis.py`          | 148   | SYSTEM_PROMPT + LLM call via OpenAI API                                                        |
| `src/agent/scope_relevance.py`    | —     | Scope filtering: in_scope / out_of_scope / unknown classification                              |


### Evaluation infrastructure


| File                                                              | Lines | Role                                                                                                                                                                    |
| ----------------------------------------------------------------- | ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `evals/mirathorn_vertical_slice/gold/gold_questions.json`         | 512   | 15 gold questions with `must_hit_tokens`, `stale_tokens`, `semantic_equivalences`, `expected_answer_summary`, `core_claims`, `must_not_cooccur`, `update_signal_tokens` |
| `evals/mirathorn_vertical_slice/run_council_room_question_set.py` | 750   | Main eval runner: runs all 15 questions, applies 4 scoring dimensions, generates reports                                                                                |
| `evals/mirathorn_vertical_slice/embedding_scorer.py`              | 185   | Local embedding model (pplx-embed-v1-0.6B) via SentenceTransformers, cosine similarity scoring                                                                          |
| `evals/mirathorn_vertical_slice/claim_verifier.py`                | 376   | Claim extraction (heuristic + LLM) and verification against projection store                                                                                            |


### Test coverage


| File                                            | Tests | What it covers                                                                                                          |
| ----------------------------------------------- | ----- | ----------------------------------------------------------------------------------------------------------------------- |
| `tests/test_synthesis.py`                       | 4     | SYSTEM_PROMPT content, mock LLM call, response extraction                                                               |
| `tests/evals/test_council_room_scoring.py`      | 14    | Strict/semantic scoring, stale detection, unicode normalization, must_not_cooccur, TL;DR extraction, threshold constant |
| `tests/evals/test_council_room_question_set.py` | 4     | Runner campaign scoping, artifact write guards                                                                          |
| `tests/evals/test_embedding_scorer.py`          | ~12   | embed_texts shape, cosine similarity, score_batch, graceful skip, optional live model smoke                             |
| `tests/evals/test_claim_verifier.py`            | 5     | Heuristic extraction, fact index building, grounded/unsupported detection, aggregate rollup                             |


### Output artifacts (latest run)


| File                                                                   | Content                                                                            |
| ---------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json` | Full structured results: per-question verdicts, answers, claim_verification blocks |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.md`   | Human-readable markdown report                                                     |


### Environment variables controlling eval behavior


| Variable                                        | Values        | Effect                                                                                  |
| ----------------------------------------------- | ------------- | --------------------------------------------------------------------------------------- |
| `DMB_EMBEDDING_SCORING`                         | `1` to enable | Loads local embedding model, scores answers against core_claims/expected_answer_summary |
| `DMB_EMBEDDING_USE_TLDR_ONLY`                   | `1` to enable | Scores only the TL;DR line instead of full answer (faster, better signal)               |
| `DMB_CLAIM_VERIFICATION`                        | `1` to enable | Extracts claims from answers and verifies against projection store                      |
| `DMB_CLAIM_VERIFICATION_USE_LLM_EXTRACTOR`      | `1` to enable | Uses LLM for claim extraction instead of heuristic sentence splitter                    |
| `DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS` | `1` to enable | Allows writing output JSON/markdown (prevents accidental clobber in CI)                 |


---

## 3. What Works Well

### The ask pipeline is production-quality for its scope

The end-to-end path from question to answer is solid. The context formatter renders entities with truth states, provenance, and conflict annotations. The projection reducer correctly resolves latest-wins across sessions with temporal ordering. Scope relevance filtering correctly prunes irrelevant entities.

**Evidence:** 13/15 questions pass semantic scoring. All 15 answers are well-grounded when read by a human. No hallucinated entities, no fabricated events. Provenance labels (CANON/OBSERVED/PREP) are applied correctly in the answers.

### The synthesis prompt produces good answers

After tightening (TL;DR requirement, conciseness target, relaxed Key Attributes), the LLM consistently:

- Opens with a direct TL;DR line answering the question
- Distinguishes CANON vs OBSERVED vs PREP provenance
- Quotes terminal outcomes verbatim ("Decapitated; head removed from body")
- Handles conflicts between PREP and OBSERVED correctly (e.g., Wolf's planned escape vs observed death)

### Strict and semantic token scoring are calibrated and useful

Strict scoring (7/15 pass) catches exact-match gaps. Semantic scoring (13/15 pass) demonstrates that equivalence groups work — "decapitated" satisfies "killing blow," "ward lockdown" satisfies "arcane lockdown." The 2 semantic failures are legitimate: the answer for q_longmont_session_12_council_chamber_roster correctly notes Ephanna is absent (failing the `must_hit_token` for "ephanna" due to `must_not_cooccur`), and q_the_city_council_4 misses specific council role terms.

### The gold question format is well-structured

Each question carries: `must_hit_tokens`, `stale_tokens`, `semantic_equivalences`, `update_signal_tokens`, `must_not_cooccur`, `expected_answer_summary`, and `core_claims`. The `must_not_cooccur` mechanism (added to handle "Ephanna was absent" false positives) is a clean solution to a real problem.

### Embedding infrastructure is operational

The local pplx-embed-v1-0.6B model loads, embeds, and scores. HuggingFace cache hardening handles unwritable HF_HOME. TL;DR-only mode reduces embedding time from ~44s to ~5s and produces better signal. The `core_claims` concatenation for reference text improved mean embedding similarity from ~0.59 to ~0.66.

---

## 4. What's Broken or Unreliable

### 4.1 Claim verification scoring is fundamentally miscalibrated

**This is the most important issue.** The claim verifier reports:

- `hallucination_rate: 0.5192` (108 of 208 claims "unsupported")
- `completeness: 0.4231`
- `provenance_accuracy: 0.3152`

These numbers are almost entirely measurement artifacts.

**Root cause: `_score_claim_to_fact` uses raw word-token overlap with no stopword removal.**

```python
# claim_verifier.py lines 211-217
def _score_claim_to_fact(claim_text: str, fact_text: str) -> float:
    claim_tokens = _tokenize(claim_text)
    fact_tokens = _tokenize(fact_text)
    if not claim_tokens or not fact_tokens:
        return 0.0
    overlap = len(claim_tokens & fact_tokens)
    return overlap / max(1, len(claim_tokens))
```

Common words ("the", "a", "of", "in", "is") inflate the denominator without contributing to semantic matching. A claim like "The wizards, via Headmaster Tinkerbright, propose an arcane lockdown of the city" tokenizes to ~11 unique words. Even when the best-matching fact is semantically correct, word overlap rarely exceeds the `grounded_threshold` of 0.55.

**Concrete example from the latest run:**

```json
{
  "claim": "The wizards, via Headmaster Tinkerbright, propose an arcane lockdown of the city.",
  "status": "unsupported",
  "score": 0.3636,
  "matched_fact": {
    "entity_name": "Headmaster Tinkerbright",
    "attribute": "governance",
    "value": "on a successful persuasion, offers to use the Wizards' College detection spell"
  }
}
```

This claim is obviously grounded in the projection. The scorer cannot see that.

**Three sub-problems:**

1. No stopword removal — common English words dilute the signal
2. `grounded_threshold` of 0.55 is too high for word overlap
3. Each claim is matched to only one fact, but claims often synthesize across multiple entity attributes

**Impact:** The hallucination rate of 52% is probably closer to <10% in reality. Every metric derived from claim verification is unreliable until the scorer is fixed.

### 4.2 Provenance accuracy scoring penalizes absence

`provenance_accuracy` (0.3152) counts claims without provenance labels as wrong. But many legitimate claims don't assert a specific provenance. The metric should only score claims that explicitly state a provenance label.

Current behavior:

```python
# claim_verifier.py lines 267-270
if isinstance(provided_provenance, str) and provided_provenance.upper() in PROVENANCE_LABELS:
    claims_with_provenance += 1
    provided_provenance = provided_provenance.upper()
```

This filter is correct — it only counts claims with explicit provenance labels. But the low `provenance_accuracy` (0.3152) comes from the fact that many provenance-labeled claims are scored as "unsupported" or "provenance_mismatch" because the underlying `_score_claim_to_fact` match is wrong, not because the provenance label is wrong.

### 4.3 Contradiction detection is narrow

```python
# claim_verifier.py lines 220-231
def _is_potential_contradiction(claim: str, fact: str) -> bool:
    # Only checks alive/dead and corrupted/not corrupted
```

This catches exactly two semantic oppositions. Any other type of contradiction (e.g., "escaped" vs "killed," "present" vs "absent") is invisible. The function reported 0 contradictions in the latest run, which is plausible for this corpus but not generalizable.

### 4.4 `overall_accuracy` block is not printed to stderr

The runner prints `=== STRICT ===`, `=== SEMANTIC ===`, `=== EMBEDDING ===` to stderr at the end, but omits `=== ACCURACY ===`. This means claim verification results require JSON inspection to see.

### 4.5 Embedding watch threshold is arbitrary

`EMBEDDING_WATCH_THRESHOLD = 0.55` was set after one iteration. The current distribution (min 0.34, median 0.66, max 0.79) flags 2/15. The threshold needs further calibration after scoring improvements, but it's functional for now.

### 4.6 Minor: Arabic text leak in synthesis output

One answer (q_the_emergency_council_meeting_1) contains "संकट" — a Hindi/Sanskrit word that has nothing to do with the D&D campaign. This is an LLM artifact, likely from the model's training data bleeding through when it encountered "crisis" in context. Harmless but worth noting as a signal of prompt boundary weakness.

---

## 5. The Live Testing Story

### What exists today

The existing `ask` command in `src/cli.py` is a fully functional live query interface:

```bash
uv run python -m src.cli --store evals/mirathorn_vertical_slice/output/phase_d_store
dungeonbuddy> ask "What does the council room look like?" --campaign longmont-c1 --require-campaign
```

This runs the full pipeline (projection → context → LLM → answer) and logs timing/metrics to JSONL. No new code needed for live testing.

### What the scoring infrastructure adds

The four scoring dimensions were built for batch evaluation of gold questions, not interactive use:

- **Strict/semantic scoring** requires pre-authored `must_hit_tokens` — not available for ad-hoc questions
- **Embedding scoring** has a ~20s cold-start for model loading
- **Claim verification** produces unreliable numbers (see §4.1) and adds either heuristic noise or an extra LLM call per question

### Recommended live testing workflow

1. Use the existing `ask` command for ad-hoc questions
2. Human judgment is currently the highest-quality accuracy signal
3. Note interesting failures as candidate gold questions
4. Promote to `gold_questions.json` with `core_claims` and `must_hit_tokens`
5. Run batch eval periodically to track quality trends

---

## 6. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         src/cli.py                              │
│                                                                 │
│  ask command ──────────────────────────────────────────────┐     │
│  │                                                        │     │
│  │  FactStore.project(campaign_id)                        │     │
│  │    └── canon_projection.py: latest-wins resolution     │     │
│  │                                                        │     │
│  │  attach_scope_relevance_metadata() [optional]          │     │
│  │    └── scope_relevance.py: in/out/unknown bucketing    │     │
│  │                                                        │     │
│  │  format_projection_context()                           │     │
│  │    └── context_formatter.py: entity→text rendering     │     │
│  │                                                        │     │
│  │  synthesize_answer_async()                             │     │
│  │    └── synthesis.py: SYSTEM_PROMPT + OpenAI call       │     │
│  │                                                        ▼     │
│  │  print(answer) ────────────────────────────── [stdout]       │
│  └──────────────────────────────────────────────────────────     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│          evals/mirathorn_vertical_slice/                        │
│                                                                 │
│  run_council_room_question_set.py                               │
│  │                                                              │
│  │  for each gold question:                                     │
│  │    cli.handle_line('ask "..." --campaign ...')                │
│  │    ├── classify_answer()          → strict verdict            │
│  │    ├── classify_answer_semantic() → semantic verdict          │
│  │    ├── embedding_scorer.py        → cosine similarity  [opt] │
│  │    └── claim_verifier.py          → accuracy metrics   [opt] │
│  │                                                              │
│  │  _tally() → overall_strict, overall_semantic                 │
│  │  _embedding_tally() → overall_embedding                      │
│  │  aggregate_accuracy() → overall_accuracy                     │
│  │                                                              │
│  └── write JSON + markdown artifacts                            │
│                                                                 │
│  gold/gold_questions.json (15 questions)                        │
│  embedding_scorer.py (pplx-embed-v1-0.6B, local)               │
│  claim_verifier.py (heuristic + LLM claim extraction)           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Latest Empirical Results

From the most recent full run (all scoring dimensions enabled, LLM claim extractor):

```
Strict:    pass_updated=7   fail_incomplete=8   fail_stale=0   fail_error=0
Semantic:  pass_updated=13  fail_incomplete=2   fail_stale=0   fail_error=0
Embedding: mean=0.6595  min=0.3357  median=0.6598  max=0.7911  below_0.55=2
Accuracy:  hallucination_rate=0.5192  completeness=0.4231  provenance_accuracy=0.3152
           (208 total claims, 88 grounded, 108 unsupported, 0 contradicted, 12 provenance_mismatch)
```

**Interpretation:** Strict and semantic scoring are reliable. Embedding scoring is directionally useful. Claim verification numbers are measurement artifacts — the true hallucination rate is estimated at <10% based on manual review of all 15 answers.

---

## 8. What Needs Design Attention

### 8.1 Fix the claim-to-fact scoring mechanism (HIGH — blocks accuracy measurement)

The `_score_claim_to_fact` function needs a fundamental upgrade. Three options, in order of increasing sophistication:

**Option A: Stopword removal + lower threshold.** Quick fix. Remove ~50 common English stopwords from both sides before computing word overlap. Lower `grounded_threshold` from 0.55 to ~0.30. Estimated improvement: cuts false-unsupported rate by ~50%.

**Option B: Embedding-based claim-to-fact matching.** Use the already-loaded pplx-embed model to compute cosine similarity between claim text and each fact's search_text. More semantically robust than word overlap. Requires the embedding model to be loaded (adds ~20s to first claim verification run).

**Option C: Hybrid.** Use word overlap as a cheap prefilter (top-K candidates), then embedding similarity for final scoring. Best accuracy with reasonable cost.

**Design question:** Should claim verification require the embedding model, making it heavier but more accurate? Or should the heuristic path remain lightweight and independent?

### 8.2 Multi-fact claim grounding (MEDIUM)

Claims often synthesize across multiple facts and entities. "Headmaster Tinkerbright proposes arcane lockdown" draws from `role`, `governance`, and `goals` attributes. The current single-best-fact-match architecture cannot handle this.

**Design question:** Should the verifier match entity_refs from the LLM claim extractor against projection entity IDs as a prerequisite? Should it sum top-K fact overlaps instead of taking the single best?

### 8.3 Decide the role of claim verification (MEDIUM)

Currently claim verification is a "fourth scoring dimension" alongside strict, semantic, and embedding. But it measures something fundamentally different — factual accuracy vs keyword/similarity coverage.

**Design question:** Is claim verification:

- A **gate** (must pass to ship)? Not ready — too noisy.
- A **watch metric** (flag regressions)? Reasonable once calibrated.
- A **debugging tool** (inspect individual claim outcomes)? Currently its best use.
- An **accuracy benchmark** (ground truth for model comparison)? The end goal, but requires calibration.

### 8.4 Gold question expansion (LOW — after calibration)

15 questions cover the Mirathorn council room vertical slice well. For statistical confidence in accuracy metrics, 30-50 questions are needed. But expanding the gold set before fixing claim verification wastes effort — new questions would inherit the same measurement noise.

### 8.5 Synthesis prompt iteration (LOW — current prompt is adequate)

The prompt works. Two minor issues:

1. Some answers still enumerate absent Key Attributes despite the relaxed contract
2. The TL;DR line quality varies — some are too long, some restate the question

These are optimization, not design problems.

---

## 9. Repro Commands

**Run the full eval with all scoring:**

```bash
DMB_EMBEDDING_SCORING=1 \
DMB_EMBEDDING_USE_TLDR_ONLY=1 \
DMB_CLAIM_VERIFICATION=1 \
DMB_CLAIM_VERIFICATION_USE_LLM_EXTRACTOR=1 \
DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1 \
uv run python evals/mirathorn_vertical_slice/run_council_room_question_set.py
```

**Run tests:**

```bash
uv run pytest tests/evals/test_claim_verifier.py \
             tests/evals/test_council_room_scoring.py \
             tests/evals/test_council_room_question_set.py \
             tests/evals/test_embedding_scorer.py \
             tests/test_synthesis.py -v
```

**Live interactive testing:**

```bash
uv run python -m src.cli --store evals/mirathorn_vertical_slice/output/phase_d_store
dungeonbuddy> ask "Your question here" --campaign longmont-c1 --require-campaign
```

---

## 10. Summary for the Design Agent

**What's solid and should not be redesigned:**

- The ask pipeline (projection → context → LLM → answer)
- Gold question format and strict/semantic scoring
- Embedding infrastructure and TL;DR mode
- The CLI `ask` command for live testing

**What needs design work:**

1. `_score_claim_to_fact` is broken and blocks all accuracy measurement (§8.1)
2. Multi-fact claim grounding needs a design decision (§8.2)
3. The role of claim verification in the overall eval framework needs definition (§8.3)

**What can wait:**

- Gold question expansion (§8.4)
- Synthesis prompt refinement (§8.5)
- Promoting embedding from watch to gate

**The single most impactful change:** Fix the claim-to-fact scorer. Everything else in the accuracy measurement pipeline is architecturally sound but produces garbage numbers because the matching function is too crude. Once that's fixed, the claim verification results become trustworthy and the system can be calibrated.

---

*End of design review.*