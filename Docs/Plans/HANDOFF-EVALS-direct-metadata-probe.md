# EVALS: observe direct current-page metadata attempts

ACTIVE under the user's over-retrieval goal. Serial successor to merged #4897;
branch `codex/negative-direct-metadata-probe`, checkout `retrieval-source-window`,
based on fetched `origin/main`. Checked open #4878 and serving candidate #4884;
neither owns this probe/report slice.

The direct saved-page path introduced in #4894 has its own metadata owner and
does not enter the full related-page catalog owner. Add an optional process-local
probe of that entry and outcome, and report observed attempts separately from
catalog discovery and body materialization. Old runtimes and absent entries
remain unknown; do not count a metadata attempt as a saved-body read, catalog
scan, complete journal, or evidence for a source-required answer. Preserve
setup/teardown and fail-closed artifact validation. Verify the actual wrapper,
raised calls, old runtimes, and reporting with focused cases; require exact-head
independent review and applicable checks.

Write lease: this handoff, `evals/negative_retrieval/related_page_probe.py`,
`evals/negative_retrieval/report.py`, `evals/negative_retrieval/README.md`, and
focused cases in `tests/evals/test_negative_retrieval_assessment.py`. No model,
database, runtime product, or production deployment changes are in this slice.
