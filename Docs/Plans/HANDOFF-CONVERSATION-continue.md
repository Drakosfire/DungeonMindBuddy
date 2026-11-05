# Conversation history access and Continue

Status: ACTIVE — PRIME owns this serial slice.
Base: 16499be31ac1b7e40f42723a79524009e66ef0b7.
Branch: codex/conversation-continue; reuse the existing Buddy checkout.

Outcome: a visible conversation history control and an explicit Continue action
that adopts AgentConversationService.reopen_conversation. Preserve unsent
composer text, reference drafts, documents and historical turn/action records.
Preview remains read-only. Switching uses the existing idempotent ReopenCommand,
its pointer compare-and-swap and ConversationCommandReceipt. No migration,
parallel store, inference call or automatic execution of historical actions.

Expected paths: this handoff; routes/conversation_library.py; UI
api/conversationLibraryApi.ts, agentInteraction/ConversationLibrary.tsx and its
tests; planSurface/components/WorldPlanAgentConversation.tsx and its existing
worldHistory tests; tests/test_conversation_library_routes.py and existing
APP conversation tests if required; api/liveApi.ts exact credential-path selector and its existing conversationLibraryAuth tests; api/conversationLibraryApi.test.ts. CI selector additions in .github/workflows/hosted-validation.yml and world-ownership-core.yml are also leased for the owning tests; ADVERSARY explicitly confirmed no conflicting lease and granted the bounded append lease, preserving all ingestion selectors. The allowlist addition is required for the new authenticated resume caller, not a wider credential scope. Prefixes resolve under their owning apps/src.

Successors remain in scope; Trash/Restore now proceeds as a stacked child of #2106 at e19fbb90cd3f1391fe6cf49ec3f88e8c391905cf, with merge order #2106 then Trash/Restore then lightweight reads: recoverable conversation Trash/Restore, then
lightweight transcript reads with exact fidelity and measured read costs. Neither
is included in this PR. Existing #2104 stays separate. Inspect current leases
before activation; no runtime/DB mutation during implementation.

Validation: authenticated mounted resume route, exact World/target ownership,
replay and stale-pointer rejection, preview versus Continue UI behavior,
uncertain retry identity, composer/reference preservation and history refresh.
Run owning tests, inspect cumulative diff, independent Bugbot review, CI, merge
under PRIME authority and protected delivery preserving live ingestion changes.
Prove ordinary switching and reload before reporting this slice delivered.
