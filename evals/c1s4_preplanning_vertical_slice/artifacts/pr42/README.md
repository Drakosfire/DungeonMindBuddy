# PR42 Benchmark Artifacts

These artifacts were generated as part of PR42 deterministic budgeted admission.

## Files

- `pr42_step2c_expected_context_multimode_report.json`
  - Generated with:
    `uv run python evals/c1s4_preplanning_vertical_slice/step2c_expected_context_benchmark.py --all-modes --output-json evals/c1s4_preplanning_vertical_slice/artifacts/pr42/pr42_step2c_expected_context_multimode_report.json`
  - Purpose:
    Captures Step 2C multimode expected-context benchmark output using active `budgeted_v1` admission.

Notes:
- This folder is PR-scoped evidence and not canonical benchmark truth.
- PR42 changes active admission behavior.
- Legacy top-k diagnostics should remain available for comparison.
