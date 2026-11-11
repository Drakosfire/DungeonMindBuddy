# INGEST: Restore worldbuilding publication fixture verification

ACTIVE serial test slice for the deferred fundamentals goal. Base
`8a9ad7902f26ef98c4da4f859361358d08566358`, branch
`codex/worldbuilding-publication-fixtures` in the recorded-names-control
checkout. QA PR #2396 closed without adoption. PRs #1163 and #1235 have
disjoint write sets.

Write lease covers this handoff, `tests/test_cutover_worldbuilding_authority_port.py`
`tests/_cutover_d3a_blocker_safe_fixtures.py`, and direct database byte reads in
`tests/test_worldbuilding_source_observations.py`,
`tests/test_worldbuilding_publication_discovery.py`, and
`tests/test_worldbuilding_source_catalog_admission.py`. Exercise registered source
bytes, sealed candidate bytes and committed Page revisions through their
owners. Check the current stored run-scope rejection for a forged World and
retain the existing zero-write and cross-World isolation checks.

Verify the 29 authority-port cases and affected shared fixture callers on
disposable evaluator clones. Independent review must inspect the cumulative
change. Historical Mirathorn Gold and the ordinary answer capture retain
their original evidence and scope.
