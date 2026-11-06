# INGEST: compare pinned paired assessments

Status ACTIVE for bounded offline tooling implementation. This consolidates the
repeated H1/H2 count, uncertainty-bound and cost/time comparison arithmetic;
it does not alter frozen captures, reviews, Gold or acceptance contracts.

Branch `codex/ingest-paired-assessment-comparison`, base #2165 exact
`18e0c3fc786f717ec4f93857d5a6708c1db17f9a`. Stacked evaluator merge order:
#2154 → #2155 → #2156 → #2160 → #2165 → this child. Product #2164/#2166
are separate. No merge authority. Current H2 captures keep frozen evaluator18e
and immutable runtimes; this tooling is only an offline consumer.

Write lease: `src/ingestion_evaluation/comparison.py`,
`scripts/evaluate_ingestion.py`, `tests/test_ingestion_evaluation_comparison.py`,
`Docs/Guides/ingestion-study-assessments.md`, and this handoff. Other active lanes
are disjoint; no runtime, port, database, provider, source/Gold or heldout writes.

One command accepts pinned assessments with declared cases and exact pair count.
Reuse existing report() for bindings, refs, criterion completeness and metrics;
verify same Gold/criterion contract per case and no reused run across pairs.
Report every pair, per-case medians and conservative unknown-outcome bounds.
Missing/zero-denominator metrics remain unknown; no available-case medians.
Do not pool cases, infer precision from recall, auto-grade severe propositions,
certify semantic truth or decide adoption. Underlying reviews/limitations remain
pinned. No model-specific settings or experiment acceptance thresholds in code.

Verify known and unknown outcome boundaries, absent/mismatched cases or pairs,
changed Gold/criteria, duplicate runs, missing/nonfinite/zero metrics, exact
pin tampering, CLI misuse and offline operation. Retained case2 calibration must
match the prior diagnostic without rescoring. Independent cumulative/exact-head
review then commit/push/open bounded PR; no modification of the active schedule.

Verification: 83 focused comparison/assessment/assembly/blinding tests pass,
independently reproduced in working-diff review. Retained case2 mechanical
calibration matches every prior diagnostic median, unknown bound and efficiency
ratio exactly, without rescoring. Calibration receipt
`case2-comparison-tool-calibration-v1.json` SHA
`ed8784eb18d251a99a2a0051387e4e8a77f09fd24ff530451d9ae309bf602e3f`
is retained under the H2 evidence directory. Semantic comparability and precision
remain independent experiment responsibilities, not numeric-tool assertions.
