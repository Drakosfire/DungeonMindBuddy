# RETRIEVAL: source observation window

Status: ACTIVE. The user authorized continuing the over-retrieval goal and
assigned this lane. This is a serial evaluator-only successor to merged #4584
(`ed0e2fe195c9e56250229a036deac82d8b79ab2f`), based on that fetched main
revision in branch `codex/retrieval-source-window`. Checkout:
`/home/drakosfire/Projects/.codex/retrieval-source-window/DungeonMindBuddy`.

Outcome: an ordinary isolated capture can retain scoped diagnostic attempts at
selected Core source-view boundaries, including work dispatched through Build's
known executor, without mistaking unrelated or unfinished work for proof of
zero acquisition. These are entry observations, not completed reads; no new
result may promote the journal to complete. Runtime/product files, provider
contracts, shared CI configuration and source data are outside this lease.

Write set: this handoff; the predecessor
`Docs/Plans/HANDOFF-RETRIEVAL-negative-intent-benchmark.md` for truthful merge
settlement; `evals/negative_retrieval/source_window.py`, `capture.py`, and
`README.md`; and `tests/evals/test_negative_retrieval_assessment.py`. No other
lane may edit these without transfer. #4857 changes the separate shared browser
runner; #4580 and #4550 are runtime lanes, and no overlapping write was found.

Verification: focused Python 3.13 tests at the capture/owner boundary must cover
the actual source-view owner, prebound aliases, existing executor threads,
unrelated calls, exceptions, late or outstanding work, monitoring slot
contention, cleanup and unavailable optional instrumentation. Do not make
network/provider calls or allocate another App clone for these tests. The
existing live owner retains its original clone and isolated checkout; this
slice does not switch that checkout or drop the clone. Independent exact-head
review and applicable CI gates remain required.

Failure critique: entry is an attempt, not proof of a materialized body; view
wrappers may overlap, batch-empty calls may be no-ops, other owners and
processes may be invisible, and raw threads may lose request context. The
capture must remain explicitly partial and preserve an unscoped/unfinished
warning; it must not claim completeness, qualified rates or a product fix.
The final goal still requires complete owner coverage, a valid native Core
control, independent holdouts, serving qualification and signed-in acceptance.
