# DEPLOY: isolated Buddy release rehearsal

Status: ACTIVE for the local, disposable rehearsal only. The operator asked to
set up the proposed deployment design; this handoff deliberately does not
authorize any production access, deploy, policy, registry, or account change.

- Owner: DEPLOY lane; parallel-independent; base
  `144c9c00912e7bc1359d0ed039c3cb9b9b87ba12`; branch
  `codex/buddy-isolated-release-rehearsal`; one review PR.
- Expected write set: this handoff, `scripts/plan_buddy_preview_release.py`,
  `tests/test_plan_buddy_preview_release.py`. Existing rollout/retention
  PR #4195, production Compose, workflows and runbook remain untouched.
- Isolate the product preview on the Projects scratch lane using a task-only
  image/container, no host port, no network, no live state, credentials or
  database, and no external provider calls. Preserve other workloads.
- Reuse the production Dockerfile/api target and built-in health and SPA
  endpoints. Distinguish a synthetic preview from hosted DMS, real DB recovery,
  browser sign-in and current production serving identity.
- Verify source/image correspondence, stale expected-serving refusal and
  duplicate request determinism. The planning CLI must perform no Docker or
  network operation. Report exact inputs, exit status and observed evidence.
- Existing production operator gates remain unchanged; see
  [the production runbook](../Runbooks/RUNBOOK-buddy-production-deployment.md)
  and [the release recovery issue](https://github.com/Drakosfire/DungeonMindBuddy/issues/3560).
