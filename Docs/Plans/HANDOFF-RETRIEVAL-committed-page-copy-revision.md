# Committed-page working-copy revision projection

Status: ACTIVE. User-authorized serial product slice under the over-retrieval
and latency goal. Buddy main base `374ee9d07740e12c4355f4995d5f2adf362cf198`;
branch `codex/committed-page-working-revision`. PR #4932 is the merged
predecessor. Open PRs and current path references were checked; #4550 owns the
unit-of-work pool, not these paths. No new database, port or provider is
allocated. The existing benchmark supervisor owns the sole App clone.

Write lease: this handoff, `src/application_state/content/pages.py`,
`src/application_state/content/repository.py`, and focused tests in
`tests/application_state/test_authored_pages_postgres.py`.

The ordinary Build work resolver reads the committed saved page and only needs
the working-copy revision for its snapshot. Case 357 observed the current
implementation also reading the entire working-copy Markdown and digest. Add
a revision-only lookup for this exact committed-snapshot path. Preserve the
repeatable-read transaction, null/no-working-copy behavior, exact revision
value, page ownership, committed body and all mutation/CAS logic. Database
columns skipped by the projection have PostgreSQL UUID/TEXT/TIMESTAMPTZ and
NOT NULL/FK constraints; the old model has no cross-field validator. This
slice does not weaken editor, draft, history or stale-confirmation checks and
does not alter schema or user-visible output.

Verify the actual SQL projection excludes body text, the committed snapshot
with and without a draft matches its previous results, a stale draft basis is
rejected without data loss, and a concurrent draft update cannot be overwritten.
Use focused checks only, one existing synthetic App clone and no provider.
Independently review the exact head and required checks before merge; follow the
authorized Actions release path and verify the changed signed-in workflow if
deployment gates are met. This is not by itself the full over-retrieval goal.

Focused evidence: the revision-only SQL projection test passed locally without
loading the autouse database fixture. Case 361 ran the candidate source files
on an inventory-verified serving-source overlay against the retained App clone:
committed snapshot with and without a draft, stale-draft and stale-metadata
rejection, concurrent draft/commit, and wrong-World/digest checks passed. The
serving and main base versions of both changed runtime files are byte-identical.
Case 362 observed the actual committed path select only the revision; with one
524,288-byte synthetic draft, five alternating warm same-connection pairs had
median full-row and revision-only times of 0.539 ms and 0.048 ms respectively.
This is a local SQL microcheck, not whole-turn or production latency.

The first local pytest attempt failed before test execution because the
repository autouse fixture had no assigned CI owner; no clone was allocated.
Case 359 failed before fixture creation because the retained clone is on the
serving schema, not current main's newer schema. Case 360 used the correct
serving overlay but exposed an incorrect test assumption that a commit leaves
no working copy; the corrected test and prior failed source are retained.
No clone was created, reset, migrated or dropped. Worker sources, logs and
results remain with cases 359–362; the last worker and its connections closed.
The test file was subsequently reformatted; the tested and final test files
have identical parsed AST SHA-256
`088350ab4b602376b2a7beef49f6d1f9d332b365aed904cb0890e934ad605494`.
The final projection unit test was rerun and passed. Runtime source bytes did
not change after cases 361–362.
