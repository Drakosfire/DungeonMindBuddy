# SURFACE — route image prompt preparation to discussion

ACTIVE serial PRIME successor from 8dc5c44fb3c80be8a5d1037b0be30fe979f76c4a,
branch codex/surface-image-prompt-intent, existing buddy-context-loop checkout.
Operator goal authorizes ordinary grounded image-prompt→Studio completion. Current
open PR census has no overlapping active implementation.

Architecture critique 01a164f6-0365-7021-9809-d932e66b421e: classify requested artifact
and destination, not any mention of an image. An image prompt is discussion that
can produce the existing typed image_prompt proposal. A scene describing an image
is Plan prose. Explicit Plan/page insertion or editing, including mixed image and
insertion requests, retains proposal preview. No implicit generation or mutation.
Manual correction for the exact message and action continuation keep precedence.
Read-only Play and Build submission gates remain their owning paths.

Extract the existing pure classifier into agentInteraction/surfaceComposerIntent.ts
and update its caller and tests directly; do not retain a compatibility re-export.
Use bounded image-artifact recognition and explicit destination precedence; do not
introduce another routing layer, intent API, provider call, schema, caps or automatic
Generate/Save/Apply. The existing Studio workflow remains explicit.

Lease: this handoff; apps/live-control-ui/src/agentInteraction/surfaceComposerIntent.ts
and its focused test; planSurface/components/WorldPlanAgentConversation.tsx;
planSurface/WorldPlanAgentConversation.worldHistory.test.tsx; predecessor
HANDOFF-AGENT-jev-dialogue-read-boundary.md and ROADMAP-demo.md settlement.
One exact-head Bugbot-reviewed PR, PRIME merge and guarded paired 8000/5202 delivery;
Core617635c and APP0045 unchanged.

Verify minimal pairs, polite phrasing, explicit destination and mixed requests,
negative insertion wording, unchanged manual correction/continuation precedence,
mounted ordinary submit→typed image prompt→Studio handoff with no edit/apply or
image side effect before explicit action. Retain existing stale/foreign/busy image
host checks. Live follow-up must display Send without manual mode correction and
open the generated prompt in Studio. Reuse retained artwork where generation is
not needed to verify this routing repair; prior actual Generate/Save/restart remains
valid but does not establish the full adventure goal.
