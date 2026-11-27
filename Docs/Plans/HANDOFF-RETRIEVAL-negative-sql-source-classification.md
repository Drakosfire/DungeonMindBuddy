# Negative retrieval: classify pinned SQL source calls

Status: ACTIVE. The user authorized the over-retrieval benchmark and owns this
serial lane. Base Buddy main `f69db302a0927ec1b5434254e7d777ff6edb3b29`, branch
`codex/negative-sql-source-classification`. The SQL-window PR #4932 is the
merged predecessor. Current relevant open retrieval/benchmark PRs were checked.
The existing owned synthetic App clone on port 32769 is reused serially for
provider-free verification; no new clone, provider, or production release is allocated.

Write lease: this handoff; `evals/negative_retrieval/sql_window.py`, `capture.py`,
`report.py`, `README.md`, and a new `sql_source_classification.py` in that
directory; focused tests in `tests/evals/test_negative_retrieval_assessment.py`.

Extend new SQL-window artifacts with interpreter provenance. Recognize only the
exact pinned App Python source, normalized code fingerprint, call line and
cursor API for page inventory, saved-revision Markdown, and working-copy
Markdown. Report these separately as observed API attempts, not returned bodies,
unique pages, source-specific evidence, extra search, or a complete journal.
Legacy artifacts, unrecognized source or interpreter, unsupported APIs, overflow
and uninstrumented work remain unknown. Do not change scoring or infer absence.
No SQL, parameters, IDs or model-visible metadata are retained.

Verify old and new artifact validation, exact known and mismatched fingerprints,
separate categories, invalid and uncertain windows, report integration and no
score changes using minimal focused provider-free checks. Verify actual SQL
call sites on the retained synthetic App clone if possible; no new clone,
full data scan or provider is permitted. Review the exact cumulative diff and
obtain independent review and required checks before merging. This is one
bounded step toward a qualified capture, not completion of the wider objective.

Verification: five focused classifier, report and SQL-window tests passed. A
provider-free real Build resolver check on the existing read-only synthetic clone
(case 363) classified one saved-revision body attempt and seven unknown calls;
working-copy body attempts were zero for that invocation. The serving checkout
tree matched deployed revision `9ec881f7e3bc091a2ea9d2a4815ab0b71fd6718d`.
This does not establish complete turn capture or benchmark qualification.
