# HANDOFF — Buddy hosted deployment preparation

**Status:** ACTIVE local preparation; no push, PR publication, host change, activation, or merge
**Date:** 2026-10-27 UTC
**Owning repository:** Drakosfire/DungeonMindBuddy
**Topology:** Local serial successor to merged PR #1814
**Base:** main at 53d4bfd70bc599e18494e258f5c2b39acbf93c21
**Branch:** codex/buddy-hosting-deploy-prep-20261027
**Preserved checkpoint:** b99c05f5f3d52746ce933558f9649a955d288368, the earlier container-oriented draft. Keep it recoverable; current local changes supersede its deployment direction.

## Authority and intent

The user steered the proposed hosted Python runtime from containers to uv-managed per-service environments supervised by systemd, with the host's already-running Nginx and one included Buddy site fragment. The user then explicitly directed this revision to remain local-only: do not push, create a PR, update remote OverMind #58, or perform a live cutover.

This work prepares a Buddy-owned systemd unit/environment example, Nginx include, runbook, manifest, and provider-free tests. Existing Docker build support remains available for compatibility and CI; it is no longer the proposed canonical hosted path. No DMS repo changes are included.

## Boundaries and current facts

- Buddy has an existing committed uv.lock and pyproject Python requirement >=3.13,<3.14. This task does not install that runtime on a host, execute a service migration, or upgrade dependencies.
- The bounded inventory observed the current DMS container on Python 3.11.15. DMS is separately owned. Its uv/systemd transition, lock state, and any 3.11-to-3.13 compatibility work need a separate DMS-owned scope decision and test plan; leave its current container/service untouched.
- Each Python service target must use its own versioned source release, committed lock, uv environment, environment file, systemd unit, and rollback contract. Buddy's unit is the only unit prepared here; do not point DMS at Buddy's release or environment.
- Dependency installation happens only during explicit release preparation with the exact lock. systemd invokes the prepared release's absolute .venv/bin/uvicorn directly; no uv run/sync, network dependency resolution, migrations, or source checkout at service start.
- Buddy application files and WorldGraph files must be separate durable roots outside all versioned release directories. Exact paths and service-user access remain operator decisions. The unit template uses ProtectSystem=strict and leaves its placeholder ReadWritePaths inactive.
- Existing host Nginx is the only proxy. The Buddy file is a location include, not a new Nginx server/master process. Its loopback upstream port 8080 matches the Buddy service template but is only a candidate until a read-only port-collision check.
- World resolver registry remains empty/fail-closed. No ownership policy, retained World, credentials, database host/role, schema migration, backup restore, or data rollback is approved here.
- Preserve the existing Dockerfile, Compose and no-push CI. The optional Docker path still requires an actual published image digest; none exists. Do not invent one.

## Expected local write set

- deploy/production/systemd/buddy.service
- deploy/production/systemd/buddy.env.example
- deploy/production/nginx-buddy.conf
- deploy/production/compose.production.yaml — identify retained Docker path as optional
- scripts/verify_production_compose.py
- tests/test_production_deployment_config.py
- .github/workflows/hosted-validation.yml — retain its Python 3.13, no-push Docker, and synthetic config checks; no host deployment job
- Docs/Plans/HOSTED-READINESS-MANIFEST-2026-10-26.md
- Docs/Plans/HANDOFF-HOSTED-buddy-deployment-preparation.md
- Docs/Runbooks/RUNBOOK-HOSTED-deployment-preparation.md

Do not change application auth/routes, pyproject.toml, uv.lock, DMS source/configuration, database containers, provider code, secrets, host services, active Nginx configuration, DNS, TLS, firewall, or any external repository. The existing HANDOFF-HOSTED-buddy-validation-ci.md records the settled #1814 predecessor.

## Verification contract

1. Use synthetic/static tests only. Verify the systemd unit starts the prepared absolute .venv executable directly; no runtime dependency sync/resolution or migration.
2. Check that all credential/database values remain explicit placeholders and World access remains empty/blocked.
3. Check that persistent paths are placeholders outside versioned releases and the unit leaves writable exceptions inactive until operator selection.
4. Check that the Nginx snippet is a location include, contains no server block, retains streaming settings, and points to the exact same loopback port as systemd.
5. Preserve the existing provider-free rendered Compose validation and build-only Docker CI as compatibility checks. They must not pull/run the synthetic image or publish any image.
6. Record local Python 3.12 limitations accurately. Do not claim the Buddy Python 3.13 test suite or systemd-analyze verify passed unless those exact checks run successfully.
7. Keep migration downgrade fences. No database migration/restore or destructive rollback. No live host/systemd/Nginx action.

## Publication and external state

This revision is local-only by explicit instruction. The previous auto-review rejected the push for the earlier container proposal; that denial remains unresolved and must not be bypassed. Do not push this revised branch, create a draft PR, update #58, or use GitHub APIs to commit external refs. If a future user request reauthorizes publication, use the supported approval path and recheck the exact target/head before writing.

No reviewer or hosted CI result exists for this local architecture revision. Preserve exact findings and file/line context if a reviewer later identifies issues, so the original implementer can continue from a concrete handoff.

## Operator decisions before any future staging

- Confirm the selected Python and uv toolchain versions per service; review Buddy's existing Python 3.13/lock contract without assuming broad upgrades.
- With DMS owner, define a separate DMS release/lock/systemd compatibility path; decide whether Python 3.13 support is in scope only after compatibility evidence.
- Select durable roots and confirm service account, group, permissions, systemd write exceptions, and release/cache retention budget.
- Verify the loopback port is free and select the existing Nginx TLS-vhost include location. DNS/TLS, cookie delivery, and proxy reload each need separate authorization.
- Identify database owners/hosts/roles/migration heads and provide checksummed backup plus isolated restore evidence for APP-STATE and WorldGraph.
- Select the exact World and approve ownership/sharing policy; keep activation blocked until exact route resolvers are reviewed.
