# PLAN: writer prompt fixture whitespace

ACTIVE under the user's release-verification instruction. Parallel-independent of #4819, #4821, #4823 and #4825: only `tests/test_native_plan_assertions.py` and this brief are owned here; no product files, shared runtime, or write-state overlap. Backend tests use their own disposable database.

The synthetic writer transport currently requires a literal sentence substring that is wrapped across a line boundary in the existing instruction. Compare the same complete required and forbidden phrases after normalizing whitespace; retain all existing proof of protected content and insertion semantics. Do not modify the actual prompt or weaken its substantive assertions. The shared fixture drives the five failing query-and-answer cases.

Verify all five affected cases with synthetic providers in an isolated exact-SHA locked environment, run the owning query-and-answer contract and frontend hosted verifier, and obtain independent exact-head review. Record inherited failures and skips honestly.
