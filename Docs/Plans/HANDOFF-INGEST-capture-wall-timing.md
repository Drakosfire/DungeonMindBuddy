# INGEST: measured ordinary capture duration

Status: ACTIVE, root adopts the user-authorized study measurement requirement.

Outcome: existing Runner records a monotonic duration for each ordinary backend
capture, separately from immutable result bytes. Existing reports expose measured,
incomplete and missing timings. No provider, product, database or retry-policy change.

Topology: stacked on PR #2155 exact 6313fa532a55d9ac26a696214c63edd97742f221.
Merge/rebase #2146 → #2154 → #2155 → this slice. Branch
codex/ingest-capture-wall-timing, current isolated checkout.

Exclusive expected writes: src/ingestion_evaluation/runner.py,
tests/test_ingestion_evaluation_runner.py, Docs/Guides/ingestion-evaluation.md,
this handoff. Runner write ownership transfers from completed evaluator lanes to
this child. No services/ports/DB writes; tests use synthetic backends only.

Critique: model-call sums are not whole-capture latency; failed/interrupted calls
cannot masquerade as successful measurements; timing retention must not hide the
original exception or permit redispatch; prior captures stay unknown. Receipts
must bind actual manifest, request and result. Timing excludes qualification,
later conservation audit and semantic review, and includes the ordinary backend
HTTP call and its component retention. It is not UI end-to-end user time.

Validation: fake-clock successful/nonreviewable/exception measurements, original
exception preservation on timing-write failure, binding drift refusal, historical
missing timings and one-shot replay refusal. Existing runner/assessment/baseline
tests; independent exact-head review; commit/push/open bounded PR. No merge authority.

Observed validation: 75 runner/assessment/baseline tests pass. Independent review
approved the working-tree slice and independently ran all13 new timing tests.
Initial two new replay assertions mistakenly requalified the same output and hit
the existing qualification guard; the tests now reuse the original qualification
to exercise the intended dispatch guard. No production replay rule was relaxed.
