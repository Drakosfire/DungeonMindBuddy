# DungeonMindBuddy hosted readiness: provisional source manifest

**Snapshot:** 2026-10-27 UTC
**Status:** Source and preparation evidence only. This is not a deployment manifest, host audit, login proof, or readiness claim.

## Current source pins

| Repository | Exact main revision checked 2026-10-27 | Role and evidence |
|---|---|---|
| DungeonMindBuddy | 53d4bfd70bc599e18494e258f5c2b39acbf93c21 | Python 3.13 Buddy API and bundled frontend. PR #1817 is merged at 7a6509b06b61c3ffba870dbc3f617e2a31d3a6e6. |
| DungeonMindServer | 48b3f5181890ee3b3362cd12d9bfb8b41ddd65c1 | Existing DMS identity/session authority; PR #45 is merged at this revision. |
| DungeonMind | 4ccd39a1e433d81569d86c05273ac33ee8f27ef3 | DungeonMind Core is an in-process package; WorldGraph is a distinct authority. |
| DungeonOverMind | 2d14d6a32e4d72d16a94254af16d49921ae91688 | Cross-repository launch plan owner. PR #58 is the existing draft plan PR and should receive the resulting exact Buddy candidate/CI checkpoint. |
| LandingPage | 9e567007cd37867fffd95db8b229c77f5950616e | Existing public frontend; no change proposed. |

## Related work preserved

- Buddy #1814 merged at c7f83c086d39e01f129fa7e31ef03262dbf65c91; its validation workflow's run #7 passed on exact head 8530d1d00fdb81679bd91872af67c898b7c48f30. Buddy #1817 merged at 7a6509b06b61c3ffba870dbc3f617e2a31d3a6e6. DMS #45 merged at 48b3f5181890ee3b3362cd12d9bfb8b41ddd65c1. None of these merge SHAs proves deployment.
- Buddy #1512 and #1514 remain separate and unchanged. Do not adopt #1514's proposed creator-only rule. Preserve the existing DMS-managed population and do not add an owner-only population restriction.
- DungeonOverMind #20, #39, and #58 remain separate plan work. PR #58 remains a draft.

## Identity, routes, and World access

- Hosted identity uses the existing DMS-managed principal. The sign-in/return work does not change DMS's provider or create another user population.
- The production World resolver registry remains empty and fail-closed. Readiness stays blocked and World/API operations remain denied until exact route resolvers and their side effects are reviewed.
- Exact retained World selection and World/subject ownership and sharing policy are unresolved. Do not infer ownership from creator identity, database rows, or a client selector. DMB_HOSTED_WORLD_ACCESS_JSON remains a hold placeholder.
- Do not add signup, a new owner-only restriction, or a readiness bypass. A user-selected World identifier is only a consistency check after a trusted resource resolver establishes the binding.

## Package and storage contract

- The production package is the existing Buddy Dockerfile, Compose service, and Nginx template. DungeonMind Core remains in-process; no parallel Core service is needed.
- Buddy's Dockerfile pins Node, Python 3.13, uv, Debian snapshot build inputs, and locked npm/uv dependencies. The source-revision build argument and OCI source/revision labels must identify the exact source built. CI builds locally with no push.
- Compose requires BUDDY_IMAGE_NAME and a 64-character BUDDY_IMAGE_DIGEST and constructs the immutable @sha256: reference. No registry digest for a production Buddy image has been created or verified. Do not invent one or treat a source SHA or local image ID as a registry digest.
- Buddy application state and DungeonMind WorldGraph require separate PostgreSQL databases/roles, DSNs, migration owners, and non-overlapping durable file roots. Compose has one Buddy service only; it does not start database services. No startup migration is configured.
- Keep Nginx request/response buffering disabled and the existing long read timeout for streaming.

## Bounded live inventory — 2026-10-27

The operator-provided bounded read-only report observed Ubuntu 24.04 on KVM/QEMU, 2 CPU, 7.8 GiB RAM, and 45 GiB available on a 96 GiB root filesystem. Eight containers were present. Buddy was absent from the inspected Docker inventory. No Buddy vhost was found among readable Nginx includes, and the host's resolver returned no Buddy hostname address; this is not evidence about authoritative/public DNS.

The running DMS image was observed only as local image ID sha256:c2d79ea52c5e46e22c18b33f3833e0a4011bb2759ebc5e79e1bc21ebe6040d89. It had no registry repository digest or OCI source/revision labels. The host's Compose checkout SHA is not image provenance. PostgreSQL/pgvector and Mongo containers in another Compose project shared Docker networks with DMS, but this establishes adjacency only; their application ownership was not verified. Their use by Buddy or WorldGraph must not be assumed.

The Store Generator health probe to loopback port 3001 was timing out with a 29,142 failure streak; no repair or broad log inspection was performed. The bounded backup scan found OS-package backup files in checked scopes and no matching application backup files within one scoped DMS data-root scan. It did not verify every possible backup location or establish that application backups are absent. No application restore evidence was verified. The DMS data-like mount was inside its Compose checkout and is not proven durable outside a replaceable checkout.

This was a bounded, unprivileged inventory, not a full server audit. Runtime environment values, database rows, and broad logs were not read. No database query, migration, restore, DNS change, TLS change, proxy activation, or service change is authorized here.

## Preparation verification status

- Buddy #1814's Python 3.13 auth/app test and no-push image build passed in GitHub Actions run #7 at exact head 8530d1d00fdb81679bd91872af67c898b7c48f30. The run reported 136 passed, 10 warnings, no skipped tests; the production Docker build passed with a local ephemeral image. It does not supply a production registry digest.
- The deployment-preparation draft adds a synthetic Compose contract check and local-only source-revision image metadata. Record its exact candidate SHA and exact PR workflow results here after publication; do not report unrun jobs as passed.
- The available task runtime has Python 3.12, while Buddy requires Python 3.13. Its Docker Compose plugin and pytest are unavailable locally. Use the existing provider-free hosted workflow for the complete Python 3.13 and Compose contract checks if local prerequisites remain unavailable.
- No real DB, data restore, OAuth/provider call, secret, server, DNS, proxy, migration, deployment, or image publication is part of this preparation.

## Operator decisions and evidence gates

1. Select the exact retained World and verified source.
2. Approve World/subject ownership and sharing policy and record the retained-World assignment procedure.
3. Name separate owners, hosts, databases, roles, and migration heads for Buddy APP-STATE and DungeonMind WorldGraph.
4. Select existing non-overlapping durable roots outside replaceable checkouts and verify access for runtime UID 10001.
5. Publish the exact reviewed Buddy source to an authorized registry, record its immutable digest, and verify source/revision labels. No digest exists yet.
6. Supply database credentials only through an approved secret mechanism; never add real values to Compose, reports, logs, or this repository.
7. Produce checksummed backups and fingerprints for both authorities, then verify them in new isolated empty targets using their owner runbooks. Do not restore over a live authority, delete volumes, or cross a migration downgrade fence as a rollback shortcut.
8. Separately review host capacity, DMS image provenance, durable DMS mounts, Nginx/TLS/DNS, cookie delivery, deployment/rollback ownership, provider limits, and the Store Generator health failure if relevant.
9. Review exact method/path World resolvers and readiness behavior against the selected World and approved policy. Keep activation blocked while the resolver registry is empty.

See RUNBOOK-HOSTED-deployment-preparation.md for the preparation checks and the boundaries of the host inventory.
