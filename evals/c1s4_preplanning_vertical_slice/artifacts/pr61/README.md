# PR61 candidate merge allocation artifacts

PR61 adds coverage-aware alias allocation inside the existing alias slot budget.

Q1 Grishna's useful admittable NPC record should now enter `candidate_context` and be admitted by PR60 preservation.

See `pr61_step2c_surface_matrix.csv` for target-surface movement vs PR60.

## Historical direct-probe output

The generated direct-probe CSV is retained in Git history rather than this
checkout. It contains 33 historical diagnostic rows; neighboring matrices and
summaries remain available to the lab. This is a preserved result, not a claim
that current inputs reproduce the historical run.

- [Exact CSV at the retirement base](https://github.com/Drakosfire/DungeonMindBuddy/blob/b69e7d712b50251f0a07d1ecf6aa827451df5cba/evals/c1s4_preplanning_vertical_slice/artifacts/pr61/pr61_direct_probe_results.csv)
- Bytes: `10530`; SHA256: `1473c0d0c02cc2dde0300f073b017730dae1b2c73a687659985d2450aae742ee`.

The existing audit generator can write new probe output to an owned external
output directory. Keep new results separate from this pinned historical record.
