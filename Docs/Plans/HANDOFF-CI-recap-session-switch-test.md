# Recap session switch test

ACTIVE: user requested frontend diagnostic repairs and Trace deployment. Serial branch `codex/frontend-recap-selection-test` based on `origin/main` at `bec150f03`, following #4800. Scope: the PR380B campaign-switch test and this brief. The older draft #3259 touches a different test in the same file; it was last updated November 13 and has no active lease in the current plans.

Changing campaign updates the session selector before the asynchronous Load button is available. Wait for that button before clicking. Preserve checks for no premature read, the exact selected World/campaign/session, rejection of the previous campaign's session, and URL state. Verify the affected file, exact-SHA hosted and independent review. The next integrated discovered checkpoint covers this and the preceding session-evidence slice; inherited failures remain red.
