# CLEANUP: current Live Control command-refresh fixture

Status: ACTIVE under standing cleanup implementation/review/merge authorization.
Base98d3157a09790e5a53a851b9ea24a5de51bd2aa5; serial after #4099,
no unmerged dependency. Existing isolated checkout; no ports/providers/databases.

## Invariant and lease

The supported legacy /surface Inspector accepted-command callback must refresh
current session data. LiveControlApp now loads through getSurfaceSessionViews();
App.commandAccepted.test.tsx still mocks only the pre-batch getSurface/events/jobs/
Plan helpers and fails before reaching its callback. Mock the actual typed batch
facade, supply distinct initial/refreshed state, and verify the real App callback
refreshes both facade calls and props delivered to the mocked SurfaceShell.
Keep callback wiring real; do not mock LiveControlApp or weaken accepted refresh.
This is client orchestration evidence, not actual API transport/command write proof.

Exclusive writes: apps/live-control-ui/src/App.commandAccepted.test.tsx; this brief;
HANDOFF-CLEANUP-lab-combat-navigation.md for truthful #4099 settlement. Runtime,
API, route, provider, schemas, manifests and other test files are read-only.
All61 current open heads have no changes to this test or LiveControlApp. Related
App/appNavigation integration files remain owned by #2405/#2219 and are excluded.
Reader/Markdown repairs are already in held owner #2298 and must not be duplicated.

## Verification

Focused parent/current callback test and safe local session-view API regressions
under global frontend lock using external task source. Prove exact initial and
post-accept batch data and expected refresh calls. A task-local no-refresh mutation
must fail rather than pass on the initial render. No actual command/provider writes.
Run exact-head repo hosted/build/validator and full discovered diagnostic; compare
against14ccffc887d938e1c90caf96b822f0c134282351 (prove actual parent source identity).
No ID additions/omissions/new failures/changed remaining leading messages; only
this intended failure may resolve. Keep130 inherited failures, conditional inventory
extras and earlier quote observation red. Independent exact-head source/evidence
review before merge; no backend/local Chat/browser/release qualification claim.
