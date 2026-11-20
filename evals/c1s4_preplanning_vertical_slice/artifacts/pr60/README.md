# PR60 admission preservation infrastructure artifacts

PR60 adds bounded admission preservation and diagnostics. It does not complete the Q1 Grishna target row.

The main result is infrastructure validation:

- NPC/location candidates can be preserved before greedy lane-budget fill.
- `presentation_lane` is preserved separately from `admission_budget_lane`.
- Q5 support does not regress.
- Q3 location context does not regress.
- Q1 Grishna remains blocked by candidate-pool merge depth.

See `pr60_step2c_surface_matrix.csv` for target-surface status and `pr60_admission_preservation_matrix.csv` for preserved items.

## Historical direct-probe output

The generated direct-probe CSV is retained in Git history rather than this
checkout. It contains 33 historical diagnostic rows; neighboring matrices and
summaries remain available to the lab. This is a preserved result, not a claim
that current inputs reproduce the historical run.

- [Exact CSV at the retirement base](https://github.com/Drakosfire/DungeonMindBuddy/blob/b69e7d712b50251f0a07d1ecf6aa827451df5cba/evals/c1s4_preplanning_vertical_slice/artifacts/pr60/pr60_direct_probe_results.csv)
- Bytes: `10530`; SHA256: `1473c0d0c02cc2dde0300f073b017730dae1b2c73a687659985d2450aae742ee`.

The existing audit generator can write new probe output to an owned external
output directory. Keep new results separate from this pinned historical record.
