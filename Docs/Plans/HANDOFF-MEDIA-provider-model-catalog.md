# MEDIA — Provider discovery and current image choices

Status: ACTIVE — ARCHITECTURE independently found no blocker at GE #25 head 7bb66c157ba0d926bd013b86e528223c5c8373b8 and accepted the Buddy consumer boundary. Final GE Bugbot supplement and merge remain gates before Buddy merge/runtime adoption. Operator requested current models and GE catalog discovery with Buddy owning selection. PRIME implements; ARCHITECTURE independently reviews; existing checkout buddy-context-loop only. No new checkout/environment. Base edf13b808b06a709212aab4c43a98ce23f13cf50. Stacked across repositories: immutable GE prerequisite #25 head 7bb66c157ba0d926bd013b86e528223c5c8373b8 → Buddy consumer; merge GE first, then pin its accepted merge revision before Buddy final review/merge. PRIME activates implementation after independent boundary acceptance rather than idling on supplemental review.

## Product contract

GE owns authenticated fixed-origin provider discovery and adapter wire controls. Buddy owns curated recommended choices, default and exposed settings. Preserve distinction between catalog-listed, GE-executable and Buddy-selectable. Default GPT Image 2.5 Flare; offer Sunburst and Nano Banana 2.1 alongside existing choices. No universal quality ranking. Existing saved provenance never relabels an older image.

Authenticated GET /api/live/media/images/catalog reads one GE page with pagination and server-side credential; adds Buddy selectability. Discovery never calls generation, storage or document writes. Catalog is explicitly requested from model settings; regular capabilities remain fast and do not depend on a remote read. Failures show unavailable, never fake fresh data. UI may select only Buddy-supported aliases and formats/controls. Model selection and browsing never regenerate. Preserve prepared prompt, preview, explicit Generate/Save/Insert and document Save boundaries. Nano uses provider 1K resolution and chosen aspect ratio; do not imply exact output pixels.

## Exact active write lease

This handoff; Docs/Plans/HANDOFF-MEDIA-agent-build-image.md (settle predecessor truthfully); pyproject.toml; uv.lock; apps/live_control_server/routes/media_images.py; tests/test_media_image_generation.py; apps/live-control-ui/src/media/MediaImageWizard.tsx; apps/live-control-ui/src/media/MediaImageWizard.test.tsx; apps/live-control-ui/src/media/MediaImageWizard.css.

## Verification and delivery

API tests exercise authorization, paging, sanitized failure, no inference on discovery and current model controls. UI tests exercise server default, explicit discovery/selectability, paging, errors and no generation on browsing. Existing media tests, typecheck, production build, cumulative diff inspection. Commit/push/open one Buddy PR, exact-head independent review before merge. Update GE pin only to accepted immutable revision; no schema changes. After review, reuse current serving export/env/UI output and same 5202/API8000 units; verify APP0032 unchanged, matched runtime bytes and real dropdown/catalog without image generation. Preserve user tabs and drafts; no automatic reload/save/discard. Stable5876/API8002 and Ingest/Graph data untouched. DOGFOOD retains Ingestion.

Predecessor #1306 accepted by ARCHITECTURE at 3dd2f52adac6e1052f8daf063bbf3bdae51c8fd5, merged edf13b808b06a709212aab4c43a98ce23f13cf50 and adopted on 5202/API8000 with APP0032. Live Edge discussion prepared a prompt and opened/reopened its wizard; no image generated. Its implementation lease is complete; this slice owns the listed media paths.
