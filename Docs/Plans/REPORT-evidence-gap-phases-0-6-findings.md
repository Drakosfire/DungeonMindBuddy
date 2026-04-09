# Report: Evidence gap rollout (Phases 0–6) — findings

**Date:** 2026-04-09  
**Benchmark:** Mirathorn vertical slice — council room gold set (`evals/mirathorn_vertical_slice/gold/gold_questions.json`), **15 questions**.  
**Store:** `evals/mirathorn_vertical_slice/output/phase_d_store`.  
**Runner:** `evals/mirathorn_vertical_slice/run_council_room_question_set.py`.

---

## 1. Executive summary

- **Phases 0–5** iterated on evidence-first retrieval (lexicon boost, alias normalization, adaptive top-k, entity-aware expansion, synthesis profile/verbosity). **Phase 3 (adaptive top-k)** achieved the best **semantic** pass rate (**9/15**) and a favorable **failure-surface** split in that checkpoint run.
- **Phases 4–5** often **reduced token-level `evidence_gap`** but did not reliably improve semantic pass; Phase 5 introduced **one stale** failure and slightly lower context support in the ledger snapshot.
- **Phase 6** (this session) is **not** a retrieval change: it enables **embedding similarity scoring** between `core_claims` (reference text) and the answer’s **TL;DR** line (`DMB_EMBEDDING_SCORING=1`, `DMB_EMBEDDING_USE_TLDR_ONLY=1`) on top of the **Phase 5-equivalent CLI flags**. It adds a **continuous alignment signal** orthogonal to token-based must-hit scoring.
- **Embedding results (Phase 6 run):** mean cosine similarity **0.626**, median **0.613**, **3/15** below watch threshold **0.55**. Lowest scores clustered on **architecture / scene-description** questions (`q_arch_current`, `q_arch_delta`, `q_the_emergency_council_meeting_4_v2`).
- **Noise proxy:** A strict “must-hit token appears in chunk text” proxy flags **~83%** of selected evidence characters as superfluous — useful for trend analysis, not literal waste.
- **Whole-document counterfactual:** If every **retrieval-selected document** were fully loaded per question, context would average **~219k characters** vs **~26k** for selected chunks (**~8.5×**), with only **6** unique source docs across the suite.

---

## 2. Phase definitions (what actually changed)


| Phase | Knobs (conceptual)                                                           |
| ----- | ---------------------------------------------------------------------------- |
| **0** | Evidence-first baseline + diagnostics / ledger scaffolding                   |
| **1** | Corpus lexicon boost + path to `corpus_lexicon.json`                         |
| **2** | + Alias / acronym normalization                                              |
| **3** | + Adaptive top-k (max 48, density threshold 0.3)                             |
| **4** | + Entity-aware provenance expansion (quotas)                                 |
| **5** | + `mirathorn` synthesis profile + verbose verbosity                          |
| **6** | **Same pipeline as 5** + **local embedding scorer** (TL;DR vs `core_claims`) |


---

## 3. Ledger metrics (all recorded runs)

Source: `evals/mirathorn_vertical_slice/output/evidence_gap_phase_ledger.json`.

### 3.1 Semantic scoring (`pass_updated` / `fail_incomplete`)


| Phase | pass_updated | fail_incomplete | fail_stale |
| ----- | ------------ | --------------- | ---------- |
| 0     | 8            | 7               | 0          |
| 1     | 7            | 8               | 0          |
| 2     | 8            | 7               | 0          |
| 3     | **9**        | **6**           | 0          |
| 4     | 8            | 7               | 0          |
| 5     | 7            | 7               | **1**      |
| 6     | 8            | 7               | 0          |


**Interpretation:** Phase 3 is the **best single checkpoint** on this metric. Phase 6 matches Phase 2/4 on *semantic* pass count (8 passes) but **does not change retrieval**; treat small swings vs Phase 5 as **stochastic synthesis** unless reproduced with fixed sampling.

