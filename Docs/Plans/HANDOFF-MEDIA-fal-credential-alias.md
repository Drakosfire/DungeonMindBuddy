# MEDIA — Dedicated fal credential alias

Status: ACTIVE — operator configured DUNGEONBUDDY_FAL_KEY in Buddy .env and requested a smoke test. PRIME owns alias adoption; independent review before merge.
Base: bef81dcc (merged media wizard). Branch: codex/media-fal-credential-alias. Serial successor #1300; independent of Ingest #1299.
Exact write lease: this handoff, apps/live_control_server/routes/media_images.py, tests/test_media_image_generation.py.

Invariant: Buddy's nonempty DUNGEONBUDDY_FAL_KEY takes precedence over generic FAL_KEY for its media generation client; key values are never returned, logged or passed to the browser. Whitespace-only dedicated values fall back to the generic key. Existing operator authentication remains required. Check capabilities and generation against the same resolution rule.

Acceptance: provider-free tests cover dedicated-only, generic fallback, dedicated precedence and empty/missing values, client construction and route forwarding. Run owning endpoint tests, Ruff and diff check; publish a bounded corrective PR. No serving changes or credential-file writes.

Live smoke evidence (local, no private key content): one GE GPT Image 1.5 low-quality 1024×1024 operation failed in 0.45s with PROVIDER_ERROR; subsequent read-only authenticated fal model metadata request returned HTTP401. No image was returned. Credential authentication remains unresolved; adding an alias is not a claim of a working key.
