# Confirmed request settlement across browser tabs

ACTIVE serial PRIME slice fromb693c78b13d7b3c871d915067fa6d03b08f7a203,
branch codex/confirmed-request-settlement. User reports next-turn Send disabled
after a retry completed in another tab. History already proves the exact request
completed, but its local record was removed elsewhere; the client mistakes absence
for replacement and retains a local pending lock.

After existing exact history correlation and source/edition/scene verification,
clear local pending state when stored bytes still match OR the record is already
absent. Remove storage only for exact matching bytes. A different non-null record,
foreign/mismatched history or unreadable storage remains blocked and untouched.
Never resend or overwrite a draft. Shared Plan/Play/Build host owns this behavior.

Writes: shared WorldPlanAgentConversation history settlement; mounted integration
tests; this handoff. Exact cumulative diff, Bugbot, PRIME merge, protected UI delivery
5202, rendered drafting/recovery verification. Preserve the active user's unsaved
editor/draft and typed next question. Build World work remains draft PR1669.
