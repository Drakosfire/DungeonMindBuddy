# Development and verification

Start with the [repository README](../../README.md) for the locked local setup,
then [AGENTS.md](../../AGENTS.md) and the authorized handoff for the current
verification standard, scope and isolation. This guide routes you to tools; it
does not replace that policy or make every listed test necessary for every edit.

## Find the owning boundary

Use the [documentation map](../README.md) to find the relevant domain guide,
contract, source and focused tests. Trace a change across the frontend, Buddy
server and external owners where applicable. For example, the
[surface map](GUIDE-surface-contributor-map.md) links page components and tests;
the [source map](GUIDE-source-ingestion-and-evidence.md) distinguishes Buddy
source storage from DungeonMind admission and publication.

Select only the minimal checks that verify the changed invariant at its owning
boundary. Inspect the cumulative diff and identify concrete affected behaviors
and failure cases. A documentation-only change normally needs a diff review and
checks of the affected links or mirrors, not product tests. For code, run focused
cases with the locked environment and an isolated exact-SHA checkout when exact
source matters. Record commands, coverage and omissions. Do not run a full named
backend contract, full frontend suite or full-project test run for local agent
verification. If separate full-suite evidence is required for release, record it
as missing rather than claiming focused checks qualify it.

The [CI contract catalog](../../ci/contracts.json) is an inventory, not a test
selection instruction. A test's inclusion in a large named contract does not
require running every other test in it. The `inventory` action classifies test
**files**; it does not establish case-level coverage. Focused database tests
require the disposable isolation in [AGENTS.md](../../AGENTS.md#local-verification-standard-and-hosted-pause).
Never use operator or live data as test fixtures.

Database CI uses one owned App clone for the complete serial workstream, including
retries. Local runs must receive `DMB_CI_APP_OWNER_FILE` (the active owner receipt)
and `DMB_CI_APP_DATABASE_URL` privately in their environment. The receipt pins the
loopback endpoint, database name, OID and cluster identity and records owner,
role and cleanup state. There is no operator database or default-port fallback.
The owner retains the clone until the result is accepted or abandoned; a pytest
fixture borrowing it never drops it. After an interruption, inspect the existing
receipt and workers before starting another run. Reuse the existing read-only
Core snapshot for cases that need Core; these fixtures allocate no Core database.

The App fixture prepares a migrated pristine dump once per pytest session and
restores the owned database before and after each case. Those resets can dominate
runtime, so select only the cases needed to verify the affected boundary. Never
skip a reset required for isolation. A lock refuses overlapping cases or pytest
sessions, and open connections refuse a reset. Predecessor migrations,
empty-schema bootstrap and recovery rehearsals use serial empty states in that
same owned database. Recovery saves the expected fingerprint and offline backup
before reset, then proves restored output/parity; it does not claim simultaneous
live source/target physical isolation. Product same-source and World guards stay
unchanged. Bootstrap's database-creation decision is tested by mocked dispatch;
real empty-schema migration and readback are tested on the owned App database.

Ephemeral GitHub jobs set `DMB_CI_APP_TEMPLATE_DATABASE` to their explicit App
seed, `DMB_APPLICATION_STATE_TEST_DATABASE_URL` to the loopback maintenance
endpoint, and `DMB_CI_WORKSTREAM_ROOT` to their job output directory. The runner
uses the repo-owned disposable helper once around the aggregate job, records
acceptance or abandonment, closes workers/connections, and verifies exact clone
removal. No per-case clones or full contents inventory scans are used. Install
matching PostgreSQL clients on PATH; local checks may use isolated task-local
clients. Keep the ownership receipt and qualifying output, parity, latency and
failure evidence; omit credentials and connection strings from reports.

## Frontend and exact-source evidence

The [frontend guide](../../apps/live-control-ui/README.md#commands) lists local
iteration commands. Select focused tests only for affected frontend behavior and
honor the shared resource lock and scratch requirements in
[AGENTS.md](../../AGENTS.md#local-verification-standard-and-hosted-pause).
A working-tree run helps debugging but is not exact-commit evidence; a local
result is not a GitHub-hosted status or a release-qualification claim.

Record the tested revision, commands, environment, isolation, failures and
limits. Choose additional owning-boundary tests for the change and distinguish
inherited failures from regressions without calling either a pass. For links in
the maintained entry points and guides, use the opt-in
[documentation checker](../../scripts/check_docs_links.py) described in the
[documentation map](../README.md#find-what-you-need).
