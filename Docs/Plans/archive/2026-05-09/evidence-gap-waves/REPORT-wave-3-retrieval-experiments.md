# Report: Wave 3 retrieval experiments (3A, 3B, 3C)

**Date:** 2026-04-08  
**Benchmark:** Council room question set (`evals/mirathorn_vertical_slice/run_council_room_question_set.py`)  
**Store:** `evals/mirathorn_vertical_slice/output/phase_d_store`  
**Reference:** `Docs/Plans/HANDOFF-execute-evidence-retrieval-synthesis-experiments.md` § Wave 3  

---

## Shared baseline (Phase 3 retrieval)

All runs used:

- `DMB_EVIDENCE_FIRST=1`
- `DMB_EVIDENCE_ADAPTIVE_TOP_K=1`
- `DMB_EVIDENCE_ADAPTIVE_TOP_K_MAX=48`
- `DMB_EVIDENCE_DENSITY_THRESHOLD=0.3`

**Comparator:** Wave 1 Phase 3 stability run 3 (`council_room_question_set.json.exp1a_run3`) — same retrieval env vars, no Wave 3 modifiers.

---

## Summary table

| Exp | Phase name | Semantic pass | Strict pass | fail_stale | evidence_gap | retriever_gap | synthesis_gap | hit | avg context_support | Failure surface (pass / retr / synth) |
|-----|------------|---------------|-------------|------------|--------------|---------------|---------------|-----|---------------------|----------------------------------------|
| **Baseline** | exp1a_run3 | 8/15 | 7/15 | 0 | 13 | 8 | 5 | 34 | 0.722 | 8 / 3 / 4 |
| **3A** | exp3a_per_seed_budget | **9**/15 | 7/15 | 0 | 13 | **7** | 5 | **35** | **0.750** | 9 / 3 / 3 |
| **3B** | exp3b_two_pass_evidence | 8/15 | 6/15 | 0 | **9** | 8 | **10** | 33 | 0.739 | 8 / 3 / 4 |
| **3C** | exp3c_doc_quotas | **9**/15 | 7/15 | 0 | **24** | **5** | **4** | **27** | 0.706 | 9 / 4 / 2 |

*Metrics from* `council_room_question_set.json.exp1a_run3`, `.exp3a`, `.exp3b`, `.exp3c` *and ledger rows.*

---

## Implementation summary

### 3A — Per-seed neighbor budgeting

**File:** `src/agent/evidence_retriever.py`  

When `DMB_EVIDENCE_PER_SEED_NEIGHBORS=1`, neighbor expansion uses a **per-seed cap**:  

`per_seed_budget = max(1, neighbor_budget // max(1, len(seeded)))`  

Each seed document walks adjacent source-order evidence only until that seed’s budget is exhausted, instead of a **single global** neighbor budget that the first seeds can consume entirely.

**Default (env unset):** Original global `neighbor_budget` loop (unchanged).

---

### 3B — Two-pass evidence retrieval

**Files:** `src/agent/evidence_retriever.py` (public helper), `src/cli.py`, `evals/mirathorn_vertical_slice/run_council_room_question_set.py`  

**Behavior when** `--evidence-two-pass` **or** `DMB_EVIDENCE_TWO_PASS=1`:

1. **Pass 1:** `retrieve_relevant_evidence(..., entity_awareness_enabled=False)` — BM25 + adaptive top-k + neighbor expansion **without** inline provenance expansion.
2. **Entity ranking:** `rank_entities_by_evidence_overlap(projection, set(pass1_evidence_ids))`.
3. **Pass 2:** Collect `collect_provenance_evidence_for_entities(projection, top_entities)` (same provenance walk as entity-aware mode, but **after** pass 1), append up to `evidence_entity_evidence_quota` (default 12) new IDs not already selected.
4. **Result:** `EvidenceRetrievalResult` is updated via `dataclasses.replace` with merged `selected_evidence_ids`, recomputed `selected_document_ids`, and `debug["two_pass_provenance_added"]`.

**Interaction:** If both `--evidence-two-pass` and `--evidence-entity-aware` are set, pass 1 disables entity-aware expansion so the two mechanisms are not double-applied inside `retrieve_relevant_evidence`.

**Eval:** `DMB_EVIDENCE_TWO_PASS=1` adds `--evidence-two-pass` to the ask command.

---

### 3C — Per-document chunk quota

**File:** `src/agent/evidence_retriever.py`  

After ordered evidence selection (BM25 order + neighbor extras), if `DMB_EVIDENCE_DOC_QUOTA` is a positive integer, the list is filtered so each `document_id` contributes at most **N** chunks (experiment: **12**).

**Default:** `0` or unset — no quota.

---

## Exp 3A — Per-seed neighbor budgeting

### Hypothesis (handoff)

A global neighbor budget lets top BM25 seeds monopolize expansion; per-seed allocation improves **diversity** and can reduce **evidence_gap** without killing semantic pass.

### Configuration

```text
DMB_EVIDENCE_PER_SEED_NEIGHBORS=1
```

### Results

- **Semantic pass 9/15** — best in this report set; **+1** vs baseline 8/15.
- **evidence_gap 13** — **unchanged** vs baseline (not below 11).
- **retriever_gap 7** — improved vs baseline 8.
- **synthesis_gap 5** — same as baseline.
- **hit 35** — best among compared rows.
- **avg context_support 0.750** — highest.

### Verdict vs handoff

- **Target:** evidence_gap ≤ **11**, semantic pass ≥ **8**.
- **Outcome:** Semantic and support metrics **met or exceeded** the spirit of the pass; **evidence_gap did not improve** vs Phase 3 baseline on this slice.

