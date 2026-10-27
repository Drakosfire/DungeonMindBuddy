# Buddy hosted deployment preparation

**Status:** Preparation only; no activation or launch authorization
**Snapshot:** 2026-10-27 UTC
**Target:** buddy.dungeonmind.net through the existing DMS-managed user population

This runbook proposes a host-native runtime using one versioned release and one uv environment per Python service, supervised by systemd. The existing host Nginx remains the only proxy; Buddy supplies a site-location include for its already-running Nginx. Existing Docker build and deployment support is retained for compatibility and build-only CI, but it is no longer the proposed canonical hosted path.

This is a local preparation contract. It does not provision a host, switch a service, install dependencies on the host, activate a route, create credentials, choose a World, run migrations, restore data, or contact a provider.

## Current source and runtime evidence

| Repository | Exact main revision checked 2026-10-27 | Role |
|---|---|---|
| DungeonMindBuddy | 53d4bfd70bc599e18494e258f5c2b39acbf93c21 | Buddy API and bundled frontend; Python constraint is >=3.13,<3.14 and uv.lock is committed |
| DungeonMindServer | 48b3f5181890ee3b3362cd12d9bfb8b41ddd65c1 | Existing DMS identity/session authority; PR #45 merged |
| DungeonMind | 4ccd39a1e433d81569d86c05273ac33ee8f27ef3 | In-process Core package and separate WorldGraph authority |
| DungeonOverMind | 2d14d6a32e4d72d16a94254af16d49921ae91688 | Cross-repository launch plan |
| LandingPage | 9e567007cd37867fffd95db8b229c77f5950616e | Existing public frontend; no change proposed |

Buddy #1817 is merged at 7a6509b06b61c3ffba870dbc3f617e2a31d3a6e6. DMS #45 is merged at 48b3f5181890ee3b3362cd12d9bfb8b41ddd65c1. Buddy #1814's existing Python 3.13 tests and build-only image job passed at its exact recorded head. Those results are source/CI evidence, not proof that the merged changes are deployed.

The bounded 2026-10-27 inventory observed the DMS container running Python 3.11.15. Its local image ID was sha256:c2d79ea52c5e46e22c18b33f3833e0a4011bb2759ebc5e79e1bc21ebe6040d89, without a registry digest or OCI source/revision label. The host Compose checkout SHA is not image provenance. Buddy was absent from the inspected Docker inventory. This report does not establish the running DMS image's source revision.

## Proposed canonical Python service layout

Each Python service must have its own versioned release directory, committed lock, uv-managed virtual environment, environment file, and systemd unit. Do not share a virtual environment, lockfile, or writable release tree between Buddy and DMS.

For Buddy, the existing committed uv.lock and pyproject Python constraint are the dependency contract. A separately reviewed release-preparation step installs the exact lock into that release's .venv, using the repository's pinned patched-Hermes preparation and a reviewed uv/Python toolchain. The intended sequence is conceptually:

1. Check out the exact Buddy commit into a new immutable directory such as /opt/dungeonmindbuddy/releases/<commit-sha>.
2. Verify the checkout and lockfile match the recorded source revision; do not edit or regenerate uv.lock during deployment preparation.
3. Run the repository's pinned Hermes source preparation, then run uv sync --locked --no-dev --no-editable with the selected Python 3.13 interpreter from that release directory. The existing project toolchain pin is uv 0.13.5 in Dockerfile.production and CI; do not change it here. This is the explicit dependency installation step; it may access package/source registries but must not call application providers or create credentials.
4. Verify the prepared interpreter, imports, lock state, and the exact release's tests before considering a service switch.
5. Point /opt/dungeonmindbuddy/current to the accepted release only under a separate operator-approved change.

At service start, systemd executes the absolute uvicorn entry point inside current/.venv directly. There is no dependency resolution at startup: the service must not invoke uv run, uv sync, source checkout, build hooks, or database migrations. A failed/missing release fails to start; it does not pull dependencies or substitute another release.

