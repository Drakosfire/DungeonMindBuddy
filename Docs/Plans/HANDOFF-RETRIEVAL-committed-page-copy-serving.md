# Committed-page revision projection: serving port

Status: ACTIVE. The user authorized deployment of the over-retrieval work.
Serial serving port of merged main PR #4933 (`e15f901cefe9c789d7bb764520cf6243021a1928`),
based on the current healthy serving revision
`95ee0e6102f77cec1806ccf83b6144e5f7305578`, branch
`codex/committed-page-copy-serving`, targeting `codex/coverage-capability-serving-base`.
The App clone remains with the benchmark owner; no new database or provider is
allocated. Open serving/product lanes and live parent must be rechecked at merge
and publication.

Write lease: this handoff, `src/application_state/content/pages.py`,
`src/application_state/content/repository.py`, and the two appended projection
and draft-safety tests in `tests/application_state/test_authored_pages_postgres.py`.

Carry the two runtime files byte-for-byte from the reviewed main merge. Their
parent versions match the serving parent byte-for-byte. Reuse the read-only
projection check, synthetic clone tests, stale-draft and concurrent CAS evidence
and local timing from the main handoff; verify the ported test functions are
identical. This changes no schema, persistent format or release configuration.
Review the exact serving head independently; merge only after required checks.
Publish and deploy through Buddy Actions using the current healthy serving and
rollback pins and the existing guest build options. Verify the staged/live
identities and readiness, then smoke the affected signed-in page flow. Partial
benchmark instrumentation is not a complete acquisition journal.

Port comparison: both runtime files exactly match merged main; both appended
test functions have identical ASTs. The serving-port projection unit test
passed. Cases 361–362 used an inventory-verified snapshot of this same serving
parent with identical runtime files, covering committed snapshot parity, draft
CAS/concurrency and the targeted synthetic query measurement. Case 359 stopped
on a schema-head mismatch before fixture creation; case 360 exposed and retained
a test assumption corrected before cases 361–362. No schema or clone was changed.
