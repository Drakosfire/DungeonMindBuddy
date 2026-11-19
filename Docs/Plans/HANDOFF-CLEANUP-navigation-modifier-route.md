# CLEANUP: navigation modifier current-route witness

Status: ACTIVE under the standing cleanup goal's implementation, independent
review and merge authority. One serial PR; base
`a043765dbbf69d3eee9a90948e9806debdf400c0`, existing isolated checkout, branch
`codex/navigation-modifier-current-route`. No runtime resources allocated.

## Scope and coordination

Exclusive writes: this handoff; the single modifier-click case in
`apps/live-control-ui/src/test/appNavigation.test.tsx`; predecessor
`HANDOFF-CLEANUP-app-session-fixture.md` for truthful completed-record removal.
The predecessor merged in #4127 at the base above; its exact head and merge
trees match, independent review approved, hosted1406/build/validator passed,
full8126pass109fail2pending. Git history retains its assignment.

All59open PR paths inspected. #2405 owns only obsolete API wrapper mock/setup
seams in the navigation file; leave those unchanged. #2298 fixtures, current
Plan/Build/Play runtime, route suites and classification remain excluded.

The modifier-click case starts at `/` and expects workspace AppChrome there.
Current root intentionally renders the landing page, so the test never reaches
its click contract. Start at `/ingest`, wait for its real existing heading,
then require the same actual navigation controls, right-click and Ctrl-click
behavior, unchanged pathname and no intercepted navigation history.

Critique: do not mock navigation, replace the App, dispatch a different click,
or weaken the pathname/history guards. Do not use this repair to claim landing
navigation, Plan/Build/Play admission, or the other obsolete root tests pass.
Preserve all other test bodies byte for byte. No production or API change.

## Verification

Exact full baseline: #4127 head6805578a53c41ae5a93e91d0903f292e18745c05,
whose entire tree equals this base. Verify current case plus full default
discovery (unchanged IDs, no new failures), hosted/build/validator and independent
exact-head review before merge. Retain red inherited failures and external raw
evidence on verified Projects storage. No live services/providers or data.
