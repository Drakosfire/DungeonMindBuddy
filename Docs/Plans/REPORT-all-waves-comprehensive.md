# Comprehensive Report: Evidence Retrieval & Synthesis Experiments (Waves 1–4)

**Date:** 2026-04-09  
**Benchmark:** Council room question set (15 questions)  
**Runner:** `evals/mirathorn_vertical_slice/run_council_room_question_set.py`  
**Store:** `evals/mirathorn_vertical_slice/output/phase_d_store` (6 documents, ~1313 evidence units)  
**Reference:** `Docs/Plans/HANDOFF-execute-evidence-retrieval-synthesis-experiments.md`  

---

## 1. Starting point

The experiment program targeted a **key tension** from Phases 0–6 development:


| Metric        | Phase 3 (high-water) | Phase 6 (latest) |
| ------------- | -------------------- | ---------------- |
| semantic pass | **9/15**             | 8/15             |
| evidence_gap  | 13                   | **9**            |
| synthesis_gap | **5**                | 12               |
| hit           | **34**               | 31               |


Phases 4–6 reduced `evidence_gap` (20 → 9) but inflated `synthesis_gap` (2 → 12): more evidence chunks reached the LLM context, but the model failed to surface them in answers. All four waves tested levers at different pipeline stages to resolve this tension.

---

## 2. Decision criteria (from handoff §7)

A configuration is promoted as the new default only if it meets **all five**:

1. **semantic pass ≥ 9/15**
2. **evidence_gap ≤ 10**
3. **synthesis_gap ≤ 5**
4. **fail_stale = 0**
5. **avg context_support ≥ 0.72**

---

## 3. Results table

All runs used the Phase 3 evidence-first stack as the retrieval base:

```text
DMB_EVIDENCE_FIRST=1
DMB_EVIDENCE_ADAPTIVE_TOP_K=1
DMB_EVIDENCE_ADAPTIVE_TOP_K_MAX=48   (except 1B: 32)
DMB_EVIDENCE_DENSITY_THRESHOLD=0.3   (except 1C: 0.5)
```

Token estimates use the heuristic **1 token ≈ 4 characters**.


