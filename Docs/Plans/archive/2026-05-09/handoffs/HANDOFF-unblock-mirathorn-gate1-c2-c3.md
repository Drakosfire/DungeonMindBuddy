# Handoff: Unblock Mirathorn Gate 1 (C2/C3)

**Date:** 2026-04-03  
**Status:** COMPLETED — Vertical Slice Gates GREEN  
**Priority:** CRITICAL  
**Owner lane:** `evals/mirathorn_vertical_slice` ingestion-quality evaluation and extraction mapping

---

## 1) Mission

Unblock Mirathorn **Gate 1 (Ingestion Quality)** by converting current `eval_fact_quality.py` C2/C3 failures into explicit mismatch categories, then fixing extraction/mapping behavior until Gate 1 is green.

This is the current top blocker to full vertical-slice green.

---

## 2) Current State Snapshot

Latest validated status:

- **Gate 2 (Projection Semantics):** PASS (`run_step1/2/3` healthy)
- **Gate 1A (Entity Recall):** PASS (`eval_entity_recall.py`)
- **Gate 1B (Fact Quality):** PASS (C1-C5 all PASS)
- **Gate 3 (QA/Synthesis):** PASS (`eval_synthesis.py` overall PASS)

Previously failing targets (now resolved):

- **C2 Gold coverage misses**
  - `ent_mirathorn/history`
  - `ent_mirathorn/economy`
  - `ent_mirathorn/operational_status`
  - `ent_shepherds_flock/goals`
- **C3 Projection parity misses**
  - `ent_mirathorn/economy`
  - `ent_shepherds_flock/goals`
  - (latest artifact inspection also showed misses for `ent_mirathorn/operational_status` and `ent_shepherds_flock/role`; verify against current evaluator logic before changing policy)

Diagnosis that drove the fix set:

- Not a structural corruption problem.
- Pipeline is contract-valid, deterministic under replay, and precision guardrails are clean.
- Primary fault zone was semantic extraction/mapping and evaluation strictness around attr/keyword alignment.

---

## 3) Scope and Non-Goals

### In scope

- `evals/mirathorn_vertical_slice/eval_fact_quality.py` mismatch diagnostics and reporting
- Diffing of:
  - `evals/mirathorn_vertical_slice/gold/gold_facts.json`
  - `evals/mirathorn_vertical_slice/output/extracted_facts.json`
  - `evals/mirathorn_vertical_slice/output/automated_projection.json`
- Extraction/prompt/mapping changes needed to restore C2/C3
- Re-run loop for Gate 1 proof

### Out of scope

- Redesigning benchmark philosophy docs
- Changes to Gate 2 reducer semantics (already green)
- Broader corpus-batch stabilization work (Phase 5 transition lane)

---

## 4) Strict Exit Criteria

All must pass:

1. `eval_fact_quality.py` returns pass with all C1–C5 gates green.
2. C2 recall meets threshold (`>= 0.90`) and no unresolved benchmark-critical misses remain.
3. C3 projection parity meets threshold (`>= 0.90`) with required attrs present.
4. Mismatch report includes explicit per-miss reason categories (not only raw missing lists).
5. After Gate 1 is green, `eval_synthesis.py` is run independently and D1–D4 are reported.
6. Final full-chain proof run succeeds end-to-end once.

---

## 5) Required Deliverables

1. **Mismatch-category artifact**
  - New or enriched output JSON/MD that classifies each C2/C3 miss into buckets:
    - `no_subject_attr_candidates`
    - `keyword_mismatch_with_candidates`
    - `attr_substituted_to_alternative`
    - `subject_mapping_miss` (if applicable)
2. **Evidence-backed fix set**
  - Minimal code/config changes that address verified miss categories.
3. **Proof logs**
  - Commands executed and resulting metrics for each iteration.
4. **Final gate report**
  - `gate_ingestion`, `gate_projection`, `gate_qa` independent statuses, plus aggregate verdict.

---

## 6) Execution Plan

### Phase A — Instrument the failure

Goal: make every C2/C3 miss explainable.

Actions:

1. Re-run fact-quality evaluation.
2. Add or extend evaluator diagnostics to emit per-item trace:
  - expected `{subject_entity_id, attribute, match_keywords}`
  - candidate extracted facts (same subject, same or alternative attrs)
  - projection attr presence/absence
  - reason code from the mismatch taxonomy
3. Write artifact to `evals/mirathorn_vertical_slice/output/` (stable filename).

