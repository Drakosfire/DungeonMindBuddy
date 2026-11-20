# ONBOARD — owner-published guest release

Status: ACTIVE. The onboarding goal authorizes this
capability, including independent Bugbot review, merge and deployment after the
applicable evidence and release gates pass. Base: `f3da3caedea4515eef9645cf3834abd44c422665`;
candidate branch: `codex/onboard-guest-release`. The predecessor prompt-boundary
fix merged in #4268. The workstream is serial.

## Outcome and boundary

An owner can prepare and inspect an immutable, player-safe copy of selected
World material, approve its exact digest and publish it behind a stable pointer.
Signed-out readers can access only the published copy; editing the private World
cannot alter it. Revocation denies subsequent origin reads, including direct asset
and citation paths. Previously delivered bytes cannot be recalled. A rollback
must not silently revive a revoked release.

The approved manifest binds the sanitizer and projection versions, release-local
citations, final served representations and copied asset digests. Release reads
must not fetch private sources, external URLs or uncontrolled signed assets.
Use `Cache-Control: no-store` for release responses until a tested revocation
mechanism supports a different policy.

Preparation must check the current owner, the managed World/native space binding,
exact committed document revisions and digests, the exact Graph revision, and
closure of included relationships, citations and copied assets. It stages the
fully sanitized representation privately before approval. Owner review applies
to the final server-computed digest and bytes, not mutable source selections.
Promotion rechecks current owner and candidate validity and atomically records
approval and compares and swaps the stable pointer in application state. It
must not hold a database transaction open across native-authority calls. Head
changes do not alone invalidate a complete approved historical candidate; an
ownership change, withdrawal or explicit invalidation does. Public reads use
only copied release data and must not fall through to private APIs.

The state machine distinguishes private candidate, published, revoked and
invalidated states. Only a current owner can approve the staged candidate and
promote or revoke it. Promotion compares both the reviewed digest and expected
stable-pointer version. Candidate authority must include a durable generation
that changes on every ownership transfer or invalidation, including a transfer
away and back. Revocation is durable and does not change on pointer rollback.
The owner needs an authenticated review surface for the exact staged result;
the implementation must define and test that surface before activation.

The hosted middleware authenticates API paths before dispatch. Any anonymous
exception must be confined to exact release read routes and methods and retain
fail-closed production and local boundaries. Open integration draft #3824
touches the middleware and routing, but the prior hosted creation handoff records
that it is not an exclusive bounded lease. Recheck its head and active leases
before activation; preserve its changes and independently review integration.

## Lease and verification

Exclusive expected write set: this handoff; a new application-state guest
release module and migration after `20261120_0170`; a new release preparation
service, request/response models and routes; the exact anonymous exception and
owner route registrations in hosted authentication and `main.py`; the minimal
owner review and guest entry UI, transport and tests; and new owning-boundary
backend tests and necessary test classification. Shared routing changes are
limited to this capability. If a required file falls outside these categories,
resolve the lease before editing it. Use disposable test databases, no live
World, and no provider calls during implementation. Bugbot critiqued the design
before activation; current #3824 head is `76c31187f3e9badecbc403f2d9c943994c5f5f9c`.

Do not assume that the GM mutation-context helper is a historical public
projection: it also reads current identity decisions. `content.pages.read_revision`
can retrieve a committed page by World, revision number and content digest;
this does not establish historical visibility or working-copy semantics.

`world_graph_reads.project_world_graph_direct` maps an explicit revision pin
and the closed `player` admissibility value into the DungeonMind projection.
Its adapted response still carries source/evidence identities and is not a
release-safe wire format. The release preparer must apply its own closed field
allowlist, localize all IDs, check endpoint and citation closure, and exercise
the actual Core visibility gate with GM-only adversarial fixture data. The
hosted owner request must choose neither a broader admissibility nor an
unverified native World binding.

At the pinned base the application-state migration head is `20261120_0170`.
`media.read_staged_bytes` checks an owner ID, length and SHA-256, while the
storage receipt also carries an HTTPS delivery URL and a public/private flag.
Those properties alone do not establish that an asset is player-safe or that
the owner is authorized to release it. Preparation must copy verified bytes
into release-owned storage after explicit selection; it must never forward the
private storage receipt or delivery URL. Confirm the lifecycle of staged bytes
for already-uploaded assets before choosing the release asset adapter.

