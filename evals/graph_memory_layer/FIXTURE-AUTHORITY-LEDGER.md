# Graph Memory Fixture Authority Ledger

Status: active fixture authority ledger<br>
Branch anchor: `experiment/ontology-taxonomy-ladder`<br>
Purpose: classify graph-memory and adjacent benchmark fixtures by what they can safely prove.

## Fixture authority classes

| Authority class | Safe for candidate graph extraction comparison? | Meaning | Allowed use | Forbidden use |
|---|---:|---|---|---|
| `candidate_graph_gold` | yes | Hand-authored or reviewed node/edge/beat candidate graph target with source-grounded evidence refs. | Direct candidate graph extraction comparison and fixture-specific recall/precision checks. | Treating as canon memory, global stable-node truth, or projection UX gold without review. |
| `projection_gold` | no | Hand-authored graph/projection payload or UI dogfood target for projection behavior. | Projection rendering, chip/node-view UX validation, and source-boundary dogfood. | Candidate graph recall/precision scoring or extractor quality claims. |
| `routing_gold` | no | Gold for sentence/unit routing to hubs, routes, or breadcrumb targets. | Routing, hub assignment, and abstention tests. | Graph node/edge extraction scoring without a dedicated conversion PR. |
| `retrieval_gold` | no | Query-answer or expected-hit gold for retrieval/admission behavior. | Retrieval, context packet admission, and answer-support checks. | Candidate graph extraction scoring or canon graph promotion. |
| `session_event_gold` | limited | Structured scene-event extraction target, not graph node/edge gold. | Event extraction benchmarks and possible reviewed conversion inputs. | Direct candidate graph node/edge scoring without explicit conversion. |
| `classifier_gold` | no | Expected classifier or live-prep route labels. | Classifier benchmark evaluation and live-turn routing checks. | Candidate graph, projection, or retrieval gold. |
| `mechanical_ingest_fixture` | no | Deterministic recap/source-span/source-artifact ingest fixture with no graph extraction. | Ingest plumbing, provenance/source-span resolver checks, and fixture inputs for later gold. | Gold graph scoring or model-quality claims. |
| `category_extraction_study_artifact` | no | Generated category-model study outputs and comparison reports. | Model-study analysis, pipeline diagnostics, and reproduction notes. | Treating generated output as gold unless a reviewed gold fixture says so. |
| `static_review_fixture` | no | Static UI/report artifact for human review or contract illustration. | Review, screenshots, report formatting, and UX communication. | Extraction, retrieval, or classifier scoring authority. |
| `generated_run_artifact` | no | Output produced by a runner, dogfood import, or local/runtime execution. | Debugging, reproducibility traces, and provenance review. | Gold authority unless separately accepted and ledgered. |
| `unknown_needs_inspection` | no | Purpose or shape is not yet established. | Discovery only; inspect before use. | Any benchmark score, architecture claim, or canon/projection assertion. |
| `vocabulary_contract_fixture` | no | Hand-authored JSON examples for vocabulary contract shape and round-trip tests. | Contract validation, example payloads, and future schema/export reference. | Candidate graph scoring, canon memory, projection gold, prompt input authority, or Stable Global Node truth. |

## Candidate graph extraction gold

| Path | Session/campaign | Authority class | Candidate graph comparison? | Proves | Must not be used for | Notes |
|---|---|---|---:|---|---|---|
| `evals/graph_memory_layer/examples/session_23_candidate_graph_gold/` | Longmont C2 S23 | `candidate_graph_gold` | yes | Hand-authored candidate graph target for nodes/edges/beats using Session 23 recap evidence. | Canon promotion, stable global-node truth, projection UX scoring, or exact `node_id` identity claims. | Manifest declares `authoring_mode: hand_authored_gold` and points at Session 23 recap ingest span refs. |
| `evals/graph_memory_layer/examples/session_22_candidate_graph_gold/` | Longmont C2 S22 | `candidate_graph_gold` | yes | Candidate graph target used by category extraction study comparison. | Projection gold, canon promotion, or generated-output authority. | Present on branch during inventory; keep separate from category-study generated artifacts. |

## Projection gold / projection dogfood

| Path | Session/campaign | Authority class | Candidate graph comparison? | Proves | Must not be used for | Notes |
|---|---|---|---:|---|---|---|
| `evals/graph_memory_layer/examples/session_24_manual_projection_dogfood/` | Longmont C2 S24 | `projection_gold` | no | Manual graph projection dogfood can test recap chips, node views, adjacency, uncertainty, and source-boundary UX. | Candidate graph extraction recall/precision, LLM extractor claims, or canon promotion. | README explicitly says this is not an extractor benchmark or canon-promotion artifact. |