### 3.2 Failure surface (question-level)


| Phase | pass  | retrieval_gap | synthesis_gap |
| ----- | ----- | ------------- | ------------- |
| 0     | 8     | 4             | 3             |
| 1     | 7     | 4             | 4             |
| 2     | 8     | 3             | 4             |
| **3** | **9** | **3**         | **3**         |
| 4     | 8     | 4             | 3             |
| 5     | 7     | 4             | 4             |
| 6     | 8     | 4             | 3             |


### 3.3 Stage loss (token × stage counts — ledger `stage_loss_report`)


| Phase | store_gap | evidence_gap | retriever_gap | synthesis_gap | hit |
| ----- | --------- | ------------ | ------------- | ------------- | --- |
| 0     | 0         | 20           | 8             | 2             | 30  |
| 1     | 0         | 20           | 8             | 3             | 29  |
| 2     | 0         | 15           | 7             | 8             | 30  |
| 3     | 0         | 13           | 8             | 5             | 34  |
| 4     | 0         | **9**        | 8             | **10**        | 33  |
| 5     | 0         | **9**        | 8             | **10**        | 33  |
| 6     | 0         | **9**        | 8             | 12            | 31  |


**Interpretation:** **Evidence_gap** shrinks from Phase 3 → 4/5/6, but **synthesis_gap** tokens often **increase** — retrieved text is closer to containing must-hits, yet the model still **fails to surface** them in the answer for some tokens. That motivates **prompt/synthesis** work and/or **narrower context** (less dilution).

### 3.4 Context support (avg `context_support_ratio`)


| Phase | avg_support_ratio |
| ----- | ----------------- |
| 0–3   | 0.7278–0.7389     |
| 4     | 0.7000            |
| 5     | 0.6889            |
| 6     | 0.7055            |


Slight dip under entity-aware + verbose stack; still **9/15** questions ≥ 0.75 support ratio in Phase 6.

---

## 4. Phase 6 — embedding scoring (executed 2026-04-09)

**Command pattern (env vars):** Phase 5 pipeline + `DMB_EMBEDDING_SCORING=1`, `DMB_EMBEDDING_USE_TLDR_ONLY=1`, `DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1`, `DMB_PHASE_WRITE_LEDGER=1`.

**Model (local):** `perplexity-ai/pplx-embed-v1-0.6B` via `sentence-transformers` (see run stderr: load ~8s, batch encode ~12.5s for 15+15 texts).

**Reference side:** Joined `core_claims` per question (fallback to `expected_answer_summary` if needed).  
**Answer side:** First `TL;DR:` / `tldr:` line only (`fallback_to_full_answer=0` in this run).

**Aggregate (`overall_embedding` in `council_room_question_set.json`):**


| Metric                       | Value  |
| ---------------------------- | ------ |
| scored_count                 | 15     |
| mean                         | 0.6262 |
| min                          | 0.3255 |
| p25                          | 0.5260 |
| median                       | 0.6132 |
| max                          | 0.8146 |
| below_watch_threshold (0.55) | 3      |


**Per-question tail (below 0.55):** `q_arch_current` (~~0.326), `q_arch_delta` (~~0.403), `q_the_emergency_council_meeting_4_v2` (~0.526).

**High alignment (examples):** `q_thalia` ~0.815, `q_battle_with_the_wolf_and_aftermath_3` ~0.789, roster / wolf status mid-high 0.77–0.77.

**Takeaway:** Embedding similarity **correlates imperfectly** with must-hit semantic pass: some **pass_semantic** items have moderate embedding scores; some **fails** align with **low embedding** on “vibe-heavy” descriptive prompts. Use as **diagnostic / ranking**, not sole gate, until calibrated against human judgment.

---

## 5. Evidence “superfluity” proxy

Source: `evals/mirathorn_vertical_slice/output/evidence_context_relevance_proxy.json`.

