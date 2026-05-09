# Report: Wave 2 synthesis experiments (2A & 2B)

**Date:** 2026-04-08  
**Benchmark:** Council room question set (`evals/mirathorn_vertical_slice/run_council_room_question_set.py`)  
**Store:** `evals/mirathorn_vertical_slice/output/phase_d_store`  
**Reference:** `Docs/Plans/HANDOFF-execute-evidence-retrieval-synthesis-experiments.md` § Wave 2  

Saved artifacts:

- `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp2a`
- `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp2b`  

Ledger entries: `exp2a_two_step_synthesis`, `exp2b_citation_structure` in `evidence_gap_phase_ledger.json`.

---

## Shared retrieval baseline (Phase 3 style)

Both runs used the same evidence-first retrieval stack:

- `DMB_EVIDENCE_FIRST=1`
- `DMB_EVIDENCE_ADAPTIVE_TOP_K=1`
- `DMB_EVIDENCE_ADAPTIVE_TOP_K_MAX=48`
- `DMB_EVIDENCE_DENSITY_THRESHOLD=0.3`

**Stage-loss retrieval side** was identical between 2A and 2B: **evidence_gap 13**, **retriever_gap 8**. Differences are entirely in the synthesis path.

---

## Summary table

| Exp | Label | Semantic pass | Strict pass | fail_stale | evidence_gap | retriever_gap | synthesis_gap | hit | avg context_support | failure surface (pass / retr / synth) |
|-----|--------|---------------|-------------|------------|--------------|---------------|---------------|-----|---------------------|----------------------------------------|
| 2A | Two-step synthesis | **7**/15 | 6/15 | 0 | 13 | 8 | **8** | 31 | 0.739 | 7 / 3 / 5 |
| 2B | Citation structure | **8**/15 | 6/15 | 0 | 13 | 8 | **6** | 33 | 0.722 | 8 / 3 / 4 |

*Semantic / strict* from `overall_semantic` / `overall_strict`. Stage-loss from `stage_loss_report.overall_counts`. *avg context_support* from `overall_context_support.avg_support_ratio`.

---

## Exp 2A — Two-step synthesis (extract → answer)

### Hypothesis

A dedicated extraction pass (numbered factual claims from context) followed by an answer pass that sees **claims only** would reduce **synthesis_gap** by forcing the model to notice must-hit facts before narrative composition.

### Implementation (for traceability)

- **Code:** `src/agent/synthesis.py` — `EXTRACTION_PROMPT`, env `DMB_TWO_STEP_SYNTHESIS=1` or CLI `--two-step-synthesis`.
- **Eval wiring:** `evals/mirathorn_vertical_slice/run_council_room_question_set.py` appends `--two-step-synthesis` when `DMB_TWO_STEP_SYNTHESIS=1`.
- **Telemetry:** `src/cli.py` records `synthesis_meta` on `_last_ask_meta` (e.g. `two_step`, `extracted_claims`).

### Configuration

```text
DMB_TWO_STEP_SYNTHESIS=1
(+ Phase 3 retrieval env vars above)
DMB_PHASE_NAME=exp2a_two_step_synthesis
```

### Results

| Metric | Value |
|--------|--------|
| Semantic pass | 7/15 |
| Strict pass | 6/15 |
| fail_stale | 0 |
| synthesis_gap (stage_loss) | **8** |
| hit | 31 |
| avg context_support | 0.739 |

Wall-clock per question was roughly **~2×** the single-call baseline (two chat completions per ask).

### Verdict vs handoff criteria

- **Target:** synthesis_gap ≤ **5** and semantic pass ≥ **9**.
- **Outcome:** **Not met.** Semantic pass **regressed** vs the typical Phase 3-style **8/15** seen in Wave 1; **synthesis_gap increased** (8 vs ~5–7 on comparable configs).

### Interpretation

