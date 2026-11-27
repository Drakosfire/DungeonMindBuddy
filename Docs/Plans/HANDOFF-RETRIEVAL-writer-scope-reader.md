# RETRIEVAL: writer scope projection reader

Status: ACTIVE. The user owns and authorized the over-retrieval lane, including
the prerequisite needed to run its audited replay. Serial prerequisite to the
producer in #4973. Branch `codex/retrieval-writer-scope-reader`, based on serving
source `6ba75fa9f27912945503ca547b43bfbbb0de105a`.

The stopped case 565 exposed a typed campaign identifier in writer evidence.
The request was not sent. Add a reader for an explicitly authorized semantic
projection that uses local campaign aliases while retaining equal/different scope
relationships. Keep exact reconstruction of all historical requests and exact
host evidence and citation bindings. Do not activate the new presentation in
this slice. Unknown typed structures must fail closed; literal source context is
not subject to recursive scrubbing.

Expected write lease: this handoff; `native_evidence_view.py`,
`native_execution.py`, `native_writer.py` under
`src/application_state/agent_conversation/`; and focused tests in
`tests/test_native_writer_projection.py` and
`tests/test_native_campaign_scope_projection.py`. Verify at actual serialized writer
admission, including historical reconstruction, scope relationships, tampering,
and original citation support. The follow-up producer is serial, after review,
merge and deployment of this reader. Production release must re-anchor on the
then-current serving parent; no database clone is created by this slice.

Working-tree evidence: two provider-free projection tests passed. Five focused
serialized-request checks passed in owner case 568 with fresh synthetic World
IDs, an in-memory Graph and the retained App clone. The ordinary CI fixture was
not used because it clears the whole App schema; the narrow fixture override
does not reset retained benchmark state. Case 566 stopped at the owner-directory
check; case 567 passed before the tampering check was added. The run emitted
pytest import-rewrite and existing Pydantic serialization warnings. Exact-head
independent review and a deployed-reader recovery check remain required.
