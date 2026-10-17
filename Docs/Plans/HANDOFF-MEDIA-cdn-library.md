# MEDIA — CDN save and reopen

Status: ACTIVE — operator requested durable public CDN image storage before more images. PRIME implements; independent review before merge.
Branch: codex/media-cdn-library. Topology: stacked on catalog PR1302 exact8ff75df2c2045cd4d74a49cd77815bdf18860669; merge catalog first, then review consumer cumulative diff. Handoff must be re-anchored on accepted parent if it changes.

## Outcome and authority

Image generation stages its returned bytes and exact prompt/model/settings/GE observation in Buddy APP before acknowledging a preview. Wizard can Save to public CDN, browse its owner-scoped library and reopen existing images after reload. Save/reconcile never calls GE. Original bytes stay available during/after save. Stable Buddy UUID is identity; provider URL is a delivery receipt. No document insertion or Agent-tool adoption in this storage slice.

Explicit operator policy: saved images use public delivery now. Prompts/settings/owner records stay private. Cloudflare metadata contains only opaque asset id and hashes for exact reconciliation; no raw prompt or owner identity. Reuse existing Cloudflare account/Images mechanics, not SERVER Firestore/auth or runtime imports.

## Write lease

This handoff; apps/live_control_server/services/media_storage.py; apps/live_control_server/routes/media_images.py; tests/test_media_image_generation.py; tests/integration/test_media_storage_postgres.py; apps/live-control-ui/src/media/MediaImageWizard.tsx; apps/live-control-ui/src/media/MediaImageWizard.test.tsx; apps/live-control-ui/src/media/MediaImageWizard.css.

## Failure invariant

Check APP schema and storage configuration before paid/network mutation. Auth required independently of Graph-facts toggle. Save claims one APP fence then uses Cloudflare custom id derived from asset UUID. Existing/unknown result is reconciled by exact object id plus asset/owner/provenance/content hashes and account-owned API response. Ready requires fresh provider verification and committed APP readback. Unknown upload cannot blindly POST again; definite provider rejection may release only current uploading fence. Concurrent Save cannot double-post. Missing/corrupt original fails closed. HTTP redirects/retries are not automatic. Browser never supplies a verified storage receipt or Cloudflare credential.

## Proof and runtime

Provider-free HTTP adapter tests + real disposable PostgreSQL stage→upload→ready→fresh-owner-read/reopen; simulate timeout, known rejection, collision/hash mismatch, concurrent claims, crash between upload and APP acknowledgment. Shared wizard tests prove Save/reopen and no generation during recovery. Typecheck/build/Ruff/diff. No live migration, CDN upload or5202restart in implementation lane. Existing Cloudflare credential location is pending operator reply; code/tests continue independently. fal authentication last failed401; no further inference until corrected.
