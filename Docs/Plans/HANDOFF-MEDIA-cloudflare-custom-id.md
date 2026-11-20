# MEDIA — Cloudflare custom ID compatibility

Status: ACTIVE. PRIME implements under operator-authorized media storage follow-through; independent review required. Base main@764b48729c54944cb535b479a5bc11402494beed. Branch codex/media-cloudflare-custom-id. Serial successor to merged CDN consumer1303.

A live synthetic-only upload found Cloudflare HTTP400 code5411: custom IDs must not be UUIDs, including bare hexadecimal UUIDs. Prefix the immutable logical asset UUID with `buddy-` for the provider object ID. Apply the same deterministic function to upload, lookup and receipt verification; APP asset UUID remains unchanged. No retained assets were uploaded by the rejected probes, so no migration or compatibility reader is needed.

Write set: this handoff; apps/live_control_server/services/media_storage.py; tests/integration/test_media_storage_postgres.py. Provider-free real APP regressions must assert prefixed IDs everywhere and reject UUID-shaped provider receipts. Rerun exact tests and independently review before merge. Then repeat one synthetic live upload/readback/public delivery and remove only that exact test object/database. No fal inference, corpus, live APP/Graph writes or5202 changes in this fix.
