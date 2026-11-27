# RETRIEVAL: reader for targeted fresh-source selection

Status: ACTIVE, authorized by the user's continuing over-retrieval goal; Root
owns this lane. Serial successor to merged and deployed #4971, serving base
`b50451c52e8f6a5efe6368b263b9c08922fd47d7`. Branch
`codex/retrieval-fresh-lookup-reader`; one focused reader PR, followed only
once deployed by a separately reviewed producer and benchmark iteration.

## Trigger and boundary

A signed-in fresh-source request for one other source returned a correct cited
answer after 236.4 seconds. Its recorded decision batches selected 13 and 15
handles; 17 native direct-source opens, one content search and two section
reads occurred. The user did request fresh evidence, but not an exhaustive
survey. This is evidence of excessive acquisition, not proof that every one
of those sources was irrelevant. Preserve the original production trace and
avoid hard source limits or suppressing explicitly broad/multi-source work.

This reader-only slice adds a distinct Build navigation input codec and exact
question wording that guides targeted next evidence, permits expansion when a
requested part remains unresolved, and preserves existing input/wire readers.
No active producer may emit it until the reader is live. The future producer
will test actual model selection and ordinary HTTP behavior on development and
independent cases, including one-source, broad survey, multiple distinct facts,
missing evidence, source authorization, cancellation and uncertain scope.
Actual acquisition counts, citations, answer quality and latency are needed;
incomplete capture is unknown. No model prompt contains host metadata.

Write lease: `src/application_state/agent_conversation/jev_retrieval_contract.py`,
`tests/test_jev_retrieval_contract.py`, and this handoff. Verify exact-wire
round trips, surface rejection, unchanged historical codecs and no producer
activation with focused tests, then independently review the cumulative diff.
The producer is a separate serial successor, not part of reader acceptance.
Use the already-owned single App clone and shared read-only Core for any
benchmark, serially; do not create a new database or scan its contents.

Local evidence: the focused V5 and old/new reader checks passed, including a
pending owner proof and a multi-source selection. Three existing
`test_historical_native_question_bytes_remain_at_adopted_control` cases fail
in the same local dependency environment on both this branch and deployed base
`50e66dd286a673da5fcef8074600d82fc99275d4`, with matching actual hashes. An
independent deterministic comparison of V1 through V4 between that base and
this change produced identical bytes. The cause of the adopted-hash mismatch
is not established; retain it as an inherited verification limitation.
