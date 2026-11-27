# Build saved-conversation fixture diagnostic repair

ACTIVE: user requested frontend diagnostic repair and Trace deployment. Serial test-only slice `codex/frontend-build-conversation-fixture`, based on `origin/main` at `2b958a727ab4231dec1533bd250f839d5536ae8f`, follows merged #4780. Scope: `BuildCompose.integration.test.tsx` and this brief.

Two integration tests fail because their shared harness mocks the retired full-history read but leaves the current active-message endpoint unmocked, causing an unavailable history state. Supply a valid, owner-matched active-message fixture at the current API boundary and retain the durable proposal, no automatic insertion, no lost edits, and no extra history read assertions. No runtime, provider, authentication, or database change.

Run the complete integration file, exact-head hosted and discovered diagnostics compared against the prior integrated baseline, and obtain independent exact-head review. Other frontend failures remain in later serial slices.
