# C1S4 Preplanning Vertical Slice

## Purpose
Deterministic scaffold proving planner-visible context can be built from C1S1-C1S3 only.

## Scope
Build bounded KB manifest + retrieval smoke context bundles for Longmont Campaign 1.

## What this proves
- This slice proves that a planner-visible context bundle can be built from C1S1–C1S3 only.
- C1S4 oracle surfaces are blocked by policy and leakage checks.

## What this does not prove
- It does not run a live planner.
- It does not grade prep against C1S4 yet.
- It does not tune retrieval.

## How to run Step 0
`uv run python evals/c1s4_preplanning_vertical_slice/step0_kb_materialize.py`

## How to run Step 1
`uv run python evals/c1s4_preplanning_vertical_slice/step1_retrieval_context.py`

## Oracle boundary policy
Policy lives in `gold/kb_policy.json`, distinguishing forbidden planner-visible C1S4 surfaces from preferred/fallback grader oracle source paths.

## Expected next PRs
- Oracle target authoring for C1S4.
- Live planner trace generation.
- Oracle grading harness.
