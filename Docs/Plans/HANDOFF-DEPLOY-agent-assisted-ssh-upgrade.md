# HANDOFF-DEPLOY — agent-assisted SSH upgrade

Status: ACTIVE for the bounded deployment-documentation change in PR #4357.
This handoff defines a controlled operator-mediated path; it does not authorize
a production deployment, migration, backup, restore, or permission grant.

## Scope and sequence

- One serial documentation slice in Buddy's existing production deployment
  runbook. Write set: this handoff and
  `Docs/Runbooks/RUNBOOK-buddy-production-deployment.md`.
- Teach agents the temporary SSH target, the exact-source release checks, the
  operator command handoff, and the limits of agent access. Keep the existing
  production runbook as the command authority; do not create a second deploy
  mechanism here.
- Validate the exact cumulative diff and the repository's documentation-link
  check. No product runtime changes, workflow permissions, credential changes,
  DB modifications, or production mutations belong to this PR.

## Operator and agent boundary

- The production host is `srv586875`, SSH target `alan@191.101.14.169`.
- The operator may load the existing key for one hour for an explicitly
  assigned release. Never copy key material into a repository or message.
- The `alan` account can access Docker, which is effectively host-root access.
  Treat an SSH session as privileged even if the command appears read-only.
  Agents may execute only exact commands authorized by the active task: bounded
  read-only probes, or an exact-reviewed-SHA image preparation command. Never
  read or print environment values or run arbitrary Docker/Compose commands.
- The operator runs all `sudo`, production Compose switches, backup/restore,
  and migration commands in the cloud terminal. Provide one exact command and
  expected result at a time; wait for the output and verify it before the next
  step. Do not pipe passwords or automate interactive `sudo` over SSH.

## Current 774aa063 deployment checkpoint

- Read-only checks observed Buddy serving image
  `dungeonmindbuddy:177b187d57f3ad077fac1d4acfce08fb563a35ba` as healthy.
- The production APP schema is at `20261119_0169`. Candidate `774aa063` has
  APP migration head `20261120_0172`; it is not the serving image.
- The cloud host has Python 3.12.3 but no `uv`, `pg_dump`, or `pg_restore` on
  its PATH. The running Buddy image includes the APP authority Python module
  but no `pg_dump`; PostgreSQL 16.14 client tools are available inside the
  database container. The release checkout contains
  `scripts/application_state_authority.py`. `/srv/dungeonmindbuddy/backups`
  is root-only.
- Therefore the checked-in host-side `uv run ... application_state_authority.py
  backup` example cannot be run as `alan` on this host as-is. Do not replace it
  with an unverified bare dump or claim a backup rehearsal from a checksum
  alone.
- The recovery tool is now implemented in PR
  [#4364](https://github.com/Drakosfire/DungeonMindBuddy/pull/4364), parallel-
  independent of this documentation PR. At head
  `20e7b404f0c101fcf373283eae83e615bbb074a0`, five focused builder tests and
  the isolated synthetic APP backup/clean-target restore proof passed with
  checksum and fingerprint parity; corrupt dumps and nonempty restore targets
  were refused. The resulting non-root image was built locally against a
  synthetic runtime image. This proves the CLI’s fixture contract, not the
  provenance of a production release image or its use with a production backup.
- PR #4364 remains draft. Its exact-head hosted frontend verifier is still
  pending because the shared verification lock is occupied; full discovered
  diagnostics are historically red. It has not been tested with the serving
  image, an operator-provided production backup, paired WorldGraph recovery,
  or a real restore. Do not use it for the 0172 rehearsal until its remaining
  review and verification gates pass. No production backup, restore, migration,
  or deployment has occurred.
- Before any production migration, rehearse restore of the current APP
  authority into a separate empty target, verify fingerprint parity, apply the
  candidate migrations only to that target, and record the resulting schema
  head and readiness. Migration `0172` is forward-only; after applying it, an
  image-only rollback to code that expects `0169` is not a safe recovery plan.
  Production migration and cutover remain separately authorized operator
  actions.

## Completion evidence

This documentation slice is complete when the runbook gives agents and the
operator the same safe, reproducible division of work and no longer implies
that the SSH target is unknown. It does not make the 0172 backup rehearsal,
production migration, hosted Plan acceptance, or a release deployment complete.
