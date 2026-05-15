# Gates

## Gate 0 — KB boundary
- Passes if C1S1-C1S3 records load into one manifest
- Fails if any C1S4 source/session/path appears

## Gate 1 — Retrieval/context bundle smoke
- Passes if preplanning queries produce oracle-safe context bundles
- Fails if bundle contains C1S4 references

## Gate 2 — Oracle target authoring / beat-question target surface
- Partial.
- Passes when `gold/c1s4_beat_question_targets.json` exists and validates.
- Passes when Q1–Q38 are represented with authority labels, oracle-risk labels, known gaps, and must-not-include terms.
- Fails if the target artifact is planner-visible retrieval material.
- Does not yet grade planner output.

## Gate 3 — Live planner trace
- Future
- Not in this PR

## Gate 4 — Oracle grading
- Future
- Not in this PR

## Gate 1B — Prior plus support retrieval
- Passes when support records load into the same normalized retrieval surface as session memory.
- Passes when content-only and lexical-hint modes report separately.
- Fails if retrieval uses question IDs or eval-only fields.
- Fails if C1S4 oracle material enters planner-visible context.
