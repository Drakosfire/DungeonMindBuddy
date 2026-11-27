# Negative retrieval: PDF discovery observation

Status: ACTIVE. The user authorized this serial evaluator slice as part of the
negative-retrieval goal. Base: Buddy main `0cd490a90a9ca68cd91cdb19624dfae3b4ffb86d`;
branch: `codex/negative-pdf-discovery-window`. No prerequisite or behavioral
change to Buddy is intended. Open retrieval/benchmark PRs were checked; none
claims these files. The current clone and read-only Core remain owned by the
existing benchmark workstream; this slice allocates no database or provider.

Write lease: this handoff, `evals/negative_retrieval/{capture,report,source_window}.py`,
`evals/negative_retrieval/README.md`, and focused evaluator tests in
`tests/evals/test_negative_retrieval_assessment.py`.

Observe the pinned PDF listing method after argument validation and transaction
entry, without recording arguments, returned metadata or PDF bytes. Treat the
observation as a lower-bound discovery attempt, never as a completed source read
or evidence support. Avoid double-counting overlapping native probes. Preserve
older artifacts and mark unscoped or unverified observations uncertain.

Verify the real capture boundary and pre-bound alias, invalid limits, failed
transaction, SQL failure, normal return, foreign-thread activity, unknown or
malformed proofs, previous schemas and score behavior. Inspect the cumulative
diff and obtain independent exact-head review before merge. No production
release is needed for this evaluator-only slice.
