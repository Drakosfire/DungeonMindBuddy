# Shared Plan/Play card paper layout

Status: ACTIVE. User authorizes shared width/layout across Plan Cards and Play,
review, merge and5202 delivery. Owner PRIME/Buddy UI. Base42093c69c; serial onePR,
reused buddy-context-loop checkout branch codex/shared-card-paper-layout. Current
open PRs inspected; no overlapping current source lease.

## Exclusive source lease
- This handoff
- apps/live-control-ui/src/shared/SceneCard.tsx
- apps/live-control-ui/src/shared/sceneCard.css
- apps/live-control-ui/src/shared/SurfaceCardLayout.tsx
- apps/live-control-ui/src/shared/surfaceCardLayout.css
- apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx
- apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx
- apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.tsx
- apps/live-control-ui/src/playSurface/playSurface.css

Shared stable paper container owns full available width, padding and surface skin.
Plan enables card layout only in Cards; remove its nested82ch paper cap/doubleframe
there. Document keeps existing reading-width presentation. Read-only Plan SceneCard fallback also uses the shared paper rather than a duplicate skin.
Play reuses same paper
container, removes duplicated skin/width rules. Existing editor/scene children stay
mounted while toggling modes; no writer, media, content or progress changes. Empty
and diagnostics still work. Do not stretch explicitly sized media objects.

## Gates
Build and owning Plan continuity integration, shared/deck and Play cockpit/SceneCard
adapter tests. Independent exact-head cumulative review before merge. Real5202
Plan/Play desktop and narrow widths, open/collapsed Contents, retained scene/Document
position and13 saved-state responses unchanged. Adopt existing UI artifact with old
assets retained; no API restart/provider calls. Settle source lease after acceptance.
