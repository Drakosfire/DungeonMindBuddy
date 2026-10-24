# SURFACE — continuous scrollable conversation history

ACTIVE PRIME UI slice at3550b70f5, branchcodex/conversation-continuous-history,
existing Buddy context-loop checkout. Explicit operator request: show multiple
turns in the available frame, scroll loaded conversation, paginate older history
intentionally. Broadgoal/API1709remainpaused. One UI-only PR.

Exclusive writes: shared WorldPlanAgentConversation.tsx/.css; focused world-history
and PlanPlay integration tests; this handoff. No API/schema/model changes. Keep
existing50-turn server pages and explicit top Load earlier messages; no automatic
history crawl, new text/token caps or all-history request. Render loaded ordered
conversation events directly instead of folding them behind Earlier conversation.
Keep retry grouping/local proposal order, duplicate-turn merge, cursor validation,
draft retention, lazy diagnostics and new-reply behavior. Preserve reading anchor
when prepending in both document and Play viewport hosts.

Verify visible prior/latest turns, explicit paged fetch/cursor, stable deduplicated
order, stale-page rejection, prepend anchor and proposal chronology. Independent
Bugbot, PRIME merge and protected UI5202delivery; rendered scroll/fullscreen/menu
proof without provider calls or source edits. API and user drafts stay intact.
