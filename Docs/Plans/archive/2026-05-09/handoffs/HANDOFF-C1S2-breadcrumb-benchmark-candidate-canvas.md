# HANDOFF — C1S2 Expansion: Breadcrumbed Ingest → Candidate Canvas → Grounded Benchmark

## Goal for the next conversation

Pick up from the now-extracted token-resolution design and execute the next vertical slice:

1. Expand the retrieval benchmark surface from C1S1 to **C1S2**.
2. Run the ingest/tagging pipeline to produce a **C1S2 breadcrumbed markdown artifact**.
3. Build a **grounded natural-query benchmark** from that artifact.
4. Present benchmark query candidates for human review in a **canvas**.
5. Run the benchmark with the approved candidates and report pass/cost using the 3-run gate.

---

## Current state to inherit

- Retrieval/token-resolution architecture is now layered and extracted under:
  - `src/token_resolution/`
  - `evals/sentence_routing_retrieval_falsification/token_resolver_shadow.py`
- Benchmark-only seed literals were moved to explicit artifact:
  - `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/benchmark_lexicon_seeds_v1.json`
- `breadcrumb_query_run.py` already supports shadow lexicon wiring and canvas refresh for the semantic-review canvas.
- **Implemented and verified:** C1S1 benchmark review canvas refresh is benchmark-owned inside `breadcrumb_query_run.py`:
  - auto refresh for natural C1S1 gold (`c1s1_canvas_refresh_auto_enabled`),
  - force targets via `--c1s1-canvas-tsx` (repeatable),
  - opt-out via `--skip-c1s1-canvas-refresh`,
  - callable emitter API in `c1s1_benchmark_canvas_emit.py`:
    - `build_c1s1_canvas_block`
    - `patch_c1s1_canvas_paths`
    - `refresh_c1s1_benchmark_canvases`
    - `c1s1_canvas_refresh_auto_enabled`
  - runner writes report first, includes `c1s1_canvas_refresh`, and exits non-zero on canvas patch errors.
  - tests: `tests/test_c1s1_benchmark_canvas_emit.py`, `tests/test_breadcrumb_query_run_canvas_integration.py`.
- C1S1 benchmark/canvas exists and is the reference pattern:
  - `canvases/c1s1-breadcrumb-query-benchmark-review.canvas.tsx`
  - `evals/sentence_routing_retrieval_falsification/c1s1_benchmark_canvas_emit.py`
  - `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s1_v1.json`

---

## C1S2 source of truth

- C1S2 recap source file:
  - `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/Session 2 - Finishing the Job.md`

Use this recap as the canonical source for the new breadcrumb artifact and benchmark questions.

---

## Architecture for this next slice

### A) Artifact generation (ingest/tagging lane)

Generate candidate breadcrumbed markdown for C1S2 using the existing tagging runner, then select one artifact as the baseline C1S2 retrieval index.

Primary runner:

- `evals/sentence_routing_retrieval_falsification/breadcrumb_tagging_variant_runner.py`

Prompt source:

- `evals/sentence_routing_retrieval_falsification/breadcrumb_prompt.py`

Normalizer/scorer:

- `evals/sentence_routing_retrieval_falsification/breadcrumb_normalize.py`
- `evals/sentence_routing_retrieval_falsification/breadcrumb_tagging_scorer.py`

### B) Candidate question surfacing (new)

Add a small generation + review surface that emits **candidate benchmark questions** from the C1S2 breadcrumb artifact and presents them in a canvas for human accept/revise/reject decisions.

Implementation pattern should mirror the now-landed C1S1 canvas API:

1. one module that builds deterministic generated-block content from artifacts,
2. one path patch helper returning `updated` / `unchanged` / `errors`,
3. optional run-orchestrator hook that can auto-refresh when C1S2 gold is in play.

Recommended new files:

- `evals/sentence_routing_retrieval_falsification/c1s2_query_candidate_build.py`
  - Reads C1S2 breadcrumbed artifact (or normalized records JSONL)
  - Emits candidate JSON with fields:
    - `candidate_id`
    - `question`
    - `expected_answer_draft`
    - `must_hit_tokens_draft`
    - `supporting_unit_ids`
    - `supporting_route_substrings`
    - `notes`
- `evals/sentence_routing_retrieval_falsification/c1s2_query_candidate_canvas_emit.py`
  - Reads candidate JSON and patches a generated block in a new canvas.
- `canvases/c1s2-breadcrumb-query-candidate-review.canvas.tsx`
  - Human review UI for candidate list + evidence snippets.

### C) Grounded benchmark lane

Once reviewed, promote approved candidates to a new gold file:

- `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s2_v1.json`

Then run:

- `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py`

Use the same 3-run acceptance protocol already documented in README.

---

## Concrete execution plan

## Phase 1 — Create C1S2 breadcrumb artifact

