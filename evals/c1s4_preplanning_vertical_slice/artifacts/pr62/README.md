# PR62 renderer / provenance section repair artifacts

PR62 expands provenance metadata and routes admitted items by semantic `presentation_lane` before prior-memory fallback.

See `pr62_render_section_matrix.csv` for per-target section routing and provenance coverage.

## Historical direct-probe output

The generated direct-probe CSV is retained in Git history rather than this
checkout. It contains 33 historical diagnostic rows; neighboring matrices and
summaries remain available to the lab. This is a preserved result, not a claim
that current inputs reproduce the historical run.

- [Exact CSV at the retirement base](https://github.com/Drakosfire/DungeonMindBuddy/blob/b69e7d712b50251f0a07d1ecf6aa827451df5cba/evals/c1s4_preplanning_vertical_slice/artifacts/pr62/pr62_direct_probe_results.csv)
- Bytes: `10530`; SHA256: `1473c0d0c02cc2dde0300f073b017730dae1b2c73a687659985d2450aae742ee`.

The existing audit generator can write new probe output to an owned external
output directory. Keep new results separate from this pinned historical record.