- **~83%** of selected evidence characters labeled **superfluous** by the rule: chunk contains **no** must-hit token (and equivalents) as literal/regex-semantic check.
- **Caveat:** Chunks can be **indirectly** supportive (reasoning glue, entity disambiguation). Treat as **upper bound on noise**, not ground truth.

---

## 6. Whole-document counterfactual

Source: `evals/mirathorn_vertical_slice/output/whole_document_if_golden_analysis.json`.


| Metric                                                           | Value             |
| ---------------------------------------------------------------- | ----------------- |
| Avg selected chunk chars / question                              | ~25,887           |
| Avg whole-doc chars (all chunks in **selected docs**) / question | ~219,481          |
| Multiplier                                                       | ~8.48×            |
| Unique docs across all 15 questions                              | 6                 |
| Union whole corpus (6 docs, once)                                | **265,963** chars |


**Note:** “Selected docs” = docs touched by retrieval for that question, **not** minimal docs for a gold answer.

---

## 7. Recommendations

1. **Default retrieval promotion candidate:** Re-run **Phase 3** with **multiple seeds** to confirm the **9/15** semantic pass is stable vs Phase 4/5 before locking entity-aware + verbose as default.
2. **Synthesis:** Address **synthesis_gap** (tokens in context but not answer) with **shorter context targets**, **stronger citation-to-answer instructions**, or **two-step** “extract facts → answer”.
3. **Phase 6 embeddings:** Keep **TL;DR-only** mode when answers are long. Calibrate **watch_threshold** (currently **0.55** in code) against human ratings; consider **per-question-type** thresholds for architecture prompts.
4. **Doc-level pruning (future):** Metadata-first **document allowlists** before chunk retrieval align with the **8× whole-doc inflation** finding and the superfluity proxy; pair with **fallback** retrieval to protect recall.
5. **Claim verification:** Phase 6 run had `DMB_CLAIM_VERIFICATION` off; enable for a future pass to cross-check **factual** accuracy vs embedding **semantic** similarity.

---

## 8. Artifacts


| Artifact                                                                       | Role                                           |
| ------------------------------------------------------------------------------ | ---------------------------------------------- |
| `evals/mirathorn_vertical_slice/output/evidence_gap_phase_ledger.json`         | Phase-to-phase metrics                         |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json`         | Latest full summary + per-question + embedding |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.md`           | Human-readable mirror                          |
| `evals/mirathorn_vertical_slice/output/council_room_trace.jsonl`               | Per-question traces                            |
| `evals/mirathorn_vertical_slice/output/evidence_context_relevance_proxy.json`  | Superfluity proxy                              |
| `evals/mirathorn_vertical_slice/output/whole_document_if_golden_analysis.json` | Whole-doc counterfactual                       |


---

## 9. Phase 6 reproduction (copy-paste)

```bash
cd /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy
uv sync --extra embedding

DMB_EVIDENCE_FIRST=1 \
DMB_EVIDENCE_ADAPTIVE_TOP_K=1 \
DMB_EVIDENCE_ADAPTIVE_TOP_K_MAX=48 \
DMB_EVIDENCE_DENSITY_THRESHOLD=0.3 \
DMB_EVIDENCE_ENTITY_AWARE=1 \
DMB_EVIDENCE_ENTITY_QUOTA=10 \
DMB_EVIDENCE_ENTITY_EVIDENCE_QUOTA=12 \
DMB_SYNTHESIS_PROFILE=mirathorn \
DMB_SYNTHESIS_VERBOSITY=verbose \
DMB_EMBEDDING_SCORING=1 \
DMB_EMBEDDING_USE_TLDR_ONLY=1 \
DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1 \
DMB_PHASE_WRITE_LEDGER=1 \
DMB_PHASE_NAME=phase6_embedding_hybrid \
DMB_PHASE_HYPOTHESIS="Embedding similarity vs core_claims (TL;DR-only)." \
uv run python evals/mirathorn_vertical_slice/run_council_room_question_set.py
```

