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

The second command runs the selected contract; use the repository's locked
Python environment and choose the contract that owns the invariant. The
`inventory` action classifies discovered test **files**; it does not run the
suite, establish case-level coverage or select PR tests. Read the contract and
its tests before treating its result as evidence for a particular behavior.
Database contracts require the disposable, uniquely owned isolation described
in [AGENTS.md](../../AGENTS.md#local-verification-standard-and-hosted-pause).
Never use operator or live data as test fixtures.

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
