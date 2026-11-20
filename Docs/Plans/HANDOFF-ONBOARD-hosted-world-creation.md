# ONBOARD — hosted owner-created World

Status: ACTIVE implementation assignment. The operator's ongoing Sizzek
onboarding goal authorizes this bounded capability and its reviewable PR; merge,
deployment and live policy enablement remain separate. Base
`e39ebc2523e5dc00c47ab18e6b0325804aa36b27`; branch
`codex/sizzek-hosted-world-creation`; checkout is this isolated Buddy lane.

Topology: parallel-independent of open #4244 (`codex/sizzek-docx-tables`), whose
DOCX converter/test paths do not overlap and whose behavior is not a prerequisite
for authenticated World creation. Both lanes use separately owned disposable
databases and no production runtime, ports or mutable user data. Draft #3824
touches shared hosted authorization files but is not an exclusive bounded lease;
preserve its behavior and require exact cumulative integration review. Open
#3528 changes World navigation helpers, not this lane's selector component;
preserve those helper contracts. Open #3808 has an unmerged 0159 migration while
main already has a different 0159 and current head 0169: do not alter or absorb
that draft; re-anchor migration topology before review. No provider calls.

Exclusive expected write set for this single capability: this handoff; new
hosted-admission migration and application-state catalog/admission modules;
`apps/live_control_server/main.py`, `routes/world_containers.py`,
`services/hosted_auth.py`, `services/hosted_native_graph_access.py`, and a new
hosted-creation service; `services/world_container_registry.py` only for the
shared create-request model; `apps/live-control-ui/src/selectedWorld/WorldSelector.tsx`
and its owning tests, plus the smallest existing API transport/types files and
tests needed for exact hosted creation; new isolated backend owner/authorization
and migration tests and their required CI classification. Shared files are
limited to this capability's exact regions. The existing
`tests/test_hosted_native_graph_access.py` fixture lease for one unrelated test
is excluded; use new tests. If required paths exceed this expected set, resolve
the ownership boundary before writing them.

Browser-witness scope amendment: creation returned a provisioning World, but
Home immediately offered a Graph action because `SelectedWorldContext` omitted
the returned binding status. Include `selectedWorld/SelectedWorldContext.tsx`
and its tests, `home/BuddyHome.tsx`, and `App.guestEntry.test.tsx` only to
propagate the existing public binding status and present a truthful Build-first
action for a not-yet-ready World. No new graph publication, source import, or
general Home redesign is authorized here. Open-PR audit found no conflicting
changes to those exact paths at the time of amendment; re-anchor at review.

The coherent review map is: transactional catalog/admission + shared policy;
hosted exact-route authentication, origin and resource checks; selector/retry
UX; migration/rollback and mounted isolated PostgreSQL tests. The combined PR is
indivisible for a usable secure creation path: none of those pieces alone gives
an owner a safely usable hosted World. The independent Bugbot critique of
`6fc77c1e0b12122c2b0c9fd64aaae5177408db09` found no new material design issue;
the only wording inconsistency was corrected before activation. Feature stays
disabled until explicitly configured and deployed under the release process.

## Problem and boundary

An authenticated hosted user can list only existing owned and deployment-admitted
Worlds. The selector intentionally disables creation. Local creation reserves a
managed World and native identity; reviewed source admission and first-graph
publication are separate operations. A newly created hosted World must belong
to the actual authenticated subject and become usable through existing hosted
World authorization, without adopting an existing World or granting access to
another account. Creation does not itself admit source content, fabricate a
Graph head, or authorize public/anonymous access.

## Evidence and unresolved contract

- `WorldSelector` currently offers create only to `local_operator`.
- The local `POST /api/live/world-containers` does not bind the request's hosted
  subject. Do not expose it as-is. Hosted middleware admits the existing exact
  owner-filtered GET collection, not a generic collection mutation.
- The catalog's `create_world(name, owner_subject)` owns creator/name
  reconciliation and native reservation. Verify its actual transactional and
  retry behavior with the current locked database environment.
- Hosted access currently combines authenticated subject, authoritative World
  ownership, and an independently configured deployment allowlist. Decide and
  review how a newly created owned World becomes admitted without letting a
  request manufacture or expand arbitrary access. A successful create followed
  by a permanently inaccessible World is not success. Do not silently waive the
  allowlist or modify environment configuration per request.
- Inspection of current middleware also found an independent allowlist check
  after route resolution, while World listing and saved-art lookup enumerate the
  static allowlist. Updating only the create route or `_owned_world` would make
  some actions fail and could produce inconsistent security decisions.
- Open draft #3824 touches hosted authorization, routing and their tests. Before
  activation, inspect its current head and active write lease; serialize or use
  an explicitly agreed region split. No dependency on its draft head is implied
  merely by a file overlap.
