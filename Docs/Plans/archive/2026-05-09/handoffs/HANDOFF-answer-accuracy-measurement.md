# Handoff: Answer Accuracy Measurement

**Date:** 2026-04-07
**Prior work:** [Embedding scoring session](a073c164-9fc1-4c03-a888-2d71dd08bc22), `REPORT-embedding-scoring-session.md`
**Goal:** Fix the embedding scoring mismatch, tighten the synthesis prompt, then build a real accuracy measurement for LLM answers.

---

## 1. Diagnosis (from review of first live run)

### What the numbers say


| Metric               | Value | Assessment                                                           |
| -------------------- | ----- | -------------------------------------------------------------------- |
| Strict pass          | 6/15  | Token matching — misses answers that say the right thing differently |
| Semantic pass        | 10/15 | Better, but 5 still fail on keyword coverage                         |
| Embedding mean       | 0.594 | Misleadingly low — driven by structural mismatch, not bad answers    |
| Embedding max        | 0.801 | Best score is the most focused/concise answer (q_thalia)             |
| Below 0.70 threshold | 13/15 | Threshold is useless — flags good answers                            |


### Root cause: the embedding scores measure verbosity, not correctness

`expected_answer_summary` values are 15-30 word dense telegrams. LLM answers are 200-800 word structured GM references with headers, citations, key-attribute sections, and markdown. Embedding cosine similarity between a telegram and an essay about the same topic will always be moderate even when the essay is perfect.

Evidence: the two lowest-scoring answers (0.385, 0.389) are actually *more complete and useful* than their expected summaries. The highest-scoring answer (0.801) is the shortest and most focused.

### The answers themselves are good

Reading all 15 answers against the question intent and projection data:

