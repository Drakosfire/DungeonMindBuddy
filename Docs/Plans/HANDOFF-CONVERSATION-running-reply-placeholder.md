# CONVERSATION: one running activity presentation

ACTIVE PRIME serial UI-only slice based on185e07be2557825a8fd7b14477cbe2d819972ad1,
branch codex/conversation-running-placeholder, existing context-loop checkout/deps.
No unmerged parent. Operator dogfood identified “Waiting for this reply…” blinking
as Buddy speech beside the desired gold activity status. No new runtime/state owner.

The lightweight history renderer invents an assistant bubble for a running row
without an answer; the full renderer does not. Switching between those views
therefore adds/removes placeholder speech while the exact-turn activity owner
continues. Match the full renderer: no assistant speech until actual output or a
terminal outcome exists. Keep gold activity, full timeline, user message, Details,
completed answers, interrupted/failed notice and native retry controls.

Exclusive writes: this handoff; UI src/planSurface/components/
WorldPlanAgentConversation.tsx (lightweight pending presentation only) and
planSurface/WorldPlanAgentConversation.worldHistory.test.tsx (owning regression).
Current Surface2330/2326/2313/2262, Storage2308 and CI2288/2298 do not own these
paths (CI integration tests are separate). Prior Plan/history lease is adopted by
PRIME for this slice. No API/provider/model/storage/dependency or CI changes.
Coordination off;2104 remains held. No primary story writes or provider tests.

First reproduce placeholder/empty-bubble assertions in the existing delayed-read
activity case; then prove it absent through history refresh while exact gold
activity and one dispatch remain. Verify terminal completed/failed states and
recovery controls remain. Run focused owning tests, exact-head hosted/build and
full discovered comparison against identical parent UI tree, independent review,
small PR and UI-only delivery. Keep inherited diagnostic failures red and browser
verification limits explicit. No fresh ingestion or source/corpus edits.
