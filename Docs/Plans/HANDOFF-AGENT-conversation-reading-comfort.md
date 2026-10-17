# Conversation: readable replies and waiting state
Status: ACTIVE — operator's live Build dogfood feedback, PRIME implements; independent ARCHITECTURE review before merge.
Base: origin/main@448e88d9006b19cfb607d4ac5afde14d6d44d856.
Lane: codex/conversation-reading-comfort, /tmp/prime-conversation-reading-comfort.
Topology: parallel-independent of DOGFOOD Ingest source-World repair; no overlapping paths.

Outcome: compact explicit context disclosure, usable composer, honest visible waiting state, new reply positioned at its beginning while preserving older-history reading. Shared Plan/Build presentation only; no provider, graph authority, persistence or model behavior changes. Context remains collapsed by default and collapses on submit. Preserve drafts/history and fullscreen/keyboard controls. Keep next-message typing available during pending work while existing Send/dispatch guards remain unchanged. No model calls for verification.

Exclusive write set: this handoff; apps/live-control-ui/src/ui/ConversationDock.tsx and its test; src/planSurface/components/PlanConversationDockAdapter.tsx and .css; src/planSurface/components/WorldPlanAgentConversation.tsx and .css; src/planSurface/components/conversationReplyPosition.ts and its test; src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx (all src paths under apps/live-control-ui).

Verify focused dock/history/position tests, typecheck/build and rendered desktop/narrow pending+long-reply fixtures. Independently review exact cumulative head, merge under PRIME operator authority, deploy matching main5202/8000. Do not submit operator's current draft or mutate retained corpus/Graph in checks. Existing source/draft remains untouched; current accepted Build3b575220 is rollback. DOGFOOD remains Ingest.
