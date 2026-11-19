# CLEANUP: navigation modifier current-route witness

Status: ACTIVE under the standing cleanup goal's implementation, independent
review and merge authority. One serial PR; base
`63cdb5d279d9bd279d3b83ebe5faf10c9f147a0a`, existing isolated checkout, branch
`codex/navigation-modifier-current-route`. No runtime resources allocated.

## Scope and coordination

Exclusive writes: this handoff; the single modifier-click case in
`apps/live-control-ui/src/test/appNavigation.test.tsx`; predecessor
`HANDOFF-CLEANUP-app-session-fixture.md` and
`HANDOFF-CLEANUP-work-plan-adopt-readiness.md` for truthful predecessor settlement.
The first predecessor merged in #4127 at a043765dbbf69d3eee9a90948e9806debdf400c0; its exact head and merge
trees match, independent review approved, hosted1406/build/validator passed,
full8126pass109fail2pending. Git history retains its assignment.

The initial navigation full run resolved its case but exposed a saved-review
readiness variant. That repair's full run exposed a separate Build initialization
variant. Both raw failures are retained. Controlled old/new witnesses established
the distinct readiness boundaries; reviewed #4134 merged331aa1beae7bafea386194aadde4ca814f4a990d,
then reviewed #4131 merged at this base. Its entire tree equals exact reviewed
c33349fcee169174333be71dda65d205f4d6e7d7: hosted1406/build/validator passed,
full8126pass109fail2pending with unchanged existing results. Remove the completed
saved-review assignment; Git history preserves it. Neither variant earned
persistent failure-reduction credit. Requalify this integrated navigation head.

All59open PR paths inspected. #2405 owns only obsolete API wrapper mock/setup
seams in the navigation file; leave those unchanged. #2298 fixtures, current
Plan/Build/Play runtime, route suites and classification remain excluded.

The modifier-click case starts at `/` and expects workspace AppChrome there.
Current root intentionally renders the landing page, so the test never reaches
its click contract. Start at `/ingest`, wait for its real existing heading,
then require the same actual navigation controls, right-click and Ctrl-click
behavior, unchanged pathname and no intercepted navigation history.
Ctrl-click targets Plan from Ingest, preserving a different-route transition;
aiming at the active route would vacuously pass via the normal same-route no-op.

Critique: do not mock navigation, replace the App, dispatch a different click,
or weaken the pathname/history guards. Do not use this repair to claim landing
navigation, Plan/Build/Play admission, or the other obsolete root tests pass.
Preserve all other test bodies byte for byte. No production or API change.

## Verification

Exact full baseline: #4131 headc33349fcee169174333be71dda65d205f4d6e7d7,
whose entire tree equals this base. Verify current case plus full default
discovery (unchanged IDs, no new failures), hosted/build/validator and independent
exact-head review before merge. Retain red inherited failures and external raw
evidence on verified Projects storage. No live services/providers or data.
