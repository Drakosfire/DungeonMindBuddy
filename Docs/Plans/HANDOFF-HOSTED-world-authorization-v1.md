# HANDOFF — HOSTED: account-level World authorization v1

**Status:** BLOCKED — design proposal only. No implementation lane, write lease, route wiring, merge, deployment, or live configuration change is authorized by this handoff.

**Owning flow:** `HOSTED`

**Steward:** Hosted Buddy v1 implementation task

**Buddy design base:** `origin/main` at `8bcbe69d1b6d7c70734927a314f4ded05846fb76` (includes merged PR #1509). Re-anchor to current main before any later dispatch.

**Design artifact:** `Docs/Design/DESIGN-HOSTED-world-access-v1.md` in this review PR. This is a rare HOSTED design/architecture PR under Buddy `AGENTS.md`'s exception for design that needs independent review before implementation. It is separate from the open route-inventory PR #1512 so that the authorization decision and its handoff remain a narrow review unit; it does not depend on #1512 being merged.

**Related identity predecessor:** DMS principal adapter PR #1508 is merged. Buddy's `DmsPrincipalResolver` remains unmounted. The cookie-Origin helper PR #1509 is merged but remains unmounted. Neither merge means hosted authentication or authorization is enabled.

## 1. Proposed capability and invariant

Proposed hosted behavior, subject to the operator decisions in the design document:

> A DMS-authenticated, externally eligible account can access only Worlds whose stored owner subject equals the DMS `sub` returned by trusted server-side introspection. New hosted Worlds are private to their creator. Legacy Worlds with no explicit account owner remain inaccessible in hosted mode until operator-mapped. Local-only `local_operator` behavior remains unchanged.

Sharing, invites, player roles, public access, self-service claims, and hosted-admin bypass are out of scope and denied until separately designed and reviewed.

## 2. Exact unresolved product decisions

Implementation stays blocked until the operator resolves:

1. Whether new hosted Worlds are private to their creating DMS account, with no v1 sharing or public Worlds.
2. Whether legacy owner assignment uses a one-time operator-reviewed manifest or per-World operator-assisted claims; confirm unclaimed Worlds stay hosted-inaccessible and local-usable.
3. Maximum revocation latency after a user is removed from the externally managed population, including already issued DMS sessions and queued Buddy work. Recommend next-request denial; DMS must prove it can deliver the chosen behavior.

No other product behavior is silently selected by this document. The user has already directed us to reuse existing DMS/Google login, not introduce a new login.

## 3. Design summary for review

- Use only the verified DMS principal's stable `sub`; never use email, request identity headers, client-submitted owner fields, or local `local_operator` as an account key.
- Treat external managed-population eligibility as a separate DMS/Google gate. Current-user authentication alone does not prove the DMS application is restricted to the intended population.
- Candidate single-host v1 storage: nullable `owner_subject` on a new World-registry schema; derive it server-side and persist with World creation under the existing registry mutation lock/CAS. The API must not return another account's World on a name collision; new Worlds require globally unique IDs and per-owner idempotency.
- Hosted list/read/write authorization must cover all World-owned API, file, media, Graph, document, play, polling/job, and result paths before side effects. UI filtering is not authorization. Workers carry server-derived `{subject, world_id}` and revalidate ownership before consuming inputs, calling providers, or saving results.
- Missing owner is denied in hosted mode and retained for local mode. Ownership migration is operator-reviewed, dry-run, backed up, audited, idempotent, and never triggered by a read.
- The JSON registry and local `flock` are a single-host boundary, not a multi-host scaling guarantee. Move registry/ownership/jobs to a shared transactional store before horizontal replicas.
- Cookie delivery, CSRF route mounting, external population proof, session revocation, deployment persistence/restore, quotas, and a full route-coverage review are explicit later gates.

## 4. Candidate future implementation decomposition (not a lease)

This section proposes sequencing for steward review only. It does not activate workers or authorize edits. Once product decisions and technical gates are satisfied, the steward must re-anchor main, inspect active PR/worktree/handoff topology, split merge-ready invariants, pin paths and base, then publish an ACTIVE handoff with a concrete §4 write lease.

1. **Offline owner core (no route callers):** add a versioned owner field and a pure/server-internal owner service with synthetic principal tests. Preserve v1/v2/local behavior. Required acceptance includes same-name Worlds created by accounts A/B never alias and caller-supplied owner values never grant authority. This code must remain unmounted; it does not implement hosted create/list HTTP behavior.
2. **Hosted identity and route integration:** only after allowed/denied population evidence, real cookie-delivery proof for `buddy.dungeonmind.net`, Origin/CSRF review, and the complete route-to-World map. Then wire World list/create and each protected resource route through the owner service; do not enable hosted access while any exposed route can bypass the policy. Reject before provider, queue, file, or registry side effects.
3. **Jobs/results and revocation:** bind subject and World to durable jobs; enforce the chosen DMS/account revocation behavior and recheck owner before execution/persistence; prove cancellation and stale-result fencing. If no durable queue exists, keep hosted job-producing routes disabled until that contract is implemented.
4. **Legacy ownership migration:** implement the selected operator-only migration procedure only after backup/restore rehearsal and exact owner mapping approval. Unmapped records remain hosted-denied.
5. **Launch rehearsal and scaling gate:** prove persistence/restore, finite per-account/World budgets, cancellation, and recovery. Limit initial hosted execution to the verified single-host storage boundary; use a shared transactional store before additional Buddy hosts.

Steps are a proposed decomposition, not parallel lanes or stacked PR authority. HOSTED defaults to serial. No implementation branch/PR should be opened under this BLOCKED handoff.

## 5. Review and verification contract

Before any implementation dispatch, ARCHITECTURE must review this exact design/handoff revision and report whether:

- DMS `sub` is an appropriate stable account key and the population/session-revocation boundary is accurate;
- owner-only new World semantics and fail-closed legacy behavior are coherent;
- same-name/unique-ID creation requirements address the current global name-based idempotency behavior;
- file/media/jobs/streams and local-mode boundaries are sufficiently explicit;
- the single-host JSON boundary and multi-host migration gate are technically sound;
- any further operator decision is required before defining an ACTIVE slice.

No code test is applicable to this documentation-only design. Verify source anchors against pinned Buddy/DMS refs, `git diff --check`, exact PR head/base, and no changes outside the two named design files. This review is not formal GitHub approval, merge authority, live evidence, or launch approval.

## 6. Separate activation gates

### 6.1 Offline owner-core slice

The current handoff remains BLOCKED. Before the steward may author a separate ACTIVE handoff for an unmounted offline owner-core slice:

- record the operator decisions in §2 that govern new-World owner semantics and legacy fail-closed behavior;
- obtain ARCHITECTURE disposition on this exact design/handoff revision;
- re-anchor to current main, check active HOSTED PR/worktree/lease topology, then write an ACTIVE handoff with the exact code/test paths, base, serial topology, and synthetic/offline acceptance.

This slice can use synthetic DMS principals and isolated test data. It must not import the owner service from an HTTP route, mount the DMS resolver or Origin helper, enable `hosted_owner`, transmit real cookies, or write production data. Live Google population, browser cookie, and CSRF evidence are **not** prerequisites for this pure unmounted core; they remain mandatory for route wiring.

### 6.2 Hosted route integration and launch

Before any hosted HTTP route wiring, account data exposure, real-user operation, or enabling of `hosted_owner`, independently establish all of the following:

- Google/DMS managed-population allowed/denied sign-in evidence and the selected account-removal/revocation behavior;
- browser proof that the existing DMS cookie reaches only the intended Buddy request on `buddy.dungeonmind.net`, with callback/deep-link, expiry, logout, and foreign-Origin tests;
- Origin/CSRF review and a complete route/resource-to-World map, with every exposed route covered before hosted access is enabled;
- actual persistent data-root and backup/restore behavior; finite per-account/World provider budgets, durable job identity, cancellation, and recovery;
- a separate exact-scope implementation handoff and exact-head ARCHITECTURE review for route integration.

Until those route-integration gates are satisfied, hosted routes remain unavailable even if an offline owner core is later approved/merged. Legacy ownership assignment, production writes, real cookie tests, server configuration, and deployment remain stopped under this design. No deployment or live calls were made here.
