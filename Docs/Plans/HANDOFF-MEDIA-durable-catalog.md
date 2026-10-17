# MEDIA — Durable asset catalog foundation

Status: ACTIVE — operator authorizes durable storage/retrieval before more generated images. PRIME implements; ARCHITECTURE reviews. Base: main@981384722723a8682e93da03bac80e0b0d37ebcf. Branch: codex/media-catalog-foundation. Independent of Ingest #1299; serial successor to media #1301.

## Ownership and invariant

Buddy APP owns media identity, owner scope, immutable original-byte identity/provenance and mutable storage lifecycle. GE owns inference only. Existing SERVER Cloudflare/Firestore code is a reference: do not import its runtime or forge its public-user identity. Media catalog reads/writes never touch World Graph.

The foundation stages validated image bytes durably in APP before callers acknowledge a candidate. Saving cannot regenerate an image. Asset UUID and original MIME/dimensions/length/SHA256/provenance are immutable. Separate storage state uses a fenced staged→uploading→ready lifecycle; ambiguous completion is unknown and cannot be blindly uploaded again. Owner checks apply to every operation. Ready requires verified original hash and a fresh committed read. Stable owner/time/UUID pagination. Backup fingerprints include media rows and pending bytes.

Exact write set: this handoff; src/application_state/media.py; src/application_state/migrations/versions/20261016_0027_media_catalog.py; src/application_state/authority.py; tests/integration/test_media_catalog_postgres.py; pyproject.toml; uv.lock.

## Bounds

Only image validation/staging, catalog reads/listing, fenced lifecycle and real PostgreSQL tests. No provider call, CDN upload, serving restart, live migration, document-format/UI change, Graph admission, audio/video writer or new service. The next consumer slice wires reviewed storage provider and wizard Save/reopen. CDN visibility choice is pending operator response; metadata foundation is independent of that choice. Cloudflare custom IDs cannot be private; do not choose them before explicit delivery policy is settled.

## Proof

Use unique disposable APP DB on fixture PostgreSQL54329, migrate only that DB, exercise restart/readback/owner denial/cursor ordering/concurrent claim/stale fence/hash mismatch/unknown upload holds/backup fingerprint. Never use liveAPP54331 orMIND54330. Run scoped Ruff/diff checks, publish one PR, independent review before merge. No automatic migrate-on-boot.
