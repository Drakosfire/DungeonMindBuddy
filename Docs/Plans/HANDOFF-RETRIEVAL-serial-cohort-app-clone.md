# Serial cohort capture on one App clone

Active assignment. The operator requested one App clone per benchmark
workstream, serial cases, shared read-only Core and verified teardown.
Base c9732a4c399fd1b8661579e7bd6cbee4cfa4ecb6. Branch
codex/benchmark-one-app-clone. Write scope is the cohort runner, its
workflow entry, disposable teardown helper, browser scratch path, tests, lab guide and this
handoff. This is independent of #4580, which owns only the Plan Jev
evidence projection and its navigation tests. No deployment or primary
database access.

Verify one clone and one migration, single-worker launch, exact
manifest binding, fresh browser conversations, retained failures and
output checks, and worker closure before teardown. Keep two shared Core
inventory checks and skip full App contents scans. The current slice
covers one invocation. Manual stop and resume with a retained database
and live Jev routing are outside the runner change. Exact-source local
review and an isolated ordinary browser proof are required before
adoption.
