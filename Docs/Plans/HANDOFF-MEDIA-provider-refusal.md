# MEDIA: actionable normalized image refusal

ACTIVE · PRIME · serial successor to merged GenerationEngine #34
(7c929082bfa9b8c5af9815e6429db5230d9caefe). Buddy base
96e5635611532e3730894cc0b4dc5e543f9b9ca8, existing buddy-context-loop checkout,
branch codex/media-provider-refusal. Open lanes checked: no media overlap.

Outcome: adopt the merged GE dependency and translate its existing PROVIDER_REFUSED
code into an actionable image-studio/contextual-edit message. GE alone interprets
provider wire errors. Buddy does not parse payloads, infer refusals from prose,
retry automatically, change prompts, or switch providers. Preserve original images,
failed attempts, authorization, integrity and all other error behavior.

Writes: pyproject.toml, uv.lock, apps/live_control_server/routes/media_images.py,
tests/test_media_image_generation.py, this handoff. No schema or frontend changes.
The predecessor Image Studio slice #2370 is merged/delivered and its write lease
is released; private retained-image placement/reload proof is preserved.

Validation: generate/edit route refusal versus unknown-failure contrasts, actual
SDK→GE→route provider-free replay, lifecycle/no stage or upload, unchanged parent.
Owning media PostgreSQL checks and relevant generation consumer regressions.
Exact-head independent Bugbot; commit/push/PR/merge under standing authority.
Stage the reviewed GE wheel in an immutable dependency overlay for the owned API
release; never mutate dependencies of a running process. Protected API delivery
with health/database/retained-state proof. UI remains unchanged. No new provider
call or corpus transfer is selected by this work.
