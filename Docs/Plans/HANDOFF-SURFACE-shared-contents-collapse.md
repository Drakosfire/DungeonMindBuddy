# Shared Contents book and collapse interaction

Status: ACTIVE. Owner: PRIME / Buddy surfaces. User explicitly authorizes shared
Plan/Play Contents implementation, review, merge and delivery on 5202.
Base: 5bfe65b77 (resolve full origin/main); branch codex/shared-contents-collapse.
Topology: serial, one PR, reused buddy-context-loop checkout. Open PRs inspected;
no overlapping current shared Contents lease. Predecessor #1473 completed.

## Exclusive write lease
- This handoff
- apps/live-control-ui/src/shared/Contents.tsx
- apps/live-control-ui/src/shared/Contents.css
- apps/live-control-ui/src/shared/Contents.test.tsx
- apps/live-control-ui/src/planSurface/components/PlanCardDeck.test.tsx
- apps/live-control-ui/src/playSurface/currentMoment/PlayCockpitPanels.tsx
- apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.tsx
- apps/live-control-ui/src/playSurface/playSurface.css

## Contract and risks
One shared native book toggle and shared disclosure/focus behavior for both
surfaces. Escape collapses and returns focus. Narrow selection dismisses the
panel; desktop selection retains it. Retain each surface's responsive layout
owner and Play overlay coordination. Hiding Contents must not unmount editors,
change current Run progress, scene cursor, drafts, notes or saved documents.
No API/storage/provider changes. Shared IDs must remain unique. Preserve existing
Play focus refs and test hooks while removing its duplicate toggle markup.

## Gates
Focused shared/Plan deck/Play cockpit tests; production build; cumulative diff
review by Architecture; exact approved-head merge. Adopt existing 5202 UI dist
with prior assets retained, no API restart. Verify desktop/narrow both surfaces,
mouse/keyboard toggle and scene continuity; all protected stored responses and
active selection unchanged. Postmerge settle handoff and release lease.

## Rendered gate correction
PR #1474 merged at 51e1c0970eab2c512a59272116952921b1f342f2;
Architecture Cycle 1 approved 9e76fb3e6fca7306867fd95fea33f7c5818c2f8b.
Desktop source behavior and 76 tests passed, but narrow 666px rendered acceptance
found dismissal focus targeting a hidden navbar Contents opener. Delivery is not
accepted yet. Same bounded capability continues serially in correction branch
codex/shared-contents-focus-fallback from that merge, one correction PR. Existing
lease remains ACTIVE, including shared and Play files/tests. Add a visible-opener
fallback in the shared dismissal contract; Play supplies More as fallback. No API,
stored state or provider changes. Review correction independently before adoption.
