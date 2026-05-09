# Report: Wave 4 — document planner and chunk embedding rerank (4A–4C)

**Date:** 2026-04-09  
**Benchmark:** Council room question set (`evals/mirathorn_vertical_slice/run_council_room_question_set.py`)  
**Store:** `evals/mirathorn_vertical_slice/output/phase_d_store` (6 documents, ~1313 evidence units)  
**Reference:** `Docs/Plans/HANDOFF-execute-evidence-retrieval-synthesis-experiments.md` § Wave 4  

---

## Executive summary

Wave 4 added two retrieval-stage levers: an **LLM document planner** (pre-filter `scope_document_ids` before evidence-first retrieval) and an optional **chunk-level embedding rerank** over the top-N BM25 hits. Both were exercised on the same Phase 3 evidence-first stack used in Waves 1–3.

**On this six-document slice:**

| Experiment | Outcome |
|------------|---------|
| **4A** (`DMB_DOCUMENT_PLANNER=1`) | **Semantic pass regressed** (6/15 vs 8/15 baseline). **Synthesis_gap increased** (8 vs 5). Planner ran with **0% fallback** but **narrowed scope** in ways that hurt answers. |
| **4B** (`DMB_EVIDENCE_EMBEDDING_RERANK=1`) | **Semantic pass matched baseline** (8/15). **evidence_gap improved** (10 vs 13). **Synthesis_gap worsened** (9 vs 5). **Latency exploded** (~42s average per question on CPU) because the embedding model **reloads every question**. |
| **4C** (4A + `DMB_EVIDENCE_PER_SEED_NEIGHBORS=1`) | **No recovery**: semantic 6/15, strict 4/15, **hit=29** (worst of the wave). |

**Verdict:** Neither lever is a drop-in win on `phase_d_store` under the handoff pass criteria. The document planner is a **plausible large-corpus tool** but is **harmful when the corpus is already tiny** (6 docs): false negatives on “optional” world docs still delete chunks that co-occur with gold must-hit tokens. Embedding rerank shows **retrieval-stage signal** (lower evidence_gap) but does not translate to semantic wins here, and **needs a process-level model cache** before any production or repeated eval use.

---

## Shared Phase 3 stack (all Wave 4 runs)

```text
DMB_EVIDENCE_FIRST=1
DMB_EVIDENCE_ADAPTIVE_TOP_K=1
DMB_EVIDENCE_ADAPTIVE_TOP_K_MAX=48
DMB_EVIDENCE_DENSITY_THRESHOLD=0.3
```

**Comparators:**

- **Baseline:** `council_room_question_set.json.exp1a_run3` (Phase 3 stability, Wave 1).
- **Best prior retrieval tweak:** `council_room_question_set.json.exp3a` (`DMB_EVIDENCE_PER_SEED_NEIGHBORS=1`, Wave 3).

---

## Summary table

Metrics are taken from the saved artifacts:  
`council_room_question_set.json.exp1a_run3`, `.exp3a`, `.exp4a`, `.exp4b`, `.exp4c`.

| Exp | Phase / artifact | Semantic pass | Strict pass | evidence_gap | retriever_gap | synthesis_gap | hit | avg_support | pass / retr_gap / synth_gap (failure surface) | avg context chars | avg total ms |
|-----|------------------|---------------|-------------|--------------|---------------|---------------|-----|-------------|-----------------------------------------------|-------------------|--------------|
| Baseline | exp1a_run3 | 8/15 | 7/15 | 13 | 8 | 5 | 34 | 0.722 | 8 / 3 / 4 | 22,416 | 5,458 |
| 3A | exp3a | **9/15** | 7/15 | 13 | **7** | 5 | **35** | **0.750** | **9** / 3 / 3 | 22,035 | 5,547 |
| **4A** | exp4a | **6/15** | 5/15 | 14 | 8 | **8** | **30** | **0.761** | 6 / 2 / 7 | 22,258 | **7,238** |
| **4B** | exp4b | 8/15 | 6/15 | **10** | 8 | **9** | 33 | 0.717 | 8 / 4 / 3 | 22,473 | **41,645** |
| **4C** | exp4c | **6/15** | **4/15** | 14 | 7 | **10** | **29** | 0.761 | 6 / 2 / 7 | 22,377 | 6,871 |

