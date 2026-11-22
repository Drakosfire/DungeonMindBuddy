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

## Release candidate and live verification

- Candidate `774aa06344eb0a9411855eccdc7e33e7fead89c4` is the merge commit for
  PR #4264 (Plan contextual paragraph placement). It is an ancestor of current
  Buddy `main` at `ebb8161672ed49d3be7fdaa48ad17fbaf55dd9eb`; it is not the
  production image observed below.
- On 2026-11-22 at 02:17 UTC, a strict, read-only SSH check to
  `alan@191.101.14.169` returned host `srv586875` and user `alan`.
- The Buddy Compose project reported container `buddy-buddy-1`, tag
  `dungeonmindbuddy:84df46088596fd45771b12158fa62c4500be102d`, image ID
  `sha256:213fd9dcdd74a8a535b343c60d6efedbde468a9dc241ea2d24aa31e44bea6f8d`,
  and health `healthy`. This is a read-only service check; database migration
  heads, backup state, and rollback-image identity were not checked.
- Revision `84df46088596fd45771b12158fa62c4500be102d` resolves to a cherry-pick
  of PR #4381's manual-summon fix. GitHub compares it with current `main` as
  diverged (63 commits ahead, 886 behind). A healthy container does not prove
  that the reviewed current-main release is serving. Before calling a release
  current, stage and verify an image built from the exact reviewed SHA and
  confirm that image ID and revision label on the running container.
- Earlier host observations below are historical and must be refreshed before
  production use: the APP schema was reported at `20261119_0169`; host
  `uv`/PostgreSQL client availability was reported; and
  `/srv/dungeonmindbuddy/backups` was reported root-only. The checked-in
  host-side `uv run ... application_state_authority.py backup` example could
  not run as `alan` at that time. Do not replace it with an unverified bare
  dump or claim a backup rehearsal from a checksum alone.
- The recovery tool was implemented in
  [#4364](https://github.com/Drakosfire/DungeonMindBuddy/pull/4364), merged as
  `54313c3b8adf0f20c77ee0b0ee5299744a7de38f` from source head
  `20e7b404f0c101fcf373283eae83e615bbb074a0`. Five focused builder tests and
  a local synthetic APP backup/clean-target restore proof passed with checksum
  and fingerprint parity; corrupt dumps and nonempty restore targets were
  refused. The non-root image was built against a locally labeled synthetic
  runtime image. The exact-head hosted frontend verifier passed; the full
  discovered diagnostic remains historically red. These results do not prove
  production release provenance or recovery.
- The 0172 backup/restore rehearsal, paired WorldGraph recovery, production
  migration, and cutover still need current evidence. Before any production
  migration, rehearse restore of both authorities from one consistent backup
  set into isolated targets, verify fingerprints and a known World read, apply
  candidate migrations only to those targets, and record schema heads and
  readiness. Migration `0172` is forward-only; after applying it, an image-only
  rollback to code that expects `0169` is not a safe recovery plan. Production
  migration and cutover remain operator-owned actions.

## Completion evidence

This documentation slice is complete when the runbook gives agents and the
operator the same safe, reproducible division of work and no longer implies
that the SSH target is unknown. It does not make the 0172 backup rehearsal,
production migration, hosted Plan acceptance, or a release deployment complete.
