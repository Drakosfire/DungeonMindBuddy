# BUILD · Resolve a save follow-up to an existing lore review

Status ACTIVE. The AW10 goal authorizes this bounded successor. Stack
codex/aw10-lore-save-followup on #4050's reviewed head
6ee635374c0b543ce30639ee0845ab2182770400. Merge #4050 first, then reconcile
this branch onto the resulting main before delivery. The parent remains
frozen. Use the separate Projects checkout and AW10 evaluator on 32787.

The ordinary “Create the page” turn currently requests a fresh title and
fails on an already populated draft. Bind the follow-up to the original
review's turn and digest in the verified active Build conversation. It must
remain a reference and never record review acknowledgement or save from
the chat message. Preserve the existing explicit review and confirm actions.

Write set is the APP lore review and conversation owner, its local-result
storage constraint, ordinary Build turn
dispatch and response projection, the existing lore confirmation UI, mounted
owner tests and this handoff. Verify same-page selection, interrupted retry,
topic switch and inactive or superseded states. Exercise exact receipt retry,
exact original citation reopening and zero pre-confirm mutations. Keep Gold
local and primary data unchanged.
