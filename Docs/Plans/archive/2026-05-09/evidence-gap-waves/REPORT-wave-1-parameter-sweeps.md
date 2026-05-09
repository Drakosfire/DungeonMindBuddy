# Report: Wave 1 parameter sweeps (Group 1 experiments)

**Date:** 2026-04-08  
**Benchmark:** Council room question set (`evals/mirathorn_vertical_slice/run_council_room_question_set.py`)  
**Store:** `evals/mirathorn_vertical_slice/output/phase_d_store`  
**Reference:** `Docs/Plans/HANDOFF-execute-evidence-retrieval-synthesis-experiments.md` § Wave 1  

Artifacts for each run are saved under `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp1*` (plus `exp1a_run{1,2,3}`). The phase ledger was appended for each run (`evidence_gap_phase_ledger.json`).

---

## Rollback rule (from handoff)

- **Fail** if semantic pass &lt; **7/15** or **fail_stale &gt; 0**.  
- No Wave 1 run violated this rule.

---

## Summary table

| Exp | Phase / label | Semantic pass | Strict pass | fail_stale | evidence_gap | retriever_gap | synthesis_gap | hit | avg context_support | Notes |
|-----|----------------|---------------|-------------|------------|----------------|---------------|---------------|-----|---------------------|--------|
| 1A-r1 | exp1a_phase3_stability_run1 | 8/15 | 6/15 | 0 | 13 | 8 | 7 | 32 | 0.750 | Phase 3 retrieval template |
| 1A-r2 | exp1a_phase3_stability_run2 | 8/15 | 7/15 | 0 | 13 | 8 | 7 | 32 | 0.739 | Same config as r1 |
| 1A-r3 | exp1a_phase3_stability_run3 | 8/15 | 7/15 | 0 | 13 | 8 | 5 | 34 | 0.722 | Best **hit** in 1A trio; lowest **synthesis_gap** |
| 1B | exp1b_tighter_topk_32 | 7/15 | 6/15 | 0 | 20 | 8 | 3 | 29 | 0.750 | **Regressed** semantic vs 1A; **evidence_gap** worst in wave |
| 1C | exp1c_density_0_5 | 7/15 | 6/15 | 0 | 18 | 8 | 4 | 30 | 0.722 | Same pattern as 1B: semantic −1, evidence_gap up |
| 1D | exp1d_phase3_compact | 8/15 | 5/15 | 0 | 13 | 8 | 6 | 33 | 0.739 | Mirathorn + **compact** verbosity |
| 1E | exp1e_phase3_default_verbosity | 8/15 | 6/15 | 0 | 13 | 8 | 6 | 33 | 0.750 | Mirathorn profile, default verbosity |
| 1F | exp1f_context_budget_10k | 8/15 | 6/15 | 0 | 13 | 8 | 5 | 34 | 0.739 | `DMB_CONTEXT_MAX_CHARS=10000` |
| 1G | exp1g_claim_verification | 8/15 | 7/15 | 0 | 13 | 8 | 6 | 33 | 0.733 | **Claim verification on** (diagnostic) |

*Strict pass* = `overall_strict.pass_updated` (must-hit token bar). *Semantic pass* = `overall_semantic.pass_updated`. Stage-loss counts = `stage_loss_report.overall_counts`. *avg context_support* = `overall_context_support.avg_support_ratio`.

---

## Exp 1A — Phase 3 stability (three runs)

**Config:** `DMB_EVIDENCE_FIRST=1`, `DMB_EVIDENCE_ADAPTIVE_TOP_K=1`, `DMB_EVIDENCE_ADAPTIVE_TOP_K_MAX=48`, `DMB_EVIDENCE_DENSITY_THRESHOLD=0.3`.

**Handoff pass criterion:** ≥2/3 runs at **9/15** semantic, zero fail_stale.

**Result:** All three runs scored **8/15** semantic (not 9/15). **0/3** at the 9/15 bar. Median semantic = **8/15** (≥ handoff floor of 7). **fail_stale = 0** on all runs.

**Interpretation:** On this store and date, the Phase 3-style configuration is **stable around 8/15** semantic pass, not the historical 9/15 cited in older ledger rows. Stage-loss **synthesis_gap** moved between **5 and 7** across seeds without changing env vars, so **synthesis_gap is somewhat run-variable** even when retrieval config is fixed.

---

## Exp 1B — Tighter adaptive top-k (max 48 → 32)

