# SURFACE · Editable conversation drafts

Serial slice on `codex/aw-conversation-drafts`, based on `b23aaa15a`.
Authorized by the Meat Mind hill-climb goal and AW09. Use the Projects
checkout and disposable evaluator on 32787.

An explicitly requested assistant draft is editable and reopenable in its
conversation. Bind it to the producing turn, preserve the original reply
and its citations, and require the current draft revision for each edit.
Two drafts in the same conversation must retain independent edits. Scope
reads and edits through existing conversation authorization. Discussion
must leave the page proposal journal empty.

The write scope is conversation draft storage and its migration, conversation
service and routes, the existing conversation UI, and focused owner tests.
Avoid the Build intent and attachment selection paths under #3729 and #3825.
The confirmed statblock creation and Edge link depend on this slice.

Verify PA03 through ordinary turn, edit and reopen, including a stale revision
and a foreign scope. Verify PA01 produces no draft or page proposal and PA02
still honors an explicit page write. Run affected local backend and frontend
contracts on the reviewed head before delivery.

## Ordinary creation dependency

The existing captured Build requested-work menu assigns both brainstorming and
written draft requests to discuss. A separate conversation-draft selection must
retain answer_from_sources and grant only chat-draft creation. Keep the existing
menu digest and resolver available for verifying retained decisions. Pin the new
menu at dispatch and at capture validation. Create revision one in the same
transaction as verified turn completion, after checking the selected work and
the matching producing attempt. Existing discuss turns remain reply-only.

This change reaches the requested-work owner shared with #3729. Settle that scope
before changing the menu, resolver, or writer output contract. Storage and the
mounted draft read/edit endpoints are independent of that change.

The active goal places the complete draft on turn 5 and approval, linking, and
Combat admission on turn 6. Score against that sequence. Review of the exact
#3729 diff found that its hunk header names the preceding resolver function,
but the four added lines are writer guidance. Its documented scope is writer
guidance. Keep the draft selection contract separate from that prose experiment.
#3825 changes the Plan Jev driver and its mounted test.
