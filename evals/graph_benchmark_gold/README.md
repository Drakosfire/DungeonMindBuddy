# Graph benchmark gold

This directory is the canonical home for graph-quality benchmark gold.

It separates two evaluation surfaces:

- `candidate_graph/` — exact snapshot copies of existing hand-authored candidate-graph gold.
- `qa/` — question/answer gold for retrieval, multi-hop reasoning, temporal continuity, authority handling, continuity warnings, and campaign-state synthesis against a graph.

## Migration policy

Loaders and local Graph Gold Review use the snapshots under `candidate_graph/`. The catalog records the original paths, migration revision, and blob identities for historical provenance. The source manifests retain the original paths as provenance, and the fixture loaders resolve the canonical files.

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