### Phase B — Fix C2 coverage misses first

Priority misses:

- `ent_mirathorn/history` (near-miss likely keyword strictness)
- `ent_mirathorn/economy` (missing extraction)
- `ent_mirathorn/operational_status` (likely attr substitution to `atmosphere`)
- `ent_shepherds_flock/goals` (missing extraction)

Actions:

1. Inspect extracted-fact candidates for near matches.
2. Update extraction prompt/schema mapping so these attributes are captured when evidence exists.
3. Re-run `eval_fact_quality.py` after each focused change until C2 is green.

### Phase C — Fix C3 projection parity

Actions:

1. Validate attr-key normalization between extraction and projection.
2. Verify reducer selection/winner behavior for targeted attrs.
3. Decide and implement parity policy explicitly:
  - strict exact attrs only, or
  - controlled alternative-attr acceptance.

### Phase D — Complete gate proof loop

1. Run `eval_synthesis.py` once Gate 1 is green.
2. Run full chain end-to-end once for final proof.
3. Record gate-level independent statuses and aggregate verdict.

---

## 7) Command Sequence (Canonical)

```bash
# 1) Reproduce current fail fast
env PYTHONPATH=. uv run python evals/mirathorn_vertical_slice/eval_fact_quality.py

# 2) Iteration loop (after each surgical fix)
env PYTHONPATH=. uv run python evals/mirathorn_vertical_slice/eval_fact_quality.py

# 3) Gate 3 once Gate 1 is green
env PYTHONPATH=. uv run python evals/mirathorn_vertical_slice/eval_synthesis.py

# 4) Final full-chain proof
env PYTHONPATH=. uv run python evals/mirathorn_vertical_slice/run_step1.py && \
env PYTHONPATH=. uv run python evals/mirathorn_vertical_slice/run_step2.py && \
env PYTHONPATH=. uv run python evals/mirathorn_vertical_slice/run_step3.py && \
env PYTHONPATH=. uv run python evals/mirathorn_vertical_slice/eval_entity_recall.py && \
env PYTHONPATH=. uv run python evals/mirathorn_vertical_slice/eval_fact_quality.py && \
env PYTHONPATH=. uv run python evals/mirathorn_vertical_slice/eval_synthesis.py
```

---

## 8) Key Files

- `evals/mirathorn_vertical_slice/eval_fact_quality.py`
- `evals/mirathorn_vertical_slice/eval_entity_recall.py`
- `evals/mirathorn_vertical_slice/eval_synthesis.py`
- `evals/mirathorn_vertical_slice/gold/gold_facts.json`
- `evals/mirathorn_vertical_slice/output/extracted_facts.json`
- `evals/mirathorn_vertical_slice/output/automated_projection.json`
- `src/ingestion/fact_extractor.py` (if extraction mapping/prompt behavior requires adjustment)
- `src/contracts/entity_taxonomy.py` (only if attr taxonomy mismatch is confirmed)

---

## 9) Risk Notes

- API/network variance can affect runtime; keep gate-level semantics independent from ops instability.
- Do not treat Gate 2 green as a proxy for Gate 1 or Gate 3.
- Avoid broad prompt/taxonomy refactors before mismatch categories are proven by artifacts.

---

## 10) Definition of Done

This handoff is complete when:

- Gate 1 is green with C1–C5 passing,
- mismatch categories are explicit and reproducible,
- Gate 3 is re-run and reported,
- and one final full-chain run proves all three gates independently pass before aggregate green is declared.

---

## 11) Completion Evidence

Final validated gate report:

- `gate_ingestion`: **PASS**
  - Gate 1A entity recall: PASS
  - Gate 1B fact quality: PASS
    - C1 Contract validity: PASS
    - C2 Gold coverage: PASS (`recall=1.000`)
    - C3 Projection parity: PASS
    - C4 Precision guardrail: PASS
    - C5 Determinism (cache replay): PASS
- `gate_projection`: **PASS**
  - `run_step1.py` / `run_step2.py` / `run_step3.py` deterministic semantics: PASS
- `gate_qa`: **PASS**
  - Gate 3 synthesis: PASS (overall PASS)

Aggregate verdict: **GREEN**.

What made this reliable:

- Mismatch taxonomy was added and used to drive targeted C2/C3 fixes.
- Gate-level validation remained independent (no blended pass/fail shortcut).
- Gate 3 rerun reliability was hardened to avoid state-induced false negatives.