The included buddy.service is a unit template only. It runs as a dedicated non-root dungeonmindbuddy account, reads /etc/dungeonmindbuddy/buddy.env, and binds to 127.0.0.1:8080. ProtectSystem=strict leaves writes disabled. The commented ReadWritePaths line must remain inactive until the operator selects existing, non-overlapping durable roots outside the release tree and replaces the placeholders. The installed environment file must be root-owned and mode 0600; the system manager reads it before passing values to the service. Create no directory or account as part of this preparation.

Buddy's DMB_MANAGED_WORLD_DATA_ROOT, DMB_ARTIFACT_DATA_ROOT and DUNGEONMIND_LIVE_SESSION_DIR must live below its selected Buddy durable root. DUNGEONMIND_WORLD_GRAPH_ROOT must live under a separate selected WorldGraph file root. The file deploy/production/systemd/buddy.env.example contains only placeholders and candidate names. Use a protected, operator-approved secret mechanism for the installed environment file; never commit its populated contents.

The architecture target is also to run DMS from its own DMS-owned versioned release, committed lock, uv environment and systemd unit. A separate local DMS branch now prepares a Python 3.11 unit and locked-release runbook; it does not change this repository's source or the current container. The observed DMS image reports Python 3.11.15. Any move to Python 3.13, dependency upgrades, or lock rewrite remains a separate DMS compatibility decision. Do not stop or change the current container as part of this preparation.

## Retained Docker compatibility path

Dockerfile.production and deploy/production/compose.production.yaml remain available and continue to receive the build-only CI checks. This is the optional container deployment option, not the proposed canonical hosted path. If that option is later selected, the Compose file still requires BUDDY_IMAGE_NAME plus BUDDY_IMAGE_DIGEST, and deploy/production/compose.production.yaml keeps DUNGEONMIND_WORLD_GRAPH_FILE_ROOT separate from the Buddy data root. No production registry digest has been published or verified. CI's synthetic registry.invalid image is configuration-only and is never pulled, published, or activated.

## One existing host Nginx

The host inventory found an existing Nginx service and readable include chain, but no Buddy virtual host in those readable includes. The server-side resolver returned no Buddy address; that is not evidence about authoritative/public DNS. The proposed deploy/production/nginx-buddy.conf remains a location include for the existing TLS virtual host, not a complete server block and not a second Nginx service or container.

The include forwards to 127.0.0.1:8080, matching the Buddy systemd unit. That port is inherited from the prior Compose host mapping and is only a candidate: verify it is unused before any separately approved service change. If the operator chooses another free loopback port, update both the unit and include together and rerun the consistency test. Keep request and response buffering disabled and the 3600-second read timeout for HTTP streaming.

Installing the include, changing Nginx configuration, reloading Nginx, adding a virtual host, issuing TLS, or changing DNS are separate live security/network actions and are not authorized here. Do not install a second proxy.

## Databases and durable data

Buddy APP-STATE and DungeonMind WorldGraph remain separate logical authorities with separate credentials, migration histories, backup owners, and recovery procedures:

* DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL — Buddy APP-STATE.
* DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL with DUNGEONMIND_WORLD_GRAPH_AUTHORITY=dungeonmind — WorldGraph authority.

The example DSNs contain role, secret, host and database placeholders only. Identify each owner, database, role and migration head before any approved deployment. The authorities may share a physical PostgreSQL server only if their logical databases, credentials, histories, backup/restore owners and recovery procedures remain separate. Do not silently reuse the server's network-adjacent PostgreSQL/pgvector or Mongo containers; their relation to these authorities was not established. This preparation neither touches nor migrates any existing database container.

All durable Buddy and WorldGraph data roots must be outside /opt/dungeonmindbuddy/releases and outside any DMS release directory. Select roots that do not overlap; verify host ownership and access for the service user; retain backups separately from the host. Do not put data, caches, generated files, runtime secrets or release-specific state inside a directory that may be replaced during a source release update.

The unit has no migration command. Record both current and candidate schema heads under their owners before any separately approved migration. Do not use startup, service restart, code rollback or a source symlink switch to reverse schema state. Honor migration downgrade fences; never drop a database/schema/volume or restore over the live authority as a rollback shortcut.