- Re-anchor at `4715f169d28f2fc6cade2f883fba4730b67445e8`: #3824 head
  `76c31187f3e9badecbc403f2d9c943994c5f5f9c` remains an open integration draft.
  `HANDOFF-BUDDY-v9-registered-world-fixture.md` explicitly records that #3824
  is not itself an exclusive bounded lease. Its own active lease is limited to
  one named test function and its handoff; avoid that test region. Draft overlap
  therefore requires reconciliation but does not by itself block a separate
  bounded lane. Recheck actual leases and the draft before activation.

## Proposed bounded delivery

Candidate admission design for independent security review: retain the existing
static allowlist unchanged and add a separately enabled, durable owner-created
admission. In one database transaction create the World and a server-owned
admission record binding its exact ID to the verified creator. Only records
created by this narrowly authorized path qualify; pre-existing ownership alone
must not convert older Worlds into admitted Worlds. An operator-controlled
deployment setting is off by default and controls creation and use of this
additional admission. Revocation or disabling it must fail closed, without
changing existing static grants. Do not store subjects, World IDs or admissions
in browser-controlled state as authority.

The candidate requires one shared, consistent admission decision across the
middleware, owner revalidation, World listing and resource-to-World discovery
such as saved artwork. Check every call site rather than assuming these are the
complete set. The migration must not backfill admissions for historical Worlds;
atomic rollback must leave neither an admitted orphan nor a visible World when
creation fails. Define recovery and same-name idempotence without permitting an
existing local World to be adopted. Require bounded creation and abuse controls
before enabling the feature; preserve a way to revoke the feature and a single
World's admission independently. This is the reviewed implementation contract,
not a claim that the policy is implemented, deployed, or enabled.

One implementation PR: authenticated hosted creation and owner-visible recovery
using a code-owned exact create capability, with owner derived only from the
verified principal. Preserve local creation semantics and existing World grants;
use the existing catalog/reservation owner and explicit cookie-origin checks.
Define same-name/retry and ambiguous-failure recovery before implementation.
The public response must not expose native IDs, owner subjects, grants, or
provisioning receipts. The UI must communicate what is and is not ready.

The activation above pins the admission contract, lane/base, exclusive paths,
migration context and overlapping hosted-route ownership. If implementation
requires a new
cross-repository or deployment contract, return that decision to the owning
steward; do not broaden this slice silently.

Verification at the owning boundary: mounted hosted HTTP tests with real
authentication boundary and isolated database for unauthenticated, foreign
origin, missing/invalid identity, same-name distinct owners, retry/concurrency,
failure/recovery and cross-account access; verify no caller-selected owner and
no accidental access to existing Worlds. Exercise the selector and exact
hosted transport in browser tests, including creation, refresh and account
switch. Run the repository's required exact-SHA backend/frontend verification
and independently review the cumulative change. A verified created World is not
evidence of source ingestion or a published native Graph.

## Independent security critique

Bugbot reviewed design head `85e1167dbc21273d6d005cc1a37cb49bbd0a512e`
against local main `e39ebc2523e5dc00c47ab18e6b0325804aa36b27`. This was a
read-only critique, without test execution. Re-anchor before implementation.

1. **One creation transaction.** Current `create_world` commits its own unit of
   work; a wrapper that inserts admission later is not atomic. World metadata,
   native reservation, creator-bound admission and quota consumption must
   commit together or not at all.
2. **Recovery without adoption.** Same-owner normalized-name reconciliation can
   return an older World. A returned record is not proof that this capability
   created it. Never admit a historical same-name match; preserve revoked
   admissions as tombstones so an identical retry cannot re-enable access.
   Lost-response recovery must bind the exact request and verified principal.
3. **One decision at all boundaries.** Middleware and owner revalidation check
   static grants, while listing and saved-art discovery enumerate them. All
   relevant paths need the same current, fail-closed admission decision. The
   resolver must still derive World identity from authoritative resource state.
4. **Define revocation semantics.** Specify whether revocation governs later
   checks only or prevents already-admitted writes from committing. The latter
   requires serializing the mutation and revocation through commit. A request
   principal is not a durable permission snapshot; deployment-wide disable
   needs an explicit multiworker propagation contract.
5. **Bound allocation before enabling.** Creation currently locks the managed
   World table and reads retained Worlds. Validate request size and throttle
   before locking. Specify durable per-subject World quotas and a shared
   multiworker request-rate limit; quota check and consumption must be atomic.
6. **Preserve fail-closed startup.** Hosted configuration currently requires a
   valid nonempty static access map. Decide whether self-service installations
   still require that map; never make malformed static grants acceptable merely
   because dynamic creation is enabled.

The candidate decision is current authoritative ownership AND (existing static
grant OR enabled, active admission for this exact creator and World). A transfer
must not transfer creator admission. The exact hosted POST derives its owner
from the verified DMS principal, never caller-selected identity or admission;
it retains origin protection and exposes only the existing public projection
with `Cache-Control: no-store`. The decision, quota, revocation and rollout
contracts are settled for this bounded assignment by the decisions below.