## Mechanical ingest fixtures

| Path | Session/campaign | Authority class | Candidate graph comparison? | Proves | Must not be used for | Notes |
|---|---|---|---:|---|---|---|
| `evals/graph_memory_layer/examples/session_22_recap_ingest/` | Longmont C2 S22 | `mechanical_ingest_fixture` | no | Normalized recap path and manual source-span seed refs are representable without LLMs. | Candidate/gold graph scoring or extraction quality claims. | Manifest diagnostics say no graph extraction and no gold graph output. |
| `evals/graph_memory_layer/examples/session_23_recap_ingest/` | Longmont C2 S23 | `mechanical_ingest_fixture` | no | Raw recap normalization, paragraph indexing, and source-span seed refs are deterministic fixture inputs. | Candidate/gold graph scoring or extraction quality claims. | Used as source fixture for Session 23 candidate graph gold. |
| `evals/graph_memory_layer/examples/live_recap_ingest_run_bundle/` | Longmont C2 S23 sample | `mechanical_ingest_fixture` | no | Static example of explicit-input recap ingest bundle and provenance/source-unit outputs. | Treating sample bundle as generated graph gold or candidate extraction output. | Manifest diagnostics say extractor execution is not required and candidate graph was not generated. |

## Category extraction study artifacts

| Path | Session/campaign | Authority class | Candidate graph comparison? | Proves | Must not be used for | Notes |
|---|---|---|---:|---|---|---|
| `evals/graph_memory_layer/artifacts/category_graph_model_study/2026-06-26/anchor_quote_n3/` | Longmont C2 S22 | `category_extraction_study_artifact` | no | Generated n=3 category-pipeline outputs and comparison metrics against Session 22 gold. | Gold authority, canon graph source, or projection target. | Cohort summary records `gpt-5.4-mini` runs with node recall around 0.80-0.88 and invalid canonical IR. |

## Routing / retrieval / breadcrumb gold

| Path | Session/campaign | Authority class | Candidate graph comparison? | Proves | Must not be used for | Notes |
|---|---|---|---:|---|---|---|
| `evals/sentence_routing_retrieval_falsification/gold/scenario_c1_session1_pc.json` | Longmont C1 S1 | `routing_gold` | no | PC hub routing/abstention expectations for sentence units. | Candidate graph node/edge scoring. | Shape is `sentence_routing_falsification_v1` with `must_route`/abstention-style route expectations. |
| `evals/sentence_routing_retrieval_falsification/gold/scenario_c1_session2_pc.json` | Longmont C1 S2 | `routing_gold` | no | PC hub routing/abstention expectations for sentence units. | Candidate graph node/edge scoring. | Notes identify legacy Stage B PC-only gate. |
| `evals/sentence_routing_retrieval_falsification/gold/scenario_c1_session3_pc.json` | Longmont C1 S3 | `routing_gold` | no | PC hub routing/abstention expectations for sentence units. | Candidate graph node/edge scoring. | Manifest is limited to C1 PC hubs. |
| `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s1_v1.json` | Longmont C1 S1 | `retrieval_gold` | no | Natural-language breadcrumb query/retrieval expectations. | Candidate graph node/edge scoring. | Found during C1 S1 search. |
| `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s2_v1.json` | Longmont C1 S2 | `retrieval_gold` | no | Natural-language breadcrumb query/retrieval expectations. | Candidate graph node/edge scoring. | Found during C1 S2 search. |
| `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s3_v1.json` | Longmont C1 S3 | `retrieval_gold` | no | Natural-language breadcrumb query/retrieval expectations. | Candidate graph node/edge scoring. | Found during C1 S3 search. |
| `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s13_v1.json` | Longmont C1 S13 | `retrieval_gold` | no | Natural-language query expectations for ingestion-to-retrieval validation. | Candidate graph node/edge scoring. | Schema is `dmb_breadcrumb_query_natural_gold_v1`. |
| `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_tagging_sentinels_c1s2.json` | Longmont C1 S2 | `routing_gold` | no | Breadcrumb tagging sentinel expectations. | Candidate graph node/edge scoring. | Found during C1 S2 search. |
| `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_tagging_sentinels_c1s3.json` | Longmont C1 S3 | `routing_gold` | no | Breadcrumb tagging sentinel expectations. | Candidate graph node/edge scoring. | Found during C1 S3 search. |
| `evals/sentence_routing_retrieval_falsification/fixtures/c1s13_session13_scene_span_v1.records_meta.jsonl` | Longmont C1 S13 | `mechanical_ingest_fixture` | no | Breadcrumb/session-memory records metadata fixture. | Candidate graph node/edge scoring. | Fixture path, not gold directory; classify as input/mechanical unless a future PR promotes it. |

