# Graph Memory Session 1 Vocabulary Ablation Projection Dogfood Run

## Result

1. C1S1 candidate graph materialized: yes.
2. Preview union store: `evals/graph_memory_layer/artifacts/graph_ingest_runs/session_1_vocabulary_ablation_projection_dogfood/preview_union_store.json`.
3. Graph-ingest manifest: `evals/graph_memory_layer/artifacts/graph_ingest_runs/session_1_vocabulary_ablation_projection_dogfood/graph_ingest_run_manifest.json`.
4. Registry discovery: {'ok': True, 'latest_manifest_path': 'evals/graph_memory_layer/artifacts/graph_ingest_runs/session_1_vocabulary_ablation_projection_dogfood/graph_ingest_run_manifest.json', 'preview_union_store_path': 'evals/graph_memory_layer/artifacts/graph_ingest_runs/session_1_vocabulary_ablation_projection_dogfood/preview_union_store.json'}.
5. Projection load: {'ok': True, 'node_view_count': 112, 'mention_count': 36, 'graph_id': 'longmont-c1:preview-union-supergraph'}.
6. Projected recap mention chips: 36.
7. Mirathorn worldbuilding merged: True.
8. Canon/write safety: preview-only; no corpus mutation or approved writes.

## /plan usage

Open Plan → **Recap** with `?session=session-1`. Campaign context should be `longmont-c1`.
The union supergraph includes session-1 recap nodes plus Mirathorn worldbuilding nodes when merged.
Worldbuilding nodes appear in node explorer/adjacency even when not linked as recap chips.

## Caveats

- This run uses the vocabulary-ablation `edge_and_node_packet` candidate graph, not hand-authored gold.
- Preview-only dogfood; not campaign canon.
