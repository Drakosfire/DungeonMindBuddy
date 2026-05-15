# Gates

## Gate 0 — KB boundary
- Passes if C1S1-C1S3 records load into one manifest
- Fails if any C1S4 source/session/path appears

## Gate 1 — Retrieval/context bundle smoke
- Passes if preplanning queries produce oracle-safe context bundles
- Fails if bundle contains C1S4 references

## Gate 2 — Oracle target authoring
- Future
- Not in this PR

## Gate 3 — Live planner trace
- Future
- Not in this PR

## Gate 4 — Oracle grading
- Future
- Not in this PR
