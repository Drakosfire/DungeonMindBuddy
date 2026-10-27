# Buddy hosted deployment preparation

**Status:** Preparation only; no activation or launch authorization
**Snapshot:** 2026-10-27 UTC
**Target:** buddy.dungeonmind.net through the existing DMS-managed user population

This runbook reconciles the existing Buddy production package and proxy template. It defines the configuration contract and evidence still required before a separate staging or launch decision. It does not provision a host, activate a route, create credentials, select a World, run migrations, or contact a provider.

## Candidate source and image provenance

The current reviewed source candidates are:

| Repository | Exact main source revision | Role |
|---|---|---|
| DungeonMindBuddy | 53d4bfd70bc599e18494e258f5c2b39acbf93c21 | Python 3.13 Buddy API and bundled frontend |
| DungeonMindServer | 48b3f5181890ee3b3362cd12d9bfb8b41ddd65c1 | Existing DMS identity/session authority; PR #45 merged |
| DungeonMind | 4ccd39a1e433d81569d86c05273ac33ee8f27ef3 | In-process Core package and separate WorldGraph authority |
| DungeonOverMind | 2d14d6a32e4d72d16a94254af16d49921ae91688 | Cross-repository launch plan |
| LandingPage | 9e567007cd37867fffd95db8b229c77f5950616e | Existing public frontend; no changes proposed |

Buddy #1817 is merged at 7a6509b06b61c3ffba870dbc3f617e2a31d3a6e6. The Buddy source has pinned build inputs, and this preparation adds source-revision metadata to locally built images. The CI image build is build-only and does not publish. No production Buddy registry digest exists yet. Do not treat a source SHA, a local image ID, or a synthetic CI image reference as a registry digest.

The bounded 2026-10-27 host inventory observed the running DMS image only as the local ID sha256:c2d79ea52c5e46e22c18b33f3833e0a4011bb2759ebc5e79e1bc21ebe6040d89. It had no registry repository digest or OCI source/revision label. The host checkout revision is not proof of that image's source. Buddy was absent from the inspected Docker inventory. The report did not establish that the merged DMS or Buddy changes are deployed.

## Production Compose contract

The existing deploy/production/compose.production.yaml remains a single Buddy service package. DungeonMind Core remains in-process. Do not add a parallel database stack or reuse the host's network-adjacent PostgreSQL/pgvector or Mongo containers: their application ownership, schemas, and migration heads were not verified.

At any later operator-approved staging preparation, set BUDDY_IMAGE_NAME to the published registry image name and BUDDY_IMAGE_DIGEST to its verified 64-character sha256 hex digest. Compose constructs the immutable @sha256: reference, and both values are required with no defaults. The API binds only to 127.0.0.1 on the host. Keep the existing Nginx streaming behavior in deploy/production/nginx-buddy.conf, including disabled request/response buffering and its 3600-second read timeout.

Two independent PostgreSQL authorities are required:

* DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL for Buddy application state.
* DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL for the DungeonMind WorldGraph authority, with DUNGEONMIND_WORLD_GRAPH_AUTHORITY explicitly set to dungeonmind.

Use separately owned logical databases and roles. The database coordinates and roles must identify distinct authorities, as enforced by the provider-free contract check. They may share a physical PostgreSQL server only if the databases, credentials, migration histories, backup/restore owners, and recovery procedures remain separate. Never point either setting at an unidentified existing host database. Keep credentials as operator-supplied placeholders such as postgresql://<dedicated-role>:<secret>@<dedicated-host>:5432/<dedicated-database>; do not commit values or place them in logs.

Buddy application files and WorldGraph files have independent durable host roots: BUDDY_PERSISTENT_ROOT and DUNGEONMIND_WORLD_GRAPH_FILE_ROOT. Select existing directories outside the checkout, ensure they do not overlap, and grant the container UID 10001 only the needed access. Compose uses bind.create_host_path=false so a typo cannot silently create an empty directory. The application-state root holds managed-world, artifact, and session paths; the WorldGraph root holds only its dedicated graph files. Verify the application path semantics with the exact candidate release before staging.

The runtime does not migrate on startup. Record each authority's current and target migration heads before any separately approved change. A mismatch or an unclear migration owner blocks activation. Respect each authority's downgrade fence: do not run reverse migrations, drop schemas/volumes, or roll back across an irreversible migration as a recovery shortcut.

