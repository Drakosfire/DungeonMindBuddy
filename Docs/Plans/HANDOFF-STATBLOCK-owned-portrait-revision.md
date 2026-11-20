# STATBLOCK — owner-admitted portrait revision

SETTLED / write lease RELEASED. Source1e554d0c1ca22d86514d4bbd81640df8202b0c3a
merged #2235 ased4f0b30799b9b1ce58ae67908e1bcd4bd1cbfc6. Delivered immutable API
6d5d9d3bd83ae6dc21100bea8a37f409c4a2e204 on schema20261108_0131; UI8b22cacb
unchanged. Source cycle2 and delivery cycle2 approved after correcting operation
proof binding and actual migration-write-connection targeting. All seven CI checks,
66 owner/integration tests, ten helper target guards and nine transition faults
passed. User rows/Core/session files conserved; only reader-fence version row
changed, with no provider/publication/content writes.

Delivered exact statblock navigation/reload/narrow/dirty-draft recovery, lazy native
citations and all14retained manual-operation GETs passed; served OpenAPI exposes the
UUID input. Evidence lives in private runtime-evidence/q01-published-graph-authority/
statblock-owned-portrait-api-resources.json and referenced proofs. Initial failed
heads/logs remain in Git/private evidence; historical checkpoints are pruned here.
This contract is retained context, not a new write/runtime lease.

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

## Historical source scope and topology

One independently useful backend API capability, serial delivery. No unmerged
parent. Required writes:
- apps/live_control_server/models/statblock_saved_revision.py
- apps/live_control_server/services/statblock_saved_revision.py
- apps/live_control_server/routes/statblock_candidates.py
- tests/test_statblock_saved_revisions.py
- tests/test_world_mechanics_associations.py (shared HTTP fixture/auth expectations only)
- src/application_state/mechanics_revisions/types.py (exact submitted intent)
- tests/application_state/test_mechanics_revisions_postgres.py (canonical fixture and journal-proof rejection)
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

