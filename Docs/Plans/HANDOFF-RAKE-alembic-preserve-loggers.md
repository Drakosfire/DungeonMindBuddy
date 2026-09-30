# HANDOFF — RAKE: preserve application loggers during Alembic setup

**Status:** ACTIVE — PRIME explicitly activated the repair
**Repository:** `Drakosfire/DungeonMindBuddy`
**Base:** Buddy `main@a8b0d5c29feaf451b4a7b562302272bc02fdad2a`
**Branch:** `codex/rake-alembic-preserve-loggers`
**Topology:** Serial; one infrastructure repair PR to `main`. No merge authority.

## Failure and capability

The Buddy Alembic environment calls `logging.config.fileConfig` with its
default `disable_existing_loggers=True`. Loading the migration environment
therefore disables previously created application loggers that are absent
from `alembic.ini`, including `dmb.agent.turn_trace`. Hermes still constructs
and returns the response trace, but its INFO log record is suppressed. The two
C1 Hermes trace-capture tests consequently passed alone and failed after the
combined test sequence loaded Alembic.

Keep non-Alembic application loggers enabled while applying the existing
Alembic logger configuration. This repair is separate from C1 PR #810. C1
remains held until this repair merges; DEMO then rebases C1 and reruns its
seven-suite PostgreSQL owning witness against a fresh disposable target.

## Exclusive write lease

Only these paths may be edited:

~~~text
Docs/Plans/HANDOFF-RAKE-alembic-preserve-loggers.md
src/application_state/migrations/env.py
tests/application_state/test_migration_logging.py
~~~

No database, container, product runtime, C1 path, migration revision, dependency,
or logger contract changes are in scope.

## Acceptance and verification

- Alembic still configures the loggers declared in its existing INI file.
- Running the real Alembic environment in offline SQL mode leaves a pre-existing
  `dmb.agent.turn_trace` logger enabled. The regression test must not connect to
  PostgreSQL or mutate database state.
- The two C1 Hermes trace-capture tests pass after this regression has exercised
  Alembic setup; report them as targeted checks only, not as the seven-suite
  witness.
- Do not access, restart, or modify the retired C1 PostgreSQL target. The
  combined seven-suite witness must be rerun by DEMO after this repair merges
  against a fresh authorized disposable target.
- Run the new regression test, the two named Hermes tests, scoped Ruff,
  `git diff --check`, and inspect the exact cumulative base-to-head diff before
  opening one PR. PRIME owns review and merge.
