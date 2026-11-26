# Conversation history cancellation fixture

ACTIVE: user requested frontend diagnostic repairs and Trace deployment. Serial branch `codex/frontend-history-cancellation-test`, based on `origin/main` at `4fd2742b9`, follows #4798. Scope: the closed-pane subscription integration test and this brief.

Observe the abort signal passed to the current lightweight-message subscription rather than the retired full-history adapter. Preserve explicit abort on close, fresh subscription on reopen, stale-result rejection and current-answer assertions. Verify the affected test, exact-SHA hosted verification, full discovered comparison and independent review.