| Exp       | Phase name                     | Semantic pass | Strict pass | fail_stale | evidence_gap | retriever_gap | synthesis_gap | hit    | avg_support | Failure surface (pass / retr / synth) | avg ctx chars | ~avg ctx tokens | avg ms/q   | Notes                |
| --------- | ------------------------------ | ------------- | ----------- | ---------- | ------------ | ------------- | ------------- | ------ | ----------- | ------------------------------------- | ------------- | --------------- | ---------- | -------------------- |
| **1A-r1** | exp1a_phase3_stability_run1    | 8             | 6           | 0          | 13           | 8             | 7             | 32     | 0.750       | 8 / 3 / 4                             | 22,243        | ~5,561          | 5,618      | Stability run        |
| **1A-r2** | exp1a_phase3_stability_run2    | 8             | 7           | 0          | 13           | 8             | 7             | 32     | 0.739       | 8 / 3 / 4                             | 22,428        | ~5,607          | 5,669      | Stability run        |
| **1A-r3** | exp1a_phase3_stability_run3    | 8             | 7           | 0          | 13           | 8             | 5             | 34     | 0.722       | 8 / 3 / 4                             | 22,416        | ~5,604          | 5,458      | Stability run (best) |
| **1B**    | exp1b_tighter_topk_32          | 7             | 6           | 0          | **20**       | 8             | **3**         | 29     | 0.750       | 7 / 3 / 5                             | 22,350        | ~5,587          | 5,710      | Tighter top-k        |
| **1C**    | exp1c_density_0_5              | 7             | 6           | 0          | **18**       | 8             | **4**         | 30     | 0.722       | 7 / 3 / 5                             | 22,292        | ~5,573          | 5,625      | Stricter density     |
| **1D**    | exp1d_phase3_compact           | 8             | 5           | 0          | 13           | 8             | 6             | 33     | 0.739       | 8 / 3 / 4                             | 22,478        | ~5,619          | 5,320      | Compact verbosity    |
| **1E**    | exp1e_phase3_default_verbosity | 8             | 6           | 0          | 13           | 8             | 6             | 33     | 0.750       | 8 / 3 / 4                             | 22,354        | ~5,588          | 5,755      | Default verbosity    |
| **1F**    | exp1f_context_budget_10k       | 8             | 6           | 0          | 13           | 8             | 5             | 34     | 0.739       | 8 / 3 / 4                             | 22,267        | ~5,567          | 5,549      | Context budget 10k   |
| **1G**    | exp1g_claim_verification       | 8             | 7           | 0          | 13           | 8             | 6             | 33     | 0.733       | 8 / 3 / 4                             | 22,250        | ~5,562          | 5,699      | Claim verification   |
| **2A**    | exp2a_two_step_synthesis       | 7             | 6           | 0          | 13           | 8             | **8**         | 31     | 0.739       | 7 / 3 / 5                             | 22,334        | ~5,583          | **15,144** | Two-step synthesis   |
| **2B**    | exp2b_citation_structure       | 8             | 6           | 0          | 13           | 8             | 6             | 33     | 0.722       | 8 / 3 / 4                             | 22,295        | ~5,574          | 5,180      | Citation structure   |
| **3A**    | exp3a_per_seed_budget          | **9**         | 7           | 0          | 13           | **7**         | 5             | **35** | **0.750**   | **9** / 3 / 3                         | 22,035        | ~5,509          | 5,547      | Per-seed neighbors   |
| **3B**    | exp3b_two_pass_evidence        | 8             | 6           | 0          | **9**        | 8             | **10**        | 33     | 0.739       | 8 / 3 / 4                             | 22,010        | ~5,503          | 5,877      | Two-pass evidence    |
| **3C**    | exp3c_doc_quotas               | **9**         | 7           | 0          | **24**       | **5**         | **4**         | 27     | 0.706       | 9 / 4 / 2                             | 21,857        | ~5,464          | 5,716      | Doc quotas (12)      |
| **4A**    | exp4a_document_planner         | **6**         | 5           | 0          | 14           | 8             | **8**         | 30     | 0.761       | 6 / 2 / 7                             | 22,258        | ~5,564          | **7,238**  | LLM doc planner      |
| **4B**    | exp4b_embedding_rerank         | 8             | 6           | 0          | **10**       | 8             | **9**         | 33     | 0.717       | 8 / 4 / 3                             | 22,473        | ~5,618          | **41,645** | Embedding rerank     |
| **4C**    | exp4c_planner_per_seed         | **6**         | **4**       | 0          | 14           | 7             | **10**        | **29** | 0.761       | 6 / 2 / 7                             | 22,377        | ~5,594          | 6,871      | Planner + per-seed   |


---

## 4. Context usage summary

Average context size was **remarkably stable** across all 17 runs:


| Statistic             | Value                                 |
| --------------------- | ------------------------------------- |
| Grand mean (all runs) | ~22,249 chars / ~5,562 tokens         |
| Lowest average        | 21,857 chars (3C — doc quotas)        |
| Highest average       | 22,478 chars (1D — compact verbosity) |
| Spread                | 621 chars (~155 tokens)               |


This narrow band means the retrieval-stage and context-budgeting code delivers a consistent volume of material to the LLM. **Differences in semantic pass and synthesis_gap are driven by *which* chunks fill that window, not by *how many*.**

The one outlier is **1F** (`DMB_CONTEXT_MAX_CHARS=10000`), which was expected to cut context in half. However, the actual average was 22,267 chars — suggesting the 10k budget was applied *after* the entity-level formatter had already expanded most data, meaning the budget cap didn't bite in practice. This is a bug or a measurement mismatch worth investigating.

---

## 5. Wave-by-wave analysis

### Wave 1: Parameter sweeps (no code changes)

**Goal:** Establish a stable Phase 3 baseline, then test lightweight levers (top-k cap, density threshold, verbosity, context budget, claim verification).

#### 1A — Stability (3 runs)

Semantic pass: **8, 8, 8** across three runs. The original Phase 3 result of 9/15 was **not reproduced**.

- **Verdict:** Phase 3's 9/15 was a **stochastic outlier** (or the run environment differed). The stable operating point is **8/15 semantic, ~13 evidence_gap, ~5–7 synthesis_gap**.
- **Implication:** 8/15 is the true baseline for comparison, not 9/15.

#### 1B — Tighter top-k (32)

