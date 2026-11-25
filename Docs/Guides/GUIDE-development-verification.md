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

The named [CI contract catalog](../../ci/contracts.json) and
[contract runner](../../scripts/ci_contract.py) show reusable commands:

```sh
python scripts/ci_contract.py commands
python scripts/ci_contract.py run <contract-name>
```

The second command runs the entire selected contract, which may contain many
unrelated tests. Start with the changed invariant and its owning boundary; inspect
the contract's contents and cost, then run focused exact-source tests when they
fully exercise that boundary and its failure cases. Run a whole named contract
when needed for that evidence or explicitly required by the user, assignment,
security or release gate. Record the selected checks and any omitted full suite;
a focused result does not establish full-contract or release qualification. Use
the repository's locked Python environment and the same database isolation for
focused tests that need App state. The `inventory` action classifies discovered
test **files**; it does not run the suite, establish case-level coverage or select
PR tests. Database checks require the disposable, uniquely owned isolation described
in [AGENTS.md](../../AGENTS.md#local-verification-standard-and-hosted-pause).
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

When multiple full contracts are independently required, the runner can combine
them in one command; list only the contracts whose evidence is needed:

```sh
python scripts/ci_contract.py run <required-contract> <another-required-contract>
```

The aggregate runner holds the owner around every selected suite, runs them
serially even if an earlier suite fails, and returns the first failure. It waits
for the exact worker process group to close before returning to its owner. The
App fixture prepares a migrated pristine dump once per pytest session and resets
that same database before and after each case. These full resets can dominate
runtime in large suites; include that cost when choosing verification scope, but
never skip a reset required for fixture isolation. A lock refuses overlapping cases
or pytest sessions, and open connections refuse a reset. Predecessor migrations,
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
iteration commands. Before review or merge, follow the exact-SHA local verifier
and evidence-validation procedure in [AGENTS.md](../../AGENTS.md#local-verification-standard-and-hosted-pause),
including the shared resource lock and external storage requirements. Frontend
changes also need the policy's discovered-suite diagnostic. A working-tree run
helps debugging but is not exact-commit evidence; a local result is not a
GitHub-hosted status or a release-qualification claim.

Record the tested revision, commands, environment, isolation, failures and
limits. Choose additional owning-boundary tests for the change and distinguish
inherited failures from regressions without calling either a pass. For links in
the maintained entry points and guides, use the opt-in
[documentation checker](../../scripts/check_docs_links.py) described in the
[documentation map](../README.md#find-what-you-need).
