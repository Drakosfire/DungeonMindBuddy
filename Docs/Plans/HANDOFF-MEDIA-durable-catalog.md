# MEDIA — Durable asset catalog foundation

Status: ACTIVE — operator authorizes durable storage/retrieval before more generated images. PRIME implements; ARCHITECTURE reviews. Base: main@981384722723a8682e93da03bac80e0b0d37ebcf. Branch: codex/media-catalog-foundation. Independent of Ingest #1299; serial successor to media #1301.

## Ownership and invariant

Buddy APP owns media identity, owner scope, immutable original-byte identity/provenance and mutable storage lifecycle. GE owns inference only. Existing SERVER Cloudflare/Firestore code is a reference: do not import its runtime or forge its public-user identity. Media catalog reads/writes never touch World Graph.

The foundation stages validated image bytes durably in APP before callers acknowledge a candidate. Saving cannot regenerate an image. Asset UUID and original MIME/dimensions/length/SHA256/provenance are immutable. Separate storage state uses a fenced staged→uploading→ready lifecycle; ambiguous completion is unknown and cannot be blindly uploaded again. Owner checks apply to every operation. Ready requires verified original hash and a fresh committed read. Stable owner/time/UUID pagination. Backup fingerprints include media rows and pending bytes.

Exact write set: this handoff; src/application_state/media.py; src/application_state/migrations/versions/20261016_0027_media_catalog.py; src/application_state/authority.py; tests/integration/test_media_catalog_postgres.py; tests/application_state/test_application_state_authority.py; pyproject.toml; uv.lock.

## Bounds

Only image validation/staging, catalog reads/listing, fenced lifecycle and real PostgreSQL tests. No provider call, CDN upload, serving restart, live migration, document-format/UI change, Graph admission, audio/video writer or new service. The next consumer slice wires reviewed storage provider and wizard Save/reopen. Operator explicitly chose public CDN delivery for saved artwork on 2026-10-16 after considering signed private delivery. Prompts, settings and owner metadata stay private in APP; only image bytes and opaque identity/hash verification metadata travel to Cloudflare. Stable logical asset IDs allow later policy changes, but already public links/caches require explicit retirement. The storage consumer may use Cloudflare custom IDs under this public policy.

## Proof

Use unique disposable APP DB on fixture PostgreSQL54329, migrate only that DB, exercise restart/readback/owner denial/cursor ordering/concurrent claim/stale fence/hash mismatch/unknown upload holds/backup fingerprint. Never use liveAPP54331 orMIND54330. Run scoped Ruff/diff checks, publish one PR, independent review before merge. No automatic migrate-on-boot.

Verification: 8 real-PostgreSQL media tests pass, including fresh-process readback, two concurrent Save claims, stale/unknown fence holds, original/provenance/owner receipt mismatches, corruption detection, keyset pagination with tied timestamps, fingerprint coverage and an actual pg_dump/pg_restore into a second fresh disposable database. Existing APP authority suite25/25 passes after extending its domain expectation. Backup test uses fixture-only wrappers for the PostgreSQL tools in prime-mirathorn-pg-20261015; host pg_dump is not installed. All created databases are dropped in finally blocks. Scoped Ruff, lock and cumulative diff checks pass. The separately probed offline-migration logging test fails in unchanged migration0011 because its Alembic MockConnection lacks exec_driver_sql; no green claim for that test. No live migration, provider call, CDN upload or5202 change.

Staged original bytes are currently retained in APP even after ready for recovery. They are not included in metadata/list projections. Cleanup/tiering requires a separate retention contract; no silent deletion. The next consumer must verify Cloudflare metadata against asset UUID, owner/provenance hashes and original digest, then perform fresh APP readback before calling the image Saved.

A trusted storage adapter may release a definitively rejected upload back to staged using its exact current fence. Unknown outcomes cannot use that path; stale fences cannot complete a later attempt. Original bytes are reused and no generation dependency exists in the catalog.
