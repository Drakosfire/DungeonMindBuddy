# Wave 5 report: full-corpus council-room benchmark

**Date:** 2026-04-09  
**Bench:** `evals/mirathorn_vertical_slice/gold/gold_questions.json` (15 questions)  
**Store:** `out/stores/dungeonbuddy_store_escalation_full_mini_to_54` (compiled projection on the escalation corpus; **~2069 entities** in retrieval)  
**Campaign:** `longmont-c1`  
**Scoring:** Council-room harness semantic / strict verdicts (must-hit tokens, stale detection); embedding and claim verification **off** (defaults).

## Purpose

Compare **compiled projection (entity) retrieval** vs **evidence-first (raw chunk) retrieval** at full-corpus scale, including **document planner** (Karpathy-style doc scoping), **projection-enriched** context (provenance appendix), and **rich entity summaries** for the lexical retrieval layer.

## Results summary

| Exp | Configuration | Semantic pass | Strict pass | `fail_stale` | Avg `context_support` | Failure surface (pass / retrieval_gap / synthesis_gap) |
|-----|---------------|---------------|-------------|--------------|------------------------|----------------------------------------------------------|
| **5A** | Projection + retrieval (baseline) | 2/15 | 1/15 | 1 | 0.506 | 2 / 5 / 8 |
| **5B** | Evidence-first + adaptive top-k + per-seed neighbors | **3**/15 | 1/15 | 1 | 0.539 | 3 / 6 / 6 |
| **5C** | Document planner + projection only | 2/15 | 1/15 | 0 | **0.344** | 2 / **9** / 4 |
| **5D** | Document planner + evidence-first stack (same as 5B) | **3**/15 | 1/15 | 0 | **0.589** | 3 / 5 / 7 |
| **5E** | Projection-enriched (`--projection-enriched`) | 2/15 | 1/15 | 1 | 0.489 | 2 / 6 / 7 |
| **5F** | Rich entity summaries (`--rich-entity-summaries`) | 2/15 | 1/15 | 0 | 0.506 | 2 / 5 / 8 |

**Pipeline flags (from artifact `pipeline_config` where set):**

- 5B/5D: `--evidence-first --evidence-adaptive-top-k --evidence-adaptive-top-k-max 48 --evidence-density-threshold 0.3` plus env `DMB_EVIDENCE_PER_SEED_NEIGHBORS=1` (not echoed in the string).
- 5C: `--document-planner`
- 5D: planner + evidence-first stack above.
- 5E: `--projection-enriched`
- 5F: `--rich-entity-summaries`

## Artifacts

Snapshots (so runs do not overwrite each other):

| Experiment | JSON snapshot |
|------------|-----------------|
| 5A | `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp5a_full_corpus_projection_only` |
| 5B | `.../council_room_question_set.json.exp5b_full_corpus_evidence_per_seed` |
| 5C | `.../council_room_question_set.json.exp5c_full_corpus_doc_planner_projection_only` |
| 5D | `.../council_room_question_set.json.exp5d_full_corpus_doc_planner_evidence_per_seed` |
| 5E | `.../council_room_question_set.json.exp5e_full_corpus_projection_enriched` |
| 5F | `.../council_room_question_set.json.exp5f_full_corpus_rich_entity_summaries` |

Matching `council_room_trace.jsonl.exp5*` files were written when present. Phase ledger rows use `DMB_PHASE_NAME` per run under `evals/mirathorn_vertical_slice/output/evidence_gap_phase_ledger.json`.

Wall-clock order of magnitude: **~90–130 s** per full 15-question run (document planner adds ~1–2 s per question for the planner LLM call).

## Checkpoint 1: compiled layer vs raw layer (5A vs 5B)

At full corpus scale, **evidence-first + adaptive top-k + per-seed (5B)** beats projection-only (5A) on **semantic passes (3 vs 2)** and **average context support (0.54 vs 0.51)**, with synthesis failures slightly reduced and retrieval failures slightly increased. The effect is **small**: both remain far below slice-scale scores, so the dominant issue is **2069-entity ambiguity** and **synthesis**, not only “chunks vs projection.”

## Checkpoint 2: document planner (5C vs 5D)

- **5C (planner + projection only):** **Average support drops sharply (0.34)** vs 5A. Failure surface shifts toward **retrieval_gap (9)**, consistent with **over-narrow doc scoping** leaving the lexical/projection head with too little signal for this bench.
- **5D (planner + evidence-first):** Recovers **best support in the wave (0.589)** and matches **5B on semantic (3/15)**. Planner + raw evidence appears to **compensate** for planner-induced narrowing by pulling chunk-level evidence after entities are selected.

**Interpretation:** On this store, the document planner **hurts** the projection-only path but **helps measured grounding** when paired with evidence-first retrieval.

## Projection-enriched (5E) and rich summaries (5F)

- **5E:** **No semantic gain** vs 5A (2/15). Provenance appendix does not fix entity ranking at this scale; support is slightly lower than 5A.
- **5F:** Semantic **unchanged** vs 5A (2/15); **stale failures go to 0** (vs 1 on 5A), suggesting slightly cleaner answers without improving must-hit coverage.

## Conclusions

1. **Full-corpus scale collapses bench scores** relative to the small Mirathorn slice: no configuration reached even **4/15** semantic on this run set.
2. **Best overall combination tested:** **5D** (document planner + evidence-first + adaptive top-k + per-seed) for **highest context support** and tied-best **semantic 3/15** with **5B**.
3. **Evidence-first (5B)** remains a **modest win** over projection-only (5A) without the planner.
4. **Document planner alone (5C)** is **unsafe** on this bench at full scale without the evidence stack.
5. **Projection-enriched** and **rich entity summaries** did **not** improve semantic pass rate on this corpus; 5F may still be worth keeping for **stale reduction**.

## Recommended next steps (not run here)

- **Hybrid retrieval:** combine embedding or BM25 over **entity summaries + doc IDs** with evidence-first (reduce pure lexical collisions in ~2k entities).
- **Re-run with** `DMB_EMBEDDING_SCORING=1` / `DMB_CLAIM_VERIFICATION=1` for auxiliary signals (does not replace must-hit semantic grading).
- **Slice vs full** ablation: confirm whether **store build** (coverage gaps) vs **retrieval** dominates by spot-checking `retrieval_gap` questions against ground-truth location in the store.
