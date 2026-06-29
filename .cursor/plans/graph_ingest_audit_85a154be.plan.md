---
name: graph ingest audit
overview: "Skeptically stabilize the graph-ingest tuning loop before prompt iteration: make scoring trustworthy, snapshot prompts, then change the beat/edge contracts with measured Session 23 re-runs."
todos:
  - id: scorecard-schema
    content: Fix semantic_state normalization and strict live-vs-gold scorecard output.
    status: pending
  - id: prompt-snapshots
    content: Persist per-run category pass prompt snapshots and manifest metadata.
    status: pending
  - id: beat-contract
    content: Give beat_pass a consolidated node catalog and verify non-empty node linkage.
    status: pending
  - id: edge-contract
    content: Seed party collective/member_of edges and enrich structural edge vocabulary.
    status: pending
  - id: session23-cohort
    content: Run and score same-config Session 23 re-extractions with cost and variance reporting.
    status: pending
  - id: ui-cleanup-boundary
    content: Keep ingest UI plumbing verification separate from scorecard/comparison UX.
    status: pending
isProject: false
---

# Graph Ingest Tuning Plan

## Findings To Act On

- The scorecard is not trustworthy yet: [`evals/graph_memory_layer/report_live_vs_gold.py`](evals/graph_memory_layer/report_live_vs_gold.py) still routes raw live runs through the strict preview parser, while live extraction emits legacy `semantic_state` keys from [`src/graph_memory/extraction/category_candidate_graph_extractor.py`](src/graph_memory/extraction/category_candidate_graph_extractor.py).
- The extraction gap is contractual, not just stochastic: `beat_pass` has no node catalog and permits empty `involved_node_ids`; `edge_pass` gets only a minimal node list and lacks structural relationship vocabulary; consolidation injects party member nodes but no party collective or deterministic `member_of` edges.
- The uncommitted ingest UI/server work is useful but incomplete: it covers resume and `force_graph_run`, but run inventory/delete/live pass progress remain separate dogfood items. Keep comparison work CLI/canvas-first for now, not inside [`apps/live-control-ui/src/modules/IngestionModule.tsx`](apps/live-control-ui/src/modules/IngestionModule.tsx).
- Prompt snapshots are currently missing from runtime artifacts. Add them before prompt iteration so every LLM run has diffable prompt inputs, prompt hashes, model id, and source span metadata.

## Implementation Sequence

1. **Stabilize the scorecard and schema contract.**
   - Normalize legacy semantic-state aliases in [`evals/graph_memory_layer/reconcile_live_candidate.py`](evals/graph_memory_layer/reconcile_live_candidate.py): map `canon_status` to `canon_state`, `lifecycle` to `lifecycle_state`, and strip non-canonical keys like `memory_status` before strict parsing.
   - Align runtime `DEFAULT_SEMANTIC_STATE` in [`src/graph_memory/extraction/category_candidate_graph_extractor.py`](src/graph_memory/extraction/category_candidate_graph_extractor.py) to the canonical preview keys.
   - Update [`evals/graph_memory_layer/live_vs_gold_compare.py`](evals/graph_memory_layer/live_vs_gold_compare.py) / [`evals/graph_memory_layer/report_live_vs_gold.py`](evals/graph_memory_layer/report_live_vs_gold.py) so the CLI can score a raw live `candidate_graph.json` and write a default `comparison_report.json` beside the run.

2. **Add prompt snapshots before changing prompt behavior.**
   - Persist per-pass prompt inputs from [`src/graph_memory/extraction/category_candidate_graph_extractor.py`](src/graph_memory/extraction/category_candidate_graph_extractor.py) into each graph-ingest run directory, probably under `category_pass_prompts/`.
   - Store `prompt_packet_manifest.json` with prompt SHA256s, pass names, model id, extractor version, and source recap SHA256; keep full prompt packets under ignored run artifacts because they contain corpus prose.
   - Add tests that verify snapshot files are written in the runner path without committing real session prompt text.

3. **Fix beat linkage as a pipeline contract.**
   - Reorder or split the pipeline so `beat_pass` receives a consolidated node catalog, including party anchors, before it is asked to fill `involved_node_ids`.
   - Change the beat prompt/schema tests so empty `involved_node_ids` is no longer the expected happy path when relevant nodes exist.
   - Verify via fixture client first, then a live Session 23 re-extract.

4. **Fix structural party and relationship edges.**
   - Add deterministic party collective and roster `member_of` edge seeding in [`src/graph_memory/session_graph_context.py`](src/graph_memory/session_graph_context.py) / [`src/graph_memory/party_context.py`](src/graph_memory/party_context.py), with diagnostics showing seeded nodes/edges.
   - Enrich the `edge_pass` prompt with structural relationship vocabulary from [`evals/graph_memory_layer/live_extractor_prompt_harness.py`](evals/graph_memory_layer/live_extractor_prompt_harness.py), keeping transient combat/actions in beats rather than edges.
   - Avoid gold leakage: use general vocabulary and roster context, not Session 23 gold IDs or expected edges in model-facing prompts.

5. **Measure, then iterate.**
   - Run the fixed scorecard on the latest existing Session 23 run to establish a clean pre-change baseline.
   - Run K same-config Session 23 live extractions using `force_graph_run: true`, with prompt snapshots captured.
   - Report node/edge/beat recall distributions, cost totals from manifests, and dominant soft misses. Only then decide whether the next move is prompt tuning, deterministic post-linking, or comparator/rubric adjustment.

6. **Keep UI cleanup separate.**
   - Re-run and review the existing uncommitted UI/server tests, but do not fold run-vs-gold UX into `IngestionModule` yet.
   - Track run inventory/delete/live pass progress as their own product cleanup slice after the scorecard and extraction loop are reliable.

## Verification Plan

- Scorecard/schema tests: `uv run pytest tests/test_graph_memory_live_extractor_prompt_harness.py tests/test_graph_memory_category_graph_model_study.py tests/test_graph_memory_reconcile_anchor_quotes.py -q`
- Existing graph-ingest API tests: `uv run pytest tests/test_live_recap_ingest_graph_preview_api.py -v`
- Existing UI tests: `cd apps/live-control-ui && npm run test -- src/modules/IngestionModule.test.tsx`
- Strict scorecard smoke: `uv run python -m evals.graph_memory_layer.report_live_vs_gold --candidate-output out/graph_memory/runs/longmont-c2/session-23/<run>/candidate_graph.json`
- Live extraction validation: forced Session 23 re-extract, then compare `comparison_report.json`, `pass_outputs.json`, `pass_telemetry.json`, `consolidation_diagnostics.json`, and prompt snapshot hashes.

## Guardrails

- Do not commit run artifacts under `out/graph_memory/runs/` or full prompt snapshots containing recap prose.
- Do not commit the existing uncommitted ingest-tool changes or new changes unless explicitly asked.
- Keep gold files fixed unless a corpus/design rationale demands gold realignment; do not tune prompts with gold-only terms.
- Prefer measured movement in edge/beat recall over broad prompt rewrites.
