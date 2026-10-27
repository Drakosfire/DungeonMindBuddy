# DungeonMindBuddy hosted readiness: provisional source manifest

**Snapshot:** 2026-10-27 UTC
**Status:** Local source and preparation evidence only. This is not a deployment manifest, full host audit, login proof, or readiness claim.

## Current source pins

| Repository | Exact main revision checked 2026-10-27 | Role and evidence |
|---|---|---|
| DungeonMindBuddy | 53d4bfd70bc599e18494e258f5c2b39acbf93c21 | Buddy API/frontend; Python >=3.13,<3.14 is the existing repo contract and uv.lock is committed |
| DungeonMindServer | 48b3f5181890ee3b3362cd12d9bfb8b41ddd65c1 | Existing DMS identity/session authority; PR #45 merged |
| DungeonMind | 4ccd39a1e433d81569d86c05273ac33ee8f27ef3 | In-process Core package and separate WorldGraph authority |
| DungeonOverMind | 2d14d6a32e4d72d16a94254af16d49921ae91688 | Cross-repository launch plan |
| LandingPage | 9e567007cd37867fffd95db8b229c77f5950616e | Existing public frontend; no change proposed |

Buddy #1817 merged at 7a6509b06b61c3ffba870dbc3f617e2a31d3a6e6. Buddy #1814's existing validation run #7 passed on head 8530d1d00fdb81679bd91872af67c898b7c48f30, including Python 3.13 auth/app tests and a no-push Docker build. DMS #45 merged at 48b3f5181890ee3b3362cd12d9bfb8b41ddd65c1. None of those source or CI references proves deployment.

## Canonical hosted deployment proposal

- The proposed canonical hosted runtime is a uv/systemd release: a versioned Buddy source tree with its own locked uv environment and a dedicated systemd unit. Dependency installation is an explicit release-preparation step using the existing committed uv.lock; the service starts the prepared release's absolute .venv/bin/uvicorn executable directly.
- Runtime start performs no dependency resolution, lockfile update, source checkout, build, or migration. Buddy data remains in separately selected durable roots outside all release directories.
- The host's existing Nginx remains the only proxy. deploy/production/nginx-buddy.conf is an included site-location fragment, not a second proxy or full server block.
- A future DMS uv/systemd release must use its own DMS repository, lock, venv, unit, tests, and rollback contract. The host inventory reported DMS Python 3.11.15 in its current container. DMS container replacement, uv migration, Python 3.13 compatibility, and dependency upgrades are not in this local Buddy preparation and require a separate scope decision.

## Retained Docker path and provenance

- Dockerfile.production, deploy/production/compose.production.yaml, and the build-only CI job remain as compatibility support. They are not the proposed canonical hosted path and are not deleted.
- The container deployment option remains available as optional compatibility support.
- The Dockerfile pins base images/build inputs and records OCI source/revision metadata when its required source argument is supplied. CI's production image job is build-only and checks the revision label; it does not publish or deploy.
- No registry digest for a production Buddy image has been obtained or verified. Do not invent one or treat a commit SHA, local image ID, or synthetic CI image as a registry digest.
- Compose requires an image name plus a sha256 digest for any future container use. It starts no database service. Do not silently reuse the host's network-adjacent PostgreSQL/pgvector or Mongo containers.

## Fail-closed World and database contract

- Hosted identity remains the existing DMS-managed population. No signup or owner-only gate is introduced.
- The production World resolver registry remains empty and fail-closed. Readiness remains blocked. Exact retained World selection and World/subject ownership and sharing policy are unresolved; do not infer ownership or enable World routes.
- Buddy APP-STATE and DungeonMind WorldGraph remain separate logical PostgreSQL authorities with separate database/role identities, migration histories, durable file roots, backup owners, and recovery procedures. No migration starts from systemd.
- The operator selects database hosts, names, credentials path, migration heads, and non-overlapping durable paths. Placeholders only are checked in.

## Bounded live inventory evidence and limits

The operator-provided 2026-10-27 report observed Ubuntu 24.04 on KVM/QEMU, 2 CPU, 7.8 GiB RAM, and 45 GiB free on a 96 GiB root filesystem. Eight containers were present. Buddy was absent from the inspected Docker inventory. Existing Nginx was running, but no Buddy virtual host was found in readable includes. The server-side resolver returned no Buddy hostname address; this is not authoritative/public DNS evidence.

The DMS image was observed only as local ID sha256:c2d79ea52c5e46e22c18b33f3833e0a4011bb2759ebc5e79e1bc21ebe6040d89, with no registry digest or OCI source/revision labels. The host checkout SHA is not image provenance. The DMS data-like mount was inside its Compose checkout and is not proven durable outside replaceable source. PostgreSQL/pgvector and Mongo containers in another Compose project shared networks with DMS, which establishes adjacency only, not application ownership.

The Store Generator health probe to loopback port 3001 was timing out with a 29,142 failure streak; no repair or broad log inspection was done. A bounded backup scan found OS package backup files in checked scopes and no matching application backup files in one scoped DMS data-root scan. This does not prove application backups are absent elsewhere. No isolated application restore was verified. The scan was bounded and unprivileged, not a full server audit.

## Local preparation verification

- The previous container-oriented preparation checkpoint is preserved at commit b99c05f5f3d52746ce933558f9649a955d288368. This local architecture revision is being tested in the same isolated Buddy worktree; it has not been pushed, published, or run on the host.
- The available task runtime has Python 3.12.3. Buddy's existing contract requires Python 3.13; this local work does not install Python, run uv sync, or migrate any service.
- Record tests for the systemd/uv contract and the retained synthetic Compose path on this exact local candidate. Do not report hosted CI or Compose rendering as passed unless an exact-head run exists.
- No database/provider call, credential creation, application migration, restore, DNS/TLS/Nginx activation, service start, deployment, or image publication is part of this preparation.

## Operator decisions and gates

1. Select the exact retained World and verified source; approve the World/subject ownership and sharing policy.
2. Identify separate APP-STATE/WorldGraph owners, databases, roles, migration heads, and recovery procedures.
3. Select non-overlapping durable roots outside versioned releases, verify service-user permissions, and agree on release/uv-cache retention and disk budget.
4. Confirm Buddy's existing Python 3.13 and uv.lock compatibility in an exact-release test. Do not upgrade dependencies without an approved scope decision.
5. Decide DMS's uv/systemd transition and any Python 3.11→3.13 compatibility work with its owner. Keep its current service untouched until that separate path is tested and approved.
6. Verify the candidate loopback port is unused; choose the existing Nginx include location and separately review DNS/TLS/cookie behavior. Do not create a second proxy.
7. Prove checksummed backups and isolated restores for both authorities. Respect downgrade fences; code release rollback does not reverse schema/data state.
8. Preserve fail-closed World authorization until the World, policy, and exact route resolvers are separately reviewed.

See RUNBOOK-HOSTED-deployment-preparation.md for the proposed release procedure and inventory limitations.
