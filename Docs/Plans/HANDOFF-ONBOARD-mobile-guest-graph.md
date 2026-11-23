# ONBOARD: readable mobile guest graph

Status: MERGED on main in #4574 (`75f1246480c22bab0306fb7b8145dcf070347972`).
Serving adoption proceeds through #4575. The owner-authorized Sizzek onboarding goal includes a usable
signed-out demo on mobile. Production inspection at 390px showed the four-column
graph forcing names such as “Sizzek’s Carnival” and “Festival of Light and Gifts”
into unreadably narrow shapes. This serial implementation starts from the fetched
main branch in `codex/onboard-mobile-graph`; no production runtime is leased.
The open PR inventory contains no competing guest-page implementation lane.

Render the same released and temporary graph with two columns on narrow screens,
keeping lines, selection, sources, sandbox actions and desktop behavior intact.
Labels must fit their nodes without overlapping neighbors, including long guest
input; full names remain available to assistive technology and in details.
Write lease: this handoff, `GuestReleasePage.tsx`, `guestReleasePage.test.tsx`,
and `guestReleasePage.css`. No backend, schema, release content or auth changes.

Verify graph positions and interactions with focused tests, and inspect desktop
and mobile rendering with realistic long names. Run the repository's exact-SHA
hosted and discovered frontend checks, document inherited failures, and obtain
independent Bugbot review. Serving adoption follows serially from the actual
deployed guest-label image after re-anchoring its runtime and active lanes.
