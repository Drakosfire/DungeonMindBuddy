# HANDOFF — Buddy hosting deployment preparation

**Status:** ACTIVE — bounded preparation only; no merge, deployment, activation, database/credential mutation, or live server action
**Date:** 2026-10-27 UTC
**Owning repository:** Drakosfire/DungeonMindBuddy
**Topology:** Serial successor to merged PR #1814
**Base:** main at 53d4bfd70bc599e18494e258f5c2b39acbf93c21
**Branch:** codex/buddy-hosting-deploy-prep-20261027
**Cross-repository plan:** DungeonOverMind draft PR #58; update its existing plan/handoff only after this candidate's exact head and CI are verified.

## Authority and intent

The user authorized a tested draft deployment-preparation PR and a careful checkpoint update to the existing OverMind #58 plan. This lane reconciles the existing Buddy production Compose, Dockerfile, and proxy templates. It defines a provider-free contract for the existing single Buddy service, two separate authorities, durable roots, source metadata, and backup/restore launch gates.

This is not staging or deployment authorization. No live host connection, database/provider call, secret creation/configuration, migration, restore, DNS/TLS/proxy activation, image publication, merge, or persistent data change is within this lane.

## Settled predecessor

Buddy #1814 merged at c7f83c086d39e01f129fa7e31ef03262dbf65c91. Its final run #7 (40447059707) passed on exact pre-merge head 8530d1d00fdb81679bd91872af67c898b7c48f30: 136 Python 3.13 auth/app tests passed, and the production image built locally in GitHub Actions without push. This establishes the existing validation lane, not a published registry digest or host readiness.

Buddy #1817 is merged at 7a6509b06b61c3ffba870dbc3f617e2a31d3a6e6. DMS #45 is merged at 48b3f5181890ee3b3362cd12d9bfb8b41ddd65c1. The bounded live inventory report is operator-provided evidence; this PR does not repeat the inventory or connect to the server.

## Design constraints

- Reuse the existing Buddy production Compose and Nginx templates. Buddy Core stays in process. Do not add a parallel database stack or database sidecars.
- Keep the Buddy application-state DSN and DungeonMind WorldGraph DSN as separate placeholders, with distinct database/role identities. Do not silently reuse the host's network-adjacent PostgreSQL/pgvector or Mongo services.
- Keep Buddy files and WorldGraph files in separate, non-overlapping durable roots outside replaceable checkouts. Compose must not create missing host roots implicitly.
- Require BUDDY_IMAGE_NAME and BUDDY_IMAGE_DIGEST to form a published registry image reference pinned by sha256 digest for any later operator configuration. Do not fabricate a digest. The CI synthetic image is never pulled, pushed, or used for activation.
- Add source-revision build metadata and make every current production Docker build entry supply and inspect the source revision.
- Keep World activation fail-closed: production resolver registry remains empty, readiness stays blocked, and the hosted World-access setting remains a hold placeholder until exact World choice, policy, and route resolvers are approved.
- Preserve the existing DMS-managed population; do not add an owner-only restriction.
- Document backup checksums/fingerprints and isolated restore proof under the owning authority procedures. Honor downgrade fences. No real restore, destructive rollback, migration, or live data operation.
- The bounded host report is not a full audit. It found Buddy absent from the inspected Docker inventory, no matching vhost among readable includes, a host resolver miss that does not establish public DNS, DMS image provenance gaps, Store Generator timeouts, and no verified isolated application restore in checked scopes. Do not claim backups are absent.

## Exclusive expected-path lease

The serial write set for this PR is limited to:

- .github/workflows/hosted-validation.yml
- Dockerfile.production
- deploy/production/compose.production.yaml
- scripts/verify_production_compose.py
- tests/test_production_deployment_config.py
- Docs/Plans/HOSTED-READINESS-MANIFEST-2026-10-26.md
- Docs/Plans/HANDOFF-HOSTED-buddy-validation-ci.md — settle the merged predecessor
- Docs/Plans/HANDOFF-HOSTED-buddy-deployment-preparation.md
- Docs/Runbooks/RUNBOOK-HOSTED-deployment-preparation.md

Do not change the production Nginx template, application runtime/auth routes, database schema, credentials, secrets, provider configuration, host state, or any other repository. Preserve all unrelated existing PRs and their path leases.

## Validation contract

1. Run standard-library synthetic tests against the rendered production Compose JSON. Reject floating image tags, added services/build contexts, shared database coordinates/roles, overlapping storage roots, public API binds, or unsafe/mismatched persistent paths.
2. In hosted validation, render Compose with only synthetic .test hosts/DSNs and /srv/synthetic roots. The workflow must not pull/start services or call a provider/database.
3. Include the focused new test in the existing Python 3.13 CI test selection and lint both the verifier and its test.
4. Build Dockerfile.production on the ephemeral GitHub-hosted runner with DUNGEONMINDBUDDY_SOURCE_REVISION equal to the checked-out commit; inspect and assert the OCI revision label matches. Use no registry login/push, secrets, deployment, or service start.
5. Preserve the previous Python 3.13 app regression tests and their exact results. Record successful checks for the exact draft PR head; no status or job evidence is not a pass.
6. If a reviewer identifies an issue, preserve the report and exact file/line context as an implementation handoff. Do not merge. The original implementer can continue in this lane after review.

## Publication and plan synchronization

Use this branch against the exact base above. Before publishing, verify the final local diff is limited to the write set, record exact source/build revisions, run available static and synthetic tests, and publish one draft Buddy PR. Do not merge it.

After the new Buddy head has terminal successful CI, re-read DungeonOverMind PR #58's exact current head. Preserve all of its existing content and update only the plan and its existing Buddy sign-in-return handoff as justified. Record the Buddy draft URL/head, exact source pins, checks and limits, bounded inventory evidence, merged predecessor references, and remaining operator decisions. Use an expected-head lease for the update; if #58 advanced, inspect the new content and carry forward its unrelated edits. Keep #58 draft and unmerged.

## Current blockers and decision owners

- Operator: select the exact retained World and approve the World/subject ownership and sharing policy.
- Authority owners: identify distinct APP-STATE and WorldGraph database hosts, owners, credentials path, and migration heads.
- Operator/storage owners: select durable roots and provide backup/fingerprint plus isolated empty-target restore evidence for each authority.
- Release owner: publish the exact reviewed Buddy source through a separately approved registry process and record its immutable digest and OCI revision evidence.
- Operator: separately review DNS, Nginx/TLS/cookie behavior, host capacity, DMS image provenance, deployment/rollback ownership, provider limits, and Store Generator health if required.

The World resolver registry stays empty and activation stays blocked until the route resolver set and policy have separate review.
