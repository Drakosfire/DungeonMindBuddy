# INGEST: settle owned inference within one absolute deadline

Status: ACTIVE. Root adopts independently critiqued design
`153b7752eb07a1d9a6ede6efcc19278c2b6cf46dd07f1bc77f100cbfe963d3c4`
under existing user implementation authorization.

Branch `codex/ingest-owned-deadline`; stacked parent PR #2113 exact head
`11ab58ce63a69fdcfca0308c0397459963878d8f`. Remote main and open PRs
rechecked before activation. Merge/rebase order: existing ingestion stack through
#2111, then #2113, then this successor. UI #2112 and REFERENCE #2104 are
independent and excluded. No merge or deployment authority.

Exclusive expected writes:
- `src/graph_memory/extraction/_recap_inference_worker.py`
- `src/graph_memory/extraction/bounded_recap_execution.py`
- `tests/test_recap_inference_worker.py`
- `tests/test_bounded_recap_execution.py`
- this handoff.

One inherited monotonic deadline bounds startup, inference, atomic receipt
settlement and direct owned-worker cleanup. Reserve at most two existing 50ms
quanta within that budget. Recompute GE's effective remaining milliseconds after
startup; retain the effective request in attempt evidence. Explicitly prove no
dispatch when budget expires before GE. Retain genuine terminal receipts before
cleanup; missing/malformed receipt remains unknown. Reject late success while
preserving actual receipt evidence. Never manufacture a GE observation from a
raw callback. Never wait indefinitely for cleanup; retain any unreaped owned
handle and block dispatch until cleanup is confirmed.

Scope is the existing daemon worker and its threads, not arbitrary subprocess
descendant management. No provider policy, public schema, prompt, output ceiling,
retry, database, source or Gold changes. GenerationEngine completion-status
truth remains separately owned by PRIME. No inference calls or publication in
this implementation slice.

Validate real spawned workers with fake providers: startup consumption, explicit
not-started, real GE timeout without an artificial shorter test budget, blocked
close/executor, missing/malformed receipts, effective callback request and bounded
cleanup. Preserve acknowledged accounting. Inspect cumulative diff, test,
commit/push/open stacked PR, and obtain independent subagent exact-head review.
Fresh Sessions 1–10 on a common qualified build remain required; historical runs
remain evidence only. Worldbuilding and benchmarking remain later stages.

## Implementation validation

Owning worker, bounded execution and usage suites: 144 passed, two existing
Pydantic field-shadow warnings (isolated cluster55447, disposable test DBs).
Original failed expectation and corrected test logs are retained under
`ingestion-resume/deadline-tests-v1.txt` and `deadline-tests-v2.txt` in the
external evidence directory. The post-suite effective-request assertion still
requires exact-head independent execution. Independent precommit critique
`19fb493d7fdd962b154d48aacd2c003eef4b2c9747033227cbb21e465949289f`
was addressed: known receipts survive cleanup uncertainty, parent observation
bounds receipt settlement, and a blocked new dispatch is not_started.

No model execution or publication was performed. Runtime quality and Session6
remain unproven pending a fresh qualified capture after review.
