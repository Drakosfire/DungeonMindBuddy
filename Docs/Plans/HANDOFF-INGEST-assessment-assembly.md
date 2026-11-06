# INGEST: assemble sealed reviews into common assessments

Status: ACTIVE. Root adopts this bounded tooling slice under the ingestion-study goal.

Base/parent: PR #2156 at `4722209f8b60abaac0fdeea5bf0d2dbbccd5dec2`.
Branch: `codex/ingest-assessment-assembly`, existing isolated checkout.
Topology: stacked; merge/rebase #2154 → #2155 → #2156 → this slice.
Independent of product prompt PR #2157; no overlapping product/runtime paths.
Merge requires separate authority.

Outcome: one offline command projects a sealed review into the existing canonical
assessment and validates it with the existing reporter. Eliminate repeated manual
assembly, including accidental copying of reviewer annotations into strict rows.
No legacy-review remapping, semantic grading, providers, database operations,
publication, new capture runner, or ingestion configuration changes.

Expected write lease:

- `src/ingestion_evaluation/assembly.py`
- `scripts/evaluate_ingestion.py`
- `tests/test_ingestion_evaluation_assembly.py`
- `Docs/Guides/ingestion-study-assessments.md`
- this handoff

The H1 execution host is separately frozen byte-for-byte at
`/tmp/ingest-study-evaluator-4722209f`; its identity and equivalent retained-report
output were verified before switching branches. The private execution bootstrap
statically targets that host. Do not change registered H1 tooling or manifests.
The new assembly command reads retained artifacts offline and does not execute
old manifests through a new runner version.

Verification: owning CLI tests for strict row projection, complete criterion/run/
candidate binding, audit/timing association, explicit unknowns, no backend startup,
and safe repeat/conflict behavior. Run existing assessment/runner tests, inspect
cumulative diff, obtain independent subagent review, commit/push/open this PR.
Historical sealed reviews and outputs stay unchanged. The command only supports
the current `judgments` review shape; earlier normalized historical assessments
remain evidence rather than executable compatibility paths.
