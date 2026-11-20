# Recoverable conversation Trash

Status: ACTIVE — PRIME owns design and implementation.
Topology: stacked child of PR #2106 at e19fbb90cd3f1391fe6cf49ec3f88e8c391905cf. Merge/rebase order: #2106, this slice, then lightweight transcript reads. Reuse codex/conversation-trash in the existing Buddy checkout; no new environment.

Outcome: move a saved conversation to recoverable Trash and restore it as archived. The existing APP conversation status, pointer lock/CAS and command receipt own lifecycle. Trashing the active conversation clears its pointer atomically; restoration never activates it. Keep all messages, drafts, saved documents, origin references, traces and command receipts. No permanent deletion or automatic execution of saved actions. Definite conflicts require refreshed state; uncertain retries retain command identity.

Write lease: this handoff and predecessor handoff topology settlement; agent_conversation/{types,service,library}.py; next APP migration 20261105_0114_conversation_trash.py; mounted conversation_library route and its tests; dedicated real-PostgreSQL conversation Trash tests; UI conversationLibraryApi and tests, liveApi exact credential selector/auth tests, types.ts occupied receipt union, ConversationLibrary and tests, WorldPlanAgentConversation host and worldHistory tests; owning existing CI selector lines. ADVERSARY has explicitly released APP migration ownership and keeps evaluator55447 isolated. No active schema collision found among current PR owners; primary runtime remains unchanged until merge/review/CI.

Validation: real PostgreSQL active/archived Trash, restore-as-archived, replay after later transitions, stale CAS, foreign World, retained turns/drafts/origin records; mounted authentication and exact target checks; UI explicit actions, uncertain retry, refresh, current-pointer and composer preservation; TypeScript/build/lint. Independently review exact cumulative parent-to-head diff. Protected schema upgrade and delivery only after parent and this PR gates pass; preserve existing live ingestion union and retained state.

Next slice remains lightweight transcript reads, not included here. The broader reference goal remains paused.
