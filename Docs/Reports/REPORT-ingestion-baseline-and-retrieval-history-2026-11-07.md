# Accepted ingestion working baseline and retrieval history

Decision recorded 2026-11-07. Repository evidence anchor: main 2008cdcf57eb8c02d08456fe373a73ca11466094.

## Working baseline

The project owner accepts Campaign 1 Sessions 1–10 ingestion coverage as a solid working baseline for moving forward. This decision does not assert perfect precision, authorize automatic publication, or accept a model as universally optimal. Known raw defects remain: identity/location strengthening, proposed actions made completed, chronology, and planning/retrospective authority leakage.

The study's case-level raw Gold counts total 1,177 pass, 31 fail, six partial and 28 unknown, out of 1,242 checks. The arithmetic fraction 94.8% is a descriptive tally of overlapping checks, not independent generated facts, precision, or a pooled quality score. The evidence index expressly cautions against aggregate pooled coverage; use per-case and per-dimension results for comparisons. Precision holds and unknowns remain explicit; severe/intervention counts are lower bounds. Human review effort remains unknown.

All ten assessment replays and the 356-test combined tooling/configuration/citation composition suite were reported passing, not re-executed for this documentation update. Retain the original standard-v2 DeepSeek reference with low requested reasoning; do not promote H1/H2/H3/H4 experimental treatments. Requesting a different reasoning allocation did not establish the model's internal reasoning behavior.

[Sanitized case-level evidence receipt](evidence/ingestion-c1s1-s10-baseline-2026-11-07.json) preserves source artifact hashes, case counts, candidate hashes and study limitations without private campaign content. Original private assessments and provider traces are not reproduced; hashes alone cannot reconstruct or independently prove them. Preserve those originals in an authorized private evidence store before claiming full independent reproducibility.

At the 2008cdcf anchor, [#2180](https://github.com/Drakosfire/DungeonMindBuddy/pull/2180), [#2189](https://github.com/Drakosfire/DungeonMindBuddy/pull/2189), [#2190](https://github.com/Drakosfire/DungeonMindBuddy/pull/2190), and [#2193](https://github.com/Drakosfire/DungeonMindBuddy/pull/2193) were open, not merged. Their review and reported verification do not establish merged-main behavior; consult their current state independently.

## Retrieval history and preserved assets

- [Buddy breadcrumb and sentence-routing experiments](../../evals/sentence_routing_retrieval_falsification/README.md) retain source-aligned recap labels, gold questions, cohorts, runners and results. The 2026-05-08 retrieval-only refresh recorded C1S1 14/16, C1S2 15/15, C1S3 12/13 and a failing C1S13 holdout, with distinct roster/identity, location hierarchy and alias-bridge failures. This is routing/retrieval evidence, not end-to-end answer-quality evidence.
- [Lysandra retrieval design](../Design/DESIGN-lysandra-statblock-vertical-slice-benchmark.md) and `evals/lysandra_vertical_slice/` preserve keyword scoring and gold for an entity-specific case; lexical signal does not prove an agent opened a file.
- [Campaign 1 historical QA](../../evals/graph_benchmark_gold/qa/longmont-c1/sessions-01-10-v1.md), graph candidate gold, canon-layering fixtures and source manifests retain different evaluation authorities; do not treat generated outputs as source Gold.
- [RulesIngestion retrieval results timeline](https://github.com/Drakosfire/RulesIngestion/blob/17854ad6eaf9aa8bdfc483f8c3eb0a6099f0bbd8/Docs/Reports/REFERENCE-Retrieval-Benchmark-Results-Timeline.md) indexes historical questions, corpus configurations, lexical BM25, dense embeddings, hybrid fusion, reranking, decomposition and cross-reference experiments.
- Its March 2026 hybrid sweep reported average MRR change from dense of -0.018 and -0.095 for RRF on Starfinder and Swords & Wizardry, versus +0.016 and -0.006 for convex-combination fusion. An earlier comparison suffered a BM25 candidate-budget wiring defect. These are configuration-specific historical observations, not present-day rankings.
- Its decomposition audit reported PHB 11 worsened, seven improved and 49 unchanged; PF2E four worsened, three improved and 63 unchanged. Internal baseline parity and low-yield expansion required further investigation. Its Swords & Wizardry analysis reported 21/21 grounded queries, MRR 0.2868, and three missing-gold candidate cases, with later benchmark/substrate contract drift blocking a straightforward comparable rerun.

## Proposed evaluation continuation

Preserve original questions, expected evidence, source/corpus revisions, runners, configurations and per-question results. Measure ingestion (source-grounded identity, relationships, chronology and authority), retrieval (source/anchor recall, ranking and multi-hop coverage), and answer composition (support, citations, qualification and abstention) separately. Compare lexical, dense, hybrid, breadcrumb/routing, graph-source and reranking approaches where their original contracts can be reconstructed. Keep clean and full working sets distinct.

A proposed initial ordinary Buddy cohort contains Q01, Q02, Q04, Q09, Q14 and Q16 from the linked C1 QA. It is design-only pending independent review and exact source/publication qualification. Q14 additionally needs planning-source availability/access checked; Q16 has a possible historical completed-action overstatement. Q11 is excluded by owner decision. RulesIngestion and C2 Lysandra remain separate future tracks; offline breadcrumb retrieval is not an ordinary graph-pipeline run.

No paid calls, new ingestion, publication, or model-comparison execution follow from this record.
