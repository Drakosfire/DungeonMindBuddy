# RETRIEVAL: read capability-aware coverage proofs

ACTIVE under the user's over-retrieval goal. First serial slice: branch
`codex/coverage-capability-reader`, base `codex/coverage-capability-serving-base`
at healthy production `e50652d27f6b11dbb424f87f0aadff7cacd8645c`, checkout
`retrieval-source-window`. The separately qualifying #4884 candidate at
`d519cfd6e4954bdab5e450fd53e056ea4a2958a1` was checked: it does not change the
coverage compiler or focused test file in this lease. No shared runtime is used.

The independently authored case 254 read its required saved page, but the
coverage controller classified more native sources as needed for a mixed request
that also asked for an unsupported reminder. The prompt asks about the entire
request and does not distinguish factual coverage from unavailable capability;
the vote itself does not prove the controller's reasoning.

Reader-only outcome: accept exact historical coverage request bytes and an
explicitly defined capability-aware variant while continuing to emit the
historical request. Never accept arbitrary instructions, changed facts or a
different verdict, and preserve request/response binding, exact read closure,
access, claims and CAS. Prove old and new reconstruction, malformed variants,
changed page/history, and actual vote validation with focused tests. Do not emit
the new prompt here. Deploy this compatible reader before any producer can use
the new variant; after production moves, port and requalify against its current
serving parent. Rollback after future new-format proofs must use a reader that
accepts both variants.

Serial successor (not authorized by this handoff to edit yet): enable the new
coverage question, review exact head, deploy against the then-current serving
parent, and replay the mixed required-source regression plus genuine missing
fact controls. A further successor owns unavailable-source graceful delivery;
the current-page-required selection repair is separate and also needs reader
compatibility before producer activation. Fresh independent held-out and app
verification remain required.

Write lease: this handoff, `src/application_state/agent_conversation/build_pending_app_coverage.py`,
and focused cases in `tests/test_build_related_pages.py`. No database, model,
schema or production writes are part of this reader-only implementation.
