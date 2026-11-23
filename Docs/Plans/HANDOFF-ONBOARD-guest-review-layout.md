# ONBOARD: preserve graph space during owner release review

Status: ACTIVE. Authorized by the user's request to deliver Sizzek onboarding
and the observed live graph layout. Serial after #4498 (merged main at
`a8817976a6f8b1ae2f31ff1a0ea087941878f392`) and serving integration #4503.
Base `a8817976a6f8b1ae2f31ff1a0ea087941878f392`, branch
`codex/onboard-guest-review-layout`, this checkout. No production runtime,
World, database, port or flag is leased.

On the signed-in Graph page, the always-rendered owner review is a flex sibling
of the graph inside a fixed-height workspace. A live desktop observation showed
it consuming most of the available height and leaving the graph a narrow strip.
Keep the graph usable and let the owner deliberately open and close a scrollable
review panel. Preserve the existing review and preparation behavior, privacy
checks, keyboard access and state when the panel is open. No guest release or
publication change is included. The panel may cover the graph while open but
must not reflow or compress it; use viewport-bounded layout on desktop/mobile.

Write lease: this handoff, `BuddyApp.tsx`, `guestRelease/GuestReleaseDrawer.tsx`,
its focused test, guest-review CSS and focused browser tests. The concurrent
#4502 source integration was inspected and does
not touch these paths; runtime cutovers remain serial and are not part of this
PR. Validate exact-head hosted and full-discovered frontend contracts, with an
exact-base comparison for failures, and browser witnesses at desktop and mobile
showing graph height before/after opening, review scrolling and closure. Inspect
the cumulative diff and obtain independent Bugbot review. The full onboarding,
release approval and deployed guest view remain open successors.

The focused test is added to `ci/test-classification.json` so the existing
guest-release hosted selector retains its classification guard; this metadata
file is included in the write lease.

Working-tree diagnostic: the focused drawer test and production UI build pass
in an isolated dependency copy. A synthetic two-node Graph preview with a
local owner-review fixture was checked in Chromium at 1440×900 and 390×844:
the Graph canvas measured 776.625px and 220px high respectively, unchanged
when review opened; the panel stayed within the viewport, scrolled, and opened
and closed via mouse and Enter. Script and screenshots are retained under
`/home/drakosfire/Projects/.codex/buddy-check.context-node.PZxr2H/` as
`drawer-visual-check.cjs`, `drawer-desktop.png` and `drawer-mobile.png`.
The preview uses synthetic responses and is not deployed-owner acceptance.
The first jsdom keyboard attempt failed because that environment did not toggle
native `summary` on Enter; native keyboard behavior was checked in Chromium.
Exact-source qualification and independent review remain outstanding.

Follow-up diagnostics: the Chromium witness now actually scrolls the panel and
checks Enter open/close, with results in `drawer-visual-result.log`. The focused
test now checks that an in-progress review input survives close/reopen. The CI
contract guard passed 17 tests with Node 22.23.0 on PATH; an initial run without
Node on PATH had 14 passes and three environment failures. The synthetic graph
and review remain fixtures, not deployed acceptance.
