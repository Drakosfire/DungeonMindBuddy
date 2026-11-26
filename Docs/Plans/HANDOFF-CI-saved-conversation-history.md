# Saved Build conversation history checks

ACTIVE: user requested diagnostic repairs and Trace deployment. Serial slice `codex/frontend-conversation-history-tests`, based on `origin/main` at `b75d1e9f9`, follows merged #4790. Scope: the ordinary saved Build conversation-history integration cases and this brief.

Saved transcript messages now load separately from exact reply details; exercise Trace to fetch and validate full receipts before asserting exact Graph and saved-source controls. Preserve invalid-receipt rejection, no source reads for invalid evidence, fresh-reply validation, and exact source assertions. Verify the affected cases, exact-head hosted verification, full discovered comparison, and independent review. Other retry and recovery cases are outside this slice.
