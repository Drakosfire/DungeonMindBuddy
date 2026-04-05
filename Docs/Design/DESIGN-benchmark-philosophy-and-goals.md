# Benchmark Philosophy and Goals (DungeonMindBuddy)

**Date created:** 2026-04-04  
**Status:** Living design document  
**Scope:** DungeonMindBuddy benchmark strategy across ingestion, projection, and synthesis layers.

---

## 1) Why This Document Exists

DungeonMindBuddy now has two realities at once:

- a working benchmark stack (`canon_layering`, `llm_ingestion_slice`, `mirathorn_vertical_slice`)
- and a newer contract-aware harness (`extraction_lab/`) intended to become the long-term evaluation spine

This document defines benchmark philosophy and goals so decisions stay consistent as we transition from ad hoc/legacy runs to contract-bound, recommendation-grade evaluations.

---

## 2) Reference Model From RulesIngestion (What To Learn)

RulesIngestion Retrieval Lab provides durable benchmark principles that are applicable here:

1. **Contract-first evaluation**
   - Metrics are valid only relative to one exact contract identity.
2. **Definition vs projection separation**
   - Human intent (definition) is stable; run-time projection is contract-bound.
3. **Surface-aware scoring**
   - Recommendation surfaces are explicit (`clean_subset` vs broader working set).
4. **Promotion as policy artifact**
   - Promotion comes from explicit readiness artifacts, not informal “best run” claims.
5. **Fail-closed contract validation**
   - Incompatible benchmark/corpus contracts block comparison and promotion.

These principles are the model, not the implementation to copy directly.

---

## 3) Key Differences: RulesIngestion vs DungeonMindBuddy

| Dimension | RulesIngestion Retrieval Lab | DungeonMindBuddy |
|---|---|---|
| Primary question | “Can we retrieve the right chunks?” | “Can we extract/projection/synthesize the right canon state?” |
| Gold durability | chunk-location anchors | entity/fact/event anchors linked to extraction intent |
| Main drift source | chunking/substrate changes | prompt/filter/taxonomy/store-state changes |
| Core metrics | MRR, recall@k, nDCG, failure buckets | entity anchor recall, fact anchor recall, unresolved anchors, state-correctness and synthesis quality |
| Promotion risk | wrong retrieval recommendation | wrong canonical state for GM workflow |

Implication: DMB must keep Retrieval Lab’s contract discipline while defining extraction/projection-native correctness signals.

---

## 4) Benchmark Philosophy For DungeonMindBuddy

### 4.1 Contract before score

No score is interpreted without a contract snapshot. For DMB this means at minimum:

- `store_sha256`
- `corpus_source_sha256`
- prompt/model IDs
- taxonomy and heuristic hashes

If contracts differ, results are drift diagnostics, not direct regressions.

### 4.2 Intent is durable; resolved match is transient

Gold anchors represent editorial intent and must survive pipeline shifts. Resolved entities/facts are run-local projections against one contract.

### 4.3 Failure taxonomy over single “pass/fail”

We optimize for explanatory failures:

- stale/wrong-state selection
- incomplete evidence coverage
- scope errors
- temporal ordering ambiguity
- anchor mismatch categories

Aggregate pass rate without failure classes is insufficient.

### 4.4 Benchmark must falsify confidence

A benchmark is useful only if it can fail for real regressions. Each suite should include adversarial and drift-prone cases, not only happy paths.

### 4.5 Promotion requires policy evidence

Promotion to baseline requires:

- contract validity
- explicit surface selection
- reviewed unresolved-anchor behavior
- reproducibility across reruns

No promotion by intuition.

---

## 5) Benchmark Goals (Near-Term and Mid-Term)

## Goal A — Stabilize the execution path

Phase 5 objective: reliable `entity_complete -> fact_submitted` transition on constrained machines with bounded telemetry.

**Success signal:** transition succeeds repeatedly without UI/system lock.

## Goal B — Validate full-corpus anchor calibration

Run Extraction Lab against finalized `batch_api_full_corpus` and classify anchor failures.

**Success signal:** actionable fail-bucket breakdown and a defensible baseline promotion decision.

## Goal C — Make regression gating trustworthy

Ensure `assert_regression` is meaningful under real drift:

- hard-fail only on core-reliability signals
- warning on count drift unless policy says otherwise

**Success signal:** gate catches real regressions without constant false alarms.

## Goal D — Reconnect vertical-slice readiness challenge

Return to the original vertical-slice intent: prove robustness beyond Milestone-1 happy path via blind replay and expanded scenarios.

**Success signal:** deterministic replay + strict gate performance across adversarial scenarios.

---

## 6) Required Benchmark Surfaces (DMB)

Baseline surface model going forward:

- `core_extraction` — recommendation-grade regression surface
- `vertical_slice` — end-to-end workflow quality surface
- `recap_lane` — session recap/event/claim quality surface
- `working_set` — experimental and non-ratified anchors

Only ratified surfaces should drive hard regressions and promotion.

---

## 7) Required Artifacts Per Recommendation-Grade Run

Minimum run bundle:

- `pipeline_contract.json`
- `run_manifest.json`
- `entity_results.json`
- `fact_results.json`
- `aggregate_metrics.json`
- `report.md`
- regression output (when baseline exists)

These are mandatory for auditability and comparison.

---

## 8) Non-Goals

- Do not overfit rubrics to force green outcomes.
- Do not compare runs across incompatible contracts.
- Do not treat “no crash” as benchmark success.
- Do not collapse all failures into one metric.

---

## 9) Decision Rules

1. **If transition is unstable:** fix execution path first (Phase 5), do not interpret quality metrics.
2. **If contract differs:** classify as drift comparison, not regression.
3. **If anchors fail:** classify by fail bucket before changing thresholds.
4. **If scores regress with same contract:** treat as real pipeline regression until disproven.
5. **If data is missing:** classify as corpus/coverage gap, not model failure.

---

## 10) Immediate Next Steps

1. Complete Phase 5 transition stability with telemetry-backed evidence.
2. Finalize `batch_api_full_corpus` store.
3. Run Extraction Lab full-corpus benchmark and produce anchor failure classification.
4. Decide baseline promotion from explicit checklist.
5. Start Phase 7 readiness challenge replay matrix.

