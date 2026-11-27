# RETRIEVAL: observe prebound PDF repository calls

Status: ACTIVE under the user-authorized over-retrieval goal. Serial evaluator
slice based on main `7b59a69da404fb41489f38e8d0d1c8240b1e8605`, branch
`codex/negative-pdf-alias-window`. Predecessor #4925 observes PDF loader
callbacks; no overlapping negative-evaluator PR was found.

Use the existing scoped source window to observe the actual imported Core PDF
repository code, including aliases bound before wrappers. Bind any scored
attempt to the registered source file, code and interpreter fingerprint, a
completed fixture-bound POST, and a clean scoped window. Entry is an attempt,
not a returned PDF or source-specific support. Overlapping callback/window
observations are a lower bound, not distinct reads. Unknown implementations,
old artifacts, foreign threads, late work, failures and other processes remain
unproven; never establish a complete journal or capture environment.

Write scope: this brief; `evals/negative_retrieval/source_window.py`,
`capture.py`, `report.py`, `README.md`; and focused cases in
`tests/evals/test_negative_retrieval_assessment.py`. Check actual prebound owner,
scoped executor and unrelated thread, failed transaction, missing and successful
source outcomes, legacy and malformed artifacts, unscoped/late work, cleanup,
owner fingerprint changes and callback overlap. No Core/App database, model,
provider or production mutation is used. Independent exact-head review and
applicable checks precede merge.

Focused verification: eleven owner, report, provenance, legacy/cleanup and
uncertainty cases passed under the pinned Core/CPython environment. The
synthetic TestClient POST/executor case passed outside the sandbox; even an
empty TestClient stalled before instrumentation inside the sandbox, so those
attempts were interrupted and do not count as passing. No real database or
provider was used. The new record remains partial and unqualified.
