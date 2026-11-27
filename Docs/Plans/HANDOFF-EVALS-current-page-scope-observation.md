# EVALS: observe current-page-only source decisions

Status: ACTIVE under the user's over-retrieval benchmark objective. Serial,
isolated branch `codex/negative-current-scope-observation`, based on fetched
`origin/main`, checkout `retrieval-source-window`. The user owns this lane.
The independent Plan browser-evaluation PR #4878 was checked for overlap.

The deployed direct-page change #4894 adds the fixed `current_saved_page` source
choice. Project that exact choice from captured controller snapshots rather
than labeling it invalid; keep arbitrary model values classified as invalid.
This observation is unvalidated and does not prove an admitted decision, a read,
absence of other acquisition, or benchmark environment qualification. Do not
change fixture thresholds, source mappings, or the partial-journal policy.

Write lease: this handoff, `evals/negative_retrieval/trace_observation.py`,
`evals/negative_retrieval/README.md`, and focused cases in the already classified
`tests/evals/test_negative_retrieval_assessment.py`. Test the actual trace
adapter with the new choice, all historical choices and unexpected input. Review
and merge the exact-head PR after applicable checks; no production deployment or
database allocation is needed. Exact current-page read mapping remains separate.