## World access remains fail-closed

The Buddy production World resolver registry remains empty. Readiness must remain blocked and World/API operations must remain denied until exact route resolvers and their side effects are reviewed. DMB_HOSTED_WORLD_ACCESS_JSON is a required hold placeholder; do not populate it during this preparation. Do not infer ownership from creator identity, database contents, or client selectors.

The operator has not selected the exact retained World to serve or approved a World/subject ownership and sharing policy. Preserve the existing DMS-managed population; no extra owner-only population restriction is approved. Before route activation, document the selected World, its source, the approved access policy, and the procedure for mapping retained Worlds to DMS subjects. Then review each route's reads, writes, media, history, jobs, streaming, and provider side effects and register a resolver for its exact method and path. A client World selector may only be a consistency check.

## Backup and isolated restore evidence

The live inventory verified neither application backup coverage nor an isolated restore. Its bounded metadata scan found OS package backup files in /var/backups and no matching application backup files in the specific checked DMS data-root scope. This does not show that backups are absent elsewhere. The dpkg database timer is not an application backup. No real restore was attempted for this preparation.

Before staging, the separate owners of APP-STATE and WorldGraph must identify their supported backup procedures and capture for each authority:

1. A timestamped backup produced from the intended source and its cryptographic checksum.
2. A schema/migration fingerprint and the source authority identity, with DSNs and secrets redacted.
3. Evidence that the backup artifact is stored separately from the host and source database.
4. A restore into a new, isolated, empty target that cannot route traffic or overwrite the source.
5. Post-restore fingerprint/content-integrity checks and an operator witness recording the exact source/target revision and result.

Use the owning repository's recovery procedure and its downgrade fences. Do not run a restore against the live authority, destroy a volume to simulate rollback, replay user/provider actions, or claim recovery from a successful schema check alone. If the owners cannot produce a safe isolated target and matching integrity evidence, backups and recovery remain unproven and activation stays blocked.

## Bounded host inventory evidence and limits

The operator-provided read-only inventory snapshot for 2026-10-27 recorded Ubuntu 24.04 on KVM/QEMU, 2 CPUs, 7.8 GiB RAM, and 45 GiB available on a 96 GiB root filesystem. DMS and Store Generator containers were present. Buddy was absent; no buddy.dungeonmind.net Nginx vhost was found among readable includes, and that host's resolver returned no address. This is not authoritative public DNS evidence. The Store Generator health probe to loopback port 3001 was timing out with a 29,142 failure streak; no repair was attempted.

The scan was bounded and unprivileged. It did not inspect runtime environment values, query databases, inspect broad logs, verify all backup locations, or establish application database ownership. PostgreSQL/pgvector and Mongo were only observed as containers on a separate Compose project sharing networks; network adjacency is not evidence that either is an application authority. The DMS data-like mount was inside its Compose checkout and is not proven durable outside a replaceable checkout. Do not describe this report as a full server audit or as proof that backups do not exist.

## Launch gates and operator decisions

Keep launch and activation blocked until every item below has a named owner and recorded evidence:

1. Choose the exact retained World and its verified source; approve the World/subject ownership and sharing policy while retaining the DMS-managed population.
2. Identify dedicated owners, hosts, database names, roles, and migration heads for APP-STATE and WorldGraph. Supply credentials only through the operator's approved secret mechanism.
3. Select non-overlapping durable host roots outside replaceable checkouts and prove ownership/permissions for the Buddy runtime UID.
4. Publish the reviewed Buddy source as an immutable registry image, record its registry digest, verify OCI source/revision labels, and bind the release to the exact Buddy revision. Source pins and a no-push local CI build are not this evidence.
5. Complete separately witnessed, isolated restore checks for both authorities, and confirm the migration downgrade fences and recovery owners.
6. Review the live host's capacity, DMS image provenance, Nginx/TLS route, DNS, cookie delivery, and deployment procedure under a separate approved change. The bounded inventory leaves these incomplete; investigate the Store Generator health failure if it is part of the planned experience.
7. Review provider limits and incident/rollback ownership. Do not reverse migrations across a downgrade fence or delete persistent storage during rollback.
8. Review the route resolver set and readiness behavior with the exact selected World and approved access policy; readiness stays blocked while the production registry is empty.

This checklist is preparation evidence only. It is not a deployment authorization or a claim that any gate has passed.
