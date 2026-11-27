# Negative retrieval: turn-scoped SQL discovery

Status: ACTIVE. The user owns and authorized this serial over-retrieval lane.
Base `c74b794c9b5a`, branch `codex/negative-scoped-sql-discovery`. Predecessor
#4937 added diagnostic-only SQL classifications; #4932 introduced the window.
Current open retrieval and benchmark PRs were inspected. No production change,
new database, or provider is allocated. The retained workstream clone may be
used serially for a synthetic owner check.

Write lease: this handoff; `evals/negative_retrieval/{capture,sql_window,sql_source_classification,report}.py`,
`evals/negative_retrieval/README.md`, and focused tests in
`tests/evals/test_negative_retrieval_assessment.py`.

Outcome: associate observed SQL starts with the source window's unique turn
scope, preserving unmatched and legacy activity as unknown. A pinned scoped
App page-inventory SQL attempt in a fixture-bound, completed, certain turn can
establish at most one catalog-discovery lower bound. It can overlap related
page and native discovery observations and must not be summed with them.
Never credit a read, prove absence, mark the journal complete, or pass the
capture environment on this basis. Host-only tags never enter product prompts.

Validate exact call provenance, scoped versus foreign and executor activity,
uncertain/unavailable/legacy windows, complete-turn/fixture gating, overlap,
negative and source-required control scoring, instrumentation cleanup, and
capture boundary behavior with focused tests. Review the cumulative diff and
obtain independent exact-head review and required checks before merge. This
is one step toward ordinary-turn measurement; it does not complete qualification.

Provider-free case 364 used the retained owned clone and a bounded synthetic
World query with limit one. Against a tree matching deployed serving revision
`9ec881f7e3bc091a2ea9d2a4815ab0b71fd6718d`, it classified one scoped
page-inventory attempt and two unmatched calls. This does not prove ordinary
turn, complete acquisition coverage, model quality, or benchmark qualification.