The extraction step may **lose or compress** phrasing the benchmark requires verbatim (terminal outcomes), or the answer step may **over-trust** a lossy list. Two-step also introduces **extra failure surface** (empty or low-quality extraction). For this slice, two-step synthesis is **not** an improvement over single-pass synthesis under the same retrieval.

---

## Exp 2B — Explicit citation structure in the system prompt

### Hypothesis

Requiring **TL;DR + Evidence bullets + optional Analysis**, with a rule that every TL;DR claim maps to an Evidence bullet, would align answers with **core_claims** and reduce **synthesis_gap**.

### Implementation (for traceability)

- **Code:** `src/agent/synthesis.py` — `_CITATION_APPENDIX`, enabled via env `DMB_SYNTHESIS_CITATION_STRUCTURE=1` or CLI `--synthesis-citation-structure`.
- **Eval wiring:** same env adds `--synthesis-citation-structure` in `run_council_room_question_set.py`.

### Configuration

```text
DMB_SYNTHESIS_PROFILE=mirathorn
DMB_SYNTHESIS_CITATION_STRUCTURE=1
(+ Phase 3 retrieval env vars above)
DMB_PHASE_NAME=exp2b_citation_structure
```

### Results

| Metric | Value |
|--------|--------|
| Semantic pass | 8/15 |
| Strict pass | 6/15 |
| fail_stale | 0 |
| synthesis_gap (stage_loss) | **6** |
| hit | 33 |
| avg context_support | 0.722 |

Answers visibly followed the **Evidence:** section pattern in console output.

### Verdict vs handoff criteria

- **Target:** embedding mean **> 0.65** (baseline ~0.626 in older notes); synthesis_gap ≤ **5**.
- **Outcome:** **Partially assessable.** **synthesis_gap 6** — still above 5. **Embedding mean was not measured** (`DMB_EMBEDDING_SCORING` was off); the embedding pass criterion should be re-run with scoring enabled if it remains a decision gate.

### Interpretation

Citation structure **restored semantic pass to 8/15** (matching Wave 1 Phase 3-style runs) and improved **hit** (33 vs 2A’s 31) and **synthesis_gap** vs 2A (6 vs 8), but **did not** reach synthesis_gap ≤ 5. Slightly lower **avg context_support** (0.722 vs 0.739) may reflect stricter formatting consuming “support budget” in the scorer or longer boilerplate.

---

## Comparison to Wave 1 baseline (same retrieval)

For the same **evidence_gap / retriever_gap** (13 / 8), representative Wave 1 Phase 3-style runs achieved about **8/15** semantic, **synthesis_gap** often **5–7**, **hit** **32–34**.

| Run | Semantic | synthesis_gap | hit |
|-----|----------|-----------------|-----|
| Wave 1 typical (1A–1F cluster) | 8/15 | 5–7 | 32–34 |
| **2A** | 7/15 | 8 | 31 |
| **2B** | 8/15 | 6 | 33 |

**2B** is closest to the baseline tradeoff; **2A** is strictly worse on this benchmark.

---

## Recommendations

1. **Do not adopt 2A** as default for this benchmark without redesign (e.g. extraction prompt tuned for verbatim terminal phrases, or answer pass that may re-open raw context for verification).
2. **2B** is a **mild** structural nudge: consider A/B with embedding scoring on to test the handoff’s embedding-mean criterion; optionally pair with **1F** (context budget 10k) if that combo is still open from Wave 1.
3. Re-run **2B + `DMB_EMBEDDING_SCORING=1`** when you want an evidence-backed read on the **> 0.65** embedding mean target.

---

## Code references

| Piece | Location |
|-------|-----------|
| Two-step + citation appendix | `src/agent/synthesis.py` |
| CLI flags & `synthesis_meta` | `src/cli.py` (`--two-step-synthesis`, `--synthesis-citation-structure`) |
| Eval env → flags | `evals/mirathorn_vertical_slice/run_council_room_question_set.py` |