## Session event extraction gold

| Path | Session/campaign | Authority class | Candidate graph comparison? | Proves | Must not be used for | Notes |
|---|---|---|---:|---|---|---|
| `evals/session_events_extraction_vertical_slice/gold/session_events_session1_c1.json` | Longmont C1 S1 | `session_event_gold` | limited | Structured scene-event extraction target with expected event records. | Direct graph node/edge scoring without conversion. | Schema is `session_events_extraction_v1`. |
| `evals/session_events_extraction_vertical_slice/gold/session_events_session2_c1.json` | Longmont C1 S2 | `session_event_gold` | limited | Structured scene-event extraction target with expected event records. | Direct graph node/edge scoring without conversion. | Schema is `session_events_extraction_v1`. |
| `evals/session_events_extraction_vertical_slice/gold/session_events_session3_c1.json` | Longmont C1 S3 | `session_event_gold` | limited | Structured scene-event extraction target with expected event records. | Direct graph node/edge scoring without conversion. | Schema is `session_events_extraction_v1`. |
| `evals/session_events_extraction_vertical_slice/gold/session_events_session13_c1.json` | Longmont C1 S13 | `unknown_needs_inspection` | no | Not present on branch. | Any scoring or architecture claim. | Search found C1 S1/S2/S3 event gold only; no Session 13 event-gold file was present. |

## Classifier / live-prep gold

| Path | Session/campaign | Authority class | Candidate graph comparison? | Proves | Must not be used for | Notes |
|---|---|---|---:|---|---|---|
| `evals/c2_live_prep/benchmarks/c2s23_route_evidence_gold.json` | Longmont C2 S23 prep / S22 evidence | `retrieval_gold` | no | Evidence-reference and authority invariants for packet checks. | Candidate graph extraction scoring. | Notes identify evidence-reference gold focused on authority and capability invariants. |
| `evals/c2_live_prep/benchmarks/c2s23_manifest_query_gold.json` | Longmont C2 S23 prep | `retrieval_gold` | no | Manifest query/admission gold for evaluator-only packet behavior. | Candidate graph extraction scoring. | Notes say runner must not read this file. |
| `evals/c2_live_prep/benchmarks/c2s23_hub_world_query_gold.json` | Longmont C2 S23 prep | `retrieval_gold` | no | Hub/world query admission gold for dogfood-full manifest checks. | Candidate graph extraction scoring. | Evaluator-only query/admission fixture. |
| `evals/c2_live_prep/gold/session_22_live_turn_classifier.json` | Longmont C2 S22 | `classifier_gold` | no | Expected live-turn classifier routes for reconstructed GM utterances. | Candidate graph, projection, or retrieval gold. | Found in adjacent `gold/`, not under `benchmarks/`. |
| `evals/c2_live_prep/benchmarks/` | Longmont C2 live prep | `retrieval_gold` | no | Query/admission benchmark surfaces for C2 live prep. | Candidate graph extraction scoring. | Directory exists; individual files may include manifests, seeds, templates, and reports with lower authority than gold JSONs. |

## Vocabulary contract fixtures

| Path | Session/campaign | Authority class | Candidate graph comparison? | Proves | Must not be used for | Notes |
|---|---|---|---:|---|---|---|
| `evals/graph_memory_layer/examples/vocabulary_contract_fixtures/` | fixture-only | `vocabulary_contract_fixture` | no | Vocabulary DTO JSON shape, validation, and round-trip contract examples. | Candidate graph extraction scoring, canon promotion, projection gold, or Stable Global Node truth. | Hand-authored deterministic fixtures; not generated output and not corpus-derived. |

## Static review fixtures

| Path | Session/campaign | Authority class | Candidate graph comparison? | Proves | Must not be used for | Notes |
|---|---|---|---:|---|---|---|
| `evals/graph_memory_layer/examples/static_preview_graph_ui_prototype/` | Longmont C2 S23 | `static_review_fixture` | no | Static preview UI model and HTML can communicate/review UX shape. | Extraction scoring, retrieval scoring, or canon graph authority. | Review-only static prototype. |
| `evals/graph_memory_layer/examples/static_extractor_output_comparison_report/` | Longmont C2 S23 | `static_review_fixture` | no | Static report fixture can validate/illustrate candidate-vs-gold report formatting. | Gold authority or extraction quality claims beyond the fixture's report-contract scope. | Human-readable and JSON report fixture, not benchmark gold. |

