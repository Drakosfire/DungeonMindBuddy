# Warm Build dialogue when conversation history opens

**ACTIVE.** The hosted retrieval latency goal and the operator's pane-open
direction authorize this serial slice. Base
`afb5897746240ae046e93fa90fbe6822ec535b77`, branch
`codex/jev-build-dialogue-warmup`, managed Projects checkout
`jev-build-dialogue-warmup/DungeonMindBuddy`.

Write set: this handoff, `apps/live_control_server/routes/conversation_library.py`,
and `tests/test_conversation_library_routes.py`. Reuse the deployed validated
dialogue cache and the existing authenticated active-message route. One
opportunistic warmup per process can read the newest six dialogue slots after
an eligible response is sent. Check the pointer before warming. Send continues
through its own current-context and durability checks. No new service, port,
schema, provider traffic, or primary writes are needed to qualify the change.

Verify route scope, response parity, stale active pointer, and warmup
deduplication. Run the owning local contract at the exact head and obtain
independent review. Measure new hosted pane and first-wire timings separately
for cold entry, immediate Send, and Send after an ordinary typing delay.
