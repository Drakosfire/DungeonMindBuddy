# HANDOFF — Graph-first recap ingest

**Status:** READY — implementation slice (separate from 2026-06-28 doc/archive cleanup)  
**Workstream:** Graph Memory / Recap Ingest  
**Goal:** Make `generate_recap_memory` graph-first; breadcrumb/session-memory becomes optional legacy, not a gate for graph projection.

## Problem

One-click **Generate Recap Memory** still runs the full breadcrumb-era pipeline before graph extraction:

```text
stage → apply/normalize → frontmatter seed → breadcrumb ingest → session memory → graph extraction → union store → projection
```

Graph projection is the product surface replacing breadcrumbing. Legacy steps add confusion, duplicate normalized files, and block ingest when breadcrumb/session-memory preconditions fail—even when a normalized recap exists and graph extraction could proceed.

Additionally, runtime extraction uses `preview_candidate_graph_extractor` — a **temporary single-call stub** (~12-node cap). Session 23 gold has 42 nodes. The proven quality path is the **category-decomposed pipeline** in `evals/graph_memory_layer/category_graph_model_study.py` (`run_category_pipeline`): 5 category node passes + beat + edge (7 LLM calls), validated in `artifacts/category_graph_model_study/2026-06-26/anchor_quote_n3/` (n=3, `gpt-5.4-mini`, Session 22 node recall ~0.80–0.88). That pipeline must replace the compact extractor in `graph_preview_runner.py`.

## Target behavior

```text
raw recap
→ stage (optional reuse of staged notes)
→ apply + normalize (canonical + normalized recap)
→ graph: source span bundle
→ graph: category-decomposed candidate extraction (`run_category_pipeline`; default `gpt-5.4-mini` per anchor_quote_n3)
→ graph: preview union store
→ graph: projection payload
→ UI: recap view with graph chips

legacy (optional / deferred):
→ frontmatter seed
→ breadcrumb ingest
→ session memory materialization
```

Graph steps must **not** require `breadcrumb_found` or `session_memory_materialized`.

## Files in scope

- `apps/live_control_server/routes/recap_ingest.py` — `_generate_recap_memory_from_request`: reorder/skip legacy steps for graph path
- `apps/live_control_server/services/recap_graph_preview_ingest.py` — ensure materialization runs when normalized recap exists
- `evals/graph_memory_layer/graph_preview_runner.py` — wire `run_category_pipeline` instead of `extract_preview_candidate_graph`
- `evals/graph_memory_layer/category_graph_model_study.py` — graduate `run_category_pipeline` / consolidate helpers into `src/graph_memory/extraction/` (or import from evals as interim)
- `apps/live-control-ui/src/modules/IngestionModule.tsx` — UI copy + default model (`gpt-5.4-mini` for graph extract)
- `tests/test_live_recap_ingest_pipeline.py`
- `tests/test_live_recap_ingest_api.py`
- `tests/test_live_recap_ingest_graph_preview_api.py`

## Files explicitly OUT OF scope

- `evals/graph_memory_layer/artifacts/**` (generated dogfood artifacts)
- `corpus/**` (except follow-up reconcile if needed)
- `src/prompts/**`
- Deleting breadcrumb scripts (`scripts/breadcrumb*.py`, `materialize_session_memory.py`) — keep for legacy compatibility
- Raising caps on `preview_candidate_graph_extractor` — stub only; do not treat as the quality fix

## Implementation notes

1. **`generate_recap_memory` graph-first path**
   - After normalize succeeds, resolve normalized recap path and call `materialize_recap_preview_supergraph(extract_graph=True)` without requiring breadcrumb/session-memory states.
   - Return graph status even when legacy steps are skipped; add warning states like `legacy_breadcrumb_skipped`.

2. **Legacy opt-in**
   - Add request flag `include_legacy_breadcrumb: bool = False` (default false for one-click) OR keep running legacy in parallel but non-blocking.
   - Document in API model and UI advanced section.

3. **Category-decomposed extraction (required for quality)**
   - Wire `run_category_pipeline` from `category_graph_model_study.py` into `graph_preview_runner.py`.
   - Passes: `actor_pass`, `location_pass`, `collective_pass`, `object_pass`, `thread_pass`, `beat_pass`, `edge_pass`.
   - Default model: `gpt-5.4-mini` (anchor_quote_n3 cohort). Party anchors from `PartyContext`, not model discovery.
   - Compare against `evals/graph_memory_layer/examples/session_23_candidate_graph_gold/candidate_graph_gold.json` after wiring.

4. **Multi-pass contract (reference only)**
   - Broader 9-pass design: `evals/graph_memory_layer/examples/multi_pass_extraction_contract/`
   - Category study is the graduated slice that already meets gold recall on Session 22.

## Verification

```bash
.venv/bin/python -m pytest \
  tests/test_live_recap_ingest_pipeline.py \
  tests/test_live_recap_ingest_api.py \
  tests/test_live_recap_ingest_graph_preview_api.py -q
```

Manual smoke: paste Session 23 raw recap → Generate Recap Memory → confirm graph manifest under `out/graph_memory/runs/` with `extraction_mode: llm` and projection payload without breadcrumb completion.

## Success criteria

- One-click ingest completes graph projection when normalized recap exists, without breadcrumb/session-memory.
- UI clearly labels breadcrumb/session-memory as legacy.
- Session 23 ingest produces candidate graph with mayor + location nodes (after extractor prompt fix) or documents gap with gold comparison in manifest diagnostics.

## References

- `Docs/Design/GRAPH-MEMORY-PROJECT-LAYOUT.md`
- `Docs/Experiments/GRAPH-MEMORY-WORKSTREAM-ANCHOR.md`
- `evals/graph_memory_layer/FIXTURE-STATUS.md`
