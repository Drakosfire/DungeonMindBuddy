# Build proposal review test diagnostic repair

ACTIVE: user requested frontend diagnostic repair and Trace deployment. Serial test-only slice `codex/frontend-build-compose-tests`, based on `origin/main` at `de569eb18a8040bd395af1f039722ca763d09524`, follows merged #4777. Scope: `BuildCompose.integration.test.tsx` and this brief.

Several saved-proposal integration tests still locate the retired `Keep on page` label. The current proposal review widget uses `Save`, scoped within the `Proposed page change` region. Update the selector to the current accessible control while retaining insert, dirty-state, revision, no-auto-save, reload and intervening-edit checks. Do not change runtime or bypass proposal review. Any separate failing conversation/recovery fixture is outside this slice unless independently proven to have the same cause.

Run the affected integration tests, exact-head hosted verification and discovered diagnostic against prior integrated source, and obtain independent exact-head review. Remaining failures continue as separate serial slices.
