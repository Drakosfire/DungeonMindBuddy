# RETRIEVAL: read a future current-page source scope

Status: ACTIVE under the user's over-retrieval objective. Serial reader-first
successor to #4888, based on serving merge `0c8c93ab79f84b6208799d53757cdf9eea73cb6d`;
branch `codex/current-page-direct-reader`, checkout `retrieval-source-window`.
The user owns and authorized this lane. The existing App clone is owned by this
workstream and reused serially; do not allocate another. #4884 is an independent
serving release; its current diff was checked for these paths before dispatch.

Prepare readers for a future controller choice meaning that the requested saved
source is exclusively the open page. Do not emit the new choice in this slice.
Preserve exact historical request reconstruction and vote validation, classify
the new choice as evidence-seeking at the existing App and writer boundaries,
and preserve action barriers, principal checks and citation authority. A later
producer must use a locked exact-revision saved read, fall back safely for
different, additional or ambiguous sources, and prove zero catalog discoveries;
this reader change alone does not accomplish that behavior.

Independent review found that an older runtime could resume the future scope by
performing a broad catalog or native lookup. The reader slice therefore also
owns a fail-closed runtime guard: unfinished future-scope work may not initiate
either acquisition in this reader. This is a safe interruption, not proof that
an interrupted future turn can complete after rollback. A successor producer
must replace the guard with the exact current-page path and prove that path.

Write lease: this handoff, `build_intentional_response.py`,
`build_source_free.py`, `native_build_work_view.py`,
`apps/live_control_server/services/build_pending_app_pages.py`,
`apps/live_control_server/services/build_pending_source.py`, and a new focused test file
`tests/test_build_current_scope_reader.py`. Avoid the `test_build_source_free_protocol.py`
path shared with #4884. Verify old and new exact request/vote validation, reject
tampered scope and guidance, preserve unavailable-action barriers, require actual
supplied source evidence for writer presentation, and prove the emitted menu
remains unchanged. Review the exact cumulative diff and get independent exact-head
review before merge. Re-anchor the serving parent before release; do not claim
zero discovery, complete acquisition capture, or end-to-end product success.
