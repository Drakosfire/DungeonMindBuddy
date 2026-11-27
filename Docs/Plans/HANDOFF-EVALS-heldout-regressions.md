# EVALS: retain observed saved-source regressions

ACTIVE under the user's over-retrieval goal. Serial successor to merged #4898;
branch `codex/negative-independent-regressions`, checkout
`negative-heldout-regressions`, based on fetched `origin/main`. The open #4878
Plan browser evaluator and #4884 serving integration were checked; neither owns
these negative-retrieval fixture or documentation files.

Promote the two already-exposed synthetic H2 failures into development fixtures:
an exact current page skipped after a current-page-only decision, and a required
related saved page read but followed by an unavailable-source failure. Retain
separate negative and source-required budgets, exact evidence and answer quality
expectations, and the fact that the baseline failed. These cases have now been
exposed to implementation and are no longer held-out qualification. Do not
weaken assessments or claim complete acquisition capture. Validate fixture/rubric
shape, pairing, labels and the affected cases with focused checks; independent
exact-head review and applicable checks are required.

Write lease: this handoff, `evals/negative_retrieval/fixtures/development.json`,
`evals/negative_retrieval/fixtures/development-private.json`, and
`evals/negative_retrieval/README.md`. No runtime changes, models, database or
production deployment in this slice.