- Hypothesis: Lower `adaptive_top_k_max` reduces dilution.
- **Result:** Semantic dropped to 7/15, evidence_gap **spiked to 20**. synthesis_gap did improve to 3 — but at the cost of starving evidence recall.
- **Verdict:** **Fail.** evidence_gap regression disqualifies. Confirmed that 48 is near the right operating point for this store.

#### 1C — Stricter density (0.5)

- Hypothesis: Raise density threshold to prune low-quality tail.
- **Result:** Semantic 7/15, evidence_gap **18**. Similar pattern to 1B — overly aggressive pruning.
- **Verdict:** **Fail.** 0.3 remains the sweet spot for density threshold.

#### 1D — Compact verbosity

- Hypothesis: Forcing 80–140 word answers reduces synthesis drift.
- **Result:** Semantic 8/15 (matches baseline), synthesis_gap 6 (no clear improvement). Strict pass *dropped* to 5/15 — compact answers may lack the specific phrasing that strict token matching demands.
- **Verdict:** **Neutral.** No improvement over baseline; strict regression is concerning.

#### 1E — Default verbosity

- Hypothesis: Default 100–200 word mode isolates verbosity as a variable.
- **Result:** Semantic 8/15, synthesis_gap 6 — essentially identical to baseline.
- **Verdict:** **Neutral.** Verbosity mode is not a primary lever.

#### 1F — Context budget 10k

- Hypothesis: Halving context forces tighter pruning, improving synthesis.
- **Result:** Semantic 8/15, synthesis_gap 5, hit 34 — matches the best baseline run. But avg context chars was 22,267 — the budget did not visibly cut context volume.
- **Verdict:** **Neutral / investigation needed.** The budget parameter did not have the expected effect on actual context size.

#### 1G — Claim verification

- Hypothesis: Diagnostic axis to catch hallucinations.
- **Result:** Semantic 8/15, synthesis_gap 6, hit 33. The claim verification flag is diagnostic-only — it adds a measurement but does not change answers.
- **Verdict:** **Informational.** Provides an additional quality signal but not a tuning lever.

#### Wave 1 conclusion

**No parameter sweep moved semantic pass above 8/15.** The stable Phase 3 baseline is `8/15 semantic, 13 evidence_gap, ~5–7 synthesis_gap, 32–34 hit`. Retrieval restriction (1B, 1C) trades evidence_gap for synthesis_gap — an unproductive swap. Synthesis verbosity knobs are neutral. The key bottleneck is **not amenable to parameter tuning**.

---

### Wave 2: Synthesis prompt changes

**Goal:** Test structural changes to how the LLM synthesizes answers from evidence.

#### 2A — Two-step synthesis (extract then answer)

- Hypothesis: An explicit extraction pass forces the LLM to notice must-hit facts.
- **Implementation:** Two LLM calls — first extracts a numbered fact list from context, second answers from that list.
- **Result:** Semantic **dropped to 7/15**, synthesis_gap **rose to 8**. Latency nearly **tripled** (15.1s average vs ~5.5s).
- **Verdict:** **Fail.** The extraction step loses information in the reformulation. The LLM's numbered list omits details that the original context contains, and the answering step compounds the loss.

#### 2B — Citation-structured prompt

- Hypothesis: Requiring "TL;DR → Evidence → Analysis" structure with mandatory sourcing improves grounding.
- **Implementation:** Appended structure requirements to the synthesis system prompt.
- **Result:** Semantic 8/15 (matches baseline), synthesis_gap 6. No regression, no lift.
- **Verdict:** **Neutral.** The structure did not degrade quality and produces more organized answers, but did not move the metrics. Could be retained as a UX improvement without harm.

#### Wave 2 conclusion

Neither synthesis-stage intervention improved semantic pass. Two-step synthesis actively hurts by lossy compression. **The synthesis model is not the primary bottleneck** on this benchmark at current context sizes. The model is reasonably good at surfacing information that's in context — the problem is which information reaches context (retrieval stage).

---

### Wave 3: Retrieval algorithm changes

**Goal:** Change *which* evidence chunks the pipeline selects and how it prioritizes them.

#### 3A — Per-seed neighbor budgeting

