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
the digest only for an explicit selection. The stored append body keeps the
existing native asset_bindings contract, so no schema change or reader fence is
needed. Older readers already understand this body and exact recovery preserves it.

## Exclusive write lease and topology

One independently useful backend API capability, serial delivery. No unmerged
parent. Required writes:
- apps/live_control_server/models/statblock_saved_revision.py
- apps/live_control_server/services/statblock_saved_revision.py
- apps/live_control_server/routes/statblock_candidates.py
- tests/test_statblock_saved_revisions.py
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
