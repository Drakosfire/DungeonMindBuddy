# TOUR — keep teaching visible over ordinary conversation

ACTIVE: PRIME serial UI slice under the continuing guided-tour goal. Branch
codex/tour-conversation-layer from fetched6c7382ed7076ebae2b84678015d9f4ec42eaba56,
reused buddy-context-loop/shared dependencies. Open ingestion1853/1855/1868,
hosted1828/held1764 inspected: no overlapping allocation.

## Demonstrated defect and invariant
Live PR1925 verification focused the actual message box, but the conversation
stack (980) covered the guidance panel and coachmark (130). Mouse Show control
hit the conversation; keyboard activation created a geometrically correct popup
that was invisible behind it. Preserve that failure and correct the owning CSS.
Both teaching surfaces must be above ordinary conversation and detached projection
chrome, with no fullscreen/top-layer/confirmation authority change. Use1100 above
conversation980/projection1000, below contextual actions1500. Native browser modal
top-layer remains above this ordinary CSS layer. The popup still avoids its target;
no backdrop, focus trap, domain action or completion authority is introduced.

## Exclusive expected write lease
This handoff; apps/live-control-ui/src/guidedTour/guidedTour.css only (two layer
values and truthful comment); predecessor HANDOFF-TOUR-memory-composer-anchor.md
settlement. No selectors, geometry, portals, protocol, backend, providers or data
changes. One small PR; no added capability.

## Proof and delivery
Existing tour/coachmark tests, typecheck/build, independent exact cumulative
Bugbot and CI. Protected UI-only5202 delivery preserves API/schema/all retained
state. Actual mouse Show control while chat open, popup hit-test/visible screenshot,
nonoverlap with textarea, retained unsent draft close/reopen, no submission. Test
narrow layout too; restore the original draft and guidance selection. Full tour
and operator acceptance remain open.
