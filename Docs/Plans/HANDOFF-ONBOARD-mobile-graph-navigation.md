# ONBOARD: reveal graph details on mobile

Status: ACTIVE. After #4575 deployed the two-column graph, a signed-out 390px
production check showed that selecting a point only highlights it: the matching
connections and sources remain below the full graph and sandbox form. The
owner-authorized onboarding goal calls for visitors to explore those connections.

Serial main implementation in `codex/onboard-mobile-graph-navigation`, followed
by serving adoption based on the actual deployed image. On narrow screens, bring
the detail panel into view when a visitor selects or adds a point and provide a
way back to the graph. Preserve desktop behavior, point/source deep links,
temporary additions, reset, keyboard focus and source navigation. The write set
is this handoff, `GuestReleasePage.tsx`, `guestReleasePage.css` and its focused
test. No API, auth, database, schema, release content or provider changes.

Verify phone and desktop interactions with released and temporary points,
sources, back navigation and reset; run the exact-SHA hosted and discovered
frontend suites and compare inherited failures; obtain independent Bugbot
review. Re-anchor serving and runtime state before the serial release.
