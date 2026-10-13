# DOGFOOD: Plan conversation reset in the header

Status: ACTIVE. The operator explicitly requested a simple new-conversation plus symbol in the chat header and asked whether that control had shipped. Current `main` at `ed2472886d208ca90fc82875d1dea185594125d1` still places the text button inside Conversation options. This UI slice moves the existing action without changing reset semantics.

Branch `codex/dogfood-plan-new-chat-icon` uses an isolated checkout. Serial PR against `main`; merge remains separate authority. Current open PRs were inspected; none owns this Plan conversation header. No live 5202 runtime, port, database, browser storage, or provider state is owned by this lane.

Exclusive write set:

- `apps/live-control-ui/src/planSurface/components/PlanConversationDockAdapter.tsx`
- `apps/live-control-ui/src/planSurface/components/PlanConversationDockAdapter.css`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx`
- This handoff

Invariant: On the saved Plan dock, one accessible `New conversation` icon appears in the conversation header. It invokes the existing guarded reset action and keeps its disabled reason; Settings and advanced controls remain in Conversation options. No duplicate reset button appears in that menu. Other surfaces retain their current presentation.

Failure cases: a disconnected presentation host must not duplicate the action, a disabled reset must stay disabled and explain why, and the menu must remain operable with the icon outside it. Verify at the mounted Plan page and conversation component boundaries, typecheck, and cumulative diff.

Verification: the focused mounted Plan header/settings test passes; the World Plan conversation suite passes all 197 tests; TypeScript typecheck passes. The combined Plan page and conversation run has 264 passes and two inherited Plan save-state failures. Both failures reproduce unchanged on `main@ed247288` in a disposable baseline checkout: `keeps Ask disabled for an unresolved pending write` and `does not send the prepared revision while its Plan save is still committing`. The icon branch adds no save-state code.
