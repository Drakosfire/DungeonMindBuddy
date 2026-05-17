# PR41 Benchmark Artifacts

These artifacts were generated as part of PR41 budget-aware admission diagnostics.

## Files

- `pr41_step2c_expected_context_multimode_report.json`
  - Generated with:
    `uv run python evals/c1s4_preplanning_vertical_slice/step2c_expected_context_benchmark.py --all-modes --output-json evals/c1s4_preplanning_vertical_slice/artifacts/pr41/pr41_step2c_expected_context_multimode_report.json`
  - Purpose:
    Captures Step 2C multimode expected-context benchmark output with budget admission diagnostics.

Notes:
- This folder is PR-scoped evidence and not canonical benchmark truth.
- Canonical generated artifacts may continue to live under the root `artifacts/` paths.