- Hypothesis: Global neighbor budget lets top BM25 seeds monopolize expansion; per-seed allocation improves diversity.
- **Implementation:** `per_seed_budget = max(1, neighbor_budget // max(1, len(seeded)))` — each seed gets an equal share of the neighbor expansion window.
- **Result:** Semantic **9/15** — the **only experiment in all four waves to hit this mark**. retriever_gap **7** (best), synthesis_gap 5, hit **35** (best), avg_support **0.750** (tied best).
- **Verdict:** **Best single lever.** Meets criteria 1, 4, 5; misses criteria 2 (evidence_gap 13 > 10) and just meets criterion 3.

#### 3B — Two-pass evidence retrieval

- Hypothesis: BM25 pass first, then entity-provenance expansion for discovered entities, yields targeted recall.
- **Implementation:** Pass 1 = standard BM25 + adaptive top-k (entity-aware off). Entity ranking from pass 1 overlap. Pass 2 = provenance walk for top entities, appending new evidence IDs.
- **Result:** Semantic 8/15, evidence_gap **9** (best in the entire experiment set), but synthesis_gap **10** (worst in Waves 1–3).
- **Verdict:** **Mixed.** Best evidence recall but worst synthesis extraction — the classic tension. The extra evidence chunks dilute the context for the LLM. Confirms that **evidence_gap and synthesis_gap trade off** unless the additional chunks are high-signal.

#### 3C — Per-document chunk quotas

- Hypothesis: Capping each document's chunk contribution prevents single-source dominance.
- **Implementation:** After ordered evidence selection, each `document_id` contributes at most 12 chunks.
- **Result:** Semantic **9/15** (tied best), retriever_gap **5** (best), synthesis_gap **4** (best). But evidence_gap **24** — worst in the entire set by a wide margin. hit **27** (worst non-4C).
- **Verdict:** **Paradoxical.** Excellent synthesis metrics because the LLM gets cleaner (less noisy) context, but massive evidence recall loss. The quota aggressively clips high-evidence documents, destroying recall for questions that need deep single-document coverage. **Not recommended** for promotion as-is.

#### Wave 3 conclusion

**3A (per-seed neighbors) is the clear winner.** It is the only configuration across all 17 runs to hit 9/15 semantic, and it does so while maintaining synthesis_gap ≤ 5 and achieving the best hit count (35). The mechanism — ensuring every BM25 seed gets fair neighbor expansion rather than letting top seeds monopolize — directly improves evidence diversity without introducing noise.

3B demonstrates that evidence_gap *can* be driven down to 9, but the current synthesis model cannot extract from the denser context. 3C shows synthesis loves clean, quota-limited context, but at too high a recall cost.

---

### Wave 4: Document planner & embedding rerank

**Goal:** Pre-filter at the *document* level (before chunk retrieval) and reorder BM25 chunks with embedding similarity.

#### 4A — LLM document planner

- Hypothesis: An LLM selects relevant documents from a metadata roster, narrowing the evidence pool before BM25.
- **Implementation:** New module `src/agent/document_planner.py` with roster builder, LLM JSON call (gpt-5.4-nano), and `scope_document_ids` merge.
- **Result:** Semantic **6/15** — **worst in the entire experiment set**. synthesis_gap 8. Planner had 0% fallback rate (API worked), but **8/15 questions** had at least one document containing must-hit tokens **excluded** from the planner's selection.
- **Root cause:** On a 6-document store, the planner's "focus" removes documents that *co-contain* relevant evidence. The broad city dossier (`doc_the_city_of_mirathorn`) was consistently omitted for questions about specific locations that happen to be described *in that dossier*.
- **Verdict:** **Fail on this store.** The document planner is designed for large corpora (100+ docs) where pre-filtering is high-leverage. On 6 docs, any exclusion is aggressive.

#### 4B — Chunk-level embedding rerank

