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
