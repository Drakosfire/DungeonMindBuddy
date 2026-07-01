# Graph Memory Layer — Fixture Status Labels

Quick reference for `examples/` and `artifacts/` subdirectories. See root [`README.md`](README.md) for commands.

Fixture authority ledger: [`FIXTURE-AUTHORITY-LEDGER.md`](FIXTURE-AUTHORITY-LEDGER.md) classifies which fixtures are candidate graph gold, projection gold, routing/retrieval gold, mechanical ingest fixtures, and generated artifacts.

## Manual gold (hand-authored, not extractor output)

| Path | Session | Use |
|------|---------|-----|
| `examples/session_1_candidate_graph_gold/` | 1 | Candidate graph gold (26 nodes); C1 cross-campaign vocabulary ablation bed |
| `examples/mirathorn_city_candidate_graph_gold/` | world | Candidate graph gold (28 nodes); world-authority vocabulary ablation bed |
| `examples/session_23_candidate_graph_gold/` | 23 | Candidate graph gold (42 nodes); compare live extraction |
| `examples/session_24_manual_projection_dogfood/` | 24 | Projection gold (36 nodes); **not** LLM extraction benchmark |

## Proven extraction pipeline (target for product runtime)

| Path | Notes |
|------|-------|
| `category_graph_model_study.py` | `run_category_pipeline`: actor → location → collective → object → thread → beat → edge |
| `artifacts/category_graph_model_study/2026-06-26/anchor_quote_n3/` | n=3 validation on Session 22 gold (`gpt-5.4-mini`, node recall ~0.80–0.88) |

## Runtime stub (replace with category pipeline)

| Path | Notes |
|------|-------|
| `src/graph_memory/extraction/preview_candidate_graph_extractor.py` | Single compact GPT call (~12-node cap); wired today, not the quality path |

## Design reference (broader contract)

| Path | Notes |
|------|-------|
| `examples/multi_pass_extraction_contract/` | 9-pass contract sketch for Session 23 |
| `examples/eval_only_extractor_harness/` | Static candidate bundle shaped by multi-pass contract |

## Contract fixtures

| Path | Session | Use | Notes |
|------|---------|-----|-------|
| `examples/vocabulary_contract_fixtures/` | fixture-only | Vocabulary DTO contract fixtures | Hand-authored JSON examples for model validation and round-trip tests; not extraction gold. |

## Generated / dogfood runs

| Path | Notes |
|------|-------|
| `artifacts/graph_ingest_runs/session_24_manual_projection_dogfood/` | Manual gold → preview union store dogfood |
| `artifacts/graph_ingest_runs/session_1_vocabulary_ablation_projection_dogfood/` | C1S1 ablation candidate → preview union store + Mirathorn world merge |
| `out/graph_memory/runs/` | Local runtime graph-ingest output (gitignored when populated) |
| `runs/live_extractor_prompt_harness/` | Gitignored prompt renders |
| `runs/live_recap_ingest/` | Gitignored live ingest bundles |

## Static review artifacts

| Path | Notes |
|------|-------|
| `examples/static_preview_graph_ui_prototype/` | HTML prototype for GM preview UX |
| `examples/static_extractor_output_comparison_report/` | Static candidate-vs-gold report fixture |

## Recap ingest fixtures (mechanical, no LLM)

| Path | Notes |
|------|-------|
| `examples/session_23_recap_ingest/` | Session 23 normalized recap + span seeds |
| `examples/session_1_recap_ingest/` | Session 1 normalized recap + span seeds |
| `examples/mirathorn_city_world_doc/` | Mirathorn city world doc snapshot + span seeds |
| `examples/session_22_recap_ingest/` | Session 22 fixture |
| `examples/live_recap_ingest_run_bundle/` | Sample run bundle for Session 23 |

**Corpus hierarchy (recaps + worldbuilding):** `Docs/Anchors/CORPUS-ANCHOR.md` · `corpus/CORPUS-INDEX.json` (built by `scripts/build_corpus_index.py`).
