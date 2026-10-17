# MEDIA: one creation workspace with visible retained results

Status: ACTIVE. PRIME owns implementation, review dispatch and coordinated local
5202/API delivery under the operator's current Image Studio dogfood request.
Base: origin/main@590686f5d5c7933480d7e57ce080bddf4f4fc473.
Branch: codex/media-studio-workspace; reuse buddy-context-loop and dependencies.
Topology: parallel-independent of frozen review #1378 (draft recovery); no shared
runtime code paths. Inspect open PRs: no other active media implementation lease.

Outcome: prompt and model/settings share one workspace; compact floating toolbar;
library remains browsable during generation; thumbnail cards preserve text; an
obvious completion thumbnail opens its retained image. Browsing must not replace
an in-flight request's captured input or steal a newer generation's completion.
Do not hide errors or claim retention/CDN success before owning acknowledgments.
Investigate actual prepared-generation retention failure without paid replay.
A serialized UUID in provenance is a concrete suspected boundary fault; verify
with the real route/storage JSON admission before fixing. Keep identities,
owner checks, upload fencing and explicit placement/save unchanged. No schema,
provider contract, credentials, server data or existing draft changes.

Exclusive write lease:
- this handoff
- apps/live-control-ui/src/media/MediaImageWizard.tsx
- apps/live-control-ui/src/media/MediaImageWizard.css
- apps/live-control-ui/src/media/MediaImageWizard.test.tsx
- apps/live_control_server/routes/media_images.py
- tests/test_media_image_generation.py

Verification: pending generation + library browse/select + completion, explicit
single submission, retained previews/errors, thumbnail reads without generation,
prepared request passes actual JSON provenance admission, owning suites/typecheck/
build, cumulative exact diff and independent ARCHITECTURE review. Existing
checkout .pytest_cache evidence only; no /tmp, new checkouts/deps or previews.
Delivery preserves Edge local drafts and retained media; no forced user reload.
