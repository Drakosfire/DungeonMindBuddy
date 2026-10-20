# Shared Plan/Play card paper layout

Status: COMPLETED; exclusive source lease released. User authorizes shared width/layout across Plan Cards and Play,
review, merge and5202 delivery. Owner PRIME/Buddy UI. Base42093c69c; serial onePR,
reused buddy-context-loop checkout branch codex/shared-card-paper-layout. Current
open PRs inspected; no overlapping current source lease.

## Exclusive source lease
- This handoff
- apps/live-control-ui/src/shared/SceneCard.tsx
- apps/live-control-ui/src/shared/sceneCard.css
- apps/live-control-ui/src/shared/SurfaceCardLayout.test.tsx
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

## Review correction
Architecture Cycle1 HOLD at a087095bfea0a3cfea2e5583dcf50e0bdd8885b4:
shared-scene body width alone does not cover Play beat/decision/option/consequence
play-body readers. Extend the shared paper body contract to those readers, retaining
outside-rail and media sizing. Add rendered-reader CSS cascade regression evidence
before the second exact-head review; no merge/adoption of held head.

## Current-contract cleanup — operator steering
The operator explicitly states there is no backwards compatibility support. Shared
layout #1477 merged a60b8dc99e7158837f88c3d3bcfb12d5fd47ad0e, source approved Cycle2
955a7227f4aa98b7c14a26cda88c733fa306a072. Real desktop/narrow Plan/Play and synthetic
actual-component beat/decision readers with production CSS passed; Document's
reading width/padding/text stayed unchanged. Before completion, a serial bounded
cleanup PR updates stale adapter harnesses to the current surface/Contents contract,
removes its v1 compatibility case and obsolete Plan-only padding override. No new
compatibility shim or runtime fallback. Existing content parsers are outside this
card-layout slice; this instruction does not authorize deleting stored documents.
Additional exclusive path: apps/live-control-ui/src/shared/SceneCard.adapters.test.tsx.
The shared sceneCard.css and this handoff remain in lease. Reused checkout branch
codex/current-card-layout-tests from1477 merge. Independent review and regression
verification remain required. No additional runtime changes/deployment inferred.

## Final acceptance — 2026-10-19
#1477 merged a60b8dc99e7158837f88c3d3bcfb12d5fd47ad0e after Cycle2 source approval
955a7227f4aa98b7c14a26cda88c733fa306a072; Cycle1 HOLD resolved Play body coverage.
#1478 current-contract cleanup merged cd3be349489107a5d90ab6b33f2d1b4ac6ea5d0a after
Cycle1 approval081e7ae570c1e3f21a6c5cd1a02ae2c02d670f1b. All85 selected tests pass,
independently rerun by Architecture. Build passes (existing chunk warning);2 Plan
integration cases emit act warnings,18 older integration cases not selected. Five
adapter failures from1477 are repaired for the current contract, not waived or shimmed.

Final5202 indexSHA256889ec7ac570100df65f0f4c9f57cae17a579ddb7b0c0cee16e2bef923902a067.
Real Plan desktop paper972px/body906px (prior inner paper739px); collapsed Contents
paper1136px/body1070px. Document width739px,40pxpadding and text identical to baseline.
Document/Cards retains selected First sight; QA returned to Journey north. Narrow666px
Plan paper600px/body557px; Play paper530px/body496px, no page overflow. Real Play desktop
paper1050px/body984px. Shared paper owns each card's inner width with intentional padding.
Actual shared React beat/scene/decision/option/consequence markup rendered in a temporary
synthetic HTML fixture using served production CSS at1422px and666px: all5 reader max-widths
none; explicit55%image width retained, no page overflow. This fixture verifies rendering
and CSS, not interaction or persistence. Fixture removed from served assets; unique private
HTML evidence retained. No separate preview/service/environment created.

All13 protected responses (Plan, Run, review, notes, active selection and other protected
stored material) stayed identical before both rollouts and after width acceptance. No API
restart/provider call. All QA tabs closed and viewport reset. Final screenshot inspected.
