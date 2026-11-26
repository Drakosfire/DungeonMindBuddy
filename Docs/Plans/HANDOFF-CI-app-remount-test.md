# App route-remount diagnostic repair

ACTIVE: user requested frontend diagnostic repair and Trace deployment. Serial test-only slice `codex/frontend-app-remount-test`, based on `origin/main` at `0d86202adfd0ad120309d4363f37ccfaac3bbfde`, follows merged #4784. Scope: `App.test.tsx` and this brief.

The route-remount test expects the old committed-page reader for normal Build editor entry. The current controller explicitly reads the workspace editor snapshot for default entry and uses committed-page reads only for bound/pinned cases. Assert both default snapshot calls and absence of committed-page calls while preserving singular host, editor and route-remount assertions. No runtime, router, or authority changes.

Verify the affected integration test, exact-head hosted and discovered diagnostic comparison, and independent exact-head review. Other failures remain later serial slices.
