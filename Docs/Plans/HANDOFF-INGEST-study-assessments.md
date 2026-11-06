# INGEST: common study assessments

Status: ACTIVE. Root adopts the user-authorized study machinery scope.

Outcome: one offline assessment format and report in the existing evaluator CLI.
Criteria reference exact Gold objects; judgments reference exact retained reviews.
Raw extraction, reviewed output and publication are independently reported.
Unknown judgments/measurements never become zero, a pass, or publication approval.

Topology: stacked on PR #2154 exact c0fbe533db9fff7315a6b426fe3f75354ef0095d.
Merge/rebase #2146, then #2154, then this slice. Root revises the earlier planned
serial successor to a stack after verifying the baseline archive and independent
review. No merge or deployment authority is implied.

Branch codex/ingest-study-assessments; same isolated checkout. Expected exclusive
writes: src/ingestion_evaluation/assessment.py, scripts/evaluate_ingestion.py
(offline assessment dispatch only), tests/test_ingestion_evaluation_assessment.py,
Docs/Guides/ingestion-study-assessments.md, this handoff. CLI ownership passes from
the completed parent to this child; parent stays unchanged. No runtime, ports,
provider or database writes. New reports go to explicitly selected evidence files.

Failure critique: phase conflation, silently shrinking criterion denominators,
changed artifact bytes, mixed run/candidate subjects, unchecked JSON selectors,
feasibility promoted to acceptance, and missing measurements reported as zero.
The tool verifies references and declared coverage, not semantic truth. Independent
review must validate criterion completeness and normalized judgment meanings.

Validation: actual CLI report, exact binding/hash/selector refusal, duplicate and
missing criterion handling, phase separation, measurement unknowns, existing CLI
regressions, independent cumulative exact-head review. Reuse completed reviews;
do not add runtime legacy-format adapters or repeat unchanged semantic reviews.

Configuration comparison and experiment execution remain separate successors.

Observed validation: 60 assessment/baseline/existing runner tests passed together.
Independent review caught reuse of an older candidate's review under the same run
ID; exact candidate plus revision/result binding now refuses it, including explicit
conflicts. Reviewer independently reran 39 assessment/baseline tests and approved
the revised cumulative slice. Scalar legacy Gold references stay unchanged.
