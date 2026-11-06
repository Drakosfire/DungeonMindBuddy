# INGEST: standard reviewed correction evaluation

Status: ACTIVE; root owns design/implementation; independent subagent review.

## Outcome

The shared evaluator qualifies, executes once and inspects an exact existing
Buddy candidate type correction or separately reviewed child semantic decision.
No new producer, correction schema, semantic judgment or publication authority.
Reuse the source one-shot lifecycle rather than copy another execution harness.

## Lane / dependencies / topology

`codex/ingest-correction-evaluator`, stacked on PR #2137 exact host head
`fef4afe95e7502094fe720f902b3805eb110c191`. Merge/rebase #2137 first.
Behavioral runtime dependency: reviewed PR #2145 head
`ceecc1854eea05558b5109e97442d02a3ec378e5`, donor-preserving frozen manifest
`ccc308ebc127022d56935f595da55623e3a21a0257e30f17c959f5855fc74104`.
PR #2145 stacks #2144; neither is merged/deployed. No overlapping product edits.

## Expected exclusive writes

- src/ingestion_evaluation/governed_operation.py (shared existing lifecycle)
- src/ingestion_evaluation/source_authority.py (thin lifecycle wrapper)
- src/ingestion_evaluation/correction.py
- src/ingestion_evaluation/authority.py (two fixed existing API routes)
- src/ingestion_evaluation/runner.py (explicit manifest validation)
- scripts/evaluate_ingestion.py
- tests/test_ingestion_evaluation_correction.py
- tests/test_ingestion_evaluation_source_authority.py
- tests/test_ingestion_evaluation_runner.py
- Docs/Guides/ingestion-evaluation.md
- this handoff

## Invariants / failure cases

One exact run/source/index/profile/runtime/operator/request/review pin set.
Correction is existing V8 type-only, creates immutable held child with V11 source
binding and exact V8 replay. Semantic disposition is a separate manifest after
reviewing that actual child. No parent review can autoaccept it. Preserve raw
quality/Gold failures independently of review correction.

APP write enabled only at the exact local route, native always read-only,
external HTTP forbidden. Prior rows conserved except the exact expected child
CAS for disposition. Correction can append only exact child run/components;
source rows and all native rows unchanged. Persist intent before dispatch;
unknown execution is inspected, never automatically retried. Source workflow
public filenames and behavior stay unchanged; publication lifecycle unchanged.

## Validation / delivery

Owning manifest, route isolation, exact-row conservation and one-shot failure
regressions; existing source/publication/capture suites; cumulative diff and
independent exact-head review. Implement/test/commit/push/open one PR. No merge
or deployment authority. Actual isolated retained correction requires a fresh
qualified manifest and reviewed request; primary unchanged. No providers.