## Proposed decisions for review

These choices are a concrete candidate, not a claim that the feature is
implemented or enabled:

- **Deployment enablement:** self-service creation is disabled by default. A
  shared durable policy record controls enablement, per-owner allocation cap,
  and request-rate parameters. Enabling requires explicit finite positive
  limits and a healthy policy store. Retain the valid nonempty static-map
  startup requirement; this slice does not bootstrap an empty installation.
  A per-process `DMB_HOSTED_OWNER_CREATION_CAPABILITY=1` is also required to
  activate dynamic code after deployment; the shared DB policy, not this flag,
  is the multiworker enable/revocation authority. Missing flags fail closed.
- **Creation and retry:** accept a bounded World name and client-generated
  idempotency key under the authenticated subject. Persist a normalized request
  fingerprint and outcome, and create World metadata, native reservation,
  creator-bound admission, idempotency receipt, and quota charge in one database
  transaction. Same subject/key/fingerprint recovers the same active outcome;
  reuse with different input conflicts. A historical or revoked same-name
  record conflicts instead of being implicitly adopted or reactivated. A
  failed transaction leaves no World or quota charge.
- **Access and revocation:** ownership remains mandatory. Admission requires an
  existing static grant or an enabled, active dynamic admission bound to the
  exact creator and World. Ownership transfer never transfers that admission;
  revocation retains a tombstone. Revocation and disabling govern subsequent
  authoritative checks; an already-authorized operation may finish, so do not
  promise in-flight cancellation. For requests relying on dynamic admission,
  every worker reads current policy at relevant checks and policy lookup failure
  denies; independent valid static grants remain available. Preserve
  owning-boundary rechecks.
- **Abuse limits:** require finite operator-supplied creation and rate limits
  before enabling. Reject malformed/oversize input and enforce shared durable
  per-subject throttling before the catalog-wide lock. Check and consume the
  per-subject allocation quota in the creation transaction. Rate and allocation
  records are not client authority; test accounting for retries and failures.
- **Failure and usability:** return only the existing public World projection,
  with no-store caching and no native IDs, subjects, or receipts. The committed
  World appears in its owner's list immediately; source admission and a
  reviewed first Graph remain separate states. Failure must not claim success.

Review must verify no access path bypasses the shared decision. The refinements
below settle rejected-attempt accounting and rate-window behavior. The activation
records the bounded implementation assignment and collision audit.

### Admission decision refinements

Bugbot's read-only critique of `6314003c46154103c19855a0f171d7dd8eb5937b`
accepts the earlier atomicity and revocation direction but requires these
additional explicit rules, adopted for this assignment:

- Bound bytes before parsing. Charge every well-formed authenticated attempt,
  including retries and conflicts, to a shared durable rate window before it can
  take the catalog lock. Commit the rate charge separately so a failed World
  transaction cannot refund it. Use database time, atomic counters, and bounded
  expiration cleanup. Malformed or oversized requests are rejected before the
  creation path; deployment edge controls handle abusive unauthenticated input.
- Require finite global retained-allocation and creation-rate limits as well as
  per-subject limits. Check and consume global and subject allocation quota in
  the same creation transaction. Count retained created Worlds even after their
  admission is revoked; there is no automatic quota refund in this slice.
- Enforce unique `(subject, idempotency_key)` and bounded key length. Retain
  successful receipts and revocation tombstones for the retained World's
  lifetime. Concurrent identical requests converge on one result; a conflicting
  fingerprint refuses. A retry never grants access merely because it has a
  receipt: recheck current ownership and applicable admission before returning
  metadata, and deny former owners and disabled/revoked dynamic admissions.
- First prove authoritative current ownership and a valid static grant. That
  path remains available even if dynamic policy is disabled or unavailable.
  Only a request relying on owner-created admission requires a healthy enabled
  dynamic policy and active exact creator/World admission; failures deny.
- Revoking owner-created admission revokes that admission only. It does not
  override an independent valid static grant. Total World suspension is a
  separate policy and is not implied by this slice.

Tests must prove aggregate and per-subject limits under concurrency, charged
failed/conflicting/retried attempts, same-key convergence, retention and
revocation, account transfer, static access during dynamic-policy failure, and
all remaining resolver and mutation-boundary checks above.

## Serial successors

1. Real private Apprentice import and source/Graph review, including faithful
   Word-to-source handling and a repeat-ingestion witness. Assess the existing
   Markdown-only Build import and DOCX converter before deciding a code slice.
2. Immutable player-safe guest release with independent access/security proof.
3. Temporary guest graph editing and guided Build/Play experience; live
   anonymous text and image generation each require separate isolation, cost
   and quality evidence. Account onboarding and measured usability remain part
   of the overall goal.
