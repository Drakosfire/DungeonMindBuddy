# Negative retrieval: SQL execution inventory

Status: ACTIVE. The user authorized the negative-retrieval benchmark goal and
owns this serial workstream. Base Buddy main `0f7716a0b37a1dbd2c536a451fb684872a9af39f`;
branch `codex/negative-sql-execution-window`. Relevant open retrieval, benchmark
and capture PRs were checked. Predecessor #4931 is merged. The existing App
clone and read-only Core remain owned by the benchmark supervisor; no new
port, clone, provider or production runtime is allocated.

Write lease: this handoff; `evals/negative_retrieval/sql_window.py`, `capture.py`,
`report.py`, and `README.md` in that directory; focused tests in
`tests/evals/test_negative_retrieval_assessment.py`.

Observe selected psycopg cursor execution APIs across Python threads during
one isolated turn POST. Retain only aggregate attempt/outcome counts and
host-only source/code fingerprints and line numbers for callers under the
executing Buddy checkout; never retain SQL, arguments, identities, DSNs,
returned rows or model-visible metadata. Treat unknown connection/caller,
unsupported driver paths, overflow, pre-existing work, concurrent/late work,
other processes and cleanup failure conservatively. This slice is an inventory,
not a source/discovery classification or complete acquisition journal; it must
not turn a benchmark budget into a pass. A follow-up classification and complete
coverage contract depends on this slice and is not yet implemented.

Verify direct and pre-bound calls, sync and async supported APIs, distinct
unknowns, exception and cleanup paths, bounded storage, POST boundary, report
validation, privacy, and co-existence with the existing source monitor using
focused provider-free tests. Exercise one owned synthetic App read and shared
read-only Core as appropriate, without full database scans. Independent exact-
head review and required checks precede merge. No product deploy is included.

Case 356 verified an initial observer against the real serving-source resolver;
case 357 repeated the same read-only synthetic App check after bounded pending
and concurrency handling changed. Case 357 recorded eight returned cursor API
calls across seven caller groups, including a saved-revision read and an
unnecessary full working-copy read. Both are retained as provider-free owner
checks, not ordinary model turns or complete acquisition evidence. The latter
working-copy projection is a separate product slice after this evaluator slice;
it must preserve working-copy CAS and draft-loss protection.
Case 358 repeated the final observer against the same resolver and additionally
verified one real asynchronous psycopg call on the read-only App connection;
its worker and redacted inventory are retained. A local synthetic 10,000-error
microcheck measured median 0.99 ms without and 1.25 ms with the global unwind
filter over three pairs. It is not a whole-turn or production latency measure;
benchmark response timings include observation overhead.

Fourteen focused final-source checks passed, including pre-bound cursor calls,
sync/async and generator behavior, pending and resumed work, bounded overflow,
cleanup failure, no available monitoring slot, privacy, malformed records,
legacy reporting, the mocked TestClient boundary and existing source-monitor
coexistence. No broad suite, model or production data was used.
