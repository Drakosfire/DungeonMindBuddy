# HANDOFF-HOSTED-buddy-auth-packaging

**Status:** ACTIVE — authorized bounded implementation lane; not a deployment or World-policy authorization  
**Date:** 2026-10-27 UTC  
**Owning repository:** Drakosfire/DungeonMindBuddy  
**Topology:** serial; one implementation PR, #1802  
**PR:** https://github.com/Drakosfire/DungeonMindBuddy/pull/1802

## Authority and pinned refs

- Architecture and sequencing reference: DungeonOverMind PR #58, `Docs/Plans/PLAN-buddy-hosted-readiness-and-launch.md`, pinned snapshot head `9c8e27a9372f14c48d090b385e93e9c987c22ca6`. That plan is planning-only and is not itself permission to edit runtime code. The user separately authorized this bounded auth-and-packaging PR and the follow-up fixes recorded in this lane.
- Current Buddy default branch at re-anchor: `main@86d1857645a7c19f395997f144b2d638f11de683`.
- PR #1802 previously used base `c5250824f3c3d5b4bb33d1897914158a3ee3d8fa` and head `a74d34dc61680c62f4a6a948744af6142d1f5c68`. Current main was 29 commits ahead with no changed paths overlapping the PR. This update re-anchors the implementation branch while preserving both histories; it does not overwrite current-main work.
- Related Buddy PRs #1512 and #1514 remain open and unchanged. Their unique route inventory, cookie-Origin handoff, and proposed World-policy design are not duplicated or adopted as policy here. DungeonOverMind #20, #39, and #58 are also left unchanged.

## Active objective

Implement and document a fail-closed hosted authentication and production-packaging foundation for `buddy.dungeonmind.net` using DungeonMindServer's existing identity and existing managed user cohort. Keep Buddy's Python runtime independent at Python 3.13, package the built SPA with a private API and streaming-aware proxy template, require explicit production configuration, preserve health/readiness behavior, and document the two logical PostgreSQL authorities and durable external roots. Startup migrations, live-service changes, and retained-data migrations are out of scope.

The hosted boundary must reject API requests unless they use the existing DMS principal and a reviewed server-side resource-to-World binding. Each future World route requires a resolver registered for its exact HTTP method and path. A client selector is only a consistency check. Production currently registers zero World resolvers; all hosted World operations therefore remain denied and readiness remains blocked. This work does not assign ownership to existing Worlds or choose an Elderwyld World.

For resolver-enabled routes, an empty request body or strict UTF-8 JSON is accepted. JSON media types are `application/json` and `application/*+json`; the body cap is 1 MiB. Oversized, malformed, duplicate-key, unsupported-encoding, non-JSON, and non-object/list JSON bodies fail before the resolver or handler. Future multipart or other body formats require an explicit reviewed route-specific validator before a route can be enabled.

Local operator access requires both `DMB_DEPLOYMENT_ENVIRONMENT=local` and `DMB_AUTH_MODE=local_operator`, a loopback peer, and no forwarded-proxy metadata. Missing or invalid mode fails with 503. Manual Uvicorn instructions must set the two values and bind to `127.0.0.1`; the `./run` launcher remains the documented local option.

## Exclusive expected-path lease

This ACTIVE serial lane may change only these DungeonMindBuddy paths:

- `.dockerignore`
- `Dockerfile.production`
- `Docs/Plans/HANDOFF-HOSTED-buddy-auth-packaging.md`
- `Docs/Plans/HOSTED-READINESS-MANIFEST-2026-10-26.md`
- `Docs/Plans/RUNBOOK-HOSTED-read-only-host-inventory.md`
- `apps/live-control-ui/README.md`
- `apps/live-control-ui/src/App.tsx`
- `apps/live_control_server/main.py`
- `apps/live_control_server/services/agent_graph_auth.py`
- `apps/live_control_server/services/hosted_auth.py`
- `deploy/production/compose.production.yaml`
- `deploy/production/nginx-buddy.conf`
- `run`
- `scripts/host_inventory.sh`
- `tests/test_agent_graph_auth.py`
- `tests/test_hosted_auth.py`

No other repository, database, provider, host, credential, DNS, TLS, firewall, proxy, account, or persistent data may be changed in this lane. Do not install software globally or retry denied Docker access. Use synthetic fixtures only. Do not merge the PR; the parent owns any merge decision.

## Verification contract

- Exercise signed-out and permitted DMS identities, exact Origin handling, local mode boundaries, forwarded-proxy denial, path variants, exact resolver binding, confused-deputy selector mismatch, missing/ambiguous/erroring resolvers, JSON and `+json` binding, and malformed/oversized/unsupported body rejection before effects.
- Run focused pytest with the repository's full conftest and the pinned Core/GenerationEngine overlays available in the task workspace. Report import/environment failures separately; do not evade the full conftest or claim integration success from helper-only tests.
- Run Ruff on changed Python files, `bash -n scripts/host_inventory.sh`, and the frontend production build after UI changes. Docker image build is optional only when the approved Docker socket is available; no escalation or retry after denial.
- Publish only to PR #1802. Recheck current main and path overlap, preserve its commits and current-main history, verify the exact remote head and changed-file list, and report workflow runs/status checks accurately. Keep the PR open; do not merge, deploy, or mark live readiness.

## Verification and current limits

- Final focused selection with the repository conftest and pinned Core/GenerationEngine overlays: 24 passed, 12 deselected. Four focused auth modules together: 128 passed; 8 app-import failures caused by the cached Python 3.12 psycopg package lacking a compatible pq wrapper/libpq (three app logout/readiness/router tests and five graph-auth route integration tests). Buddy declares Python 3.13, so the full app integration suite remains unverified.
- Ruff 0.15.7 passed on `hosted_auth.py` and `test_hosted_auth.py`. `bash -n scripts/host_inventory.sh` passed. `npm run build` passed after the UI copy changes, transforming 902 modules; Vite emitted its existing non-fatal static/dynamic import warning for `connectedPageApi.ts`.
- The task mirror is partial and is not the full latest-main tree. The changed manual-entrypoint files were verified against current main and had no changes between the original PR base and the current main re-anchor. Repository test/build results do not establish the whole updated main tree or live deployment.
- Earlier `uv sync --locked --offline` could not prepare an environment because generated `out/hermes-agent` is absent from the mirror and the available uv cache is read-only. Docker image build remains unbuilt because the approved Docker socket was denied; do not retry or elevate.
- No workflow runs or commit status checks were present on the pre-reanchor PR head. Recheck after publishing. No live host inventory, database, provider, or retained World was used.

## Future World selection and access policy — BLOCKED

This blocked follow-on requires the operator to select the exact Elderwyld World and source, and a verified procedure for assigning existing retained Worlds to DMS subjects. It must preserve the existing DMS-managed population; do not add an owner-only population gate. Before enabling any World route, review its read/write/media/history/job/streaming/provider side effects and implement a trusted resource-to-World resolver plus body validation for its actual request format. Do not infer or migrate ownership. The future policy is not an active write lease and this handoff does not approve production route activation.

Before any staging work, the operator must also provide a sanitized read-only host inventory and establish deployed versions, capacity, provider limits, separate application-state and WorldGraph authorities, durable media/artifact/recap/session roots, migration heads, backup/restore evidence, DMS login-return behavior, and browser cookie delivery. This repository PR does not establish those facts or live-host readiness.