## Generated run artifacts

| Path | Session/campaign | Authority class | Candidate graph comparison? | Proves | Must not be used for | Notes |
|---|---|---|---:|---|---|---|
| `evals/graph_memory_layer/artifacts/graph_ingest_runs/session_24_manual_projection_dogfood/` | Longmont C2 S24 | `generated_run_artifact` | no | Not present on branch. | Any scoring or architecture claim. | Required inspection path was absent; do not infer contents from docs. |

## Unknown or needs-inspection fixtures

| Path | Session/campaign | Authority class | Candidate graph comparison? | Proves | Must not be used for | Notes |
|---|---|---|---:|---|---|---|
| `evals/stage_c_npc_candidates_vertical_slice/gold/stage_c_session1_c1.json` | Longmont C1 S1 | `unknown_needs_inspection` | no | Not established by this graph-memory ledger pass. | Candidate graph extraction scoring. | Found during broad C1 search but outside requested adjacent surfaces; inspect in a dedicated PR before use. |
| `evals/stage_c_npc_candidates_vertical_slice/gold/stage_c_session2_c1.json` | Longmont C1 S2 | `unknown_needs_inspection` | no | Not established by this graph-memory ledger pass. | Candidate graph extraction scoring. | Found during broad C1 search but outside requested adjacent surfaces; inspect in a dedicated PR before use. |
| `evals/stage_c_npc_candidates_vertical_slice/gold/stage_c_session3_c1.json` | Longmont C1 S3 | `unknown_needs_inspection` | no | Not established by this graph-memory ledger pass. | Candidate graph extraction scoring. | Found during broad C1 search but outside requested adjacent surfaces; inspect in a dedicated PR before use. |
| `evals/stage_d_entity_resolution_vertical_slice/gold/stage_d_session1_c1.json` | Longmont C1 S1 | `unknown_needs_inspection` | no | Entity-resolution gold may be related, but shape and conversion rules are not established here. | Candidate graph extraction scoring. | Needs a future entity-resolution authority pass before graph-memory use. |
| `evals/stage_d_entity_resolution_vertical_slice/gold/stage_d_session2_c1.json` | Longmont C1 S2 | `unknown_needs_inspection` | no | Entity-resolution gold may be related, but shape and conversion rules are not established here. | Candidate graph extraction scoring. | Needs a future entity-resolution authority pass before graph-memory use. |
| `evals/stage_d_entity_resolution_vertical_slice/gold/stage_d_session3_c1.json` | Longmont C1 S3 | `unknown_needs_inspection` | no | Entity-resolution gold may be related, but shape and conversion rules are not established here. | Candidate graph extraction scoring. | Needs a future entity-resolution authority pass before graph-memory use. |
| `evals/session_recap_timeline_pass_vertical_slice/gold/timeline_pass_session1_c1.json` | Longmont C1 S1 | `unknown_needs_inspection` | no | Timeline-pass authority is not established for graph-memory extraction. | Candidate graph extraction scoring. | Found during broad C1 search; inspect in a dedicated PR before use. |
| `evals/session_recap_timeline_pass_vertical_slice/gold/timeline_pass_session2_c1.json` | Longmont C1 S2 | `unknown_needs_inspection` | no | Timeline-pass authority is not established for graph-memory extraction. | Candidate graph extraction scoring. | Found during broad C1 search; inspect in a dedicated PR before use. |
| `evals/session_recap_timeline_pass_vertical_slice/gold/timeline_pass_session3_c1.json` | Longmont C1 S3 | `unknown_needs_inspection` | no | Timeline-pass authority is not established for graph-memory extraction. | Candidate graph extraction scoring. | Found during broad C1 search; inspect in a dedicated PR before use. |

## Rules for future agents

1. Do not use a fixture for candidate graph extraction comparison unless its authority class is `candidate_graph_gold`.
2. Do not treat projection dogfood as extraction gold.
3. Do not treat routing, retrieval, classifier, or session-event fixtures as graph node/edge gold without an explicit conversion PR.
4. Do not treat generated graph runs as gold unless a separate reviewed artifact says so.
5. When adding a fixture, add a ledger row in the same PR.
6. When using a fixture in a benchmark, cite its ledger authority class in the benchmark README or report.
7. If the fixture's purpose is unclear, classify it as `unknown_needs_inspection`.