- Facts are correctly grounded in CANON/OBSERVED/PREP with correct provenance
- Terminal outcomes quoted verbatim ("Decapitated; head removed from body")
- Conflicts between PREP and OBSERVED handled correctly (Wolf's escape vs death)
- One LLM artifact: Arabic word "سقوط" leaked into q_arch_delta answer (harmless but odd)
- Core problem areas are in the *strict/semantic scoring*, not in the answers

### The prompt is a working draft with one structural issue

`src/agent/synthesis.py` SYSTEM_PROMPT says "Keep the tone helpful and concise — this is a GM's quick reference, not a novel" but the Output Contract section forces Key Attributes enumeration that drives verbosity. Several answers spend tokens explaining *why* they can't list 3+ attributes from the specified set rather than just answering the question.

---

## 2. Tuning phases (prerequisite to accuracy work)

### Phase A: Reshape expected_answer_summary (editorial, no code)

**Problem:** Summaries are the wrong shape for what the system produces.

**Approach:** Don't change the summaries to match current output. Instead, add a new field `core_claims` — a list of 3-6 atomic factual claims the answer must contain. This is more useful than a prose summary for both embedding comparison and future accuracy checking.

**File:** `evals/mirathorn_vertical_slice/gold/gold_questions.json`

**Example transform for q_the_emergency_council_meeting_1:**

```json
{
  "expected_answer_summary": "They propose arcane lockdown wards for detection and containment, but at the cost of citywide disruption, panic risk, and festival cancellation.",
  "core_claims": [
    "Headmaster Tinkerbright / Wizard's College proposes the arcane measures",
    "The proposal involves magical lockdown and ward-based detection",
    "Wards do not distinguish friend from foe",
    "Risks include citywide disruption and restrictions on magic use",
    "Could trap innocent civilians"
  ]
}
```

**For embedding scoring:** concatenate `core_claims` into a single text block before embedding. This produces a ~50-100 word reference that is much closer in density to the LLM output's core content, without needing to match the output's formatting/structure.

**Work estimate:** 30-45 min to author core_claims for all 15 questions.

### Phase B: Tighten the synthesis prompt

**File:** `src/agent/synthesis.py`, lines 11-37 (SYSTEM_PROMPT)

**Changes:**

1. **Relax the Key Attributes contract.** Current: "list at least 3 explicitly named attributes... If fewer than 3... state that explicitly." Replace with: "If notable attributes (history, geography, demographics, economy, defenses) are present in the projection, list them briefly. Do not enumerate attributes absent from the context."
2. **Add a structured summary requirement.** Prepend the answer with a 1-2 sentence "TL;DR:" line that directly answers the question. This gives embedding scoring a focused target to extract and score against, without sacrificing the detailed body.
3. **Reinforce conciseness.** The current instruction is ignored. Strengthen to: "Aim for 100-200 words. Exceed only when the projection contains conflicting truth states that require explanation."

**Impact on embedding scoring:** If answers get shorter and include a TL;DR line, the embedding vector will be denser and closer to the expected summary's vector. Alternatively, the runner can extract just the TL;DR line for embedding comparison.

**Risk:** Changing the prompt changes all answer quality metrics. Re-run the full eval before and after to measure the delta. Save pre-change artifacts.

### Phase C: Calibrate the watch threshold

**File:** `evals/mirathorn_vertical_slice/run_council_room_question_set.py`, line 33

**Current:** `EMBEDDING_WATCH_THRESHOLD = 0.70`

**After Phase A + B re-run:** Set threshold empirically based on observed distribution:

- If the new mean is ~0.70-0.80, set threshold at p10 (roughly: mean - 1.5 * stdev)
- If the new mean is ~0.55-0.65 (still low), the threshold should be ~0.40 to flag genuine outliers

**Rule:** The threshold should flag <=3 answers, not 13. If it flags most answers, it provides no signal.

**Deferred decision:** Whether embedding scoring becomes a gate (fail/pass) vs remaining a watch metric depends on the variance after Phase A+B stabilize.

---

## 3. Accuracy measurement design (the real goal)

After tuning, none of the three scoring dimensions answer the core question: **is the answer factually correct given the projection data?**

- **Strict/semantic token scoring** checks keyword presence, not factual correctness
- **Embedding similarity** checks vector proximity to a reference, not grounding
- An answer could hit all tokens, score 0.90 on embedding, and still contain fabricated claims

### What "accuracy" means for this system

There are four dimensions of answer accuracy, ordered by severity:


| Dimension         | Question it answers                                           | Severity                                   |
| ----------------- | ------------------------------------------------------------- | ------------------------------------------ |
| **Hallucination** | Does the answer assert facts not in the projection?           | Critical — GM acts on false info           |
| **Completeness**  | Does the answer cover the key facts from the projection?      | High — GM misses important context         |
| **Provenance**    | Does the answer correctly label CANON vs OBSERVED vs PREP?    | Medium — GM confuses planning with reality |
| **Currency**      | Does the answer prefer OBSERVED over PREP when they conflict? | Medium — GM uses stale state               |


### Proposed approach: Claim extraction + store verification

**Concept:** Extract atomic claims from the LLM answer, then check each claim against the fact store.

```
LLM answer → claim extractor → list of atomic claims
                                        ↓
                               for each claim:
                                 - search store for supporting fact(s)
                                 - classify: grounded / unsupported / contradicted
                                        ↓
                               accuracy_score = grounded / total_claims
```

**Implementation sketch:**

#### Step 1: Claim extractor (LLM-based, one prompt call per answer)

A second LLM call that takes the answer and returns structured JSON:

```json
{
  "claims": [
    {
      "text": "Headmaster Tinkerbright proposes arcane lockdown",
      "type": "factual",
      "entity_refs": ["headmaster tinkerbright", "wizard's college"],
      "provenance_label": "OBSERVED"
    },
    {
      "text": "The wards do not distinguish between friend and foe",
      "type": "factual",
      "entity_refs": ["council chambers", "wards"],
      "provenance_label": "CANON"
    }
  ]
}
```

Claim types: `factual` (checkable against store), `interpretive` (reasonable inference — harder to check), `structural` (markdown/formatting — ignore).

#### Step 2: Claim verifier (store lookup, no LLM)

For each `factual` claim:

1. Find the referenced entities in the projection
2. Search their attributes for supporting facts (fuzzy text match or embedding similarity against fact value_labels)
3. Classify:
  - **grounded**: matching fact found in the projection with correct entity
  - **unsupported**: no matching fact found (possible hallucination)
  - **contradicted**: fact found but says the opposite
  - **provenance_mismatch**: fact found but wrong truth state label

#### Step 3: Accuracy metrics

```
hallucination_rate = (unsupported + contradicted) / total_factual_claims
completeness       = grounded / total_factual_claims  
provenance_accuracy = correct_provenance / total_factual_claims
```

### Alternative: LLM-as-judge (simpler, less precise)

A single LLM call that receives the projection context + the answer + a scoring rubric, returns a structured judgment. Faster to implement but less transparent — you can't trace *which* claim failed.

**Recommendation:** Start with claim extraction + store verification. It's more work but produces inspectable, debuggable output. The LLM-as-judge approach can be a fallback if claim extraction proves too noisy.

### Why this matters more than embedding scoring

Embedding scoring tells you "does this answer *feel like* the expected answer." Claim verification tells you "is this answer *true* according to the store." For a GM assistant, truth is the non-negotiable.

---

## 4. Execution plan

### Phase A: Reshape gold data (30-45 min, editorial)

- Add `core_claims` to all 15 gold questions
- Update `_load_gold_questions` to load `core_claims`
- Update `score_batch` call to use concatenated `core_claims` as the reference text
- Run eval, compare embedding scores to current baseline

### Phase B: Tighten synthesis prompt (30 min code, then re-run)

- Save current artifacts as `output/pre_prompt_tighten/`
- Edit SYSTEM_PROMPT in `src/agent/synthesis.py`
- Run full eval with `DMB_EMBEDDING_SCORING=1 DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1`
- Compare: did scores improve? Did answer quality change?
- If answers degraded, iterate on prompt

### Phase C: Calibrate threshold (10 min after B)

- Examine post-B embedding distribution
- Set `EMBEDDING_WATCH_THRESHOLD` to flag only genuine outliers (<=3 answers)
- Update tests if threshold constant changed

### Phase D: Claim extraction prototype (2-4 hours)

- Design claim extraction prompt
- Create `evals/mirathorn_vertical_slice/claim_verifier.py`
- Run claim extraction on all 15 answers
- Manually review extracted claims for quality
- Implement store lookup verification
- Compute accuracy metrics, compare against strict/semantic/embedding

### Phase E: Integration into runner (1-2 hours)

- Wire claim verification into `run_council_room_question_set.py` as a fourth scoring dimension
- Gate behind env var (e.g. `DMB_CLAIM_VERIFICATION=1`)
- Add accuracy metrics to JSON and markdown reports
- Add tests

---

## 5. Key files


| File                                                                   | Role                                                                        |
| ---------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| `evals/mirathorn_vertical_slice/gold/gold_questions.json`              | Gold data — add `core_claims`                                               |
| `src/agent/synthesis.py`                                               | Synthesis prompt — tighten                                                  |
| `evals/mirathorn_vertical_slice/run_council_room_question_set.py`      | Runner — update embedding reference text, wire claim verifier               |
| `evals/mirathorn_vertical_slice/embedding_scorer.py`                   | Embedding module — no changes expected                                      |
| `evals/mirathorn_vertical_slice/claim_verifier.py`                     | **New** — claim extraction + store verification                             |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json` | Current baseline results                                                    |
| `src/agent/context_formatter.py`                                       | Context formatter — read-only reference for understanding what the LLM sees |


---

## 6. Open questions

1. **Should the claim extractor use the same model as the synthesis LLM?** Using a different model avoids self-reinforcing bias. Using the same model is cheaper. Recommendation: use the same model initially, note it as a known limitation.
2. **How do we handle interpretive claims?** The LLM sometimes makes reasonable inferences ("this means Thalia is recoverable"). These aren't strictly in the store but aren't hallucinations either. Start by classifying them separately and not penalizing them in the accuracy score.
3. **Does changing the synthesis prompt invalidate existing benchmark comparisons?** Yes. Pin the current artifacts in `output/pre_prompt_tighten/` before changing anything. All future runs compare against the post-change baseline.
4. **Is 15 questions enough?** For tuning, yes. For statistical confidence in accuracy metrics, we'll want 30-50 eventually. But get the machinery working on 15 first.

---

*End of handoff.*