*Note:* `pipeline_config` in the JSON only reflects CLI flags. **4B** also had `DMB_EVIDENCE_EMBEDDING_RERANK=1`. **4C** also had `DMB_EVIDENCE_PER_SEED_NEIGHBORS=1` (not shown in the string).

---

## Implementation (what shipped)

### Document planner

- **Module:** `src/agent/document_planner.py`  
  - `build_document_roster(evidence_units, campaign_id)` — per-document roster from allowed units (`_unit_allowed` from `evidence_retriever`).  
  - `plan_documents_async` / `plan_documents` — OpenAI JSON response, markdown/``` fence tolerance, **fallback to all candidate doc IDs** on empty roster / parse failure / missing key.  
  - Model resolution: `MODEL_POLICY.json` → `actions.document_planning` or `query_planning`, else `gpt-5.4-nano`.

- **CLI:** `src/cli.py`  
  - `--document-planner`, `--document-planner-model`.  
  - Runs **after** `project()`, **before** `attach_scope_relevance_metadata`: merges `selected_document_ids` into `scope_document_ids` when not fallback.  
  - `retrieval_meta["document_planner"]` always present (`enabled: false` when off).

- **Eval runner:** `evals/mirathorn_vertical_slice/run_council_room_question_set.py`  
  - `DMB_DOCUMENT_PLANNER=1` → `--document-planner`; `DMB_DOCUMENT_PLANNER_MODEL` → optional model override.  
  - Trace rows include `document_planner` and stderr logs `document-planner: n=… fallback=…`.

### Chunk embedding rerank

- **File:** `src/agent/evidence_retriever.py` — `_embedding_rerank_evidence_hits` after BM25 scoring, before adaptive top-k.  
- **Gate:** `DMB_EVIDENCE_EMBEDDING_RERANK=1`.  
- **Tunables:** `DMB_EVIDENCE_EMBEDDING_RERANK_TOP_N` (default 48), `DMB_EVIDENCE_EMBEDDING_RERANK_WEIGHT` (default 0.6).  
- **Model:** `evals/mirathorn_vertical_slice/embedding_scorer.py` (`load_embedding_model`, `embed_texts`). Requires `uv sync --extra embedding`.  
- **Failure behavior:** import/embed errors → **no-op** (original BM25 order).

---

## Exp 4A — Document planner

### Configuration

```text
DMB_DOCUMENT_PLANNER=1
DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1
DMB_PHASE_WRITE_LEDGER=1
DMB_PHASE_NAME=exp4a_document_planner
```

### Observations

- **Fallback rate:** 0/15 (`fallback=False` in traces) — planner API path was healthy.
- **Latency:** ~+1.3–2.4s per question for the planner call; average wall time **~7.2s** vs **~5.5s** baseline (synthesis dominates either way).
- **Quality:** **Semantic 6/15**; **synthesis_gap 8**; **hit 30** — clear regression vs baseline and vs 3A.
- **context_support:** avg **0.761** (slightly up vs baseline 0.722) — the benchmark’s context-support metric and semantic pass **diverged**, which points to **synthesis / strict token matching** pain, not a simple “less context” story.

### Document-selection audit (heuristic)

A coarse audit was run: for each gold must-hit token, find documents whose evidence text **contains that substring**, then compare to planner `selected_document_ids` in `council_room_trace.jsonl.exp4a`.

- **8 / 15** questions showed at least one such document **missing** from the planner selection.
- **Repeated miss:** `doc_the_city_of_mirathorn` (broad city dossier) was often omitted while still containing strings that overlap gold must tokens; **`doc_longmont_campaign_general_notes`** was missed on at least one architecture question.

This supports the handoff’s **false-negative** risk: on a small store, “focused” selection **removes** chunks that are still lexically tied to graded tokens, even when BM25-over-full-corpus would have kept them in play.

### Verdict vs handoff §4 pass/fail

- **evidence_gap ≤ 10:** **Fail** (14).  
- **semantic pass ≥ 9:** **Fail** (6).  
- **avg context_chars decreases:** **Inconclusive / small** (22,258 vs 22,416 — not a reliable win).  
- **No false negatives on must-hit doc coverage:** **Fail** (audit above).  

---

## Exp 4B — Chunk-level embedding rerank

### Configuration

```text
DMB_EVIDENCE_EMBEDDING_RERANK=1
```

### Observations

- **evidence_gap 10** vs baseline **13** — rerank **does** change which chunks enter the entity/evidence pipeline in a way that reduces “token never appeared in evidence” failures.
- **Semantic pass 8/15** — **no improvement** vs baseline; **synthesis_gap 9** — **worse** than baseline (5).
- **Performance:** **~41.6s average per question**. Logs show **`load_embedding_model()` per question** (full weight load each time). The handoff assumed “< 500ms for 48 chunks”; that may hold **after one-time load**, but the current integration **does not amortize** the model.

### Verdict vs handoff

- **Latency / economics:** **Fail** for repeated evals until the model is **cached at process scope** (or loaded once in the runner process).
- **Quality:** **Inconclusive / weak** — retrieval-stage gap improved, end-to-end semantic did not.

---

## Exp 4C — Document planner + per-seed neighbors (3A stack)

### Configuration

```text
DMB_DOCUMENT_PLANNER=1
DMB_EVIDENCE_PER_SEED_NEIGHBORS=1
```

### Observations

- **Strict 4/15**, **semantic 6/15**, **hit 29** — **strictly worse** than 4A and much worse than 3A alone.
- Combining **scope narrowing** (planner) with **per-seed neighbor budgeting** does not compensate on this slice.

### Verdict

**Do not promote** this combination for `phase_d_store`. Revisit only with **planner fixes** (e.g., union with BM25-top documents, or “always include city dossier when Mirathorn entities fire”) and **full-corpus** tests.

---

## Recommendations

1. **Document planner**  
   - Treat as **large-corpus** lever: re-benchmark on `out/stores/dungeonbuddy_store_escalation_full_mini_to_54` (120 docs) where scope reduction is high leverage.  
   - On small stores, consider **disabling** or **unioning** planner output with a deterministic guard (e.g., always include docs linked to top-k BM25 chunks before planning).  
   - Extend `pipeline_config` or summary JSON to echo **env-only** flags (`DMB_EVIDENCE_PER_SEED_NEIGHBORS`, `DMB_EVIDENCE_EMBEDDING_RERANK`) so artifacts are self-describing.

2. **Embedding rerank**  
   - Add a **module-level or CLI-lifetime cache** for `load_embedding_model()` so eval and interactive CLI do not reload weights per question.  
   - Re-run 4B after caching; record **p50/p95** retrieval-stage timing per `engineering-principles.mdc` harness norms.

3. **Keep 3A as the leading retrieval tweak** on this benchmark until planner/rerank variants beat **exp3a** on semantic pass and stage losses.

---

## Artifact index

| Artifact | Contents |
|----------|----------|
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp4a` | Full summary, 4A |
| `evals/mirathorn_vertical_slice/output/council_room_trace.jsonl.exp4a` | Per-question trace incl. `document_planner` |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp4b` | 4B |
| `evals/mirathorn_vertical_slice/output/council_room_trace.jsonl.exp4b` | 4B trace |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json.exp4c` | 4C |
| `evals/mirathorn_vertical_slice/output/council_room_trace.jsonl.exp4c` | 4C trace |
| `evals/mirathorn_vertical_slice/output/evidence_gap_phase_ledger.json` | Appended rows `exp4a_document_planner`, `exp4b_embedding_rerank`, `exp4c_planner_per_seed` |

---

## Code touchpoints (for reviewers)

- `src/agent/document_planner.py` — roster + planning  
- `src/cli.py` — `--document-planner`, `retrieval_meta["document_planner"]`  
- `src/agent/evidence_retriever.py` — `_embedding_rerank_evidence_hits`  
- `evals/mirathorn_vertical_slice/run_council_room_question_set.py` — `DMB_DOCUMENT_PLANNER*` wiring and trace fields  