**Hypothesis:** Lower cap reduces dilution and improves synthesis_gap without large evidence_gap regression.

**Result:** **synthesis_gap** improved to **3**, but **evidence_gap** rose to **20** and semantic pass fell to **7/15**. **Hit** dropped to **29**.

**Verdict:** **Tradeoff confirmed in the wrong direction** for this benchmark: pruning the adaptive cap hurt recall enough to fail the semantic bar and inflate evidence_gap. Not a default recommendation.

---

## Exp 1C — Stricter density threshold (0.3 → 0.5)

**Hypothesis:** Higher threshold prunes low-density tail of adaptive expansion.

**Result:** Same qualitative pattern as 1B: semantic **7/15**, **evidence_gap 18**, **synthesis_gap 4**, **hit 30**.

**Verdict:** **Too aggressive** for this slice; retrieval loss dominates over any synthesis benefit.

---

## Exp 1D — Compact verbosity (Phase 3 retrieval + mirathorn)

**Hypothesis:** Shorter answers reduce hedge/drift and synthesis_gap.

**Result:** Semantic **8/15** (unchanged vs 1A). **synthesis_gap 6** (worse than best 1A run’s 5). **Strict pass 5/15** (lowest in the 8/15 semantic cluster).

**Verdict:** **Did not** beat the best Phase 3 baseline on synthesis_gap; **strict** bar suffered—likely dropping must-hit phrasing under tighter word limits.

---

## Exp 1E — Default verbosity, mirathorn profile

**Hypothesis:** Control vs verbose mode; middle-ground wording.

**Result:** Semantic **8/15**, same stage-loss shape as 1D (**synthesis_gap 6**, **hit 33**). Slightly higher **avg_support** than 1D (0.750 vs 0.739).

**Verdict:** **Parity** with 1D on headline metrics; no clear win over the best 1A run.

---

## Exp 1F — Context budget 10k characters

**Hypothesis:** Halving `context_max_chars` from 20k → 10k tightens noise seen by the model.

**Result:** Semantic **8/15**. **synthesis_gap 5**, **hit 34**—aligned with the **best 1A run** on those two fields. stderr still reported large pre-budget context sizes for some rows; the effective trim happens in the formatter path—worth confirming in trace if budget is actually binding per question.

**Verdict:** **Promising tie** to the best 1A **hit** / **synthesis_gap** combo without dropping semantic pass; follow up with per-question **context_chars** in trace if you need to confirm the budget is doing work.

---

## Exp 1G — Claim verification enabled

**Hypothesis:** Second quality axis beyond token must-hits.

**Result:** Answers and semantic/stage-loss metrics match the non-verification cluster (**8/15**, **evidence_gap 13**, **synthesis_gap 6**, **hit 33**)—expected, since verification does not rewrite answers. **overall_accuracy** (heuristic extractor) reported:

- **total_factual_claims:** 159  
- **grounded / unsupported / contradicted / provenance_mismatch:** 23 / 132 / 0 / 4  
- **hallucination_rate:** ~0.83, **completeness:** ~0.14, **provenance_accuracy:** ~0.23  

**Verdict:** **Diagnostic only** for this harness: high unsupported rate flags that the heuristic claim extractor and/or answer style produces many claims not cleanly tied to extracted supports—useful for tooling iteration, not for pass/fail until extractor quality is validated.

---

## Cross-cutting observations

1. **Retrieval knobs (1B, 1C)** that shrink the adaptive pool **hurt semantic pass and evidence_gap** on this benchmark; they are not free paths to lower synthesis_gap.  
2. **Synthesis-only knobs (1D, 1E)** did not improve **synthesis_gap** vs the best 1A run; compact hurt **strict** pass.  
3. **1F** matched the **strongest 1A** outcomes on **hit** and **synthesis_gap** at **8/15** semantic—candidate for combination with later waves.  
4. **1A stability:** Semantic **8/15** is repeatable; **9/15** was **not** reproduced in three consecutive runs under the documented Phase 3 env.

---

## Files

| Role | Path |
|------|------|
| Saved JSON snapshots | `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp1a_run{1,2,3}`, `.exp1b` … `.exp1g` |
| Latest full run (after 1G) | `evals/mirathorn_vertical_slice/output/council_room_question_set.json` |
| Ledger | `evals/mirathorn_vertical_slice/output/evidence_gap_phase_ledger.json` |
