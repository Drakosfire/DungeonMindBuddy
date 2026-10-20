# Design proposal — HOSTED account-level World access v1

**Status:** Proposed for ARCHITECTURE review. This document is not product approval, implementation authority, or launch approval.

**Buddy source anchor:** `origin/main` at `8bcbe69d1b6d7c70734927a314f4ded05846fb76`.

**Related evidence:** draft [HOSTED route-authorization inventory PR #1512](https://github.com/Drakosfire/DungeonMindBuddy/pull/1512), currently at `d20627acd39709e8c0be839c3b6abac0fbca2ccd`. This proposal independently cites the pinned source above; it does not depend on that draft being merged.

## Summary

Reuse DungeonMind's existing Google sign-in and its server-validated DMS principal. For hosted Buddy access, make each new World private to the DMS account that created it. That account may list, read, and mutate the World and its subordinate data. No sharing, membership invitations, player roles, or public Worlds are introduced in this v1 proposal. The UI's selected-World filter remains a convenience; every server operation must authorize the World.

The proposed default matches the operator's stated expectation that Worlds are private. It is not treated as an approved product policy until the decisions at the end of this document are confirmed. Most importantly, existing local Worlds have **no inferred account owner**. Missing ownership fails closed in hosted mode, while the current explicit local-operator mode keeps its existing local behavior.

Identity, population eligibility, and object access remain distinct:

1. **Identity:** the unmounted Buddy DMS resolver accepts only the `sub` returned by DMS `/api/auth/current-user`; caller headers, email, World IDs, and local `local_operator` are not account identity.
2. **Population eligibility:** whether the DMS Google application is restricted to Alan's managed population is enforced by external Google/DMS configuration and is not established by the code-level `sub` check. An authenticated DMS session alone is not evidence of that restriction.
3. **World authorization:** after trusted identity and eligibility, Buddy compares that account subject with the stored owner of the requested World. The HTTP layer and background workers use the same policy.

## Proposed v1 policy

### New hosted Worlds

- The server derives `owner_subject` from the verified DMS principal. The client cannot submit or override it.
- Creation persists owner and World record together before returning success. Repeated creation of the same normalized name is idempotent only within the same account. A different account may create an equally named World, but receives a distinct globally unique `world_id` and source path; a collision must never return another account's World.
- The owner has the only hosted read/write capability in this proposal. Do not return owner identity in ordinary public World-list responses unless the UI has a reviewed need.
- Share/invite, public access, ownership transfer, and privileged hosted-admin bypass are not implemented. Cross-account access is denied until a separate policy and reviewed implementation exist.

### Existing Worlds and local mode

- Existing v1/v2 registry records lack account owner data. They remain `owner_subject = null` on schema migration; there is no “first signed-in user” claim, email match, filesystem-owner inference, or `local_operator` conversion.
- Hosted list queries omit unowned Worlds. Direct reads, writes, media/file retrieval, and queued actions against them fail closed using a non-disclosing not-found response.
- Local mode retains the existing explicit loopback `local_operator`/local-session path and its behavior. Local identity must not be treated as a hosted account, and a hosted principal must not gain local-mode ambient access.
- If a legacy World is mapped to an account, that assignment is an explicit operator-controlled migration, never an implicit read-time mutation.

### Candidate persistence and scale boundary

The current `GET` and `POST /api/live/world-containers` handlers (`apps/live_control_server/routes/world_containers.py:43-58`) take no request principal and the list returns the complete registry. `WorldContainerRecord` in `services/world_container_registry.py:71-85` has no owner field; the registry is `out/registries/world_containers.json` (`:173-176`). Mutations use a local filesystem `flock` and compare-and-swap (`services/registry_file_lock.py:18-33`; `world_container_registry.py:257-278,319-345`). Creation currently derives `world_id` from name and returns an existing record on any normalized-name match (`world_container_registry.py:190-205,319-345`), so hosted creation must make that idempotency owner-scoped before it can safely serve multiple accounts.

For a single Buddy host with its existing persistent data volume, the smallest compatible implementation candidate is a v3 registry record with nullable `owner_subject` plus a server-only create argument. Creation, source-root allocation, and owner assignment must remain serialized by the existing registry mutation path. v1/v2 records normalize to unowned; no migration writes owner values by default. The deployment must back up and restore the entire registry and World data together.

This JSON registry is not a horizontal-scaling contract. Before running multiple Buddy hosts against World state, migrate the World registry and owner relation to a shared transactional database with unique owner/name semantics and atomic creation. Do not assume `flock` on a mounted filesystem provides cross-host consistency. This proposal does not select a database schema or claim multi-replica readiness.

## Authorization contract

A future hosted access service should expose a narrow owner check, conceptually:

```text
list_owned_worlds(principal) -> Worlds where owner_subject == principal.subject
require_world_owner(principal, world_id) -> authorized World record or generic 404
```

The exact code boundary is for ARCHITECTURE to refine. Invariants:

- Every protected request first resolves a DMS principal; missing, invalid, expired, or unavailable DMS identity fails closed. No `X-User-ID`, request body, query parameter, referer, forwarded header, or client-owned `owner_subject` can create authority.
- Every list is filtered by the authenticated account in the server query/service, not only in React. This includes the World picker and every API that lists World-derived objects.
- Read, write, delete, export, import, graph binding, plan/play, workspace document, media, image-preparation, and file operations resolve their trusted parent `world_id` and authorize it before side effects. Do not authorize a filesystem path selected by the client.
- Resource `owner_id` fields are supplementary, not an alternative World ACL. In current local mode they can contain `local_operator`; that value does not identify a DMS account. World-bound resources inherit the World-owner check. Any owner-scoped resource without a World parent must have its own explicit DMS-subject ownership contract or remain unavailable in hosted mode.
- Enqueue operations bind the server-derived DMS subject and World ID in the durable job record. Workers re-check that the recorded subject is still the World owner before reading protected inputs, calling a provider, or persisting output. A changed/missing owner invalidates stale jobs; cookies and bearer credentials are never copied into job payloads.
- Polling job status/results and any future WebSocket/SSE subscription are authorized to the same owner. The current source inventory did not establish a hosted streaming route; any later stream must authorize subscription and close/reject access on reconnect or ownership change.
- Use generic 404 for unknown and other-account World IDs to reduce enumeration. Tests must prove no file, queue, provider, or registry mutation occurs on denial.

The source inventory identifies 235 route declarations, so adding one global middleware or guarding only `world_containers.py` is insufficient. The implementation handoff must include a route-to-World authorization map and coverage for all routes that expose or mutate World-owned data. Retired routes may retain their existing 410 behavior; routes that are truly local-only must be proven unreachable in hosted topology rather than assumed safe from a local guard name.

The current inventory describes process-local worker/job boundaries; this proposal does not claim that existing job IDs or worker state are durable or safe across restarts. Hosted jobs must either be persisted in the selected one-host durable store or remain unavailable until that contract exists. Horizontal workers require a shared durable queue and the same owner revalidation.

### Required acceptance for a future implementation

- Account A and B each create a World with the same normalized display name; each receives a different ID, list contains only the caller's World, and neither can retrieve the other's World by guessed ID. A retry by the same account follows documented owner-scoped idempotency.
- Forged `owner_subject`, `user_id`, or identity headers cannot change the server-derived DMS `sub`; a missing/invalid principal and a DMS outage cannot fall back to `local_operator`.
- A/B tests cover each route family in the inventory for list/read/write/delete/export and verify denial occurs before file, media, job, provider, or database side effects.
- Existing v1/v2 records remain intact and locally usable; hosted list excludes them and direct access fails until an explicit mapping is applied. Failed or interrupted migration leaves the previous registry and World files recoverable.
- A worker receives only a server-created subject + World ID, rejects an owner mismatch before provider work, and cannot publish a stale result after ownership changes or job cancellation.
- A local-mode regression proves the current loopback/local-session contract still works and never persists `local_operator` as a DMS owner.
- Browser/integration acceptance proves the selected Origin/cookie flow and selected DMS account-removal SLA. These are separate from the offline A/B route tests and cannot be claimed from synthetic cookies.

## Legacy claim and migration options

Recommended default: unowned records remain local-only until an operator explicitly supplies an owner mapping. No claim endpoint is exposed to ordinary users.

1. **Reviewed one-time mapping manifest (recommended):** operator supplies `world_id -> DMS subject` rows from known account ownership. An offline migration validates every World ID and subject, rejects duplicates/unknown records, shows a dry-run, requires a backup, applies atomically, emits an auditable before/after receipt, and is idempotent. Unmapped rows remain unowned and hosted-inaccessible.
2. **Operator-assisted per-World claim:** an operator reviews a World and selects the DMS account in a protected administration workflow or offline command. Require explicit confirmation, reason, actor, timestamp, audit receipt, and an atomic owner assignment. This is slower but suitable when ownership is ambiguous.

Do not bulk-assign every existing World to Alan or to the first successful DMS subject unless the operator supplies and approves an exact mapping. Do not expose a self-service “claim this World” action: it lets a caller convert an existing unowned record into authority.

## Revocation, sessions, and paid work

Buddy's principal adapter (`apps/live_control_server/services/dms_principal.py`) is currently unmounted. It forwards the DMS cookie to the fixed current-user endpoint and returns its `sub`; it does not prove the external eligible-user policy or implement World ownership.

The DMS source anchor at `DungeonMindServer` `origin/main` `223cbbe92f64bb14019a1678cac1f4e2336efd40` configures a 24-hour cookie (`session_config.py:49-76`). The OAuth callback stores parsed user claims but does not add `exp` (`routers/auth_router.py:213-235`); `auth_service.py:48-65` checks `exp` only if present. Thus source alone does not establish an absolute session lifetime or immediate account revocation. The browser cookie being HttpOnly does not prove that Google population eligibility is rechecked. Before promising “remove an account and it immediately loses Buddy access,” verify the deployed DMS session and eligibility contract and select a revocation SLA. Likewise, define what happens to queued work on account removal and prove stale jobs cannot continue paid work under an invalid owner.

World ownership alone does not bound provider spend. Before a multi-account hosted pilot can trigger paid agent work, set finite per-account/World request, concurrency, and spend budgets and verify cancellation/timeout behavior. Existing route/auth audit gates remain in force.

## Preconditions before hosted route wiring

These are technical/evidence gates, not new login features:

1. **Population proof:** inspect the authoritative Google OAuth/Workspace restriction for DMS and provide an allowed-account and denied-account sign-in witness. Establish the session-removal/revocation behavior as part of that contract. Do not rely on the DMS current-user `sub` alone.
2. **Browser cookie proof:** on the selected `buddy.dungeonmind.net` topology, show the existing DMS HttpOnly cookie is sent only to the intended Buddy request; verify callback/deep-link destination, expiry, logout/revocation, and foreign-Origin rejection. No actual cookie transmission was done for this design.
3. **CSRF and auth-mode wiring:** mount the reviewed cookie-Origin helper only after cookie auth selection and before every unsafe side effect. Preserve Buddy's local-session HMAC-CSRF path and non-cookie bearer/service behavior. The helper is currently unmounted.
4. **Complete authorization inventory:** map every protected route and its parent World/resource, including routes that read files, media, Graph objects, documents, jobs, polling results, and any future streams. Add authenticated A/B negative tests at each owning service boundary; a picker filter is not acceptance evidence.
5. **Persistence and recovery:** prove the actual deployment uses a persistent data root, backups include registry + World files + job state as applicable, and a restore retains owners. Limit v1 to a single Buddy host until the shared transactional-store migration is complete.
6. **Operational rehearsal:** health/readiness, rate/concurrency/spend caps, logs without cookie/PII leakage, cancellation, rollback, and owner-migration dry-run are verified before inviting multiple accounts.

No live OAuth, cookie, DNS, TLS, database, server, provider, or deployment checks were run while preparing this proposal.

## Decisions requested from the operator

1. **New World default:** confirm or reject “every newly created hosted World is private to the creating DMS account; no sharing/invites/public Worlds in v1.” The report and design treat this as proposed, not approved.
2. **Legacy Worlds:** choose the recommended one-time reviewed mapping manifest or operator-assisted per-World claims. In either case, confirm unmapped Worlds remain unavailable in hosted mode while continuing to work in local mode.
3. **Removal/revocation expectation:** choose the maximum time after removing an account from the managed population before existing DMS sessions and its queued Buddy work lose access. Immediate next-request revocation is the safest target, but DMS's deployed session/eligibility contract must support it; otherwise choose a bounded documented expiry before implementation.

No sharing model is designed here. It remains deny-by-default until a separate policy review.
