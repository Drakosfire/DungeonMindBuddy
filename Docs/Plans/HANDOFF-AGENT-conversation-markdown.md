# Conversation Markdown presentation

Status: ACTIVE — operator requests Markdown in conversation. PRIME implements;
ARCHITECTURE independently reviews. Serial PR from remote main309d240e.
Checkout /tmp/prime-recap-mention-boundaries; branch codex/conversation-markdown.

Render the complete answer with the existing shared Markdown AST parser, without
applying the editable document import subset or splitting syntax at evidence
segment boundaries. Tables, headings, emphasis, lists, quotes and code should read
naturally. Preserve exact stored answers and evidence receipts. Escape raw HTML;
never load model-provided embedded media or activate unsafe URLs. Existing Graph
reference labels remain inert. No provider, persistence or editor admission change.

Exclusive writes: this handoff; apps/live-control-ui/src/planSurface/components/
WorldPlanAgentAnswer.tsx, WorldPlanAgentAnswer.test.tsx and
WorldPlanAgentAnswer.css. No Ingest, Harness capability or runtime API changes.

Verify mixed Markdown including aligned tables and segmented table/code syntax,
unsafe HTML/URLs, and existing Build proposal rendering. Typecheck/build, cumulative
diff, independent review, commit/push/PR. Deploy reviewed compiled UI to5202,
preserving operator drafts; API and5876 remain unchanged. Operator acceptance open.