### Interpretation

Per-seed budgeting **redistributes** neighbor mass across seeds. Here it **helped semantic pass and global support** without increasing stage-loss evidence_gap. It is a strong **candidate default** to trial alongside synthesis tuning (handoff §7 combination runs).

---

## Exp 3B — Two-pass evidence (entity-informed provenance)

### Hypothesis (handoff)

Separating **initial** evidence selection from a **second** provenance pull from top-overlap entities improves recall (lower **evidence_gap**) while keeping semantic quality.

### Configuration

```text
DMB_EVIDENCE_TWO_PASS=1
```

(Default entity quotas: top **10** entities, up to **12** provenance IDs added.)

### Results

- **evidence_gap 9** — **best** in this table; **−4** vs baseline 13.
- **Semantic pass 8/15** — same as baseline semantic count (not 9).
- **synthesis_gap 10** — **worst** in this table; many failures moved to synthesis despite more evidence in the pipeline.
- **hit 33** — slightly below baseline 34.

### Verdict vs handoff

- **Target:** evidence_gap ≤ **8**, semantic pass ≥ **8**.
- **Outcome:** **Partial.** evidence_gap **9** misses the ≤8 bar by one; semantic **8** passes. **synthesis_gap regression** is the main downside.

### Interpretation

Extra provenance chunks **do** surface more must-hit-bearing material (lower evidence_gap) but **dilute or complicate** what the model uses, inflating **synthesis_gap**. Next steps could include: tighter cap on two-pass adds, pairing with **1F** context budget, or **2B** citation structure — **not** recommended as a standalone default without synthesis-side mitigation.

---

## Exp 3C — Per-document quota (12 chunks / doc)

### Hypothesis (handoff)

Capping chunks per document limits **single-source dominance** and can improve **diversity** on multi-doc questions.

### Configuration

```text
DMB_EVIDENCE_DOC_QUOTA=12
```

### Results

- **Semantic pass 9/15** — matches 3A high water mark.
- **evidence_gap 24** — **large regression** vs baseline 13.
- **retriever_gap 5** — improved (fewer entity-level misses in stage-loss taxonomy).
- **synthesis_gap 4** — best synthesis_gap in table.
- **hit 27** — **lowest** hit count in table.
- **avg context_support 0.706** — lowest support.

Trace lines showed **much smaller** `evidence-first: selected=` counts (e.g. 12–60 vs ~66–104 baseline), confirming the quota **aggressively trims** the evidence set.

### Verdict vs handoff

- **Target:** Qualitative (“better token diversity”); watch depth loss on single-doc questions.
- **Outcome:** **evidence_gap and hit** show **clear harm** on this benchmark; **synthesis_gap** improved partly because **fewer tokens** sometimes align with what the model actually says, not because end-to-end quality improved.

### Interpretation

Quota **12** is **too harsh** for this 6-document slice when combined with adaptive top-k + neighbors — it drops too much relevant material. A **higher** quota or quota **only when doc count is large** (full-corpus runs) might behave differently; **do not** adopt 12 for `phase_d_store` without retuning.

---

## Cross-wave comparison (headline)

| Config | Semantic | evidence_gap | synthesis_gap | hit | Notes |
|--------|----------|----------------|-----------------|-----|--------|
| Baseline 1A-r3 | 8 | 13 | 5 | 34 | Wave 1 stability |
| **3A per-seed** | **9** | 13 | 5 | **35** | Best **balanced** lift here |
| 3B two-pass | 8 | **9** | **10** | 33 | Recall vs synthesis tradeoff |
| **3C quota-12** | **9** | 24 | **4** | 27 | **Evidence-starved** |

---

## Rollback rule (handoff)

No Wave 3 run had **fail_stale &gt; 0** or semantic pass **&lt; 7/15**. All runs are within the stated safety floor.

---

## Artifacts and ledger

| Exp | JSON snapshot | Ledger `phase_name` |
|-----|----------------|---------------------|
| 3A | `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp3a` | `exp3a_per_seed_budget` |
| 3B | `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp3b` | `exp3b_two_pass_evidence` |
| 3C | `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp3c` | `exp3c_doc_quotas` |

Full ledger: `evals/mirathorn_vertical_slice/output/evidence_gap_phase_ledger.json`.

---

## Recommendations

1. **3A (`DMB_EVIDENCE_PER_SEED_NEIGHBORS=1`):** Promote to **primary candidate** for combination experiments (Wave 1 best synthesis + optional 2B / 1F). Delivers **9/15** semantic and strong **hit / support** on this run.
2. **3B:** Treat as **research** — lower evidence_gap but **synthesis_gap** spiked; revisit with budgeted context or prompt changes before any default.
3. **3C (12):** **Avoid** for the Mirathorn vertical slice as configured; retry only with **higher quota** or **store-gated** activation when many documents exist.
4. **Next:** Handoff **§7** combination run: e.g. **3A + 1F + 2B** or **3A + default synthesis**, then re-check all five global criteria.

---

## Code references

| Experiment | Primary code |
|------------|----------------|
| 3A | `src/agent/evidence_retriever.py` — `DMB_EVIDENCE_PER_SEED_NEIGHBORS` |
| 3B | `src/cli.py` — `--evidence-two-pass`; `collect_provenance_evidence_for_entities` in `evidence_retriever.py` |
| 3C | `src/agent/evidence_retriever.py` — `DMB_EVIDENCE_DOC_QUOTA` |
| Eval env mapping | `evals/mirathorn_vertical_slice/run_council_room_question_set.py` — `DMB_EVIDENCE_TWO_PASS` |