1. Prepare C1S2 frontmatter seed:
  - New file:
    - `evals/sentence_routing_retrieval_falsification/manual_labels/Session 2 - Finishing the Job.breadcrumbed.frontmatter_seed.md`
  - Use C1S1/C20 frontmatter format as template; update:
    - `source_recap_path`
    - campaign/session metadata
    - `entity_index` entries relevant to C1S2
2. Run tagging cohort:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_tagging_variant_runner \
  --variant pronoun_resolution_v1 \
  --n 3 \
  --corpus-root corpus/eldyrwild-markdown \
  --recap-relative-path "Longmont Campaign/Campaign 1/Session Recaps/Session 2 - Finishing the Job.md" \
  --frontmatter-source "evals/sentence_routing_retrieval_falsification/manual_labels/Session 2 - Finishing the Job.breadcrumbed.frontmatter_seed.md" \
  --sentinels evals/sentence_routing_retrieval_falsification/gold/breadcrumb_tagging_sentinels_session20.json
```

1. Select best run and save canonical C1S2 breadcrumb file:
  - `evals/sentence_routing_retrieval_falsification/manual_labels/Session 2 - Finishing the Job.breadcrumbed.md`
2. Normalize/smoke:
  - run `breadcrumb_query_run.py` once with `--breadcrumb-md` to ensure normalization + retrieval path is healthy.

## Phase 2 — Candidate generation + review canvas

1. Implement candidate builder script and output contract (JSON artifact under `artifacts/runs/<date>/`).
2. Implement candidate canvas emitter with generated markers, following the C1S1 helper style (`build_*_block`, `patch_*_paths`, `refresh_*`).
3. Add/refresh:
  - `canvases/c1s2-breadcrumb-query-candidate-review.canvas.tsx`
4. Human review pass:
  - mark candidate status (`accept`, `revise`, `reject`)
  - collect edits to expected answer/must-hit/supporting evidence.

## Phase 3 — Grounded C1S2 benchmark file

1. Create:
  - `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s2_v1.json`
2. Include only accepted candidates from canvas review.
3. Ensure each scenario is grounded in C1S2 evidence:
  - explicit `expect_route_substrings`
  - explicit `must_hit_tokens`
  - optional `semantic_equivalences` only when needed.

## Phase 4 — Benchmark execution + acceptance

Run 3 identical C1S2 benchmark invocations and report:

- per-run pass count,
- failing `scenario_id`s,
- `scenario_estimated_cost_usd`,
- min/mean/max/sum cost,
- dominant failure families.

Use current acceptance protocol from README (`dmb_breadcrumb_query_natural_gold_v1` 3-run gate).

Also capture canvas-refresh status in the report/output summary for the C1S2 review canvas once that hook is added (same operational shape as `c1s1_canvas_refresh`).

---

## Required tests for this handoff

Add/extend tests as you implement:

- `tests/test_c1s2_query_candidate_build.py` (new)
- `tests/test_c1s2_query_candidate_canvas_emit.py` (new)
- `tests/test_breadcrumb_natural_query.py` (existing; add C1S2 scenarios if needed)
- `tests/test_breadcrumb_query_canvas_payload.py` (if shared canvas payload code is reused)

Also run existing token-resolution and query suites before finalizing.

---

## File checklist (minimum expected edits)

- New:
  - `Docs/Plans/archive/2026-05-09/handoffs/HANDOFF-C1S2-breadcrumb-benchmark-candidate-canvas.md` (this file)
  - `evals/sentence_routing_retrieval_falsification/manual_labels/Session 2 - Finishing the Job.breadcrumbed.frontmatter_seed.md`
  - `evals/sentence_routing_retrieval_falsification/manual_labels/Session 2 - Finishing the Job.breadcrumbed.md`
  - `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s2_v1.json`
  - `evals/sentence_routing_retrieval_falsification/c1s2_query_candidate_build.py`
  - `evals/sentence_routing_retrieval_falsification/c1s2_query_candidate_canvas_emit.py`
  - `canvases/c1s2-breadcrumb-query-candidate-review.canvas.tsx`
  - tests for candidate build/emitter
- Existing likely touched:
  - `evals/sentence_routing_retrieval_falsification/README.md`
  - `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py` (wire C1S2 candidate-canvas auto refresh, modeled on C1S1 flow)
  - `evals/sentence_routing_retrieval_falsification/c1s1_benchmark_canvas_emit.py` (reference-only; no behavior changes expected)

---

## Constraints and guardrails

- Keep benchmark grounded in C1S2 artifact evidence only.
- Do not hand-edit generated canvas blocks.
- Keep C1S1 behavior stable; C1S2 should be additive.
- Use 3-run cost/pass gate for LLM-lane acceptance.
- If candidate quality is poor, iterate candidate generation prompt/heuristics before loosening benchmark rubric.

---

## Done definition

This handoff is complete when a fresh conversation can run one documented sequence that:

1. builds C1S2 breadcrumbed markdown,
2. generates benchmark query candidates,
3. presents candidates in canvas for human review,
4. materializes reviewed C1S2 gold benchmark,
5. runs C1S2 benchmark 3 times with pass/fail + cost summary.