At this base `media.storage.staged_bytes` is non-null in every lifecycle state,
and the owner's original-image route reads it through `media.read_staged_bytes`,
which checks the stored length and SHA-256. No staged-byte deletion or clearing
was found in the application sources. This supports copying the original bytes
without using a delivery URL, but ownership-to-World association and explicit
release selection still need validation at preparation. This is a code inspection,
not a retention guarantee against external maintenance or a completed test.

The catalog's shared `_write` upsert can update `owner_subject`. Current-owner
comparison alone therefore cannot establish that ownership never changed. A
database-enforced generation or candidate invalidation must cover all updates,
not just one application route, and its migration must be tested against
transfer away and back and concurrent promotion.

The intended owner review surface is an authenticated in-product preview of the
staged release using the same release-local projection as the public reader,
followed by explicit digest-bound publication. A JSON-only operator workflow
would not deliver the requested owner experience. The graph and media selection
must produce an allowlisted projection, not expose a generic private Graph API.

Verification must include mounted production-mode authorization tests with two
anonymous sessions and an unrelated authenticated account, private candidate
and asset denial, exact route/method handling, owner transfer, stale digest and
pointer conflicts, concurrent promotion/revocation, citation and asset closure,
private edits after publication, rollback, cache behavior, and unpublish.
Use disposable databases and exact-SHA owning-boundary verification. Separate
real browser, release-host and owner content acceptance remain required. This
slice does not authorize live guest generation, direct private-source access, or
turning on hosted World creation without its release gates.

Approved copied excerpts are part of the release; their inclusion requires the
owner's explicit review of the final candidate. Guest sandbox reset is a
successor capability, not a publication-state operation.

## Cross-authority publication gap

The current implementation must not enable preparation or promotion yet.
Bugbot verified at Core `046791d` that native source withdrawal serializes on
Core's private global source-authority epoch lock, while its public source view
is a closed-transaction epoch snapshot. A fresh native check followed by an APP
promotion can race a withdrawal committed between the two operations. APP's
visibility and ownership generations do not observe direct Core withdrawal.
This handoff requires withdrawal to invalidate a staged candidate, so an epoch
check alone is insufficient. Do not use Core's private SQL lock as an implicit
cross-database protocol. The cross-owner contract needs a durable publication
fence, withdrawal interaction, crash recovery and a defined linearization point;
its owner is the DungeonOverMind/Core boundary. A different independent-copy
policy would be a design change and must be explicit, not silently substituted.

### Candidate cross-owner protocol for critique

Core owns a durable release authorization keyed by a unique intent, exact native
space/revision, admitted source proofs and candidate digest. APP first records a
private pending intent under an owner/pointer fence; it is not guest-readable.
Core then atomically checks source eligibility and records the authorization under
its own source-withdrawal serialization boundary. That Core commit is the
publication linearization point: a prior withdrawal rejects authorization; a
later source edit or withdrawal does not rewrite an already approved release.
APP finalizes the pointer only for the still-current fenced intent, and guest
reads require both APP's published pointer and the corresponding live Core
authorization. Release revocation withdraws the Core authorization and clears the
APP pointer through an idempotent, recoverable operation; intermediate states
must fail closed. A crash between either store's commits may make the release
temporarily unavailable, never anonymously expose an unapproved candidate.

This is a proposed cross-owner contract, not an available Core API. Bugbot's
critique found that this optimistic protocol does **not** meet the currently
required withdrawal rule: Core authorization is only a source-validation
cutoff, not public publication. A native withdrawal after that authorization but
before APP finalization would still permit publication. The current contract
therefore remains unsatisfied; do not implement the sketch as though it closes
that interval. A stricter joint fence or a deliberate owner-adopted change to
the withdrawal cutoff is needed.

A synchronous Core-owned guard around APP finalization is also insufficient as
currently specified. Bugbot identified a lock-loss race: the Core connection
can terminate and release the epoch lock, a withdrawal can commit, and an
already-dispatched APP commit can still complete. A later health check cannot
undo the exposure. A strict design needs enforceable commit/fence coupling and
recovery for uncertain APP commit outcomes; it must also audit APP-to-Core lock
ordering and bound the global Core epoch contention. A prepared transaction or
shared durable commit coordinator might supply this, but either introduces a
cross-owner operational contract and cannot be inferred from existing APIs.

The sketch also needs
explicit rules for competing intents, ownership transfer during either commit,
rollback without reviving revoked grants, current authorization checks on
assets/citations, caching, operation recovery and orphan cleanup. In particular,
the ordering above alone does not prove atomicity against APP ownership changes:
the Core activation must be fenced by a durable APP authorization that cannot
remain valid after a transfer, or a stronger joint protocol is required. Do not
activate implementation from this sketch without the owning contract and tests.
