# Graph benchmark gold

This directory is the canonical home for graph-quality benchmark gold.

It separates two evaluation surfaces:

- `candidate_graph/` — exact snapshot copies of existing hand-authored candidate-graph gold.
- `qa/` — question/answer gold for retrieval, multi-hop reasoning, temporal continuity, authority handling, continuity warnings, and campaign-state synthesis against a graph.

## Migration policy

The pre-existing graph-gold fixtures under `evals/graph_memory_layer/examples/` remain in place for compatibility with current loaders and tests. The files under `candidate_graph/` are byte-identical snapshot copies of those gold graphs and source manifests at the migration revision recorded in `catalog.json`.

New benchmark consumers should prefer this namespace. Legacy loaders may continue to use the old paths until they are deliberately migrated in a separate implementation slice.

Do not silently edit a migrated graph snapshot to make a model score better. A changed gold judgment requires an explicit version bump or a new benchmark fixture.

## QA authority policy

For campaign recap QA gold:

- observed `Recap` prose is played campaign truth by default;
- frontmatter supplies campaign/session identity;
- planning sections such as `Major Beats`, `Next Beats`, and `Looking Ahead` are not played truth unless a question explicitly tests planning/authority;
- synthesis may connect multiple supported facts, but must not turn an inference into a fact.

The Campaign 1 Sessions 1–10 QA suite intentionally emphasizes the later sessions. Difficulty rises from direct late-session lookup through cross-session joins, path queries, continuity warnings, temporal identity, authority-aware reasoning, and end-of-window campaign-state synthesis.

## Current migrated graph gold

See `catalog.json` for the exact fixture IDs, legacy origins, canonical snapshot paths, and Git blob identities.
