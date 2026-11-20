# PR59 query alias expansion artifacts

Deterministic Step2C query variants bridge planner-language questions to materialized evidence records.
See `pr59_query_variant_manifest.csv` for per-variant hit counts and `pr59_step2c_alias_probe_matrix.csv` for PR58→PR59 surface movement.

## Historical direct-probe output

The generated direct-probe CSV is retained in Git history rather than this
checkout. It contains 33 historical diagnostic rows; neighboring matrices and
summaries remain available to the lab. This is a preserved result, not a claim
that current inputs reproduce the historical run.

- [Exact CSV at the retirement base](https://github.com/Drakosfire/DungeonMindBuddy/blob/b69e7d712b50251f0a07d1ecf6aa827451df5cba/evals/c1s4_preplanning_vertical_slice/artifacts/pr59/pr59_direct_probe_results.csv)
- Bytes: `10530`; SHA256: `1473c0d0c02cc2dde0300f073b017730dae1b2c73a687659985d2450aae742ee`.

The existing audit generator can write new probe output to an owned external
output directory. Keep new results separate from this pinned historical record.
