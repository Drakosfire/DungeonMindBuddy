# Trace activity diagnostic repair

ACTIVE: user requested repairing the frontend diagnostic. Serial first slice on `codex/frontend-conversation-diagnostic`, rebased on inventory prerequisite #4767 (`ab044995afd5496e977a57548eaef20c29d6ee90`). Scope: `BuddyActivity.test.tsx` and this brief only. Later suites require separate scoped repairs and are not declared complete here.

The inherited failures assume a direct CSS ancestry and a unique text label, but the existing renderer now wraps the legacy timeline and the reply shell also has a tab named Execution timeline. Select its summary and accessible recorded-activity list without weakening event counts, labels, loading, or no-prompt assertions. No production or provider behavior changes.

Verify the full affected test file, exact-head hosted verification, full discovered diagnostic and exact-base failure comparison. Obtain independent exact-head review before merge. Do not alter or delete unrelated failing tests.
