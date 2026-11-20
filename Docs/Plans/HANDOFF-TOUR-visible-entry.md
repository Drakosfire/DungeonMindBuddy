# TOUR — visible guidance entry

SETTLED: reviewed168a819bcb86949471359a730c644226825edd3c; PR1922 merged74e59171b15b9eaae30f97eb5589ad90c6ea172b, UI-only delivered5202. Independent Bugbot approved after stale-World read fix;191owningtests/typecheck/build+3CI pass. Live visible Resume opens saved2of15 Sheep guidance; narrow header fits. All4139APP/371native rows/41067files retained; API/schema unchanged. Evidence: private runtime-evidence/tour-visible-entry-1922 and PRIME tour-entry-1922 screenshots. Anchored popup and operator acceptance remain unfinished.

Former serial UI-only slice under PRIME's standing guided-tour goal. Base ba7a64c9f602258e9617b00f1987afc0fb1040e4, branch codex/tour-visible-entry, existing buddy-context-loop checkout/dependencies. Independent architecture_review_1197 approved this invariant before implementation. Open ingestion1853/1855/1868, hosted1828 and held1764 are separate; no overlapping UI lease found.

## Invariant
Always show one guidance entry in compact navigation. Existing GuidedTourProvider exclusively derives Start tour (resolved, no record), Resume tour (current v3, including paused/exited), Review tour (historical read-only), or neutral Open tour (unreadable, unresolved or changed World). Navigation does not read storage or create another authority. Opening only invokes the existing panel; no automatic start/resume, binding, domain command or storage write. Remove the duplicate hidden menu entry. Keep keyboard access and narrow layouts usable.

## Exclusive paths and gates
This handoff; native-read-controller-feedback predecessor settlement; apps/live-control-ui/src/guidedTour/GuidedTour.tsx; apps/live-control-ui/src/chrome/CompactAppNavigation.tsx, .css and .test.tsx; guidedTour/Navigation.integration.test.tsx (existing route test must use the replacement visible entry). Verify real-provider navigation integration for new/current/paused/exited/historical/corrupt guidance, World switching and zero writes on open. Existing tour tests, typecheck/build; exact cumulative independent Bugbot and CI. Commit/push/open one PR, merge under PRIME authority after gates, deliver UI only with API/schema/data unchanged and inspect live desktop/narrow layout. No new tour protocol, model, provider, runtime API or database lease.

This delivers discoverability only. Anchored popups are the next separate capability; tour and complete journey operator acceptance remain open. ADVERSARY's independent ingestion preflight proceeds without waiting for this UI work.
