# RETRIEVAL: Read bounded current-page partial results

Status: ACTIVE. The user owns and authorized the over-retrieval lane, including
reviewed releases and deployment. This serial reader prerequisite is based on
serving revision `aed180541cbf1ff1f06e51a5ce777ee84b6e8357`; branch
`codex/current-page-partial-reader`. The successor producer will be based on
the merged reader and deployed only after its reader is live. The current
serving rollback floor remains the compatible deployed reader.

In a signed-in test World, a request restricted to the saved current page asked
for both a supported price and an unsupported founding date. Coverage chose
`native_sources_required`; the reply stopped with `build_execution_exception`
instead of answering from the page. The page was unchanged. An unrestricted
saved-page request succeeded on the deployed unobserved-native path.

This reader slice must recognize a distinct partial terminal only after the
frozen current-page-only work, exact current-page selection and complete read,
and acknowledged further-source coverage. It must not start writing, expand
the source scope, accept unrelated or incomplete reads, or infer absence in the
rest of the World. Receipt validation must bind the saved page to its captured
World, revision, visibility and content. Check decoding and rejection cases at
the pending execution boundary. Preserve existing unobserved-native behavior.

Expected writes: this brief, `build_pending_app_coverage.py`,
`build_source_free.py`, `writer_evidence_selection.py`, and focused cases in
`test_build_current_page_direct.py`.
The adjacent open serving PR #4884 at head `4eea4fe1c7ff` was checked; its
changed-file list does not include those paths. Runtime/evaluator: existing
owned App clone only for subsequent focused runs; no new database or provider
access is needed for reader tests. Independent exact-head review and applicable
checks precede merge; deploy the reader before authorizing its producer.
