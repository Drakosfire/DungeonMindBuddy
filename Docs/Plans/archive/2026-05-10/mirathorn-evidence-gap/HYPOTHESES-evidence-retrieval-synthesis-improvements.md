# Hypotheses: improving evidence retrieval and answer quality

**Context:** Mirathorn council-room gold suite (15 questions), evidence-first pipeline, metrics from `evidence_gap_phase_ledger.json`, embedding scoring (Phase 6), relevance proxy, and whole-doc counterfactuals.

For each item: **hypothesis** → **expected outcome** → **how we’d falsify or confirm**.

---

## A. Document- and corpus-level gating (recall vs noise)

1. **H:** A **metadata-first document allowlist** (tags, campaign, source class, session, title/summary index) before chunk retrieval will **cut superfluous evidence** without dropping must-hit coverage if we keep a **fallback path** (e.g. merge global top-k when confidence is low or allowlist is empty).
  **Expected:** Lower average selected chunks/chars; **unchanged or improved** `context_support_ratio`; `evidence_gap` stable or down; watch for **retrieval_gap** if the router misses a doc.  
   **Measure:** `diagnostics.context_chars`, relevance proxy ratios, semantic pass, manual audit of allowlist misses.
2. **H:** A **small planner model** over a **tight doc index** (id, one-line summary, tags) will outperform keyword-only gating on **cross-doc** questions while staying cheaper than full chunk retrieval.
  **Expected:** Better precision on multi-doc questions; similar cost to one short LLM call + smaller embedding/BM25 pool.  
   **Measure:** Per-question allowlist size vs support ratio; A/B vs no gate.
3. **H:** **Hard filters** (e.g. `campaign_id`, `canon_layer`, `source_class`) applied **before** scoring will remove entire irrelevant strata with **near-zero recall cost** when metadata is accurate.
  **Expected:** Step-down in context size; flat or improved semantic pass on this campaign.  
   **Measure:** Ablation with filters on/off; spot-check for facts that live in “unexpected” layers.

---

## B. Chunk retrieval and ranking

1. **H:** **Tightening adaptive top-k** (lower max, stricter density threshold) after doc gating will **reduce dilution** and improve **synthesis_gap** (tokens in context but not in answer).
  **Expected:** Fewer `synthesis_gap` token counts; possible small rise in `evidence_gap` if k is too aggressive.  
   **Measure:** Stage loss report; per-question selected count.
2. **H:** Re-promoting **Phase 3–only** retrieval (adaptive top-k **without** entity-aware + verbose stack) will **restore the best observed semantic pass (9/15)** if later phases mainly added noise or variance.
  **Expected:** Semantic pass ≥ Phase 5 median; `evidence_gap` may rise vs Phase 4/5.  
   **Measure:** 3+ seeded ledger runs with fixed temperature if available.
3. **H:** **Per-doc quotas** (max chunks per document in the final context) will curb single-source dominance and improve **must-hit diversity** for questions that need multiple sources.
  **Expected:** Better roster / multi-entity questions; risk of splitting needed depth on single-doc questions.  
   **Measure:** Token stage matrix; failure surface by question type.
4. **H:** A **lightweight chunk-level embedding rerank** (reuse Phase 6 family model) on the **candidate pool after lexical seed** will lift **recall of paraphrased** must-hits vs lexicon alone.
  **Expected:** Lower `evidence_gap` on wording-drift cases; +latency and +compute.  
   **Measure:** Subset of questions with known paraphrase gaps; p95 latency in trace.

---

## C. Synthesis and prompting

1. **H:** A **two-step synthesis** (“extract grounded bullet claims from context” → “answer the user”) will **reduce synthesis_gap** when context is long or noisy.
  **Expected:** More must-hits in final answer; possible verbosity or latency cost.  
   **Measure:** Stage loss; strict vs semantic pass; user preference on length.
2. **H:** Requiring **explicit answer structure** (TL;DR + “Evidence:” cites) with **penalties for unsourced claims** will align outputs with **core_claims** and raise **embedding similarity** without changing retrieval.
  **Expected:** Higher Phase 6 embedding mean; possible strict token match noise if phrasing shifts.  
   **Measure:** `overall_embedding`; human spot-check.
3. **H:** **Shorter synthesis verbosity** (or dynamic length from question type) after retrieval improvements will **reduce hedge and drift** that causes incomplete must-hits.
  **Expected:** Fewer fail_incomplete; possible loss of nuance on open questions.  
    **Measure:** Semantic pass; stale rate.
4. **H:** **Question-type-conditioned prompts** (e.g. architecture/set-dressing vs factual roster vs causal “why”) will fix the **low embedding tail** on `q_arch_`* style prompts without hurting roster questions.
  **Expected:** Embedding p25 up; semantic pass stable.  
    **Measure:** Per-tag aggregates if questions are tagged.

---

## D. Store, extraction, and provenance

1. **H:** **Better entity resolution and aliases** (e.g. Bonogo → `ent_bonogo`) will shrink **retriever_gap** and wrong-entity evidence pulls.
  **Expected:** Higher post-filter relevance; fewer wrong roster answers.  
    **Measure:** Stage loss; targeted questions with known resolution bugs.
2. **H:** **More granular or better-located evidence units** (chunking, section_path) will reduce **store_gap** and **evidence_gap** for facts that are true in projection but never surface in selected chunks.
  **Expected:** Higher context support; possible ingestion cost.  
    **Measure:** Stage loss; context_support_ratio.
3. **H:** **Canon / time-aware retrieval** (prefer OBSERVED over PREP when the question is “current state”) will reduce **stale** answers and wrong-era facts.
  **Expected:** Fewer fail_stale; fewer contradictions.  
    **Measure:** Stale tokens; human review on timeline questions.

---

## E. Evaluation and gating

1. **H:** **Claim verification** (`DMB_CLAIM_VERIFICATION`) as a **second axis** will catch **hallucinations** that still pass must-hit token tests.
  **Expected:** Non-zero hallucination signal on some passes; complements embedding score.  
    **Measure:** `overall_accuracy` in runner; correlation with semantic pass.
2. **H:** Calibrating **embedding threshold by question cluster** (not one global 0.55) will improve **precision of automated regression alerts** without more human review.
  **Expected:** Fewer false alarms on architecture questions; still catch bad factual answers.  
    **Measure:** Precision/recall vs human labels on a small labeled set.
3. **H:** **Frozen golden subset + CI** on Phase 3 (or chosen default) with **deterministic or low-variance** settings will make **phase comparisons trustworthy**.
  **Expected:** Narrower variance across runs; slower iteration if API is required.  
    **Measure:** Stdev of semantic pass across N runs.

---

## F. Summary priority stack (suggested order to try)


| Priority | Hypothesis area               | Why                                                                      |
| -------- | ----------------------------- | ------------------------------------------------------------------------ |
| 1        | A (doc gating + fallback)     | Targets ~8× whole-doc inflation and ~83% superfluity proxy               |
| 2        | C8–C10 (synthesis)            | Stage loss shows **synthesis_gap** alongside compressed **evidence_gap** |
| 3        | B4–B6 (top-k / quotas)        | Cheap ablations; directly reduces dilution                               |
| 4        | D12–D14 (store/time/entities) | Fixes root causes that retrieval cannot fix                              |
| 5        | E (eval hardening)            | Makes “improved” claims provable                                         |


---

**Note:** Several hypotheses **trade off** (e.g. smaller k vs evidence_gap). Treat **expected outcomes** as directional; pair each change with **pre-registered** metrics and a **rollback** if retrieval_gap or semantic pass regresses.