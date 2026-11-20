# PR63 source-derived context gap artifacts

PR63 emits `source_derived_context_gaps` from deterministic absence analysis over allowed retrieved/admitted context. Gold `known_context_gaps` remain evaluator-only.

See `pr63_source_derived_gap_matrix.csv` for per-target gap emission and rendering.

## Historical direct-probe output

The generated direct-probe CSV is retained in Git history rather than this
checkout. It contains 33 historical diagnostic rows; neighboring matrices and
summaries remain available to the lab. This is a preserved result, not a claim
that current inputs reproduce the historical run.

- [Exact CSV at the retirement base](https://github.com/Drakosfire/DungeonMindBuddy/blob/b69e7d712b50251f0a07d1ecf6aa827451df5cba/evals/c1s4_preplanning_vertical_slice/artifacts/pr63/pr63_direct_probe_results.csv)
- Bytes: `10530`; SHA256: `1473c0d0c02cc2dde0300f073b017730dae1b2c73a687659985d2450aae742ee`.

The existing audit generator can write new probe output to an owned external
output directory. Keep new results separate from this pinned historical record.
