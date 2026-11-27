# Negative retrieval: observe saved primary-page stability

Status: ACTIVE. The user authorized this serial benchmark slice as part of the
negative-retrieval goal. Base: `8cff02a65f8dda0036e47dc37efe295096dd07d2`;
branch `codex/negative-primary-page-stability`. PR #4929 is the merged
predecessor. Relevant open retrieval/benchmark PRs were checked. No new
runtime, provider, port or database is allocated; this slice is provider-free.

Write lease: this handoff; `evals/negative_retrieval/primary_page_stability.py`,
`capture.py`, `report.py`, `README.md` in that directory; and focused tests in
`tests/evals/test_negative_retrieval_assessment.py`.

The benchmark must inspect the actual saved primary page outside the turn
probe, before and after a fixture-bound turn. Bind World, document, revision
and a digest computed from returned body to the fixture and request. A changed
saved primary page can demonstrate premature mutation; an unchanged page
cannot prove that no other state changed or that a transient change did not
occur. Missing, failed, mismatched, unstarted, legacy and untrusted observations
remain unknown; never emit page content into the evidence. No source read or
acquisition-journal completeness follows from fixture inspection.

Verify owner-bound pre/post snapshots and report behavior for stable, changed,
missing, wrong identity, changed digest, unstarted and failure paths, plus
legacy artifacts and no global no-mutation pass. Inspect the cumulative diff,
obtain independent exact-head review and pass required checks before merging.
No production release is needed for this evaluator-only slice.

Focused local verification: seven provider-free tests cover the real owner
interface, preflight mismatch, changed and failed postflight, bound report
scoring, wrong identities and forged statuses. Real-owner check case 354 used
the existing clone and read-only connections to compare the exact synthetic
saved page twice against its frozen fixture; no ordinary turn was dispatched.
Earlier cases 352 and 353 failed before the page query due to harness DSN
formatting, then the corrected case passed. The subsequent helper edit only
changed offline record validation, not the owner-read functions (verified by
reconstructing the original helper SHA). None of this proves mutation coverage
outside the primary page, a complete journal, or a qualified capture environment.
