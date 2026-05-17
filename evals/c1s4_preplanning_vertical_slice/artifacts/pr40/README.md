# PR40 Benchmark Artifacts

These artifacts were generated as part of **PR40 follow-up work** and are scoped to this PR's diagnostics.

## Files

- `pr40_step2c_expected_context_multimode_report.json`
  - Command:
    - `uv run python evals/c1s4_preplanning_vertical_slice/step2c_expected_context_benchmark.py --all-modes --output-json evals/c1s4_preplanning_vertical_slice/artifacts/pr40/pr40_step2c_expected_context_multimode_report.json`
  - Purpose:
    - Captures Step 2C multimode expected-context benchmark output tied to PR40 changes.

Notes:
- This folder is PR-scoped evidence and not canonical benchmark truth.
- Canonical generated artifacts may continue to live under the root `artifacts/` paths.
