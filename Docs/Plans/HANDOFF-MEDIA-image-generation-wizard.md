# MEDIA — Reusable image generation wizard

Status: ACTIVE — operator requests prompt/model/parameter image generation via existing fal credential and GenerationEngine, hosted in reusable media UI. PRIME implements; independent review before merge.
Base: Buddy 168938813fd4b15ff00277142cce51dc50696b97.
Branch: codex/media-image-wizard. Topology: serial consumer of accepted GE #24 merge 7e3ed2202684316c6d426462f4928824bb2e99ca; independent of DOGFOOD Ingest PR1299.

## One capability

Generate and preview/download an image through a reusable media wizard, first hosted in Build. The host supplies no map-specific generation logic. Prompt → model/settings → explicit paid Generate → preview. Result remains in the component until downloaded; no automatic document insertion/save, graph assertion, or claim of durable asset publication. This initial prompt-only image capability does not adopt the old map layout/inpainting/project editor.

GE owns model wire mechanics and call observations. Buddy owns model choices, prompts, UI, auth, result presentation. Existing SERVER map/image code provides reference patterns; no SERVER contract changes or Cloudflare dependency in this slice.

Exact write lease: this handoff; pyproject.toml; uv.lock; apps/live_control_server/main.py; apps/live_control_server/routes/media_images.py; tests/test_media_image_generation.py; apps/live-control-ui/src/api/liveApi.ts; apps/live-control-ui/src/media/MediaImageWizard.tsx; apps/live-control-ui/src/media/MediaImageWizard.css; apps/live-control-ui/src/media/MediaImageWizard.test.tsx; apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx.

## Invariant / failure cases

Only explicit Generate submits a paid request. Existing local operator auth is required independent of World facts/Graph toggle. Expose only controls supported by selected model; never resend on ambiguous transport failure. Preserve prior preview on error; prevent duplicate button submission while pending. Closing warns that undownloaded results are transient. No provider key reaches browser. Report actual/unknown usage honestly. Host callback/component reuse must not depend on Build document state.

## Verification

Provider-free endpoint auth/validation/forwarding and encoding result tests; rendered wizard model-dependent controls, one explicit call and failure behavior; Build host leaves editor unchanged. Compile/build and inspect cumulative diff, finish PR. Existing typecheck failures stay explicit. No 5202 restart or live provider call until reviewed; separate runtime rollout.
