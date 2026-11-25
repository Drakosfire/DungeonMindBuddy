# Read-only media test diagnostic repair

ACTIVE: user requested frontend diagnostic repair and Trace deployment. Serial slice `codex/frontend-readonly-media-tests` based on `origin/main` at `ffb90394e34eaf9c44a250a71a36fabfa93524d0`, after merged #4764. Scope: `ReadOnlyBodyContent.test.tsx` and this brief.

Seven tests fail before their intended saved-media assertions because the test replaces the entire live API module with only `authenticatedApiFetch`, omitting the current access-generation export. Preserve the real module exports and mock only the fetch boundary. Return the current real access generation and a complete response from the successful metadata fixture so the existing stale-access checks remain active. Do not weaken the URL, identity, error or access assertions; change no product behavior.

Verify the complete affected file, exact-SHA hosted suite and discovered diagnostic with base comparison; obtain independent exact-head review. Remaining diagnostic suites continue as later serial slices.