## Backup and isolated restore evidence

The bounded inventory verified neither application backup coverage nor an isolated restore. Its scoped metadata scan found OS package backup files in /var/backups and no matching application backup files in one checked DMS data-root scope. This does not prove application backups are absent elsewhere. The dpkg database timer is not an application backup. No restore was attempted here.

Before staging, each authority owner must identify its supported backup procedure and capture:

1. A timestamped backup plus cryptographic checksum.
2. A schema/migration fingerprint and authority identity, with DSNs and secrets redacted.
3. Evidence the backup is stored separately from the source host and database.
4. A restore into a new isolated empty target that cannot receive traffic or overwrite the source.
5. Post-restore integrity/fingerprint checks and an operator witness with source and target revisions.

Use each owner repository's recovery procedure. Do not restore against a live authority, destroy a volume to simulate rollback, replay user/provider actions, or claim recovery from a schema check alone. If isolated targets or matching integrity evidence are unavailable, recovery remains unproven and activation stays blocked.

## Bounded host observations and their limits

The operator-provided read-only snapshot recorded Ubuntu 24.04 on KVM/QEMU, 2 CPUs, 7.8 GiB RAM, and 45 GiB available on a 96 GiB root filesystem. DMS and Store Generator containers were present; Buddy was absent from the inspected Docker inventory. No Buddy vhost was found among readable Nginx includes. The host resolver returned no address for the Buddy hostname, not a public DNS determination. The Store Generator loopback port 3001 health probe had a 29,142 timeout failure streak; no repair was attempted.

PostgreSQL/pgvector and Mongo containers in another Compose project shared Docker networks with DMS, which establishes network adjacency only. No application ownership, database contents, or migration tables were inspected. The DMS data-like mount was inside its Compose checkout and is not proven durable outside replaceable source. The scan was bounded and unprivileged, not a full server audit; it did not inspect environment values, broad logs, or every backup location. Do not claim backups are absent.

## Python and dependency compatibility boundary

Buddy already declares Python >=3.13,<3.14 and has a committed uv.lock; using that existing contract in its isolated release is the proposed starting point. This preparation did not run uv sync or install Python on the host. It does not authorize changing Python versions or broad dependency upgrades.

DMS was observed as Python 3.11.15 in its current container. Its separate local preparation uses its own committed lock and Python 3.11 systemd template. This does not move or stop the current container. Python 3.13 or broad dependency/lock changes still require a separate compatibility scope and evidence. Keep the DMS code, environment and rollback contract in its owning repository.

The current Buddy project lists pytest and Ruff in its main dependency set, so uv sync --no-dev does not omit them. Moving tools into a development-only dependency group would change pyproject.toml and uv.lock; that dependency-hygiene change is not included or authorized by this preparation.

## Gates before a later staging decision

1. Select the exact retained World and verified source; approve World/subject ownership and sharing policy while retaining the existing DMS-managed population.
2. Identify independent APP-STATE and WorldGraph owners, database names/roles, migration heads, credentials path, and recovery procedures.
3. Select existing non-overlapping durable roots and confirm service-user access. Decide how much disk to reserve for versioned releases, uv cache, logs, and rollback retention; do not delete old releases or data as part of preparation.
4. Review Buddy release preparation with the exact source commit, committed lock, patched-Hermes source, Python/uv versions, tests, and source revision evidence.
5. Review DMS's separately prepared Python 3.11 uv/systemd contract with its owner; decide any Python-version or dependency/lock compatibility work separately.
6. Review free loopback port, existing Nginx include location, DNS/TLS/cookie behavior, deployed DMS provenance, host capacity, deployment and rollback owner, and Store Generator health if it is part of the planned experience.
7. Prove isolated backups/restores for both authorities and review downgrade fences.
8. Keep the World resolver registry empty and readiness blocked until exact route resolvers and the approved World policy have separate review.

The retained Dockerfile and Compose path remain available for compatibility and no-push CI; choosing Docker for a future release is an explicit operator architecture decision, not the proposed canonical path in this runbook. No launch gate is marked passed by this document.
