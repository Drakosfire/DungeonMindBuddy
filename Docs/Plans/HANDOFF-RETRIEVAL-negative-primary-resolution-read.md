# Negative retrieval: account for primary-work resolution reads

Status: ACTIVE. User-authorized serial evaluator slice; base Buddy main
`dd82927a767a6b50bcc330c4f62b72c1762de396`, branch
`codex/negative-primary-resolution-read`. The merged primary-page stability
slice is the predecessor. Relevant open retrieval and benchmark PRs were
checked. No new database, port or provider is allocated.

Write lease: this handoff; `evals/negative_retrieval/primary_resolution_probe.py`,
`capture.py`, `report.py`, and `README.md` in that directory;
`Docs/Benchmarks/OBSERVATION-negative-retrieval-h4.md`; focused tests in
`tests/evals/test_negative_retrieval_assessment.py`.

The ordinary Build work resolver loads a saved primary page to validate the
World, revision, digest and work-context basis before dispatch. Observe the
actual route-bound committed-page reader during the turn POST, separately from
related catalog discovery and selected-page acquisition. Record started,
returned and raised attempts without IDs, arguments, page text or digest.
This is a partial diagnostic, not a source-specific citation proof or a complete
journal; alias bypass, other processes, concurrent/late work and older captures
remain unknown. Report it separately and do not treat the required work-context
validation read as an extra related-source search or silently omit it.

Verify real route resolver success, invalid preconditions and reader failure,
post-window cleanup and pending/late uncertainty, actual capture entry,
malformed/legacy artifacts and report separation with focused provider-free
tests. Inspect cumulative diff and obtain independent exact-head review and
required checks before merge. No production change or release is included.

Focused provider-free checks exercised real route resolver success and failure,
invalid preconditions, pending worker uncertainty, malformed/legacy evidence,
separate report accounting, capture failures, late work, rejected async clients,
and a real mocked TestClient POST. In owned-clone case 355, the serving-source
Build resolver read the exact frozen synthetic saved page using read-only App
connections, and the new observer recorded one returned read. No ordinary model
turn was dispatched. The last worker closed; cases and worker logs remain with
the owner. Neither this check nor the probe establishes all page-read coverage
or capture-environment qualification.
