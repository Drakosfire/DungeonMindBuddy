# DOGFOOD: expose saved lore review in compact chat

ACTIVE under Alan's actual-app completion instruction; owner DOGFOOD.
Topology revised to a stack so the runtime source checkout remains immutable
while its owning backend contract runs. Parent #4445 at exact c7f4dacd16c9800584d02b9cc2fb05e14311ac0c;
merge order #4445, then this UI slice. #4445 is now merged into the dedicated
release base as b65603b447fa1335c436c28a097eb65ecf8506fd; this slice targets that
base and the runtime/source tree remains the reviewed c7f4 parent. Base branch initially
codex/dogfood-onboarding-context-page; retarget only after its dedicated release
merge. No source from unrelated main/COMBAT work is adopted.

Isolated checkout: dogfood-lore-review/DungeonMindBuddy, branch
codex/dogfood-compact-lore-review. Expected writes: library.py compact reply
projection, conversationLibraryApi.ts descriptor decoder, ConversationLibrary.tsx
label, WorldPlanAgentConversation.tsx existing exact-review loader condition,
their owning existing decoder/integration tests, the ordinary Build compact
projection regression, and these two DOGFOOD handoffs. COMBAT confirmed no
exclusive lease on WorldPlanAgentConversation; #4441 owns only its statblock
module/test/handoff. This slice does not touch that lease.

The existing saved-page descriptor must identify a lore review without supplying
save authority. Clicking Review new page loads the exact saved Turn through the
existing pointer/generation/World/page guards, then mounts the existing digest-
bound review/confirm UI. Build is marked read-only for Plan edits; that flag
must not suppress its own standalone lore save control. Require Build and no
Play mode for lore review/follow-up, preserving actual Plan edit protections. Do not automatically fetch full execution while a turn
runs, add direct saves to compact summaries, or invent a new persisted DTO.
Reject foreign World/conversation/turn/page, Plan-surface lore, noncompleted and
unapproved mixed records. Preserve the unsent composer and saved reply on errors.

Verify backend lightweight projection without execution decode, frontend scoped
decoder, compact chat -> exact load -> existing review/save controls, async error
and stale-scope behavior. Exact-head hosted and integrated discovered diagnostics,
independent cumulative review, compatible188recovery and deployed browser
save/reopen/no-retrieval acceptance remain required. This PR alone is not goal
completion.
