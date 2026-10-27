# HANDOFF-HOSTED-buddy-validation-ci

**Status:** SETTLED — PR #1814 merged at c7f83c086d39e01f129fa7e31ef03262dbf65c91; this validation lane is complete. The deployment-preparation successor is documented in HANDOFF-HOSTED-buddy-deployment-preparation.md.
**Date:** 2026-10-27 UTC  
**Owning repository:** Drakosfire/DungeonMindBuddy  
**Topology:** serial; one successor to merged PR #1802  
**Base:** `main@e754f68f1d6a9e726c23657e2884be36cc3e8759`  
**Branch:** `codex/hosted-validation-ci-20261027`  
**PR:** [#1814](https://github.com/Drakosfire/DungeonMindBuddy/pull/1814), merged.

## Authority and predecessor settlement

The user authorized a narrow validation-only workflow and draft PR. The cross-repository sequencing reference was DungeonOverMind PR #58, `Docs/Plans/PLAN-buddy-hosted-readiness-and-launch.md`; the current deployment-preparation successor separately records the source pins and sync point for that existing plan. This handoff records completed CI work only.

Buddy PR #1802 merged at `e754f68f1d6a9e726c23657e2884be36cc3e8759`. Its predecessor handoff is settled in `HANDOFF-HOSTED-buddy-auth-packaging.md`. That merge delivered a fail-closed hosted-auth and packaging foundation, not launch readiness: production registers zero World resolvers, hosted World operations remain denied, and readiness intentionally returns not-ready. This CI lane preserves that state.

Related open Buddy PRs #1512 and #1514 remain unchanged; their route inventory, cookie-Origin helper, and World-policy proposal have separate documentation paths.

## Read-only Actions preflight

Using supported GitHub read tools, `main` resolved to `e754f68f1d6a9e726c23657e2884be36cc3e8759`. The `.github/workflows` contents request returned 404, the supported workflow-run lookup returned an empty list for the predecessor merge/head, and the combined status lookup for the merge returned no checks. This establishes no existing workflow/run/status evidence. It does not establish that Actions is disabled. Do not change repository Actions permissions or security settings; the PR-triggered run is the next evidence point.

## Validation scope

- Use a complete, non-sparse checkout of the exact PR merge candidate on standard `ubuntu-24.04` GitHub-hosted runners.
- Set up Python 3.13 with `actions/setup-python` pinned to commit `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0` (v7.1.0) and uv 0.13.5 with `astral-sh/setup-uv` pinned to `07a047e608db84b3d8c06cd9a7c7dcc9c355c18e` (v10.3.2). `actions/checkout` is pinned to `3d3c42e5aac5ba805825da76410c181273ba90b1` (v7.0.1).
- Run `python scripts/prepare_patched_hermes.py`, install the exact locked project with `uv sync --locked`, then run the full-root-conftest auth/app selection: `tests/test_hosted_auth.py`, `tests/test_dms_principal.py`, `tests/test_trusted_cookie_origin.py`, and `tests/test_agent_graph_auth.py`. Use concise, capture-suppressed pytest output. Do not skip failures.
- The checked-in lock resolves `psycopg-binary` 3.3.4 with a CPython 3.13 Linux wheel, addressing the prior cached Python 3.12 libpq import issue without changing the lock. These four modules do not request the disposable application-state fixture, so the workflow uses no PostgreSQL service, live DB, or database credentials.
- Run the production-image job after the auth/app job completes, even if the tests fail (unless the workflow is cancelled), so both checks produce terminal outcomes. Build `Dockerfile.production` with Buildx and `--load`; do not push. The production Dockerfile runs the frontend `npm ci` and `npm run build` stage, so a separate duplicate frontend job is unnecessary.
- Preserve the test that production readiness returns the expected 503 fail-closed response while no route policies are registered. Do not enable World routes or introduce World policy to make CI green.

## Workflow boundaries

- Trigger only on `pull_request` to `main` for `opened`, `synchronize`, and `reopened`.
- Set workflow and job token permissions to `contents: read` only. Persist no checkout credentials.
- Use only the pinned official actions listed above; no `pull_request_target`, secrets, provider calls, real OAuth, OIDC, registry login, build credentials, artifacts, deployment, or automatic merge.
- Bound each job with a 45-minute timeout and cancel superseded runs for the same PR. Do not cache dependencies or retain generated data.
- Use standard `ubuntu-24.04` GitHub-hosted runners only; do not provision self-hosted or paid runner capacity.
- The production image command is a build-only local load on the ephemeral hosted runner; it never publishes or starts a service.

## Exact write set

- `.github/workflows/hosted-validation.yml`
- `Docs/Plans/HANDOFF-HOSTED-buddy-validation-ci.md`
- `Docs/Plans/HANDOFF-HOSTED-buddy-auth-packaging.md` — predecessor settlement only
- `.dockerignore` — expose only the synthetic statblock fixture required to typecheck the UI; keep it out of the application image
- `Dockerfile.production` — minimal build-time corrections required by verified CI failures
- `tests/test_hosted_auth.py` — isolate the mocked logout integration test with a synthetic `.test` origin
- `pyproject.toml` and `uv.lock` — only if exact Python 3.13 CI proves a locked dependency incompatibility; keep direct source pins intact

No runtime/auth routes, World policy, database schema, credentials, provider configuration, deployment, or retained data are changed. The only test fixture admitted to the Docker build context is synthetic and is excluded from the production application stage. If a concrete Python dependency or Dockerfile build issue blocks the requested checks, diagnose from the exact job log and make only the path-limited compatibility repair listed above; do not hide failures with broad skips or expand product behavior.

## Verification and remaining limits

The task directory is not a Git checkout, and its available source mirror is partial. A clean clone attempt failed because the sandbox could not resolve `github.com`; no escalation or alternate shell network path was attempted. No full-tree local tests or local image build are claimed. Complete-checkout evidence comes from the standard GitHub-hosted runner.

Run #5 (`40446428689`) completed successfully on code head `ea86bd8fd6ab7661701308dd311418b020734ac8`:

- **Python 3.13 auth/app integration tests:** success on Python 3.13.16. Patched Hermes preparation, locked dependency install, psycopg import, and the full-conftest selection all passed: 136 passed, 10 warnings, no skipped tests. This includes the expected fail-closed readiness assertion with no registered route policies.
- **Production Docker build:** success. The pinned Debian Trixie base and snapshot installed cleanly; `npm ci` and `npm run build` passed (Vite 6.4.2, 904 modules transformed); the production image exported and loaded to the ephemeral runner. No image push, service start, or deployment occurred. Docker emitted one non-fatal `SecretsUsedInArgOrEnv` build-check warning for the pre-existing non-secret `DMB_AUTH_MODE` setting; no repository secrets or provider credentials were configured.

The handoff-only commit recording these outcomes triggered run #6 (`40446773323`) at head `0b8dd83ef6c6c3764a14b76d015436494f7c45d5`; both jobs passed again on that exact head. Final run #7 (`40447059707`) passed both jobs on exact PR head `8530d1d00fdb81679bd91872af67c898b7c48f30`. PR #1814 is now merged at `c7f83c086d39e01f129fa7e31ef03262dbf65c91`; no production image was published and no deployment occurred.