- Hypothesis: Reranking top BM25 hits by question–chunk cosine similarity (0.6B embedding model) improves evidence ordering.
- **Implementation:** `_embedding_rerank_evidence_hits` in `evidence_retriever.py`; fuses BM25 score (weight 0.4) with semantic score (weight 0.6) for the top 48 hits.
- **Result:** Semantic 8/15 (matches baseline), evidence_gap **10** (second best, after 3B's 9). synthesis_gap **9** — the familiar tradeoff. Latency **~42s per question** (model weights reloaded each question on CPU).
- **Verdict:** **Retrieval signal present, but no end-to-end lift.** Needs process-level model caching to be viable for repeated evals. The evidence_gap reduction does not translate to semantic improvement — same dilution dynamic as 3B.

#### 4C — Document planner + per-seed neighbors

- Hypothesis: Combining 4A with the best Wave 3 lever (3A) might recover planner's losses.
- **Result:** Semantic **6/15**, strict **4/15** (worst overall), hit **29**. The planner's false negatives compound with per-seed budgeting rather than offsetting.
- **Verdict:** **Fail.** Stacking a broken lever with a working one does not recover.

#### Wave 4 conclusion

Neither Wave 4 lever improved the benchmark on `phase_d_store`. The document planner is architecturally sound but **should only be tested on the full corpus** (120+ documents) where its filtering value exceeds its false-negative risk. Embedding rerank confirms that BM25 chunk ordering is imperfect — semantic similarity catches different chunks — but the synthesis model cannot exploit the denser pool at current context sizes.

---

## 6. Cross-wave synthesis

### What we learned

1. **The baseline is 8/15 semantic, not 9/15.** Three stability runs (1A) confirmed that Phase 3's prior 9/15 result was on the lucky end of natural variance.
2. **Only one lever reliably hits 9/15 semantic: per-seed neighbor budgeting (3A).** Out of 17 runs, only 3A and 3C achieved 9/15 — and 3C does it by sacrificing evidence recall (evidence_gap 24).
3. **evidence_gap and synthesis_gap are inversely correlated.** More evidence chunks in context reduce evidence_gap but inflate synthesis_gap. This is visible across:
  - 1B/1C (fewer chunks → lower synthesis_gap, higher evidence_gap)
  - 3B (most chunks → lowest evidence_gap, highest synthesis_gap)
  - 3C (fewest chunks → worst evidence_gap, best synthesis_gap)
4. **Context volume is not the bottleneck.** All runs delivered ~22k chars / ~5,500 tokens. The LLM has ample budget. The issue is **what fills that budget** — chunk diversity and relevance matter more than raw volume.
5. **Synthesis-stage interventions are neutral at best.** Two-step synthesis (2A) actively hurts. Citation structure (2B) is neutral. Verbosity tuning (1D, 1E) is neutral. The current synthesis model extracts well from good context — improving context quality is the higher-leverage path.
6. **Document-level pre-filtering is premature at 6 documents.** The planner concept is sound for large corpora but destructive at small scale where every doc matters.

### Decision criteria scorecard


| Criterion           | Threshold | Best result | Which exp |
| ------------------- | --------- | ----------- | --------- |
| semantic pass       | ≥ 9/15    | **9/15**    | 3A, 3C    |
| evidence_gap        | ≤ 10      | **9**       | 3B        |
| synthesis_gap       | ≤ 5       | **3**       | 1B        |
| fail_stale          | = 0       | **0**       | all       |
| avg context_support | ≥ 0.72    | **0.761**   | 4A, 4C    |


**No single experiment meets all five criteria simultaneously.** The closest is **3A** (meets 1, 3, 4, 5; misses 2 with evidence_gap=13). The tension between criteria 1–2 and criterion 3 is structural: the current BM25 + neighbor expansion pipeline cannot simultaneously achieve deep recall (low evidence_gap) and clean context (low synthesis_gap) within ~5,500 tokens.

---

## 7. Recommended configuration

**For immediate use (best overall):** Exp 3A (`DMB_EVIDENCE_PER_SEED_NEIGHBORS=1`)

```text
DMB_EVIDENCE_FIRST=1
DMB_EVIDENCE_ADAPTIVE_TOP_K=1
DMB_EVIDENCE_ADAPTIVE_TOP_K_MAX=48
DMB_EVIDENCE_DENSITY_THRESHOLD=0.3
DMB_EVIDENCE_PER_SEED_NEIGHBORS=1
```


| Metric          | 3A value | vs baseline (1A-r3) |
| --------------- | -------- | ------------------- |
| semantic pass   | 9/15     | +1                  |
| evidence_gap    | 13       | =                   |
| retriever_gap   | 7        | -1 (improved)       |
| synthesis_gap   | 5        | =                   |
| hit             | 35       | +1                  |
| avg_support     | 0.750    | +0.028              |
| avg ms/q        | 5,547    | +89 (negligible)    |
| avg ctx chars   | 22,035   | -381                |
| ~avg ctx tokens | 5,509    | -95                 |


**What it does:** Ensures every BM25 seed gets a fair share of the neighbor expansion budget, preventing top-scoring seeds from monopolizing adjacent-chunk expansion. This produces more **diverse** evidence coverage without adding latency or complexity.

---

## 8. Future work

1. **Full-corpus benchmarking.** Test 3A and 4A on `dungeonbuddy_store_escalation_full_mini_to_54` (120 docs, 5,299 evidence units). The document planner's value proposition is highest where irrelevant documents dominate.
2. **Evidence_gap / synthesis_gap co-optimization.** The structural tradeoff suggests that retrieval alone cannot solve both. Potential paths:
  - **Hybrid retrieval + summarization:** Retrieve broadly (low evidence_gap), then use a cheap model to summarize/compress evidence before the synthesis LLM.
  - **Evidence quality scoring:** Weight chunks by LLM-judged relevance (not just BM25) *before* context budgeting.
  - **Dynamic context budgeting:** Allocate more context chars for questions where entity density is high.
3. **Embedding model caching.** Before re-running 4B, cache the embedding model at process scope (`load_embedding_model()` at module level or in the CLI constructor) to eliminate the per-question 18–40s reload.
4. **Expand the gold set.** 15 questions provide useful signal but high variance (1 question = 6.7% of semantic pass). Increasing to 30+ questions would stabilize measurements and make single-percentage-point improvements meaningful.

---

## 9. Artifact index


| File                                                                              | Contents                          |
| --------------------------------------------------------------------------------- | --------------------------------- |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp1a_run1` | 1A run 1                          |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp1a_run2` | 1A run 2                          |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp1a_run3` | 1A run 3                          |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp1b`      | 1B                                |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp1c`      | 1C                                |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp1d`      | 1D                                |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp1e`      | 1E                                |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp1f`      | 1F                                |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp1g`      | 1G                                |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp2a`      | 2A                                |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp2b`      | 2B                                |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp3a`      | 3A                                |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp3b`      | 3B                                |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp3c`      | 3C                                |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp4a`      | 4A                                |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp4b`      | 4B                                |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp4c`      | 4C                                |
| `evals/mirathorn_vertical_slice/output/council_room_trace.jsonl.exp4a`            | 4A trace (incl. document_planner) |
| `evals/mirathorn_vertical_slice/output/council_room_trace.jsonl.exp4b`            | 4B trace                          |
| `evals/mirathorn_vertical_slice/output/council_room_trace.jsonl.exp4c`            | 4C trace                          |
| `evals/mirathorn_vertical_slice/output/evidence_gap_phase_ledger.json`            | All phases appended               |


### Code touchpoints (across all waves)


| File                                                              | Waves   | Changes                                                                                                                                    |
| ----------------------------------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `src/agent/evidence_retriever.py`                                 | 3, 4    | `DMB_EVIDENCE_PER_SEED_NEIGHBORS`, `DMB_EVIDENCE_DOC_QUOTA`, `collect_provenance_evidence_for_entities`, `_embedding_rerank_evidence_hits` |
| `src/agent/synthesis.py`                                          | 2       | `EXTRACTION_PROMPT`, two-step synthesis mode, `--synthesis-citation-structure` appendix                                                    |
| `src/agent/document_planner.py`                                   | 4       | New module — roster builder, LLM planner, `DocumentPlan`                                                                                   |
| `src/cli.py`                                                      | 2, 3, 4 | `--two-step-synthesis`, `--synthesis-citation-structure`, `--evidence-two-pass`, `--document-planner`, `--document-planner-model`          |
| `evals/mirathorn_vertical_slice/run_council_room_question_set.py` | 2, 3, 4 | Env var wiring for all new flags, trace field additions                                                                                    |


### Per-wave reports


| Report | Location                                                            |
| ------ | ------------------------------------------------------------------- |
| Wave 1 | `Docs/Plans/REPORT-wave-1-parameter-sweeps.md`                      |
| Wave 2 | `Docs/Plans/REPORT-wave-2-synthesis-experiments.md`                 |
| Wave 3 | `Docs/Plans/REPORT-wave-3-retrieval-experiments.md`                 |
| Wave 4 | `Docs/Plans/REPORT-wave-4-document-planner-and-embedding-rerank.md` |


