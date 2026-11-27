# EVALS: bind current-page acquisition attempts to the fixture

Status: ACTIVE under the user's over-retrieval goal. Serial successor to #4895;
branch `codex/negative-current-page-attempt`, checkout `retrieval-source-window`,
based on fetched `origin/main`. The user owns this lane. The independent Plan
browser-evaluation PR #4878 was checked for overlapping paths.

After exact fixture, prior conversation and owner-receipt verification, label an
observed related-page materialization attempt for the request's exact primary
document as `current-page`. Do not promote the probe's returned status into proof
of a completed exact saved-revision read: the public capture does not carry the
necessary read event/body binding. Unknown IDs, failed fixture binding, other
source-owner activity and incomplete journal remain unknown; do not weaken a
budget, claim source support, or change cohort qualification. Tests must cover
foreign/missing IDs, mismatched fixture bindings, unsuccessful calls, and the
distinction between attempted and proven completed reads.

Write lease: this handoff, `evals/negative_retrieval/report.py`,
`evals/negative_retrieval/README.md`, and focused cases in the already classified
`tests/evals/test_negative_retrieval_assessment.py`. No product runtime changes,
model calls, database allocation or production deployment are in this slice.
Review the exact cumulative diff and require focused boundary tests and
independent exact-head approval. Complete source mapping and capture-environment
qualification remain separate work.
