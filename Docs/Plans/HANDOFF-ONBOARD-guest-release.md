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
ownership change, APP source visibility/status withdrawal or explicit invalidation
does. Native source withdrawal follows the cutoff below. Public reads use
only copied release data and must not fall through to private APIs.

Owner-adopted cutoff clarification: the owner is approving a copied snapshot,
and the native source eligibility cutoff is one freshly opened, coherent Core
source-authority view for the explicit publish attempt. A native withdrawal
before that view must fail publication; one after that cutoff does not cancel
the already approved copy, even if it occurs before the APP pointer commit.
APP ownership and page-visibility/status generations must still be checked
atomically at pointer commit. Published copies are withdrawn using release
revocation. The owner interface must state this distinction. This intentionally
replaces the earlier proposed rule that every native withdrawal before APP
commit cancels a pending candidate; it avoids a distributed commit dependency
while preserving the requested independently controlled snapshot. Bugbot
critiqued this change and identified audit, retry and disclosure requirements.

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

The Core player projection excludes assertions supported only by GM-only
sources, including player-designated assertions; a pinned native fixture proves
this. To support ordinary first-World ingestion, the owner-approved release
must be a distinct copy, not described as Core player-admitted Graph data. The
preparer may privately inspect the exact native Graph under verified owner/GM
authority, but may copy only explicitly selected labels, facts, relationships,
excerpts and assets into a closed release-local representation. Every displayed
field must be shown for explicit digest-bound owner approval; do not copy GM
summaries, aliases, neighbors or private identifiers by default. Revalidate
exact evidence and source withdrawal at the adopted cutoff. Anonymous reads
must use only the approved copy and never this private reader. This deliberately
replaces the earlier player-projection-only restriction, which cannot represent
the intended source path; the user chooses what becomes public.

The experimental assembler now binds each selected name and classification to
its own native assertion, evidence and release-local excerpt; publication
validation reconstructs those fields and the selected relationships from a
fresh owner view. Unknown and timeless scope are retained separately in the
candidate. Other temporal scopes and non-established or non-factual claims are
currently rejected, not converted into facts. This is not yet a usable owner
selection or review interface, and preparation remains disabled. A real Core
fixture confirms unknown scope is common. A synthetic integration fixture now
joins a committed APP page to a private Core source, stages and reviews two
nodes and a relationship, publishes the copy, verifies a later private edit
does not alter it, rejects another publication after Core withdrawal, and
revokes the published copy. It uses a private service entry point, substitutes
the Core repository/binding, and is not an ordinary first-World or mounted
route witness. A complete real first-World preparation, owner review,
publication and withdrawal test remains required before activation.

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
An epoch check does not prove the earlier strict withdrawal-before-APP-commit
rule. The owner-adopted cutoff above changes that rule explicitly; do not claim
the stricter property. Core unavailability, incomplete proof, evidence outside
the owner's selected copy, or an invalid exact native origin must fail closed. Record the native authority,
cutoff epoch, operation ID, principal, candidate digest, source coordinates,
APP generations, pointer CAS basis and outcome privately. Lost responses must
recover the committed outcome without republishing a revoked release.

## Explicit release-copy visibility decision

Ordinary first-World and Worldbuilding source admissions are GM-only even when
an individual reviewed Graph assertion is player-visible. The release cannot
therefore require its private evidence to be player-openable without excluding
the intended ingestion path. The owner may explicitly select exact excerpts
from their private source, inspect the final sanitized copy and approve its
digest for publication. This approval authorizes only that copy; it does not
change the source's native visibility or grant guests access to the World.
Graph fields and source proofs come from one authorized owner/GM read at the
same pinned Graph revision and coherent Core source epoch. This is a release
declassification decision, not a claim of Core player admissibility. Neither the
private view, its identifiers, nor any unselected text is guest output.
APP source status and visibility changes after staging invalidate the candidate
even when the original selected visibility was internal. Published copies remain
independent until release revocation. The owner review must clearly identify
that selected private excerpts will become public and show their exact final
contents and assets before approval. Do not automatically release a whole source.

Select every displayed node name and classification from exact assertions (or
use an explicitly declared release-local display category); reject fallback IDs
and silently joined names. Each relationship binds its exact assertion,
endpoints, predicate, displayed transformation and selected support. Selection
of a node must not imply its descriptions, aliases or neighboring facts. Each
copied fact preserves uncertainty, negation, temporal scope and standing, or is
clearly presented as newly authored owner text. Privately retain exact proof and
source coordinates for each selected field. Never expand an evidence span to
include unselected material. The approved digest covers final rendered content,
transformations, sanitizer/projection versions and copied asset bytes.

The current draft's `read_player_graph` and projected-label selector do not meet
this amended contract. Keep preparation disabled until they are replaced and
the owner review and fresh-proof checks cover the selected fields. Include a
real GM-only source fixture with multiple names, secret neighboring facts,
mixed-visibility relationships and provisional or negated claims; verify only
explicitly selected material appears and the original World is unchanged.

The sketch also needs
explicit rules for competing intents, ownership transfer during either commit,
rollback without reviving revoked grants, current authorization checks on
assets/citations, caching, operation recovery and orphan cleanup. In particular,
the ordering above alone does not prove atomicity against APP ownership changes:
the Core activation must be fenced by a durable APP authorization that cannot
remain valid after a transfer, or a stronger joint protocol is required. Do not
activate implementation from this sketch without the owning contract and tests.
