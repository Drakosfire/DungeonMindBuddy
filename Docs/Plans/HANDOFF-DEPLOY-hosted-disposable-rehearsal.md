# DEPLOY: hosted disposable Buddy rehearsal

Status: ACTIVE for drafting and verification only. No merge, dispatch, production
target, credentials, publishing, or permission change is authorized here.

- Owner: DEPLOY lane; parallel-independent; base
  `ba22ffac5a7fe4e07d1192569e9fde658929ed9d`; branch
  `codex/buddy-hosted-disposable-rehearsal`; one draft PR.
- Expected write set: this handoff, `.github/workflows/buddy-disposable-rehearsal.yml`,
  `scripts/rehearse_buddy_disposable_release.sh`. #4356 and #4195 paths
  remain untouched. The local #4356 failure/recovery witness informs this
  harness but is not an unmerged code dependency.
- Manual fixed default ref only; accept two immutable Buddy commits already in
  that history. No interpolation of inputs into scripts, secrets, cloud identity,
  production controls, registry publishing, hosted environments, or exposed ports.
- GitHub-hosted ephemeral runner, isolated PostgreSQL authorities with no
  egress, production Dockerfile builds, and expected readiness failure followed
  by actual prior-image recovery. Fail closed on startup, migration, identity,
  connectivity or acceptance mismatches; clean up task containers/data.
- Verify shell/workflow syntax and the actual local harness; verify the exact
  GitHub-hosted runner only after authorized default-branch integration and
  separate manual dispatch. No claim about cloud staging or production access.
