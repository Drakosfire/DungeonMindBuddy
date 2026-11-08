# STATBLOCK — owner-admitted portrait revision

ACTIVE. PRIME owns this serial slice after delivered #2231. Source base
671c79d04f165f2eb7a70b13758f1ed5623482aa; branch
codex/statblock-owned-portrait-revision; reuse buddy-context-loop checkout and
existing dependencies. The implementation has no runtime write lease. Live API
d636d61c1a136b968b830bf4153fdbc3e600960a and UI
8b22cacbbe50b099cc057cec67dc05407e28cfb2 are immutable and independently pinned.

## Outcome and owner contract

The existing manual-revision Save may explicitly select a portrait by APP media
asset UUID. Authenticate the media owner through the existing native GM dependency;
resolve the selected image through application_state.media. Only an already-ready,
public Cloudflare Images receipt can supply the existing DMS AssetRefV1. The
browser never supplies a URL, provider receipt, owner or native asset object.
Staged/uploading/unknown/private assets refuse without an append or implicit
upload. The existing media Save remains the explicit public-CDN action.

Replace only the unphased portrait slot. Preserve other roles and phase bindings.
A new immutable mechanics revision carries the chosen native binding through the
existing APP operation journal, exact producer CAS and result verification. No
new media/statblock store, association authority, upload or generation pipeline.
No encounter, original acceptance reference or World association retargeting.

Before activation, the failure critique identified two important boundaries:
selection admission must precede claiming a Save, while committed/unknown-outcome
replay must use the original admitted body without reopening media; and omitted
portrait selection must retain existing Save intent digests. Include the UUID in
the digest only for an explicit selection. The stored append body keeps the existing native asset_bindings contract.
The operation owner must also reconstruct the submitted media UUID from the
existing accepted_through metadata; reader fence 20261108_0131 protects this new
intent meaning. No data rows are rewritten.

## Exclusive write lease and topology

One independently useful backend API capability, serial delivery. No unmerged
parent. Required writes:
- apps/live_control_server/models/statblock_saved_revision.py
- apps/live_control_server/services/statblock_saved_revision.py
- apps/live_control_server/routes/statblock_candidates.py
- tests/test_statblock_saved_revisions.py
- tests/test_world_mechanics_associations.py (shared HTTP fixture/auth expectations only)
- src/application_state/mechanics_revisions/types.py (exact submitted intent)
- src/application_state/migrations/versions/20261108_0131_portrait_revision_intent.py (no-op reader fence)
- .github/workflows/world-ownership-core.yml (register owning Save tests only)
- this handoff and truthful HANDOFF-STATBLOCK-exact-full-view.md settlement.

Open PRs/leases inspected: held Play #2172 and retrieval/composition drafts do not
overlap. ADVERSARY's announced retained-writer diagnostic work is eval-only; it
owns its experiments and assessment. Other local-World/ingestion drafts are not
adopted. Disposable tests use unique APP database clones on 54329; no primary APP,
Core, benchmark 55447, providers, ports or external writes. No new checkout/env.

## Verification and remaining scope

Exercise real HTTP authentication/owner injection, real APP media admission and
manual-operation persistence with synthetic CDN/DMS IO. Prove preserved bindings,
exact readback, rejection of foreign/staged/unknown/private assets and raw URL
fields, original intent on retry/recovery, changed-selection key conflicts and
existing no-selection replay behavior. Run affected existing Save/association and
media tests, inspect cumulative base-to-head diff, independent Bugbot review,
commit/push/open one PR, CI and protected delivery.

Popup image generation/selection/rendering and shared conversation/node editing
remain subsequent consuming UI slices. They must reuse MediaImageWizard and this
API, not add parallel ownership. Native threat association/creation and the real
Corrupted Edge ooze remain in the full objective. Held Play #2172 is not resumed;
dogfooding/operator acceptance remain excluded.

## Fixture checkpoint

The first owning run retained its failure log: the inherited shared TestClient
fixture reached hosted_auth_unavailable before any endpoint (44 failures;14
unaffected checks passed). Add only the shared fixture file to this lease: set
explicit local deployment/auth mode and a loopback TestClient peer. Keep actual
native dependency overrides for synthetic authenticated cases, and explicitly
prove unauthenticated loopback401 / non-loopback403. Do not bypass middleware or
change product auth. This is necessary to exercise the selected Save boundary and
register its tests in CI; it is not a separate authentication capability.

## Journal-boundary checkpoint

The corrected HTTP fixture exposes the actual owner invariant:48 pass,2 portrait
cases refuse construction because RevisionOperation reconstructs the submitted
input digest without a media selection. Preserve that invariant. Extend its exact
reconstruction with the selected UUID retained in the existing native append's
accepted_through metadata, and compare the entire returned accepted_through map.
Do not add another selection store or weaken digest checks. The new meaning needs
reader fence0131, which is not present on fetched main; rejected #2233's unmerged
fence is not adopted. No active product-schema lease overlaps (ADVERSARY's #2234
is eval-only). This extension is indivisible from a replayable image Save: splitting
it would leave a capability whose durable intent cannot be reopened. The write
lease expands only to those two owner paths. Protected backend delivery will
require upgrade/restart; no live schema or runtime action is authorized by source
implementation alone before review/CI and a delivery lease.

## Candidate verification

Current production code passes58 owning HTTP/APP revision, association and journal
checks (owner-tests-v3.log), plus the additional selected-intent resealing and
reader-fence case (intent-check.log). Eight unchanged media-storage checks passed
in the initial run. All use disposable54329 databases, synthetic CDN/DMS IO and no
provider/primary writes. Four existing schema-field shadow warnings remain.
Original fixture rejection and journal-intent failures are retained in v1/v2;
the later owning checks prove their corrections. CI registers both Save and
journal owner tests. Cumulative diff check is clean. Independent review, CI and
protected backend delivery remain pending; this source slice is not live yet.
