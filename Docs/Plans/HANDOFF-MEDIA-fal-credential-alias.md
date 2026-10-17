# MEDIA — Dedicated fal credential alias

Status: MERGED — Buddy #1301 independently reviewed PASS at d775bd664b457553233a1e9e957d2a712faa7885; merge 281c723aed188130e298335c12fe7725762fff22. Alias implementation lease complete; live key authentication and runtime adoption remain unresolved.
Base: bef81dcc (merged media wizard). Branch: codex/media-fal-credential-alias. Serial successor #1300; independent of Ingest #1299.
Exact write lease: this handoff, apps/live_control_server/routes/media_images.py, tests/test_media_image_generation.py.

Invariant: Buddy's nonempty DUNGEONBUDDY_FAL_KEY takes precedence over generic FAL_KEY for its media generation client; key values are never returned, logged or passed to the browser. Whitespace-only dedicated values fall back to the generic key. Existing operator authentication remains required. Check capabilities and generation against the same resolution rule.

Acceptance: provider-free tests cover dedicated-only, generic fallback, dedicated precedence and empty/missing values, client construction and route forwarding. Run owning endpoint tests, Ruff and diff check; publish a bounded corrective PR. No serving changes or credential-file writes.

Live smoke evidence (local, no private key content): one GE GPT Image 1.5 low-quality 1024×1024 operation failed in 0.45s with PROVIDER_ERROR; subsequent read-only authenticated fal model metadata request returned HTTP401. No image was returned. Credential authentication remains unresolved; adding an alias is not a claim of a working key.

Verification: 13 owning tests independently pass; scoped Ruff and diff check pass. No credential-file writes, serving restart or subsequent inference retry.
