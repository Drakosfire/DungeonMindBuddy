# EVALS: bind observed related-page evidence

ACTIVE under the user's over-retrieval goal. Serial successor to merged #4899;
branch `codex/negative-related-evidence-binding`, checkout
`negative-heldout-regressions`, based on fetched `origin/main`. Open #4878 and
#4884 do not own the benchmark probe and report paths.

The current report can credit a related-page return using only a document ID,
without binding the attempted World/revision or returned body to the fixture.
Bind attempt attribution to the exact fixture pointer and count a completed
related-page read only when the observed returned World, document, revision and
body digest match the verified fixture and returned Markdown. Capture only
host-side identity and digest, never returned text; preserve actual owner
behavior. Legacy, malformed, foreign, failed and unmatched records remain
unknown. Display-only trace labels do not prove a completed exact fixture read.
No partial capture becomes a complete journal and a read alone does not prove a
citation or answer quality. Verify the actual owner wrapper, old artifacts,
wrong World/revision/body, failed calls, fixture mismatch and report assessment
with focused cases. Require independent exact-head review and applicable checks.

Write lease: this handoff, `evals/negative_retrieval/related_page_probe.py`,
`evals/negative_retrieval/report.py`, `evals/negative_retrieval/README.md`, and
focused cases in `tests/evals/test_negative_retrieval_assessment.py`. No model,
database, runtime product or production deployment changes are in this slice.
